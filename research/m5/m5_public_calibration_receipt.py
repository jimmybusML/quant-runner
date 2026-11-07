#!/usr/bin/env python3
"""Publish an allowlisted aggregate view of a private M5 calibration run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


VARIANTS = ("raw_holdout", "calibrated_holdout",
            "score_grid_logloss_calibrated_holdout",
            "shrunk_league_calibrated_holdout")
METRICS = ("unique_fixtures", "simulated_bets", "settled_bets", "pending_bets",
           "settlement_counts", "net_units", "total_stake_units", "roi_pct",
           "max_drawdown_units_by_quote_event_time", "roi_bootstrap_95pct",
           "settlement_log_loss", "settlement_brier", "source_fixture_markets")


def build_receipt(source: dict) -> dict:
    if source.get("protocol") != "M5_CROWN_FIRST_TOTALCORNER_GOAL_RATE_TEMPORAL_HOLDOUT_V1":
        raise ValueError("unexpected private calibration report protocol")
    if source.get("calibration_training_scope") != "all_prior_oos_forecasts":
        raise ValueError("report must use all prior OOS forecasts for calibration training")
    markets = {}
    for market in ("AH", "OU"):
        row = source["markets"][market]
        if row.get("training_fixture_ids_disjoint_from_holdout") is not True:
            raise ValueError(f"{market} calibration training overlaps holdout")
        variants = {}
        for name in VARIANTS:
            result = row[name]
            variants[name] = {key: result[key] for key in METRICS}
            variants[name]["roi_target_3pct_reached"] = result["roi_pct"] >= 3
        markets[market] = {
            "calibration_training_scope": source["calibration_training_scope"],
            "training_unique_fixtures": row["training_unique_fixtures"],
            "training_kickoff_range_utc": row["training_kickoff_range_utc"],
            "holdout_unique_fixture_markets": row["holdout_unique_fixture_markets"],
            "holdout_kickoff_range_utc": row["holdout_kickoff_range_utc"],
            "training_fixture_ids_disjoint_from_holdout": True,
            "training_quotes_used_for_calibration": 0,
            "holdout_source_fixture_markets": row["holdout_source_fixture_markets"],
            "timing": row["timing"],
            "variants": variants,
        }
    return {
        "protocol": "M5_SOURCE_UNION_ALL_PRIOR_OOS_CALIBRATION_HOLDOUT_V1",
        "generated_utc": source["generated_utc"],
        "holdout_start_utc": source["holdout_start_utc"],
        "calibration_training_scope": source["calibration_training_scope"],
        "candidate_fixtures": source["candidate_fixtures"],
        "forecast_rows": source["forecast_rows"],
        "input_hashes": source["input_hashes"],
        "markets": markets,
        "roi_definition": "net_units / total_stake_units * 100; one 1U wager per unique fixture-market",
        "timing_limitations": source["limits"],
        "strategy_definition": source["strategy_definition"],
        "production_or_telegram_changes": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_receipt(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                      indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "market_roi_pct": {m: {k: v["roi_pct"] for k, v in x["variants"].items()}
                                         for m, x in report["markets"].items()},
                      "output": str(args.output)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
