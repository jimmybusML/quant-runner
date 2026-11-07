import unittest

from research.m5.m5_m1_m5_distribution_blend_oos import (
    blend_distribution, opposite_distribution, validate_m1_match,
)


class M1M5DistributionBlendTests(unittest.TestCase):
    def test_opposite_side_mirrors_asian_settlement_categories(self):
        source = {"win": .4, "half_win": .1, "push": .2, "half_loss": .15, "loss": .15}
        self.assertEqual(opposite_distribution(source), {
            "win": .15, "half_win": .15, "push": .2, "half_loss": .1, "loss": .4})

    def test_blend_preserves_probability_mass_and_endpoints(self):
        m5 = {"win": .5, "half_win": .1, "push": .1, "half_loss": .1, "loss": .2}
        m1 = {"win": .2, "half_win": .2, "push": .1, "half_loss": .2, "loss": .3}
        self.assertEqual(blend_distribution(m5, m1, 0), m5)
        self.assertEqual(blend_distribution(m5, m1, 1), m1)
        self.assertAlmostEqual(sum(blend_distribution(m5, m1, .35).values()), 1.0)

    def test_rejects_m1_contract_mismatch(self):
        row = {"event_utc": "2026-01-01T10:00:00Z", "kickoff_utc": "2026-01-01T12:00:00Z",
               "line": -.5, "source": "Crown", "prices": [1.9, 1.9], "score": (1, 0)}
        m1 = {"event_utc": "2026-01-01T10:00:00Z", "kickoff_utc": "2026-01-01T12:00:00Z",
              "line": -.5, "source": "Crown", "prices": [1.9, 1.9], "actual_home_goals": 1,
              "actual_away_goals": 0, "prediction_asof_utc": "2026-01-01T09:00:00Z"}
        self.assertIsNone(validate_m1_match(row, m1, row["kickoff_utc"]))
        self.assertEqual(validate_m1_match(row, {**m1, "source": "TotalCorner_default"},
                                          row["kickoff_utc"]), "source_mismatch")


if __name__ == "__main__":
    unittest.main()
