import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from research.m5.m5_m3_expanded_source_union_contract_replay import (
    crown_first_exact_quote,
    m5_probabilities,
    select_side_from_probabilities,
    settlement_distribution,
)


UTC = timezone.utc


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def quote(line, observed, home_price="1.90", away_price="1.95"):
    return [None, str(line), home_price, away_price, observed, 0, 0, 0]


class M3ExpandedSourceUnionReplayTests(unittest.TestCase):
    def test_m5_grid_aggregates_1x2_and_ou_probabilities(self):
        grid = [[0.0] * 15 for _ in range(15)]
        grid[2][1] = 0.4
        grid[1][1] = 0.3
        grid[0][3] = 0.3
        forecast = {"prediction": {"grid": grid}}
        result = m5_probabilities(forecast)
        self.assertEqual(result["AH"], (0.4, 0.3, 0.3))
        self.assertAlmostEqual(result["OU"][0], 0.7)
        self.assertAlmostEqual(result["OU"][1], 0.3)

    def test_selection_uses_probabilities_and_actual_prices(self):
        self.assertEqual(
            select_side_from_probabilities("AH", (0.7, 0.1, 0.2), (1.9, 2.0))[0],
            "home",
        )
        self.assertEqual(
            select_side_from_probabilities("OU", (0.6, 0.4), (1.5, 2.5))[0],
            "under",
        )

    def test_settlement_distribution_reverses_for_away_and_under(self):
        self.assertEqual(
            settlement_distribution("AH", "away", (0.6, 0.2, 0.2)),
            {"win": 0.2, "push": 0.2, "loss": 0.6},
        )
        self.assertEqual(
            settlement_distribution("OU", "under", (0.7, 0.3)),
            {"win": 0.3, "loss": 0.7},
        )

    def test_crown_is_preferred_when_both_sources_have_valid_exact_contract(self):
        zone = ZoneInfo("UTC")
        selected = crown_first_exact_quote(
            [quote(0, "2026-11-06T10:00:00")],
            [quote(0, "2026-11-06T11:00:00")],
            "AH", 0.0, instant("2026-11-06T09:00:00Z"),
            instant("2026-11-06T12:00:00Z"), zone,
            instant("2026-11-06T13:00:00Z"), instant("2026-11-06T13:00:00Z"),
        )
        self.assertEqual(selected[1], "Crown")
        self.assertEqual(selected[0][0], instant("2026-11-06T10:00:00Z"))

    def test_totalcorner_is_used_when_crown_is_absent_or_receipt_is_invalid(self):
        zone = ZoneInfo("UTC")
        cutoff, kickoff = instant("2026-11-06T09:00:00Z"), instant("2026-11-06T12:00:00Z")
        total = [quote(2.5, "2026-11-06T11:00:00")]
        received = instant("2026-11-06T13:00:00Z")
        selected = crown_first_exact_quote([], total, "OU", 2.5, cutoff, kickoff,
                                           zone, None, received)
        self.assertEqual(selected[1], "TotalCorner_default")
        selected = crown_first_exact_quote(
            [quote(2.5, "2026-11-06T10:00:00")], total, "OU", 2.5,
            cutoff, kickoff, zone, instant("2026-11-06T09:30:00Z"), received,
        )
        self.assertEqual(selected[1], "TotalCorner_default")

    def test_no_source_quote_is_returned_outside_cutoff_or_kickoff_window(self):
        zone = ZoneInfo("UTC")
        selected = crown_first_exact_quote(
            [quote(0, "2026-11-06T08:00:00")],
            [quote(0, "2026-11-06T12:00:00")],
            "AH", 0.0, instant("2026-11-06T09:00:00Z"),
            instant("2026-11-06T12:00:00Z"), zone,
            instant("2026-11-06T13:00:00Z"), instant("2026-11-06T13:00:00Z"),
        )
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
