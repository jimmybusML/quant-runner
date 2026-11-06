import unittest

from research.m5.m5_three_penaltyblog_expanded_oos import (
    CATEGORIES,
    category_distribution,
    instant,
    normalized_grid,
)


class ThreePenaltyblogExpandedOOSTests(unittest.TestCase):
    def test_grid_requires_normalized_finite_probability_mass(self):
        class Prediction:
            grid = [[0.25, 0.75], [0.0, 0.0]]

        self.assertEqual(normalized_grid(Prediction()), [[0.25, 0.75], [0.0, 0.0]])

        Prediction.grid = [[0.25, 0.25]]
        with self.assertRaises(ValueError):
            normalized_grid(Prediction())

    def test_quarter_line_settlement_distribution_is_complete(self):
        grid = [[0.10, 0.10, 0.05], [0.10, 0.20, 0.10], [0.10, 0.10, 0.15]]
        distribution = category_distribution(grid, "OU", "over", 2.25)

        self.assertEqual(set(distribution), set(CATEGORIES))
        self.assertAlmostEqual(sum(distribution.values()), 1.0)
        self.assertGreater(distribution["half_loss"], 0.0)

    def test_kickoff_and_source_times_require_explicit_timezone(self):
        self.assertIsNone(instant("2026-11-06T12:00:00"))
        self.assertIsNotNone(instant("2026-11-06T12:00:00Z"))


if __name__ == "__main__":
    unittest.main()
