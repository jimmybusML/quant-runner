import unittest

from research.m5.m5_market_residual_roi_fit_diagnostic import select_beta


class MarketResidualRoiFitTests(unittest.TestCase):
    def test_selects_best_training_objective(self):
        score, beta = select_beta([-1.0, 0.0, 1.0], lambda b: { -1.0: -2.0, 0.0: 1.0, 1.0: 0.0}[b])
        self.assertEqual((score, beta), (1.0, 0.0))

    def test_tie_breaks_toward_smallest_absolute_tilt(self):
        score, beta = select_beta([-1.0, -0.25, 0.25, 1.0], lambda _: 2.0)
        self.assertEqual(score, 2.0)
        self.assertEqual(beta, -0.25)

    def test_rejects_nonfinite_objective(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            select_beta([0.0], lambda _: float("nan"))


if __name__ == "__main__":
    unittest.main()
