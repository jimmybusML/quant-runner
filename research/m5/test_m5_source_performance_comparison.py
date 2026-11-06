import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_source_performance_comparison import SCENARIOS, build_report


def source_report():
    market = {
        "unique_fixtures": 12, "simulated_bets": 12, "settled_bets": 12,
        "pending_bets": 0, "settlement_counts": {k: 1 for k in
            ("win", "half_win", "push", "half_loss", "loss")},
        "net_units": -1.0, "roi_pct": -8.333333,
        "max_drawdown_units_by_source_event_time": 3.0,
        "settlement_log_loss": 1.0, "settlement_brier": 0.5,
        "roi_bootstrap_95pct": {"lower_95": -20, "upper_95": 4},
        "by_utc_kickoff_year": {"2026": {"fixtures": 12, "net_units": -1.0, "roi_pct": -8.333333}},
        "source_fixture_markets": {"Crown": 12},
        "quote_receipt_timing": {"post_kickoff": 12},
        "utc_coverage": {"first_kickoff": "2026-01-01T00:00:00Z"},
        "private_raw_response": "must not be copied",
    }
    return {"generated_utc": "2026-11-06T00:00:00Z", "side_selection_policy": "higher_ev",
            "input_hashes": {"candidate_manifest_sha256": "a", "forecast_sha256": "b",
                              "quote_response_hash_set_sha256": "c"},
            "markets": {"AH": market, "OU": market}}


class SourcePerformanceComparisonTests(unittest.TestCase):
    def test_emits_six_independent_scenarios_and_only_aggregate_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = {}
            for name, _, _ in SCENARIOS:
                path = root / f"{name}.json"
                path.write_text(json.dumps(source_report()), encoding="utf-8")
                inputs[name] = path
            result = build_report(inputs, "2026-11-06T08:00:00Z")
        self.assertEqual(len(result["scenarios"]), 6)
        self.assertEqual(result["scenarios"]["crown_only_baseline"]["markets"]["AH"]["unique_fixture_markets"], 12)
        self.assertNotIn("private_raw_response", json.dumps(result))
        self.assertIn("post-kickoff", result["timing_limitations"])

    def test_rejects_unexpected_side_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = {}
            for name, _, _ in SCENARIOS:
                path = root / f"{name}.json"
                data = source_report()
                if name == "crown_only_baseline":
                    data["side_selection_policy"] = "unknown_filter"
                path.write_text(json.dumps(data), encoding="utf-8")
                inputs[name] = path
            with self.assertRaisesRegex(ValueError, "side-selection policy"):
                build_report(inputs, "2026-11-06T08:00:00Z")


if __name__ == "__main__":
    unittest.main()
