import unittest

from research.m5.m5_market_residual_scoregrid_2025fit_2026holdout import (
    market_residual, tilt_grid,
)


class MarketResidualScoregridTests(unittest.TestCase):
    def setUp(self):
        self.grid = [
            [0.12, 0.10, 0.06],
            [0.11, 0.14, 0.08],
            [0.07, 0.10, 0.22],
        ]

    def test_zero_residual_is_identity(self):
        result = tilt_grid(self.grid, "OU", 0.0, 2.0)
        for actual, expected in zip(result, self.grid):
            for got, want in zip(actual, expected):
                self.assertAlmostEqual(got, want)

    def test_positive_residual_tilts_toward_more_goals(self):
        result = tilt_grid(self.grid, "OU", 0.5, 1.0)
        base_mean = sum((h + a) * self.grid[h][a]
                        for h in range(3) for a in range(3))
        new_mean = sum((h + a) * result[h][a]
                       for h in range(3) for a in range(3))
        self.assertGreater(new_mean, base_mean)
        self.assertAlmostEqual(sum(map(sum, result)), 1.0)

    def test_positive_residual_tilts_toward_home_in_ah(self):
        result = tilt_grid(self.grid, "AH", 0.5, 1.0)
        base_diff = sum((h - a) * self.grid[h][a]
                        for h in range(3) for a in range(3))
        new_diff = sum((h - a) * result[h][a]
                       for h in range(3) for a in range(3))
        self.assertGreater(new_diff, base_diff)

    def test_market_residual_uses_no_vig_price_and_m5_grid(self):
        row = {"grid": self.grid, "line": 0.5, "prices": (1.9, 2.0)}
        result = market_residual(row, "AH")
        self.assertTrue(-5 < result < 5)

    def test_invalid_beta_rejected(self):
        with self.assertRaises(ValueError):
            tilt_grid(self.grid, "AH", 0.0, float("nan"))


if __name__ == "__main__":
    unittest.main()
