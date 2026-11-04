import unittest
from datetime import datetime, timezone

from research.m5.m5_crown_oos_source_union import summarize


class CrownSourceUnionTests(unittest.TestCase):
    def test_simultaneous_quote_events_are_drawdown_batched(self):
        instant = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        rows = [
            {"observed": instant, "units": 1.0, "category": "win", "log_loss": 1.0, "brier": 0.2},
            {"observed": instant, "units": -1.0, "category": "loss", "log_loss": 1.0, "brier": 0.2},
        ]
        result = summarize(rows)
        self.assertEqual(result["unique_fixtures"], 2)
        self.assertEqual(result["max_drawdown_units_by_quote_event"], 0.0)

    def test_market_rows_remain_fixture_level_for_summary(self):
        start = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        rows = [
            {"observed": start, "units": -1.0, "category": "loss", "log_loss": 1.0, "brier": 0.2},
            {"observed": datetime(2026, 11, 4, 13, tzinfo=timezone.utc), "units": 2.0, "category": "win", "log_loss": 1.0, "brier": 0.2},
        ]
        result = summarize(rows)
        self.assertEqual(result["simulated_bets"], 2)
        self.assertEqual(result["settled_bets"], 2)
        self.assertEqual(result["net_units"], 1.0)
        self.assertEqual(result["max_drawdown_units_by_quote_event"], 1.0)


if __name__ == "__main__":
    unittest.main()
