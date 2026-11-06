import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_forward_shadow_public_receipt import build_receipt, instant


class ForwardShadowPublicReceiptTests(unittest.TestCase):
    def test_instant_rejects_naive_datetime(self):
        self.assertIsNone(instant("2026-11-06T12:00:00"))
        self.assertIsNotNone(instant("2026-11-06T12:00:00Z"))

    def test_sanitizes_and_checks_private_pairing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_id = "private-fixture-id-123"
            forecast = {"match_id": fixture_id, "train_end_utc": "2026-11-01T00:00:00Z",
                        "prediction_asof_utc": "2026-11-06T10:00:00Z",
                        "kickoff_utc": "2026-11-06T15:00:00Z",
                        "prediction": {"grid": [[0.4, 0.6]]}}
            forecast_path = root / "forecasts.jsonl"
            forecast_path.write_text(json.dumps(forecast) + "\n")
            forecast_hash = hashlib.sha256(forecast_path.read_bytes()).hexdigest()
            forecast_meta = root / "forecast-meta.json"
            forecast_meta.write_text(json.dumps({"forecast_sha256": forecast_hash,
                                                 "generated_utc": "2026-11-06T10:00:00Z"}))
            crown_capture = root / "crown-capture.json"
            crown_capture.write_text(json.dumps({"generated_utc": "2026-11-06T12:00:00Z",
                "attempted_fixtures": 1, "aggregate_counts": {"verified_fixture_responses": 1},
                "response_hash_set_sha256": "c" * 64}))
            pairs_path = root / "pairs.jsonl"
            pair_row = {"match_id": fixture_id, "market": "AH", "source": "Crown",
                        "train_end_utc": "2026-11-01T00:00:00Z",
                        "prediction_asof_utc": "2026-11-06T10:00:00Z",
                        "quote_event_utc": "2026-11-06T11:00:00Z",
                        "quote_received_utc": "2026-11-06T12:00:00Z",
                        "kickoff_utc": "2026-11-06T15:00:00Z",
                        "line": -0.5, "prices": [1.9, 2.0]}
            pair_bytes = (json.dumps(pair_row) + "\n").encode()
            pairs_path.write_bytes(pair_bytes)
            pair_meta = root / "pair-meta.json"
            pair_meta.write_text(json.dumps({"forecast_sha256": forecast_hash,
                "pair_sha256": hashlib.sha256(pair_bytes).hexdigest(), "paired_rows": 1,
                "paired_fixture_markets": {"AH": 1}, "generated_utc": "2026-11-06T12:00:01Z",
                "crown_index_sha256": "a" * 64, "totalcorner_index_sha256": "b" * 64}))

            report = build_receipt(forecast_path, forecast_meta, crown_capture,
                                   pairs_path, pair_meta)
            serialized = json.dumps(report)
            self.assertEqual(report["markets"]["AH"]["source_fixture_markets"], {"Crown": 1})
            self.assertIsNone(report["markets"]["AH"]["roi_pct"])
            self.assertNotIn(fixture_id, serialized)
            self.assertNotIn('"prices":', serialized)

    def test_rejects_post_kickoff_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forecast_path = root / "f.jsonl"
            forecast_path.write_text(json.dumps({"match_id": "fixture-id"}) + "\n")
            forecast_hash = hashlib.sha256(forecast_path.read_bytes()).hexdigest()
            forecast_meta = root / "fm.json"
            forecast_meta.write_text(json.dumps({"forecast_sha256": forecast_hash}))
            crown = root / "c.json"
            crown.write_text("{}")
            pairs = root / "p.jsonl"
            row = {"match_id": "id", "market": "OU", "source": "TotalCorner_default",
                   "train_end_utc": "2026-11-01T00:00:00Z",
                   "prediction_asof_utc": "2026-11-06T10:00:00Z",
                   "quote_event_utc": "2026-11-06T11:00:00Z",
                   "quote_received_utc": "2026-11-06T16:00:00Z",
                   "kickoff_utc": "2026-11-06T15:00:00Z"}
            pair_bytes = (json.dumps(row) + "\n").encode()
            pairs.write_bytes(pair_bytes)
            pair_meta = root / "pm.json"
            pair_meta.write_text(json.dumps({"forecast_sha256": forecast_hash,
                "pair_sha256": hashlib.sha256(pair_bytes).hexdigest(), "paired_rows": 1,
                "paired_fixture_markets": {"OU": 1}}))
            with self.assertRaisesRegex(ValueError, "chronology"):
                build_receipt(forecast_path, forecast_meta, crown, pairs, pair_meta)


if __name__ == "__main__":
    unittest.main()
