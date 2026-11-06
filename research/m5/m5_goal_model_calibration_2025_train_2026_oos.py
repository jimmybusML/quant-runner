#!/usr/bin/env python3
"""Fit M5 score-grid calibration on 2025 outcomes and emit 2026 OOS variants.

All calibration fitting is based on earlier-year OOS forecasts and actual FT
scores, never market ROI. 2026 forecasts remain M5-only and fixture-level
outputs are written outside the public repository.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from research.m5.crown_historical_capture import atomic_write, ensure_private_destination
from research.m5.m5_source_union_goal_rate_temporal_holdout import (
    fit_rate_factors, fit_score_grid_logloss_factors, fit_shrunk_league_factors, tilt_grid,
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path: Path) -> dict[str, dict]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            mid = str(row["match_id"])
            if mid in result:
                raise ValueError("duplicate fixture ID in forecast file")
            result[mid] = row
        except (KeyError, json.JSONDecodeError):
            continue
    return result


def fit_rows(rows):
    return [{"match_id": r["match_id"], "league": r["league"],
             "actual": (int(r["home_goals"]), int(r["away_goals"])),
             "grid": r["prediction"]["grid"]} for r in rows]


def add_probs(grid):
    n, m = len(grid), len(grid[0])
    home = sum(grid[h][a] for h in range(n) for a in range(m) if h > a)
    draw = sum(grid[i][i] for i in range(min(n, m)))
    away = max(0.0, 1.0 - home - draw)
    over = sum(grid[h][a] for h in range(n) for a in range(m) if h + a > 2.5)
    return {"grid": grid, "p_home": home, "p_draw": draw, "p_away": away, "p_over_2_5": over}


def run(private_dir: Path, output_dir: Path, public_report: Path) -> dict:
    root = ensure_private_destination(private_dir)
    forecast_path = root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    raw = forecast_path.read_bytes()
    forecasts = read_jsonl(forecast_path)
    train = [r for r in forecasts.values() if str(r.get("kickoff", "")).startswith("2025-")]
    target = [r for r in forecasts.values() if str(r.get("kickoff", "")).startswith("2026-")]
    if not train or not target:
        raise ValueError("expected non-empty 2025 train and 2026 OOS rows")
    for row in train + target:
        cutoff = row.get("prediction_asof_utc")
        train_end = row.get("train_end_utc")
        kickoff = row.get("kickoff")
        if not (train_end and cutoff and kickoff and train_end < cutoff < kickoff):
            raise ValueError("forecast chronology is invalid")
        grid = row.get("prediction", {}).get("grid")
        if not isinstance(grid, list):
            raise ValueError("score grid missing")
    train_ids = {r["match_id"] for r in train}
    target_ids = {r["match_id"] for r in target}
    if train_ids & target_ids:
        raise ValueError("2025 and 2026 fixture IDs overlap")

    training_rows = fit_rows(train)
    global_rate = fit_rate_factors(training_rows)
    scoregrid_fit = fit_score_grid_logloss_factors(training_rows)
    league_factors, league_fit = fit_shrunk_league_factors(training_rows, shrinkage_fixtures=100)
    variants = {
        "global_rate": (global_rate["home_rate_multiplier"], global_rate["away_rate_multiplier"]),
        "scoregrid_logloss": (scoregrid_fit["home_rate_multiplier"], scoregrid_fit["away_rate_multiplier"]),
    }
    output_dir = ensure_private_destination(output_dir)
    variant_hashes = {}
    output_counts = {}
    for variant, factors in variants.items():
        rows = []
        for source in sorted(target, key=lambda r: (r["kickoff"], r["match_id"])):
            prediction = dict(source["prediction"])
            grid = tilt_grid(source["prediction"]["grid"], *factors)
            rows.append({**source, "model": f"M5_baseline_2026_{variant}", "prediction": add_probs(grid)})
        encoded = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode()
        path = output_dir / f"m5_goal_model_2026_calibrated_{variant}.jsonl"
        atomic_write(path, encoded)
        variant_hashes[variant] = sha(encoded)
        output_counts[variant] = len(rows)
    rows = []
    for source in sorted(target, key=lambda r: (r["kickoff"], r["match_id"])):
        factors = league_factors.get(source["league"], league_factors["__global__"])
        grid = tilt_grid(source["prediction"]["grid"], *factors)
        rows.append({**source, "model": "M5_baseline_2026_shrunk_league", "prediction": add_probs(grid)})
    encoded = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode()
    path = output_dir / "m5_goal_model_2026_calibrated_shrunk_league.jsonl"
    atomic_write(path, encoded)
    variant_hashes["shrunk_league"] = sha(encoded)
    output_counts["shrunk_league"] = len(rows)

    report = {"protocol": "M5_2025_TRAIN_2026_OOS_SCOREGRID_CALIBRATION_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "baseline_forecast_sha256": sha(raw), "calibrated_forecast_sha256": variant_hashes,
        "training_year": 2025, "training_unique_fixtures": len(train),
        "target_year": 2026, "target_unique_fixtures": len(target),
        "training_target_fixture_ids_disjoint": not bool(train_ids & target_ids),
        "all_forecast_chronology_passed": True,
        "fitted_parameters": {"global_rate": global_rate, "scoregrid_logloss": scoregrid_fit,
                               "fixed_100_fixture_league_shrinkage": league_fit},
        "fit_objective": "prior-year actual-goal likelihood or exact-score negative log likelihood; no ROI, holdout outcome, or market variable used to fit parameters",
        "target_rule": "Apply fixed 2025-trained calibration to every 2026 M5 baseline forecast; no target-date/league/price filters.",
        "target_rows_written_by_variant": output_counts,
        "crown_roi": None, "source_event_quote_roi": None,
        "private_fixture_forecasts_remain_outside_public_repository": True}
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-report", type=Path, required=True)
    args=parser.parse_args()
    report=run(args.private_dir,args.private_output_dir,args.public_report)
    print(json.dumps({k:report[k] for k in ("generated_utc","training_unique_fixtures","target_unique_fixtures","fitted_parameters","target_rows_written_by_variant")},sort_keys=True))

if __name__ == "__main__": main()
