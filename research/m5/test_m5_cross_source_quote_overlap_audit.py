import unittest

from research.m5.m5_cross_source_quote_overlap_audit import summarize_pairs


class CrossSourceQuoteOverlapAuditTests(unittest.TestCase):
    def test_empty_pairs_have_no_fabricated_metrics(self):
        result = summarize_pairs([])
        self.assertEqual(result["same_fixture_market_quote_pairs"], 0)
        self.assertIsNone(result["median_absolute_event_time_gap_seconds"])
        self.assertIsNone(result["mean_max_side_price_difference"])

    def test_aggregates_only_same_fixture_quote_pairs(self):
        rows = [
            {"same_line": True, "event_gap_seconds": 0, "prices_close": True,
             "max_side_price_difference": 0.0, "both_pregame": True,
             "both_receipts_post_kickoff": True},
            {"same_line": False, "event_gap_seconds": 120, "prices_close": False,
             "max_side_price_difference": 0.07, "both_pregame": True,
             "both_receipts_post_kickoff": True},
        ]
        result = summarize_pairs(rows)
        self.assertEqual(result["same_fixture_market_quote_pairs"], 2)
        self.assertEqual(result["same_contract_line_pairs"], 1)
        self.assertEqual(result["same_event_timestamp_pairs"], 1)
        self.assertEqual(result["event_times_within_60_seconds"], 1)
        self.assertAlmostEqual(result["mean_max_side_price_difference"], 0.035)


if __name__ == "__main__":
    unittest.main()
