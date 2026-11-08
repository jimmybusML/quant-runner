import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import rate_limit_retry_seconds
from research.m5.m5_forward_shadow_totalcorner_capture import (
    needs_totalcorner_fallback, totalcorner_rows,
)


class ForwardTotalCornerCaptureTests(unittest.TestCase):
    def setUp(self):
        self.zone = ZoneInfo("Asia/Shanghai")
        self.asof = datetime(2026, 11, 6, 4, 0, tzinfo=timezone.utc)
        self.kickoff = datetime(2026, 11, 6, 5, 0, tzinfo=timezone.utc)

    def test_rate_limit_reset_epoch_is_converted_to_relative_wait(self):
        self.assertEqual(rate_limit_retry_seconds("1794163207", now_epoch=1794163200), 7)

    def test_rate_limit_reset_relative_duration_is_preserved(self):
        self.assertEqual(rate_limit_retry_seconds("12"), 12)

    def test_invalid_rate_limit_reset_uses_short_fallback(self):
        self.assertEqual(rate_limit_retry_seconds("invalid"), 10)

    def test_skips_totalcorner_request_only_when_crown_covers_both_markets(self):
        self.assertFalse(needs_totalcorner_fallback(True, True))
        self.assertTrue(needs_totalcorner_fallback(False, True))
        self.assertTrue(needs_totalcorner_fallback(True, False))
        self.assertTrue(needs_totalcorner_fallback(False, False))

    def test_accepts_only_post_forecast_open_pregame_rows(self):
        rows = [
            [0, "2.5", 1.91, 1.91, "2026-11-06 12:00:00", None, None],
            [0, "2.5", 1.90, 1.92, "2026-11-06 11:59:59", None, None],
            [0, "2.5", 1.91, 1.91, "2026-11-06 13:00:00", None, None],
            [0, "2.5", 1.91, 1.91, "2026-11-06 12:30:00", None, None, 1],
        ]
        selected = totalcorner_rows(rows, self.asof, self.kickoff, self.zone)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["line"], 2.5)
        self.assertEqual(selected[0]["prices"], (1.91, 1.91))
        self.assertEqual(selected[0]["quote_event_utc"], "2026-11-06T04:00:00Z")

    def test_quarter_handicap_and_prices_are_validated(self):
        rows = [
            [0, "-0.25", 1.95, 1.85, "2026-11-06 12:10:00", None, None],
            [0, "-0.30", 1.95, 1.85, "2026-11-06 12:11:00", None, None],
            [0, "-0.25", 1.0, 1.85, "2026-11-06 12:12:00", None, None],
        ]
        selected = totalcorner_rows(rows, self.asof, self.kickoff, self.zone)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["line"], -0.25)


if __name__ == "__main__":
    unittest.main()
