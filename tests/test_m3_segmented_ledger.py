import json
import unittest
from research.m3.segmented_ledger import split_lines
from research.m3.shadow_performance_report import summarize
from pathlib import Path
from tempfile import TemporaryDirectory


class M3StorageAndOneOrderStats(unittest.TestCase):
    def test_segments_preserve_all_events_in_original_order(self):
        events = [{"event_id": str(i), "text": "汉字" * 40} for i in range(2500)]
        chunks = split_lines(events)
        result = [json.loads(line) for chunk in chunks for line in chunk]
        self.assertEqual(events, result)

    def test_per_fixture_model_market_earliest_order_only(self):
        a = {"protocol": "M3_SHADOW_ORDER_V1", "event_id": "first", "fixture_identity_id": "game", "model": "poisson", "market": "AH", "side": "home", "line": -0.5, "forecasted_at_utc": "2026-10-01T01:00:00Z"}
        b = {**a, "event_id": "later", "forecasted_at_utc": "2026-10-01T02:00:00Z"}
        settle = {"protocol": "M3_TOTALCORNER_FORWARD_SETTLEMENT_V1", "event_id": "settle", "shadow_order_event_id": "first", "market": "AH", "side": "home", "line": -0.5, "settlement_state": "FULL_WIN", "hypothetical_unit_return": 0.9}
        with TemporaryDirectory() as t:
            p = Path(t) / 'mini.jsonl'
            p.write_text(''.join(json.dumps(e) + '\n' for e in (a,b,settle)))
            result = summarize(p)
        self.assertEqual(result["raw_shadow_order_events"], 2)
        self.assertEqual(result["unique_shadow_orders"], 1)
        self.assertEqual(result["models"]["poisson"]["AH"]["settled"], 1)
        self.assertAlmostEqual(result["models"]["poisson"]["AH"]["net_units"], 0.9)


if __name__ == '__main__':
    unittest.main()
