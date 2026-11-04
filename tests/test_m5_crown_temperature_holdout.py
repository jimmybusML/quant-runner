import unittest
from datetime import datetime, timedelta, timezone

from research.m5.m5_crown_temperature_holdout import chronological_split, transformed


class CrownTemperatureHoldoutTests(unittest.TestCase):
    def test_training_outcomes_must_precede_holdout_quote_cutoff(self):
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        rows = []
        for i in range(10):
            quote = start + timedelta(hours=i)
            ft_lag = timedelta(hours=2) if i == 6 else timedelta(minutes=1)
            rows.append({"observed": quote, "ft_observed": quote + ft_lag})
        # A pre-boundary quote whose FT arrives after holdout begins is purged.
        train, test, cutoff, purged = chronological_split(rows)
        self.assertEqual(cutoff, start + timedelta(hours=7))
        self.assertEqual(len(test), 3)
        self.assertEqual(purged, 1)
        self.assertEqual(len(train), 6)
        self.assertTrue(all(r["ft_observed"] < cutoff for r in train))
        self.assertTrue(all(r["observed"] >= cutoff for r in test))

    def test_same_quote_instant_is_never_split(self):
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        rows = []
        for i in range(10):
            quote = start + timedelta(hours=i // 2)
            rows.append({"observed": quote, "ft_observed": quote - timedelta(minutes=1)})
        train, test, cutoff, _ = chronological_split(rows)
        self.assertTrue(all(r["observed"] < cutoff for r in train))
        self.assertTrue(all(r["observed"] >= cutoff for r in test))

    def test_temperature_preserves_normalized_score_grid(self):
        grid = [[0.4, 0.1], [0.2, 0.3]]
        same = transformed(grid, 1.0)
        flat = transformed(grid, 2.0)
        self.assertAlmostEqual(sum(map(sum, same)), 1.0)
        self.assertAlmostEqual(same[0][0], 0.4)
        self.assertAlmostEqual(sum(map(sum, flat)), 1.0)
        self.assertLess(flat[0][0], same[0][0])


if __name__ == "__main__":
    unittest.main()
