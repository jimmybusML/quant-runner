import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.m5_crown_1x2_residual_scoregrid import (
    model_result_probs, residual_vector, select_crown_1x2, tilt_grid,
)


class Crown1x2ResidualScoregridTests(unittest.TestCase):
    def setUp(self):
        self.grid = [[0.10, 0.10, 0.05],
                     [0.10, 0.20, 0.10],
                     [0.05, 0.10, 0.20]]

    def test_result_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(model_result_probs(self.grid)), 1.0)

    def test_beta_zero_preserves_grid(self):
        residual = residual_vector(self.grid, [0.60, 0.20, 0.20])
        adjusted = tilt_grid(self.grid, residual, 0.0)
        for got_row, expected_row in zip(adjusted, self.grid):
            for got, expected in zip(got_row, expected_row):
                self.assertAlmostEqual(got, expected)

    def test_beta_one_anchors_result_mass_to_market_probs(self):
        target = [0.60, 0.20, 0.20]
        adjusted = tilt_grid(self.grid, residual_vector(self.grid, target), 1.0)
        got = model_result_probs(adjusted)
        for actual, expected in zip(got, target):
            self.assertAlmostEqual(actual, expected)

    def test_receipt_must_not_precede_quote_event(self):
        payload = {"success": 1, "data": [{
            "id": "safe-test-id", "h": "Home", "a": "Away", "l": "League",
            "start": "2026-11-08T12:00:00Z",
            "bookmakers": [{"slug": "crown", "odds": {
                "open": {"home": 2.0, "draw": 3.0, "away": 4.0,
                         "time": "2026-11-08T09:00:00Z"},
                "close": {"home": 2.1, "draw": 3.0, "away": 3.8,
                          "time": "2026-11-08T10:00:00Z"}}}]}]}
        forecast = {"match_id": "safe-test-id", "league": "League", "home": "Home", "away": "Away",
                    "prediction_asof_utc": "2026-11-08T08:00:00Z",
                    "kickoff": "2026-11-08T12:00:00Z"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "response.json"
            path.write_text(json.dumps(payload))
            receipt = datetime(2026, 11, 8, 9, 30, tzinfo=timezone.utc)
            selected = select_crown_1x2(path, "safe-test-id", forecast, ZoneInfo("UTC"), receipt)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["field"], "open")
        self.assertEqual(selected["receipt_timing"], "pre_kickoff")

    def test_invalid_receipt_rejects_quote(self):
        forecast = {"match_id": "absent", "league": "L", "home": "H", "away": "A",
                    "prediction_asof_utc": "2026-11-08T08:00:00Z",
                    "kickoff": "2026-11-08T12:00:00Z"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "response.json"
            path.write_text("{}")
            selected = select_crown_1x2(path, "absent", forecast, ZoneInfo("UTC"), None)
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
