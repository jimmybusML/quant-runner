from __future__ import annotations

import pytest

from research.m5.m5_public_calibration_receipt import build_receipt


def private_report():
    variants = {
        name: {"unique_fixtures": 12, "simulated_bets": 12,
               "settled_bets": 12, "pending_bets": 0,
               "settlement_counts": {"win": 5, "half_win": 1, "push": 1,
                                     "half_loss": 1, "loss": 4},
               "net_units": -1.0, "total_stake_units": 12,
               "roi_pct": -8.333, "max_drawdown_units_by_quote_event_time": 3.0,
               "roi_bootstrap_95pct": {"lower_95": -20, "upper_95": 3},
               "settlement_log_loss": 1.1, "settlement_brier": .6,
               "source_fixture_markets": {"Crown": 10, "TotalCorner_default": 2}}
        for name in ("raw_holdout", "calibrated_holdout",
                     "score_grid_logloss_calibrated_holdout",
                     "shrunk_league_calibrated_holdout")
    }
    market = {"training_unique_fixtures": 100, "training_unique_fixture_markets": 100,
              "training_kickoff_range_utc": ["2020-01-01T00:00:00Z", "2024-12-31T00:00:00Z"],
              "holdout_unique_fixture_markets": 12,
              "holdout_kickoff_range_utc": ["2025-01-01T00:00:00Z", "2025-12-31T00:00:00Z"],
              "training_fixture_ids_disjoint_from_holdout": True,
              "holdout_source_fixture_markets": {"Crown": 10, "TotalCorner_default": 2},
              "timing": {"all_api_receipts_after_kickoff": True,
                         "holdout_quote_event_between_prediction_asof_and_kickoff": True,
                         "holdout_receipts_before_kickoff": 0},
              **variants}
    return {"protocol": "M5_CROWN_FIRST_TOTALCORNER_GOAL_RATE_TEMPORAL_HOLDOUT_V1",
            "generated_utc": "2026-11-07T00:00:00Z",
            "holdout_start_utc": "2025-01-01T00:00:00Z",
            "calibration_training_scope": "all_prior_oos_forecasts",
            "candidate_fixtures": 1000, "forecast_rows": 1000,
            "input_hashes": {"candidate_manifest_sha256": "a" * 64},
            "markets": {"AH": market, "OU": market},
            "limits": ["receipt timing is retrospective"],
            "strategy_definition": "one bet per fixture-market"}


def test_public_calibration_receipt_allowlists_only_aggregate_fields():
    report = build_receipt(private_report())
    assert report["markets"]["AH"]["training_unique_fixtures"] == 100
    assert report["markets"]["AH"]["variants"]["raw_holdout"]["roi_target_3pct_reached"] is False
    assert "training_quotes_used_for_calibration" in report["markets"]["OU"]
    assert report["production_or_telegram_changes"] is False


def test_public_calibration_receipt_rejects_overlap_and_wrong_training_scope():
    value = private_report()
    value["markets"]["AH"]["training_fixture_ids_disjoint_from_holdout"] = False
    with pytest.raises(ValueError):
        build_receipt(value)
    value = private_report()
    value["calibration_training_scope"] = "priced_fixture_markets"
    with pytest.raises(ValueError):
        build_receipt(value)
