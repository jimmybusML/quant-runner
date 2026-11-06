import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_m3_selector_same_quote_m5_comparison import load_m5_for_targets


class SameQuoteM5ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "fixture-1": {
                "league": "Test League", "home": "Home", "away": "Away",
                "kickoff_utc": "2026-08-01T12:00:00Z",
                "actual_home_goals": 1, "actual_away_goals": 0,
            }
        }

    def write_forecast(self, path, *, asof="2026-01-01T00:00:00Z"):
        row = {
            "match_id": "fixture-1", "year": 2026, "league": "Test League",
            "home": "Home", "away": "Away", "kickoff": "2026-08-01T12:00:00Z",
            "home_goals": 1, "away_goals": 0,
            "train_end_utc": "2025-12-31T10:00:00Z", "prediction_asof_utc": asof,
            "prediction": {"grid": [[1.0]]},
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_loads_exact_identity_with_strict_oos_time_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecasts.jsonl"
            self.write_forecast(path)

            found, audit = load_m5_for_targets(path, self.target, "M5 baseline")

        self.assertEqual(found["fixture-1"]["grid"], [[1.0]])
        self.assertEqual(audit, {"identity_errors": 0, "chronology_errors": 0})

    def test_rejects_forecast_timestamp_after_kickoff(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecasts.jsonl"
            self.write_forecast(path, asof="2026-09-01T00:00:00Z")

            found, audit = load_m5_for_targets(path, self.target, "M5 baseline")

        self.assertEqual(found, {})
        self.assertEqual(audit["chronology_errors"], 1)


if __name__ == "__main__":
    unittest.main()
