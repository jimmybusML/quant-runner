import unittest
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research.m5 import m5_m1_mr1_ou_quote_timing_diagnostic as diagnostic


class QuoteTimingDiagnosticTests(unittest.TestCase):
    def test_drawdown_batches_same_quote_event(self):
        event = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [
            {"result": "win", "m1_quote": {"event": event}},
            {"result": "loss", "m1_quote": {"event": event}},
        ]

        def fake_score(row, quote, model):
            return (1.0 if row["result"] == "win" else -1.0, row["result"], "over")

        with patch.object(diagnostic, "score", side_effect=fake_score):
            result = diagnostic.metric(rows, "m1_quote", "M5_baseline", 1)

        self.assertEqual(result["unique_fixtures"], 2)
        self.assertEqual(result["net_units"], 0.0)
        self.assertEqual(result["max_drawdown_by_quote_event_units"], 0.0)
        self.assertEqual(result["full_win"], 1)
        self.assertEqual(result["full_loss"], 1)

    def test_paired_delta_resamples_fixture_differences(self):
        rows = [
            {"m1_quote": {"event": "early"}, "mr1_quote": {"event": "late"}},
            {"m1_quote": {"event": "early"}, "mr1_quote": {"event": "late"}},
        ]

        def fake_score(row, quote, model):
            return (0.5 if quote["event"] == "late" else -0.5, "win", "over")

        with patch.object(diagnostic, "score", side_effect=fake_score):
            result = diagnostic.paired_delta(rows, "M5_baseline", 7)

        self.assertEqual(result["paired_unique_fixtures"], 2)
        self.assertEqual(result["late_minus_early_net_units"], 2.0)
        self.assertEqual(result["late_minus_early_roi_percentage_points"], 100.0)
        interval = result["paired_fixture_bootstrap_95pct_interval_pp"]
        self.assertEqual(interval["lower_2_5_pct"], 100.0)
        self.assertEqual(interval["upper_97_5_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
