#!/usr/bin/env python3
"""Strict UTC year-forward M5 score grids from penaltyblog Bivariate Poisson.

Fits separately within the frozen M5 league scope using only prior UTC-year
matches. Fixture-level predictions stay private; the script writes only a
sanitized proper-score receipt to the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
from penaltyblog.models import BivariatePoissonGoalModel

from research.m5.m5_goal_model_oos import read_manifest, score_report
from research.m5.crown_historical_capture import atomic_write, ensure_private_destination


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_grid(prediction) -> list[list[float]]:
    matrix = prediction.grid.tolist() if hasattr(prediction.grid, "tolist") else prediction.grid
    grid = [[float(value) for value in row] for row in matrix]
    if not grid or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("model returned an empty or ragged score grid")
    if any(not np.isfinite(value) or value < 0 for row in grid for value in row):
        raise ValueError("model returned an invalid probability")
    mass = sum(sum(row) for row in grid)
    if abs(mass - 1.0) > 1e-8:
        raise ValueError(f"normalized grid mass is {mass}")
    return grid


def run(private_dir: Path, private_output: Path, public_report: Path,
        years: tuple[int, ...] = (2025, 2026), limit_leagues: int | None = None) -> dict:
    root = ensure_private_destination(private_dir)
    manifest_raw, fixtures = read_manifest(root / "candidate-manifest.json")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in fixtures:
        grouped[row["league"]].append(row)
    league_names = sorted(grouped)
    if limit_leagues is not None:
        league_names = league_names[:limit_leagues]
    out_rows, fold_receipts, failures = [], [], Counter()
    league_counts: dict[str, Counter] = defaultdict(Counter)
    for league in league_names:
        matches = grouped[league]
        for year in years:
            cutoff = datetime(year, 1, 1, tzinfo=timezone.utc)
            train = [r for r in matches if r["kickoff"] < cutoff]
            target = [r for r in matches if r["kickoff"].year == year]
            if not target:
                continue
            if not train:
                failures["no_prior_training_rows"] += len(target)
                continue
            train_end = max(r["kickoff"] for r in train)
            if not train_end < cutoff:
                raise AssertionError("training data reaches the first target UTC date")
            try:
                model = BivariatePoissonGoalModel(
                    [r["home_goals"] for r in train], [r["away_goals"] for r in train],
                    [r["home"] for r in train], [r["away"] for r in train],
                )
                model.fit()
                known = set(model.teams)
            except Exception as exc:
                failures[f"fit_{type(exc).__name__}"] += len(target)
                fold_receipts.append({"league": league, "target_utc_year": year,
                    "status": "fit_failed", "training_matches": len(train),
                    "training_end_utc": utc_text(train_end), "error_type": type(exc).__name__})
                continue
            used, unseen = 0, 0
            for fixture in target:
                if fixture["home"] not in known or fixture["away"] not in known:
                    unseen += 1
                    failures["unseen_team"] += 1
                    continue
                try:
                    grid = serialize_grid(model.predict(fixture["home"], fixture["away"], max_goals=15, normalize=True))
                    p_home = sum(grid[h][a] for h in range(len(grid)) for a in range(len(grid[h])) if h > a)
                    p_draw = sum(grid[i][i] for i in range(min(len(grid), len(grid[0]))))
                    p_away = max(0.0, 1.0 - p_home - p_draw)
                    p_over = sum(grid[h][a] for h in range(len(grid)) for a in range(len(grid[h])) if h + a > 2.5)
                    out_rows.append({"match_id": fixture["match_id"], "league": league,
                        "home": fixture["home"], "away": fixture["away"],
                        "kickoff": utc_text(fixture["kickoff"]),
                        "home_goals": fixture["home_goals"], "away_goals": fixture["away_goals"],
                        "prediction_asof_utc": utc_text(cutoff), "train_end_utc": utc_text(train_end),
                        "training_fixtures": len(train), "model": "penaltyblog_bivariate_poisson",
                        "prediction": {"grid": grid, "p_home": p_home, "p_draw": p_draw,
                                       "p_away": p_away, "p_over_2_5": p_over}})
                    used += 1
                except Exception as exc:
                    failures[f"predict_{type(exc).__name__}"] += 1
            league_counts[league][str(year)] += used
            fold_receipts.append({"league": league, "target_utc_year": year,
                "status": "predicted", "training_matches": len(train), "training_end_utc": utc_text(train_end),
                "forecast_asof_utc": utc_text(cutoff), "target_matches": len(target),
                "predicted_matches": used, "unseen_team_matches": unseen,
                "training_ids_disjoint_from_target": not bool({r["match_id"] for r in train} & {r["match_id"] for r in target})})
    out_rows.sort(key=lambda r: (r["kickoff"], r["match_id"]))
    encoded = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for r in out_rows).encode()
    private_output = private_output.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if private_output == repo or repo in private_output.parents:
        raise ValueError("fixture-level forecasts must remain private")
    atomic_write(private_output, encoded)
    scored = [{"home_goals": r["home_goals"], "away_goals": r["away_goals"], "prediction": r["prediction"]} for r in out_rows]
    report = {"protocol": "M5_PENALTYBLOG_BIVARIATE_POISSON_UTC_YEAR_FORWARD_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "penaltyblog_version": version("penaltyblog"),
        "candidate_manifest_sha256": sha(manifest_raw), "private_forecast_sha256": sha(encoded),
        "target_utc_years": list(years), "league_count_in_scope": len(league_names),
        "training_rule": "For each league and target UTC year, train on every earlier kickoff in that league; predict only target-year fixtures. Train cutoff < January 1 UTC; no same-year match outcomes enter fitting.",
        "model": "penaltyblog BivariatePoissonGoalModel; fixed default fit; no ROI or target-year score used for model or parameter selection.",
        "forecast_count": len(out_rows), "forecast_coverage_by_year": {
            str(y): sum(1 for r in out_rows if r["kickoff"].startswith(str(y))) for y in years},
        "unique_forecast_fixtures": len({r["match_id"] for r in out_rows}),
        "time_order_passed": all(r["train_end_utc"] < r["prediction_asof_utc"] < r["kickoff"] for r in out_rows),
        "id_split_passed": all(x.get("training_ids_disjoint_from_target") is True for x in fold_receipts if x.get("status") == "predicted"),
        "proper_scores": score_report(scored), "failure_counts": dict(failures),
        "fold_count": len(fold_receipts), "fold_status_counts": dict(Counter(x["status"] for x in fold_receipts)),
        "scope_note": "M5-only public aggregate. Per-fixture predictions and identifiers remain in the protected private archive; no M1/MR1/M3 forecasts, ledgers, orders, or production routes are consumed.",
        "crown_roi": None, "quote_source": None}
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-report", type=Path, required=True)
    parser.add_argument("--years", default="2025,2026")
    parser.add_argument("--limit-leagues", type=int)
    args = parser.parse_args()
    years = tuple(int(x) for x in args.years.split(",") if x.strip())
    report = run(args.private_dir, args.private_output, args.public_report, years, args.limit_leagues)
    print(json.dumps({k: report[k] for k in ("generated_utc", "penaltyblog_version", "forecast_count", "forecast_coverage_by_year", "proper_scores", "failure_counts", "fold_status_counts")}, sort_keys=True))


if __name__ == "__main__":
    main()
