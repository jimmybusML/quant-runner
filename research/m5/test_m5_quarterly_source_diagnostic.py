import unittest

from research.m5.m5_quarterly_source_diagnostic import build_diagnostic


class QuarterlySourceDiagnosticTests(unittest.TestCase):
    def test_partitions_preserve_all_rows_and_source_identity(self):
        row = {"match_id": "a", "line": -0.5, "prices": (1.9, 1.9),
               "event_utc": "2026-01-01T09:00:00Z", "source": "Crown",
               "receipt_timing": "post_kickoff", "league": "League A", "score": (1, 0),
               "grid": [[0.25, 0.25], [0.25, 0.25]]}
        row2 = {**row, "match_id": "b", "source": "TotalCorner_default",
                "event_utc": "2026-05-01T09:00:00Z"}
        row3 = {**row, "match_id": "c", "event_utc": "2026-05-02T09:00:00Z"}
        result = build_diagnostic({2026: {"AH": [row, row2, row3], "OU": [row, row2, row3]}}, {},
                                  {"a": "2026-01-01T10:00:00Z", "b": "2026-05-01T10:00:00Z",
                                   "c": "2026-05-02T10:00:00Z"})
        for market in ("AH", "OU"):
            item = result["markets"][market]
            self.assertEqual(item["all_years"]["unique_fixture_markets"], 3)
            self.assertEqual(sum(x["unique_fixture_markets"] for x in item["by_utc_year_quarter"].values()), 3)
            self.assertIn("2026-Q1|Crown", item["by_utc_year_quarter_and_source"])
            self.assertIn("2026-Q2|TotalCorner_default", item["by_utc_year_quarter_and_source"])
            self.assertEqual(item["all_years"]["quote_sources"], {"Crown": 2, "TotalCorner_default": 1})
            self.assertEqual(item["common_league_source_comparison_by_utc_quarter"]["2026-Q1"]["shared_league_count"], 0)
            self.assertEqual(item["common_league_source_comparison_by_utc_quarter"]["2026-Q2"]["shared_league_count"], 1)

    def test_duplicate_fixture_market_is_rejected(self):
        row = {"match_id": "same", "line": -0.5, "prices": (1.9, 1.9),
               "event_utc": "2026-01-01T09:00:00Z", "source": "Crown",
               "receipt_timing": "post_kickoff", "league": "League A", "score": (1, 0),
               "grid": [[0.25, 0.25], [0.25, 0.25]]}
        with self.assertRaisesRegex(ValueError, "duplicate fixture-market"):
            build_diagnostic({2026: {"AH": [row, row], "OU": [row]}}, {},
                             {"same": "2026-01-01T10:00:00Z"})


if __name__ == "__main__":
    unittest.main()
