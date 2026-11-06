import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_forward_shadow_source_union_pairing import pair


class ForwardSourceUnionPairingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.forecast = {
            "match_id": "private-fixture", "league": "League", "home": "Home", "away": "Away",
            "kickoff_utc": "2026-11-08T12:00:00Z",
            "prediction_asof_utc": "2026-11-06T12:00:00Z",
            "train_end_utc": "2026-11-05T00:00:00Z",
            "prediction": {"grid": [[1.0]]},
        }
        self.forecasts = self.root / "forecasts.jsonl"
        self.forecasts.write_text(json.dumps(self.forecast) + "\n", encoding="utf-8")
        self.crown = self.root / "crown.jsonl"
        self.crown.write_text("", encoding="utf-8")
        self.total = self.root / "total.jsonl"
        self.output = self.root / "paired.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def write_total(self, **updates):
        row = {
            "status": "verified_fixture_response", "match_id": "private-fixture",
            "prediction_asof_utc": self.forecast["prediction_asof_utc"],
            "forecast_sha256": hashlib.sha256(self.forecasts.read_bytes()).hexdigest(),
            "captured_at_utc": "2026-11-06T12:05:00Z", "response_sha256": "response-hash",
            "selected_default_ah": {"line": 0.0, "prices": [1.9, 1.9],
                                     "quote_event_utc": "2026-11-06T12:02:00Z"},
            "selected_default_ou": None,
        }
        row.update(updates)
        self.total.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_pairs_only_actual_pregame_totalcorner_fallback(self):
        self.write_total()
        report = pair(self.forecasts, self.crown, self.total, self.output)
        self.assertEqual(report["paired_fixture_markets"], {"AH": 1})
        self.assertEqual(report["paired_rows"], 1)
        row = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(row["source"], "TotalCorner_default")
        self.assertEqual(row["prices"], [1.9, 1.9])

    def test_rejects_post_kickoff_receipt_and_prefers_crown(self):
        self.write_total(captured_at_utc="2026-11-08T12:01:00Z")
        report = pair(self.forecasts, self.crown, self.total, self.output)
        self.assertEqual(report["paired_rows"], 0)
        crown_row = {
            "status": "verified_fixture_response", "match_id": "private-fixture",
            "quote_event_asof_utc": self.forecast["prediction_asof_utc"], "ah_qualified": True,
        }
        self.crown.write_text(json.dumps(crown_row) + "\n", encoding="utf-8")
        self.write_total()
        report = pair(self.forecasts, self.crown, self.total, self.output)
        self.assertEqual(report["paired_rows"], 0)
        self.assertEqual(report["audit_counts"]["AH_crown_preferred"], 1)


if __name__ == "__main__":
    unittest.main()
