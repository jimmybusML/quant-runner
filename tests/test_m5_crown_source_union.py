import unittest
from datetime import datetime, timezone

from research.m5.m5_crown_oos_source_union import paired_roi_delta, summarize


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

    def test_paired_roi_bootstrap_is_zero_for_identical_models(self):
        baseline = [{"units": 0.5}, {"units": -1.0}, {"units": 1.2}]
        candidate = [dict(row) for row in baseline]
        result = paired_roi_delta(baseline, candidate, resamples=500)
        self.assertEqual(result["candidate_minus_baseline_roi_pp"], 0.0)
        self.assertEqual(result["fixture_bootstrap_95pct_interval_pp"]["lower_2_5_pct"], 0.0)
        self.assertEqual(result["fixture_bootstrap_95pct_interval_pp"]["upper_97_5_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
