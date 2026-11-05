import unittest
from datetime import datetime, timezone

from research.m3.m3_crown_forward_capture import (
    build_commitments,
    choose_forecasts,
    exact_schedule_matches,
    _line_ev,
    movement_rows,
    pairing_status,
    source_local_to_utc,
    safe_api_error,
)


class M3CrownForwardCaptureTest(unittest.TestCase):
    def test_pairing_status_counts_only_crown_with_valid_forward_utc_order(self):
        row = {
            "provider": "TotalCorner", "bookmaker": "crown", "market": "AH",
            "fixture_identity_id": "fixture-hash", "forecasted_at_utc": "2026-11-06T01:00:00Z",
            "quote_observed_at_utc": "2026-11-06T02:00:00Z", "received_at_utc": "2026-11-06T02:01:00Z",
            "kickoff_at_utc": "2026-11-06T03:00:00Z",
        }
        rows = [row, dict(row, bookmaker="default"), dict(row, market="OU", forecasted_at_utc="2026-11-06T02:00:00Z")]
        result = pairing_status(rows, "2026-11-06T02:02:00Z")
        self.assertEqual(result["forward_commitment_rows_by_market"], {"AH": 1, "OU": 0})
        self.assertEqual(result["forward_unique_fixture_markets_by_market"], {"AH": 1, "OU": 0})
        self.assertEqual(result["quote_receipts_before_kickoff"], 1)
        self.assertFalse(result["raw_quotes_or_credentials_persisted"])

    def test_api_error_classification_is_allowlisted(self):
        self.assertEqual(safe_api_error({"error": {"code": "TOO_MANY_REQUEST"}}), "TOO_MANY_REQUEST")
        self.assertEqual(safe_api_error({"error": {"code": "arbitrary private response detail"}}), "OTHER")

    def test_forecast_selector_requires_forward_grid_and_prior_training_date(self):
        now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
        base = {
            "event_type": "FORECAST", "forecast_status": "PREDICTED_NO_MARKET",
            "forecast_id": "f", "fixture_identity_id": "i", "model": "poisson",
            "league": "D1", "source_fixture_date": "2026-11-07",
            "forecasted_at_utc": "2026-11-05T10:00:00Z",
            "train_end_calendar_date": "2026-11-04", "score_probability_grid": [[1.0]],
        }
        same_day_training = dict(base, train_end_calendar_date="2026-11-05")
        no_grid = dict(base, score_probability_grid=None, forecast_id="no-grid")
        future_forecast = dict(base, forecasted_at_utc="2026-11-05T13:00:00Z", forecast_id="future")
        selected = choose_forecasts([base, same_day_training, no_grid, future_forecast], now, 14)
        self.assertEqual([row["forecast_id"] for row in selected], ["f"])

    def test_profile_wall_time_is_explicitly_converted_to_utc(self):
        self.assertEqual(source_local_to_utc("2026-11-06 10:00:00", "Asia/Shanghai"),
                         datetime(2026, 11, 6, 2, 0, tzinfo=timezone.utc))

    def test_ambiguous_dst_wall_time_fails_closed(self):
        with self.assertRaises(ValueError):
            source_local_to_utc("2026-11-01 01:30:00", "America/New_York")

    def test_only_open_quote_after_forecast_and_before_kickoff_is_eligible(self):
        forecast = datetime(2026, 11, 6, 1, 0, tzinfo=timezone.utc)
        kickoff = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
        match = {"asianList": [
            [None, "0", 1.9, 1.9, "2026-11-06 08:00:00", 0, 0, 0],
            [None, "-0.25", 1.9, 2.0, "2026-11-06 10:00:00", 0, 0, 0],
            [None, "-0.5", 1.9, 2.0, "2026-11-07 21:00:00", 0, 0, 0],
            [None, "-0.5", 1.9, 2.0, "2026-11-06 11:00:00", 0, 0, 1],
        ]}
        rows = movement_rows(match, "AH", forecast, kickoff, "Asia/Shanghai")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1][1], "-0.25")

    def test_fixture_join_requires_exact_curated_identity(self):
        forecast = {"league": "D1", "home_team": "SV Werder Bremen", "away_team": "FC Augsburg"}
        schedule = [
            {"l": "Germany Bundesliga I", "h": "Werder Bremen", "a": "Augsburg", "id": "1"},
            {"l": "Germany Bundesliga I", "h": "Werder Bremenn", "a": "Augsburg", "id": "2"},
        ]
        matches = exact_schedule_matches(forecast, schedule)
        self.assertEqual([row["id"] for row in matches], ["1"])

    def test_commitment_is_crown_only_and_suppresses_prices(self):
        forecast = {
            "forecast_id": "forecast-hash", "fixture_identity_id": "fixture-hash",
            "forecasted_at_utc": "2026-11-06T01:00:00Z", "train_end_calendar_date": "2026-11-04",
            "model": "poisson", "league": "D1", "model_version_id": "model-version-hash",
            "training_input_sha256": "a" * 64,
            "ah_home_0_p_win": 0.5, "ah_home_0_p_push": 0.2,
            "ah_home_0_p_lose": 0.3, "ou_p_over_2_5": 0.55,
            "score_probability_grid": [[0.25, 0.25], [0.25, 0.25]],
        }
        schedule = {"id": "match-id", "start": "2026-11-07 20:00:00",
                    "h": "Werder Bremen", "a": "Augsburg",
                    "l": "Germany Bundesliga I"}
        payload = {"success": 1, "data": [{"id": "match-id",
          "start": "2026-11-07 20:00:00", "h": "Werder Bremen", "a": "Augsburg",
          "l": "Germany Bundesliga I", "bookmakers": [
            {"slug": "crown", "asianList": [], "goalList": [
                [None, "2.5", 1.91, 1.91, "2026-11-06 10:00:00", 0, 0, 0]]},
            {"slug": "default", "asianList": [[None, "0", 1.8, 2.0,
                "2026-11-06 10:00:00", 0, 0, 0]], "goalList": []},
        ]}]}
        events, status = build_commitments([forecast], schedule, payload,
            datetime(2026, 11, 6, 2, 1, tzinfo=timezone.utc), "Asia/Shanghai", "private-key")
        self.assertEqual(status["status"], "CROWN_IDENTIFIED")
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["bookmaker"], "crown")
        self.assertEqual(event["market"], "OU")
        self.assertFalse(event["price_or_line_persisted"])
        self.assertNotIn("price1", event)
        self.assertNotIn("line", event)
        self.assertIn("mean_expected_unit_return", status["mean_ev"]["OU|poisson|over"])

    def test_legacy_forecast_direct_probabilities_score_only_supported_lines(self):
        forecast = {"ah_home_0_p_win": 0.5, "ah_home_0_p_push": 0.2,
                    "ah_home_0_p_lose": 0.3, "ou_p_over_2_5": 0.55}
        ah = _line_ev(forecast, "AH", "0", (2.0, 2.0))
        ou = _line_ev(forecast, "OU", "2.5", (2.0, 2.0))
        unsupported = _line_ev(forecast, "OU", "3.0", (2.0, 2.0))
        self.assertEqual(ah, {"home": 0.2, "away": -0.2})
        self.assertAlmostEqual(ou["over"], 0.1)
        self.assertAlmostEqual(ou["under"], -0.1)
        self.assertIsNone(unsupported)


if __name__ == "__main__":
    unittest.main()
