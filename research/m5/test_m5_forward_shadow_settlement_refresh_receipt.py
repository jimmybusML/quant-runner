import json
import tempfile
import unittest
from pathlib import Path

from research.m5.m5_forward_shadow_settlement_refresh_receipt import build_receipt


class SettlementRefreshReceiptTests(unittest.TestCase):
    def test_sanitizes_incremental_market_settlements(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / "capture.json"
            capture.write_text(json.dumps({
                "protocol": "M5_FORWARD_SHADOW_PUBLIC_CAPTURE_RECEIPT_V1",
                "pairing": {"pair_sha256": "a" * 64,
                            "paired_fixture_markets": {"AH": 2, "OU": 1},
                            "source_fixture_markets_by_market": {
                                "AH": {"Crown": 1, "TotalCorner_default": 1},
                                "OU": {"TotalCorner_default": 1}}},
                "integrity": {"private_fixture_level_data_published": False}}))
            previous = root / "previous.json"
            previous.write_text(json.dumps({
                "protocol": "M5_FORWARD_SHADOW_SETTLEMENT_V1",
                "paired_input_sha256": "a" * 64, "settled_fixture_markets": 1,
                "markets": {
                    "AH": {"settled_bets": 1},
                    "OU": {"settled_bets": 0}}}))
            current = root / "current.json"
            empty = {"win": 0, "half_win": 0, "push": 0, "half_loss": 0, "loss": 0}
            current.write_text(json.dumps({
                "protocol": "M5_FORWARD_SHADOW_SETTLEMENT_V1",
                "paired_input_sha256": "a" * 64, "settled_fixture_markets": 2,
                "pending_fixture_markets": 1, "capture_counts": {"verified_ft": 2},
                "verified_result_response_hash_set_sha256": "b" * 64,
                "markets": {
                    "AH": {"unique_fixture_markets": 2, "simulated_bets": 2,
                           "settled_bets": 1, "pending_bets": 1,
                           "paired_source_fixture_markets": {"Crown": 1, "TotalCorner_default": 1},
                           "settled_source_fixture_markets": {"Crown": 1},
                           "settlement_counts": {**empty, "win": 1}, "net_units": 0.9,
                           "realized_roi_on_settled_stake_pct": 90.0,
                           "roi_pct": None, "max_drawdown_units_by_kickoff": 0.0},
                    "OU": {"unique_fixture_markets": 1, "simulated_bets": 1,
                           "settled_bets": 1, "pending_bets": 0,
                           "paired_source_fixture_markets": {"TotalCorner_default": 1},
                           "settled_source_fixture_markets": {"TotalCorner_default": 1},
                           "settlement_counts": {**empty, "loss": 1}, "net_units": -1.0,
                           "realized_roi_on_settled_stake_pct": -100.0,
                           "roi_pct": -100.0, "max_drawdown_units_by_kickoff": 1.0}}}))
            report = build_receipt(capture, previous, current)
            self.assertEqual(report["markets"]["AH"]["newly_verified_settlements_since_previous_receipt"], 0)
            self.assertEqual(report["markets"]["OU"]["newly_verified_settlements_since_previous_receipt"], 1)
            self.assertIsNone(report["markets"]["AH"]["roi_pct"])
            self.assertNotIn('"match_id"', json.dumps(report))

    def test_rejects_different_pair_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / "capture.json"
            capture.write_text(json.dumps({"protocol": "M5_FORWARD_SHADOW_PUBLIC_CAPTURE_RECEIPT_V1",
                "pairing": {"pair_sha256": "a" * 64}, "integrity": {"private_fixture_level_data_published": False}}))
            previous = root / "previous.json"
            previous.write_text(json.dumps({"protocol": "M5_FORWARD_SHADOW_SETTLEMENT_V1",
                "paired_input_sha256": "a" * 64, "markets": {}}))
            current = root / "current.json"
            current.write_text(json.dumps({"protocol": "M5_FORWARD_SHADOW_SETTLEMENT_V1",
                "paired_input_sha256": "c" * 64}))
            with self.assertRaisesRegex(ValueError, "another pairing"):
                build_receipt(capture, previous, current)


if __name__ == "__main__":
    unittest.main()
