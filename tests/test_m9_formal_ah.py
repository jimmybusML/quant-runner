"""M9 formal-only semantics; offline tests cannot contact Crown or Telegram."""
import datetime as dt
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ops import m9_formal_ah as m9
from research.m3.m3_shadow_orders import choose as old_m3_choose
from research.m3.probabilities import settle_score


class TestM9FormalAH(unittest.TestCase):
    def test_identity_and_market_stable(self):
        self.assertEqual(m9.MODEL, "bivariate_poisson")
        self.assertEqual(m9.MARKET, "AH")
        self.assertEqual(m9.MAX_DATES, 2)

    def test_exact_single_line_formal_message_format(self):
        row={"kickoff":"2026-11-03T17:00:00Z","league":"Polish Ekstraklasa",
             "home":"Radomiak","away":"Wloclawek"}
        names={"competitions":{"polish ekstraklasa":"波兰甲级联赛"},
               "teams":{"radomiak":"拉多米亚克","wloclawek":"弗罗茨瓦克"}}
        message=m9.format_order_message(row,"away",{"line":-0.25},2.06,names)
        self.assertEqual(message,"【M9】2026-11-04 01:00 波兰甲级联赛 拉多米亚克 vs 弗罗茨瓦克 全场让球 弗罗茨瓦克 +0.25@1.06")
        self.assertEqual(message.count("\n"),0)
        self.assertNotIn("双变量泊松",message)

    def test_direction_matches_old_m3_neutral_odds_policy(self):
        grid = [[0.1, 0.15], [0.1, 0.65]]
        quote = {"line": -0.25, "home_decimal": 1.91, "away_decimal": 1.97}
        selected, price, scores = m9.choose(grid, quote)
        quotes = [{"side":"home","line":-0.25,"decimal_odd":1.91},
                  {"side":"away","line":-0.25,"decimal_odd":1.97}]
        old_selected, old_scores = old_m3_choose({"score_probability_grid":grid},"AH",quotes)
        self.assertEqual(selected, old_selected["side"])
        self.assertEqual(price, old_selected["decimal_odd"])
        self.assertEqual(scores, old_scores)

    def test_real_crown_receipt_preserves_exact_market_and_raw_hash(self):
        now = dt.datetime.now(dt.timezone.utc)
        source = (now-dt.timedelta(minutes=5)).astimezone(dt.timezone(dt.timedelta(hours=8)))
        quote_time = source.strftime("%Y-%m-%d %H:%M:%S")
        kickoff = (now+dt.timedelta(hours=4)).isoformat()
        data = {"success":1,"data":[{"id":"123","bookmakers":[
            {"slug":"crown","asian_list":[[0,"-0.25",1.92,1.96,quote_time,0,0]]}]}]}
        raw = json.dumps(data).encode()
        class Response:
            content = raw
            def raise_for_status(self):return None
            def json(self):return data
        with TemporaryDirectory() as folder:
            with patch.object(m9,"EVIDENCE",Path(folder)),patch.object(m9.requests,"get",return_value=Response()):
                result=m9.crown_ah("123","fake",kickoff)
                self.assertEqual(result["bookmaker"],"crown")
                self.assertTrue(result["bookmaker_verified"])
                self.assertEqual(result["line"],-0.25)
                self.assertEqual(result["home_decimal"],1.92)
                self.assertEqual(result["away_decimal"],1.96)
                self.assertEqual(Path(result["raw_path"]).read_bytes(),raw)
                self.assertEqual(result["raw_sha256"],m9.digest(raw))

    def test_absent_crown_is_never_relabelled_formal(self):
        now = dt.datetime.now(dt.timezone.utc)
        data={"success":1,"data":[{"id":"123","bookmakers":[{"slug":"other","asian_list":[]}]}]}
        class Response:
            content=b"{}"
            def raise_for_status(self):return None
            def json(self):return data
        with patch.object(m9.requests,"get",return_value=Response()):
            with self.assertRaisesRegex(ValueError,"Crown"):
                m9.crown_ah("123","fake",(now+dt.timedelta(hours=4)).isoformat())

    def test_confirmed_sent_only_and_unknown_not_formal(self):
        with TemporaryDirectory() as folder:
            folder=Path(folder)
            with patch.object(m9,"STATE",folder),patch.object(m9,"LEDGER",folder/"events.jsonl"):
                x={"kind":"M9_PREPARED","order_key":"M9_BIVARIATE_AH:123",
                   "fid":"123","model":"bivariate_poisson","market":"AH"}
                m9.append(x)
                m9.append({"kind":"M9_TG_UNKNOWN","order_key":x["order_key"],"fid":"123"})
                stats=m9.report()
                self.assertEqual(stats["sent"],0)
                self.assertEqual(stats["unknown"],1)
                m9.append({"kind":"M9_PREPARED","order_key":"M9_BIVARIATE_AH:456",
                    "fid":"456","model":"bivariate_poisson","market":"AH",
                    "crown":{"bookmaker_verified":True}})
                m9.append({"kind":"M9_TG_SENT","order_key":"M9_BIVARIATE_AH:456",
                    "fid":"456","telegram_message_id":"44","at_utc":m9.now()})
                stats=m9.report()
                self.assertEqual(stats["sent"],1)
                self.assertEqual(stats["settled"],0)
                self.assertEqual(stats["pending"],1)

    def test_asian_quarter_line_settlement(self):
        state,pnl=settle_score("AH",-0.25,"home",1,1,2.0)
        self.assertEqual(state,"HALF_LOSS")
        self.assertAlmostEqual(pnl,-0.5)
        state,pnl=settle_score("AH",-0.25,"away",1,1,2.0)
        self.assertEqual(state,"HALF_WIN")
        self.assertAlmostEqual(pnl,0.5)


if __name__=="__main__":
    unittest.main()
