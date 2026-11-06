#!/usr/bin/env python3
"""Same-quote 2026 holdout comparison of the M3 selector and M5 goal models."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m5_penaltyblog_prior_year_selector import (
    MARKETS, MODELS, make_bet, select_model, summarize,
)


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def load_m5_for_targets(path: Path, targets: dict[str, dict], model_name: str):
    found = {}
    chronology_errors = 0
    identity_errors = 0
    duplicates = 0
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                row = json.loads(line)
                mid = str(row["match_id"])
                if mid not in targets or int(row.get("year", 0)) != 2026:
                    continue
                if mid in found:
                    duplicates += 1
                    continue
                target = targets[mid]
                if (row.get("league"), row.get("home"), row.get("away"), row.get("kickoff"),
                    int(row.get("home_goals")), int(row.get("away_goals"))) != (
                    target["league"], target["home"], target["away"], target["kickoff_utc"],
                    target["actual_home_goals"], target["actual_away_goals"]):
                    identity_errors += 1
                    continue
                train_end, asof, kickoff = instant(row.get("train_end_utc")), instant(row.get("prediction_asof_utc")), instant(row.get("kickoff"))
                if not train_end or not asof or not kickoff or not train_end < asof < kickoff:
                    chronology_errors += 1
                    continue
                grid = row.get("prediction", {}).get("grid")
                if not isinstance(grid, list) or not grid or not grid[0]:
                    continue
                mass = math.fsum(float(x) for grid_row in grid for x in grid_row)
                if abs(mass - 1.0) > 1e-7 or any(not math.isfinite(float(x)) or float(x) < 0 for grid_row in grid for x in grid_row):
                    continue
                found[mid] = {"grid": grid, "train_end_utc": row["train_end_utc"],
                              "prediction_asof_utc": row["prediction_asof_utc"]}
            except (ValueError, TypeError, KeyError):
                continue
    if duplicates:
        raise ValueError(f"duplicate {model_name} forecasts for target fixture identities: {duplicates}")
    return found, {"identity_errors": identity_errors, "chronology_errors": chronology_errors}


def run(private_predictions: Path, m5_baseline: Path, m5_recency: Path,
        selector_report: Path, output: Path):
    cache = {}
    training_scores = {market: defaultdict(lambda: {model: [] for model in MODELS}) for market in MARKETS}
    global_scores = {market: {model: [] for model in MODELS} for market in MARKETS}
    targets = {}
    holdout_fixtures = []
    with private_predictions.open("r", encoding="utf-8") as stream:
        for line in stream:
            fixture = json.loads(line)
            year = int(fixture["kickoff_utc"][:4])
            if year == 2025:
                for market in MARKETS:
                    for model in MODELS:
                        bet = make_bet(fixture, market, model, cache)
                        training_scores[market][fixture["league"]][model].append(bet["log_loss"])
                        global_scores[market][model].append(bet["log_loss"])
            elif year == 2026:
                targets[str(fixture["match_id"])] = fixture
                holdout_fixtures.append(fixture)
    baseline, baseline_audit = load_m5_for_targets(m5_baseline, targets, "M5 baseline")
    recency, recency_audit = load_m5_for_targets(m5_recency, targets, "M5 recency")
    common_ids = set(targets) & set(baseline) & set(recency)
    if len(common_ids) != len(targets):
        raise ValueError(f"M5 forecasts do not cover the complete common M3 holdout: {len(common_ids)}/{len(targets)}")

    output_markets = {}
    for market in MARKETS:
        global_model = select_model({}, global_scores[market])
        selection = {league: select_model(scores, global_scores[market])
                     for league, scores in training_scores[market].items()}
        selected_rows = []
        fixed_rows = {model: [] for model in MODELS}
        baseline_rows, recency_rows = [], []
        for fixture in holdout_fixtures:
            mid, league = str(fixture["match_id"]), fixture["league"]
            picked = selection.get(league, global_model)
            selected_rows.append(make_bet(fixture, market, picked, cache))
            for model in MODELS:
                fixed_rows[model].append(make_bet(fixture, market, model, cache))
            for name, source, dest in (("m5_baseline", baseline, baseline_rows), ("m5_recency", recency, recency_rows)):
                pred_asof = instant(source[mid]["prediction_asof_utc"])
                train_end = instant(source[mid]["train_end_utc"])
                kickoff = instant(fixture["kickoff_utc"])
                if not train_end < pred_asof < kickoff:
                    raise ValueError(f"invalid {name} training/as-of chronology")
                for quote in fixture["quotes"].values():
                    if not pred_asof <= instant(quote["event_utc"]) < kickoff:
                        raise ValueError(f"{name} forecast was not available before the selected source event")
                replacement = {**fixture, "model_score_grids": {name: source[mid]["grid"]}}
                dest.append(make_bet(replacement, market, name, cache))
        output_markets[market] = {
            "selection_training_2025_fixtures": len(next(iter(global_scores[market].values()))),
            "common_2026_holdout_fixtures": len(holdout_fixtures),
            "same_source_quote_comparison": True,
            "quote_source_fixture_markets": dict(Counter(
                q["source"] for fixture in holdout_fixtures for mk, q in fixture["quotes"].items() if mk == market)),
            "model_results": {
                "m3_2025_per_league_logloss_selector": summarize(selected_rows),
                "m3_fixed_models": {model: summarize(rows) for model, rows in fixed_rows.items()},
                "m5_baseline": summarize(baseline_rows),
                "m5_recency": summarize(recency_rows),
            },
            "selection_model_fixture_counts": dict(Counter(selection.get(x["league"], global_model) for x in holdout_fixtures)),
            "global_fallback_model": global_model,
        }

    report = {
        "protocol": "M5_M3_SELECTOR_VS_M5_SAME_QUOTE_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "private_m3_forecasts_sha256": sha_file(private_predictions),
        "m5_baseline_forecasts_sha256": sha_file(m5_baseline),
        "m5_recency_forecasts_sha256": sha_file(m5_recency),
        "selector_report_sha256": hashlib.sha256(selector_report.read_bytes()).hexdigest(),
        "common_2026_holdout_fixtures": len(holdout_fixtures),
        "market_results": output_markets,
        "m5_prediction_identity_audit": {"baseline": baseline_audit, "recency": recency_audit,
                                         "common_coverage_equals_m3_holdout": len(common_ids) == len(targets)},
        "time_order_passed": all(
            instant(source[mid]["train_end_utc"]) < instant(source[mid]["prediction_asof_utc"]) < instant(targets[mid]["kickoff_utc"])
            for source in (baseline, recency) for mid in common_ids),
        "all_quote_receipts_post_kickoff": all(not quote["receipt_before_kickoff"]
            for fixture in holdout_fixtures for quote in fixture["quotes"].values()),
        "method": "M3 selector was chosen using only 2025 OOS Log Loss by league. M3, M5 baseline, and M5 recency forecast grids were replayed against the exact same source quote, line, odds, and 2026 FT. Every available fixture remained; one side was selected by higher expected return with no threshold.",
        "limitations": ["The 2026 holdout contains 9,400 fixture-markets per market, below the 10,000 acceptance sample.",
                        "All historic API responses were retrieved after kickoff, so the ROI is retrospective event-time replay.",
                        "No M1/MR1 production output, order, ledger, or model parameters are consumed."],
        "production_changes": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-predictions", type=Path, required=True)
    parser.add_argument("--m5-baseline", type=Path, required=True)
    parser.add_argument("--m5-recency", type=Path, required=True)
    parser.add_argument("--selector-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_predictions, args.m5_baseline, args.m5_recency, args.selector_report, args.output)
    print(json.dumps({market: {name: result["roi_pct"] for name, result in data["model_results"].items()
                               if name != "m3_fixed_models"}
                      | {"m3_fixed_models": {model: result["roi_pct"] for model, result in data["model_results"]["m3_fixed_models"].items()}}
                      for market, data in report["market_results"].items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
