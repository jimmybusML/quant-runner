import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_forward_shadow_refresh_receipt import build_receipt


class ForwardShadowRefreshReceiptTests(unittest.TestCase):
    def test_sanitizes_refresh_and_counts_changes_not_new_samples(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def write_json(name, value):
                path = root / name
                path.write_text(json.dumps(value) + "\n")
                return path

            fixture_id = "private-fixture-id"
            forecast = {"match_id": fixture_id, "league": "Private League", "home": "Private Home",
                        "away": "Private Away", "train_end_utc": "2026-11-01T00:00:00Z",
                        "prediction_asof_utc": "2026-11-06T10:00:00Z",
                        "kickoff_utc": "2026-11-06T15:00:00Z", "prediction": {"grid": [[1.0]]}}
            forecast_path = write_json("forecast.jsonl", forecast)
            target_path = write_json("targets.jsonl", forecast)
            capture = {"generated_utc": "2026-11-06T12:00:00Z", "attempted_fixtures": 1,
                       "forecast_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
                       "aggregate_counts": {"verified_fixture_responses": 1}}
            capture_path = write_json("capture.json", capture)
            old_row = {"match_id": fixture_id, "market": "AH", "source": "Crown",
                       "train_end_utc": forecast["train_end_utc"],
                       "prediction_asof_utc": forecast["prediction_asof_utc"],
                       "quote_event_utc": "2026-11-06T11:00:00Z",
                       "quote_received_utc": "2026-11-06T11:30:00Z",
                       "kickoff_utc": forecast["kickoff_utc"], "line": -0.5, "prices": [1.9, 2.0]}
            new_row = {**old_row, "quote_event_utc": "2026-11-06T11:10:00Z",
                       "quote_received_utc": "2026-11-06T12:00:00Z", "prices": [1.95, 1.95]}
            old_pair = write_json("old.jsonl", old_row)
            new_pair = write_json("new.jsonl", new_row)
            old_meta = write_json("old-meta.json", {"pair_sha256": hashlib.sha256(old_pair.read_bytes()).hexdigest()})
            new_meta = write_json("new-meta.json", {
                "forecast_sha256": hashlib.sha256(forecast_path.read_bytes()).hexdigest(),
                "pair_sha256": hashlib.sha256(new_pair.read_bytes()).hexdigest(),
                "paired_fixture_markets": {"AH": 1}, "paired_rows": 1})

            report = build_receipt(forecast_path, target_path, capture_path, old_pair,
                                   old_meta, new_pair, new_meta)
            serialized = json.dumps(report)
            self.assertEqual(report["added_fixture_markets"], 0)
            self.assertEqual(report["changed_quote_fields_on_common_fixture_markets"],
                             {"odds_pair_changed": 1, "quote_event_time_changed": 1,
                              "receipt_time_changed": 1})
            self.assertIsNone(report["roi_pct"])
            self.assertNotIn(fixture_id, serialized)
            self.assertNotIn("Private Home", serialized)
            self.assertNotIn('"prices":', serialized)

    def test_rejects_target_with_changed_forecast_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            forecast = {"match_id": "id", "league": "L", "home": "H", "away": "A",
                        "train_end_utc": "2026-11-01T00:00:00Z", "prediction_asof_utc": "2026-11-06T10:00:00Z",
                        "kickoff_utc": "2026-11-06T15:00:00Z"}
            f = root / "f.jsonl"; f.write_text(json.dumps(forecast) + "\n")
            target = {**forecast, "prediction_asof_utc": "2026-11-06T10:01:00Z"}
            t = root / "t.jsonl"; t.write_text(json.dumps(target) + "\n")
            capture = root / "c.json"
            capture.write_text(json.dumps({"generated_utc": "2026-11-06T12:00:00Z", "attempted_fixtures": 1,
                                           "forecast_sha256": hashlib.sha256(t.read_bytes()).hexdigest()}))
            old = root / "o.jsonl"; old.write_text("")
            new = root / "n.jsonl"; new.write_text("")
            om = root / "om.json"; om.write_text(json.dumps({"pair_sha256": hashlib.sha256(b"").hexdigest()}))
            nm = root / "nm.json"; nm.write_text(json.dumps({"pair_sha256": hashlib.sha256(b"").hexdigest(),
                "forecast_sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "paired_fixture_markets": {}, "paired_rows": 0}))
            with self.assertRaisesRegex(ValueError, "frozen forecast"):
                build_receipt(f, t, capture, old, om, new, nm)


if __name__ == "__main__":
    unittest.main()
