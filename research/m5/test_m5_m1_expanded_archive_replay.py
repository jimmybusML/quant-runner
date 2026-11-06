import unittest

from research.m5.m5_m1_expanded_archive_replay import settle


class M1ExpandedReplaySettlementTests(unittest.TestCase):
    def test_quarter_handicap_half_win_and_half_loss(self):
        self.assertEqual(settle("AH", "HOME", 0.25, 2.0, 0, 0), 0.5)
        self.assertEqual(settle("AH", "AWAY", -0.25, 2.0, 0, 0), -0.5)

    def test_quarter_totals_half_win_and_half_loss(self):
        self.assertEqual(settle("OU", "UNDER", 2.25, 2.0, 1, 1), 0.5)
        self.assertEqual(settle("OU", "OVER", 2.25, 2.0, 1, 1), -0.5)

    def test_full_win_loss_and_push(self):
        self.assertAlmostEqual(settle("AH", "HOME", -0.5, 1.9, 2, 0), 0.9)
        self.assertAlmostEqual(settle("OU", "UNDER", 2.5, 1.9, 1, 1), 0.9)
        self.assertEqual(settle("AH", "HOME", 0.0, 1.9, 1, 1), 0.0)

    def test_rejects_non_quarter_line_and_bad_side(self):
        with self.assertRaises(ValueError):
            settle("AH", "HOME", 0.1, 2.0, 1, 0)
        with self.assertRaises(ValueError):
            settle("OU", "MIDDLE", 2.5, 2.0, 1, 1)


if __name__ == "__main__":
    unittest.main()
