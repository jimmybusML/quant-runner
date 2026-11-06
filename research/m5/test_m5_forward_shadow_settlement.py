import unittest
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from research.m5.m5_forward_shadow_settlement import run, summarize, verified_final, settle_pair


class ForwardShadowSettlementTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {"match_id": "fixture-1", "league": "League", "home": "Home",
                        "away": "Away", "kickoff_utc": "2026-11-06T15:00:00Z"}
        self.payload = {"success": 1, "data": [{"id": "fixture-1", "l": "League",
                         "h": "Home", "a": "Away", "start": "2026-11-06 23:00",
                         "status": "FT", "hg": "2", "ag": "1"}]}

    def test_verifies_identity_kickoff_and_post_kickoff_receipt(self):
        result = verified_final(self.payload, self.fixture, "2026-11-06T17:10:00Z", "raw-sha")
        self.assertEqual((result["home_goals"], result["away_goals"]), (2, 1))
        self.assertEqual(result["response_sha256"], "raw-sha")
        with self.assertRaisesRegex(ValueError, "after kickoff"):
            verified_final(self.payload, self.fixture, "2026-11-06T14:59:00Z", "raw-sha")

    def test_rejects_fixture_and_kickoff_mismatch(self):
        wrong = {**self.fixture, "away": "Other"}
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            verified_final(self.payload, wrong, "2026-11-06T17:10:00Z", "raw-sha")
        wrong = {**self.fixture, "kickoff_utc": "2026-11-06T15:01:00Z"}
        with self.assertRaisesRegex(ValueError, "kickoff mismatch"):
            verified_final(self.payload, wrong, "2026-11-06T17:10:00Z", "raw-sha")

    def test_settles_ah_and_ou_independently_and_summarizes(self):
        result = {"home_goals": 2, "away_goals": 1,
                  "observed_at_utc": "2026-11-06T17:10:00Z", "response_sha256": "raw-sha"}
        common = {**self.fixture, "source": "Crown", "line": 0.0,
                  "prices": [1.9, 1.9], "quote_event_utc": "2026-11-06T14:00:00Z",
                  "quote_received_utc": "2026-11-06T14:05:00Z",
                  "prediction_asof_utc": "2026-11-06T13:00:00Z",
                  "train_end_utc": "2026-11-05T00:00:00Z", "score_grid": [[1.0]]}
        ah = settle_pair({**common, "market": "AH"}, result)
        self.assertEqual(ah["settlement"], "win")
        self.assertAlmostEqual(ah["pnl_units"], 0.9)
        row = {**ah, "market": "OU", "settlement": "loss", "pnl_units": -1.0}
        report = summarize([ah, row], "AH", [ah, row])
        self.assertEqual(report["settled_bets"], 1)
        self.assertEqual(report["roi_pct"], 90.0)
        self.assertEqual(report["settlement_counts"]["win"], 1)

    def test_preserves_quarter_handicap_half_loss(self):
        pair = {**self.fixture, "market": "AH", "source": "TotalCorner_default",
                "line": -0.25, "prices": [1.9, 1.9],
                "quote_event_utc": "2026-11-06T14:00:00Z",
                "quote_received_utc": "2026-11-06T14:05:00Z",
                "prediction_asof_utc": "2026-11-06T13:00:00Z",
                "train_end_utc": "2026-11-05T00:00:00Z",
                "score_grid": [[0.0, 0.0], [0.0, 0.0], [1.0, 0.0]]}
        result = {"home_goals": 0, "away_goals": 0,
                  "observed_at_utc": "2026-11-06T17:10:00Z", "response_sha256": "raw-sha"}
        settled = settle_pair(pair, result)
        self.assertEqual(settled["side"], "home")
        self.assertEqual(settled["settlement"], "half_loss")
        self.assertEqual(settled["pnl_units"], -0.5)

    def test_pending_bets_keep_final_roi_null(self):
        pending = {"market": "AH", "source": "Crown"}
        report = summarize([], "AH", [pending])
        self.assertEqual(report["simulated_bets"], 1)
        self.assertEqual(report["settled_bets"], 0)
        self.assertEqual(report["pending_bets"], 1)
        self.assertIsNone(report["roi_pct"])

    def test_run_keeps_future_cohort_pending_without_network_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            kickoff = datetime.now(timezone.utc) + timedelta(days=1)
            pair = {"match_id": "fixture-1", "market": "AH", "league": "League",
                    "home": "Home", "away": "Away",
                    "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                    "source": "Crown", "line": 0.0, "prices": [1.9, 1.9],
                    "quote_event_utc": (kickoff - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
                    "quote_received_utc": (kickoff - timedelta(hours=2) + timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
                    "prediction_asof_utc": (kickoff - timedelta(hours=3)).isoformat().replace("+00:00", "Z"),
                    "train_end_utc": (kickoff - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
                    "score_grid": [[1.0]]}
            pairs_path = root / "pairs.jsonl"
            pairs_path.write_text(json.dumps(pair) + "\n", encoding="utf-8")
            summary_path = root / "summary.json"
            with patch("research.m5.m5_forward_shadow_settlement.token_value", return_value="unused"), \
                 patch("research.m5.m5_forward_shadow_settlement.request_json",
                       side_effect=AssertionError("future fixture must not call the API")):
                report = run(root / "private", pairs_path, summary_path)
            self.assertEqual(report["markets"]["AH"]["simulated_bets"], 1)
            self.assertEqual(report["markets"]["AH"]["pending_bets"], 1)
            self.assertIsNone(report["markets"]["AH"]["roi_pct"])


if __name__ == "__main__":
    unittest.main()
