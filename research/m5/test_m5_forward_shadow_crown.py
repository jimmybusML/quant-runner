import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.m5_forward_shadow_crown_capture import valid_market_rows
from research.m5.m5_forward_shadow_crown_pairing import run as pair_run


class ForwardCrownCaptureTests(unittest.TestCase):
    def test_market_rows_require_post_asof_open_pregame_quote(self):
        asof = datetime.fromisoformat("2026-11-05T22:00:00+00:00")
        kickoff = datetime.fromisoformat("2026-11-06T12:00:00+00:00")
        rows = [
            [None, "0/0.5", "1.91", "1.95", "2026-11-06 06:30:00", None, None, 0],
            [None, "0/0.5", "1.91", "1.95", "2026-11-06 05:30:00", None, None, 0],
            [1, "0/0.5", "1.91", "1.95", "2026-11-06 06:30:00", None, None, 0],
            [None, "0/0.5", "1.91", "1.95", "2026-11-06 06:30:00", None, None, 1],
        ]
        accepted = valid_market_rows(rows, "AH", asof, kickoff, ZoneInfo("Asia/Shanghai"))
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["line"], 0.25)

    def test_pairing_accepts_only_capture_receipt_in_forecast_window(self):
        with tempfile.TemporaryDirectory(prefix="m5-forward-crown-test-") as temp:
            root = Path(temp)
            forecast = {
                "match_id": "synthetic-fixture", "league": "Synthetic League",
                "home": "Synthetic Home", "away": "Synthetic Away",
                "train_end_utc": "2026-11-01T00:00:00Z",
                "prediction_asof_utc": "2026-11-05T22:00:00Z",
                "kickoff_utc": "2026-11-06T12:00:00Z",
                "prediction": {"grid": [[0.25, 0.25], [0.25, 0.25]]},
            }
            quote = {"market": "AH", "line": 0.25, "prices": [1.91, 1.95],
                     "quote_event_utc": "2026-11-05T22:30:00Z"}
            capture = {
                "match_id": "synthetic-fixture", "league": "Synthetic League",
                "home": "Synthetic Home", "away": "Synthetic Away",
                "status": "verified_fixture_response", "source_bookmaker": "Crown",
                "captured_at_utc": "2026-11-05T22:31:00Z",
                "kickoff_utc": "2026-11-06T12:00:00Z", "ah_eligible_rows": [quote],
                "ou_eligible_rows": [], "response_sha256": "synthetic-hash",
            }
            forecast_path, capture_path, output = root / "forecast.jsonl", root / "capture.jsonl", root / "pairs.jsonl"
            forecast_path.write_text(json.dumps(forecast) + "\n", encoding="utf-8")
            capture_path.write_text(json.dumps(capture) + "\n", encoding="utf-8")
            receipt = pair_run(forecast_path, None, output, capture_path)
            self.assertEqual(receipt["paired_rows"], 1)
            self.assertEqual(receipt["unique_fixture_markets"], {"AH": 1})

            capture["captured_at_utc"] = "2026-11-05T21:59:00Z"
            capture_path.write_text(json.dumps(capture) + "\n", encoding="utf-8")
            receipt = pair_run(forecast_path, None, output, capture_path)
            self.assertEqual(receipt["paired_rows"], 0)
            self.assertEqual(receipt["audit_counts"]["m5_capture_receipt_outside_window"], 1)


if __name__ == "__main__":
    unittest.main()
