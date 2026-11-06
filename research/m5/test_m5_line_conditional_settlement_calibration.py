import unittest

from research.m5.m5_line_conditional_settlement_calibration import (
    fit_and_evaluate, fit_temperature, temperature_adjust,
)


class LineConditionalCalibrationTests(unittest.TestCase):
    def test_temperature_adjustment_preserves_probability_mass(self):
        adjusted = temperature_adjust({"win": 0.2, "half_win": 0.1, "push": 0.1,
                                       "half_loss": 0.2, "loss": 0.4}, 1.7)
        self.assertAlmostEqual(sum(adjusted.values()), 1.0)
        self.assertGreater(adjusted["win"], 0.2)

    def test_line_temperature_shrinks_toward_global_fit(self):
        rows = [{"distribution": {"win": 0.1, "half_win": 0.0, "push": 0.0,
                                   "half_loss": 0.0, "loss": 0.9},
                 "actual": "win", "global_temperature": 1.5}
                for _ in range(6)]
        unshrunk = fit_temperature(rows, shrinkage=0.0)
        shrunk = fit_temperature(rows, shrinkage=25.0)
        self.assertLess(abs(shrunk - 1.5), abs(unshrunk - 1.5))

    def test_holdout_size_is_not_filtered_and_does_not_fit_global_temperature(self):
        base = {
            2025: {"AH": [self.row(0.25, (1, 0)), self.row(-0.25, (0, 1))],
                   "OU": [self.row(2.5, (2, 1)), self.row(2.5, (1, 2))]},
            2026: {"AH": [self.row(0.25, (1, 0)), self.row(-0.25, (0, 1))],
                   "OU": [self.row(2.5, (2, 1)), self.row(2.5, (1, 2))]},
        }
        first = fit_and_evaluate(base)
        changed = {year: {market: [dict(row) for row in rows]
                          for market, rows in markets.items()} for year, markets in base.items()}
        changed[2026]["AH"][0]["score"] = (0, 3)
        second = fit_and_evaluate(changed)
        self.assertEqual(first["AH"]["holdout_fixture_markets_2026"], 2)
        self.assertEqual(first["AH"]["global_temperature_fit_on_2025_log_loss"],
                         second["AH"]["global_temperature_fit_on_2025_log_loss"])

    @staticmethod
    def row(line, score):
        return {"line": line, "prices": (1.91, 1.91), "score": score,
                "source": "Crown", "receipt_timing": "post_kickoff",
                "event_utc": "2026-01-01T00:00:00Z",
                "grid": [[0.25, 0.25], [0.25, 0.25]]}


if __name__ == "__main__":
    unittest.main()
