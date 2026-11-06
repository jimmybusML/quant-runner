import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_league_direction_walkforward import POLICIES, build


def result_for(policy):
    direction_roi = {"higher_ev": 1.0, "favorite": 2.0, "underdog": 3.0}
    leagues = {
        "League A | 2025": {"fixtures": 20, "roi_pct": direction_roi[policy],
                             "net_units": direction_roi[policy] / 100 * 20,
                             "settlement_counts": {"win": 10, "half_win": 0, "push": 0,
                                                   "half_loss": 0, "loss": 10}},
        "League A | 2026": {"fixtures": 15, "roi_pct": direction_roi[policy],
                             "net_units": direction_roi[policy] / 100 * 15,
                             "settlement_counts": {"win": 8, "half_win": 0, "push": 0,
                                                   "half_loss": 0, "loss": 7}},
        "League B | 2025": {"fixtures": 19, "roi_pct": direction_roi[policy],
                             "net_units": direction_roi[policy] / 100 * 19,
                             "settlement_counts": {"win": 10, "half_win": 0, "push": 0,
                                                   "half_loss": 0, "loss": 9}},
        "League B | 2026": {"fixtures": 10, "roi_pct": direction_roi[policy],
                             "net_units": direction_roi[policy] / 100 * 10,
                             "settlement_counts": {"win": 5, "half_win": 0, "push": 0,
                                                   "half_loss": 0, "loss": 5}},
    }
    return {"markets": {market: {
        "descriptive_splits_no_filter_applied": {
            "by_league_and_utc_kickoff_year": leagues,
            "by_source_and_utc_kickoff_year": {
                "Crown | 2026": {"fixtures": 22},
                "TotalCorner_default | 2026": {"fixtures": 3},
            },
        },
        "by_utc_kickoff_year": {
            "2025": {"fixtures": 39},
            "2026": {"fixtures": 25, "roi_pct": -1.0},
        },
    } for market in ("AH", "OU")}}


class LeagueDirectionWalkforwardTests(unittest.TestCase):
    def test_selects_training_policy_and_preserves_full_holdout_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {}
            for policy, name in POLICIES.items():
                path = Path(tmp) / name
                path.write_text(json.dumps(result_for(policy)), encoding="utf-8")
                paths[policy] = path
            report = build(paths)

        ah = report["markets"]["AH"]
        self.assertEqual(ah["holdout_unique_fixtures"], 25)
        self.assertEqual(ah["simulated_bets"], 25)
        self.assertEqual(ah["policy_fixture_counts"], {"underdog": 15, "higher_ev": 10})
        self.assertEqual(ah["source_fixture_markets"], {"Crown": 22, "TotalCorner_default": 3})

    def test_uses_higher_ev_when_training_cohort_is_below_minimum(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {}
            for policy, name in POLICIES.items():
                path = Path(tmp) / name
                path.write_text(json.dumps(result_for(policy)), encoding="utf-8")
                paths[policy] = path
            report = build(paths)

        self.assertEqual(report["markets"]["OU"]["leagues"]["League B"]["selected_policy"], "higher_ev")


if __name__ == "__main__":
    unittest.main()
