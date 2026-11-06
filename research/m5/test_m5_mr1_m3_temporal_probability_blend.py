import unittest

from research.m5.m5_mr1_m3_temporal_probability_blend import (
    CATEGORIES, INVERSE, blend, normalize, score_sample, side_distribution,
)


class TemporalProbabilityBlendTests(unittest.TestCase):
    def test_inverse_distribution_is_involution(self):
        p = {"win": .31, "half_win": .12, "push": .08, "half_loss": .19, "loss": .30}
        once = {c: p[INVERSE[c]] for c in CATEGORIES}
        twice = {c: once[INVERSE[c]] for c in CATEGORIES}
        self.assertEqual(twice, p)

    def test_side_distribution_flips_when_selected_side_differs(self):
        p = {"win": .6, "half_win": .1, "push": .1, "half_loss": .1, "loss": .1}
        self.assertEqual(side_distribution(p, "home", "away"), {
            "win": .1, "half_win": .1, "push": .1, "half_loss": .1, "loss": .6})

    def test_blend_respects_endpoints_and_normalizes(self):
        a = {"win": .6, "half_win": .1, "push": .1, "half_loss": .1, "loss": .1}
        b = {"win": .1, "half_win": .1, "push": .1, "half_loss": .1, "loss": .6}
        self.assertEqual(blend(a, b, 0.0), normalize(a))
        self.assertEqual(blend(a, b, 1.0), normalize(b))
        self.assertAlmostEqual(sum(blend(a, b, 0.5).values()), 1.0)

    def test_equal_blend_selects_shared_quote_side_and_settles(self):
        home = {"win": .60, "half_win": 0, "push": 0, "half_loss": 0, "loss": .40}
        item = {"market": "AH", "line": 0.0, "prices": [2.0, 2.0],
                "event_utc": "2026-01-01T10:00:00Z", "kickoff_utc": "2026-01-01T11:00:00Z",
                "home_goals": 0, "away_goals": 1, "mr1_side": "away",
                "mr1_probabilities": {"win": .80, "half_win": 0, "push": 0,
                                      "half_loss": 0, "loss": .20},
                "m3_probabilities": {"poisson": {
                    "home": home,
                    "away": {"win": .40, "half_win": 0, "push": 0, "half_loss": 0, "loss": .60}}}}
        result = score_sample(item, "poisson", .5)
        self.assertEqual(result["side"], "away")
        self.assertEqual(result["category"], "win")
        self.assertEqual(result["pnl"], 1.0)


if __name__ == "__main__":
    unittest.main()
