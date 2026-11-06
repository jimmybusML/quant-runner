import unittest

from research.m5.m5_m3_selector_settlement_calibration import temperature_adjust, validate_chronology
from research.m5.m5_penaltyblog_prior_year_selector import CATEGORIES


class M3SelectorSettlementCalibrationTests(unittest.TestCase):
    def test_temperature_one_preserves_probabilities_and_mass(self):
        distribution = {"win": 0.2, "half_win": 0.1, "push": 0.3, "half_loss": 0.2, "loss": 0.2}

        adjusted = temperature_adjust(distribution, 1.0)

        self.assertEqual(set(adjusted), set(CATEGORIES))
        for category in CATEGORIES:
            self.assertAlmostEqual(adjusted[category], distribution[category])
        self.assertAlmostEqual(sum(adjusted.values()), 1.0)

    def test_temperature_adjustment_preserves_mass_and_rejects_invalid_values(self):
        distribution = {"win": 0.6, "half_win": 0.1, "push": 0.1, "half_loss": 0.1, "loss": 0.1}

        adjusted = temperature_adjust(distribution, 1.5)

        self.assertAlmostEqual(sum(adjusted.values()), 1.0)
        with self.assertRaises(ValueError):
            temperature_adjust(distribution, 0.0)

    def test_rejects_quote_event_after_kickoff(self):
        fixture = {
            "train_end_utc": "2025-12-31T23:00:00Z",
            "prediction_asof_utc": "2026-01-01T00:00:00Z",
            "kickoff_utc": "2026-02-01T12:00:00Z",
            "quotes": {
                market: {"event_utc": "2026-01-05T00:00:00Z", "receipt_utc": "2026-02-01T13:00:00Z"}
                for market in ("AH", "OU")
            },
        }
        validate_chronology(fixture)
        fixture["quotes"]["OU"]["event_utc"] = "2026-02-02T00:00:00Z"
        with self.assertRaises(ValueError):
            validate_chronology(fixture)


if __name__ == "__main__":
    unittest.main()
