import unittest
from datetime import datetime, timezone

from research.m5.m5_v26_crown_oos_replay import pnl_summary


class V26CrownReplayTests(unittest.TestCase):
    def test_ou_quote_uses_over_under_sides_and_settlement(self):
        grid = [[0.0] * 15 for _ in range(15)]
        grid[2][0] = 1.0
        row = {
            "mid": "private-test-id",
            "market": "OU",
            "observed": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "line": 2.5,
            "prices": (1.90, 2.10),  # over, under
            "forecast": {"prediction": {"grid": grid}},
            "home_goals": 2,
            "away_goals": 0,
        }
        result = pnl_summary([row])
        self.assertEqual(result["unique_fixtures"], 1)
        self.assertEqual(result["full_win"], 1)
        self.assertEqual(result["full_loss"], 0)
        self.assertAlmostEqual(result["net_units"], 1.10)
        self.assertAlmostEqual(result["roi_pct"], 110.0)


if __name__ == "__main__":
    unittest.main()
