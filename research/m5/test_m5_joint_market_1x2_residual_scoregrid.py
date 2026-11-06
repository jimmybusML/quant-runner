import math
import unittest

from research.m5.m5_joint_market_1x2_residual_scoregrid import _combined_grid, _nll


class JointResidualScoregridTests(unittest.TestCase):
    def setUp(self):
        self.row = {"match_id": "fixture-a", "grid": [[0.10, 0.25], [0.40, 0.25]],
                    "line": 0.0, "prices": (1.91, 1.91), "score": (1, 0)}
        self.features = {"fixture-a": {"market": 0.35, "1x2": [0.2, -0.1, 0.05]}}

    def test_zero_coefficients_preserve_baseline_grid(self):
        result = _combined_grid(self.row, "AH", self.features["fixture-a"], 0.0, 0.0)
        for actual_row, expected_row in zip(result, self.row["grid"]):
            for actual, expected in zip(actual_row, expected_row):
                self.assertAlmostEqual(actual, expected)

    def test_missing_1x2_feature_keeps_grid_well_formed(self):
        feature = {"market": -0.2, "1x2": None}
        result = _combined_grid(self.row, "OU", feature, 0.0, 2.0)
        for actual_row, expected_row in zip(result, self.row["grid"]):
            for actual, expected in zip(actual_row, expected_row):
                self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(math.fsum(x for line in result for x in line), 1.0)

    def test_joint_fit_objective_is_finite(self):
        value = _nll([self.row], "AH", self.features, (0.2, 0.3))
        self.assertTrue(math.isfinite(value))


if __name__ == "__main__":
    unittest.main()
