import unittest

import numpy as np

from research.m5.m5_recency_m3_walkforward_blend import score_probabilities


class RecencyM3BlendTests(unittest.TestCase):
    def test_binary_ou_brier_matches_single_event_probability_convention(self):
        matrix = np.asarray([[[0.8, 0.2]], [[0.25, 0.75]]])
        result = score_probabilities(matrix, np.asarray([0, 1]), np.asarray([1.0]))
        self.assertAlmostEqual(result["brier"], (0.2**2 + 0.25**2) / 2)

    def test_multiclass_ah_uses_sum_of_three_class_brier(self):
        matrix = np.asarray([[[0.7, 0.2, 0.1]]])
        result = score_probabilities(matrix, np.asarray([0]), np.asarray([1.0]))
        self.assertAlmostEqual(result["brier"], 0.3**2 + 0.2**2 + 0.1**2)


if __name__ == "__main__":
    unittest.main()
