"""Local dashboard self-checks; no real API or Telegram requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import model_test


class FakeResponse:
    def __init__(self, payload):
        self.data=json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.data


class DashboardConnectionsTests(unittest.TestCase):
    def test_all_models_have_real_readonly_core_check(self):
        for key in ("m1","mr1","m3","m4"):
            with self.subTest(key):
                res=model_test.offline_test(key)
                self.assertTrue(res["ok"],res["message"])

    def test_batch_validates_names_and_saves_only_values_provided(self):
        with patch.object(app,"put_credential") as store:
            got=app.put_credential_batch({
                "M1_TELEGRAM_BOT_TOKEN": "fake-test-token",
                "M1_TELEGRAM_CHAT_ID": "",
            })
        self.assertEqual(got, ["M1_TELEGRAM_BOT_TOKEN"])
        store.assert_called_once_with("M1_TELEGRAM_BOT_TOKEN", "fake-test-token")
        with self.assertRaises(ValueError):
            app.put_credential_batch({"UNKNOWN_SECRET":"x"})

    def test_telegram_missing_credentials_never_calls_network(self):
        with patch.object(model_test.urllib.request,"urlopen") as urlopen:
            got=model_test.telegram_test("m3","","")
        self.assertEqual(got["status"],"missing")
        urlopen.assert_not_called()

    def test_confirmed_test_only_receipt_is_separate_from_official_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            temporary=Path(folder)/"test-receipts.jsonl"
            with patch.object(model_test,"RECEIPTS",temporary):
                with patch.object(model_test.urllib.request,"urlopen",
                            return_value=FakeResponse({"ok":True,"result":{"message_id":37}})) as send:
                    response=model_test.telegram_test("m1","dummy","123")
            self.assertEqual(response["status"],"sent")
            data=json.loads(temporary.read_text().strip())
            self.assertEqual(data["kind"],"TEST_ONLY")
            self.assertEqual(data["message_id"],"37")
            self.assertNotIn("dummy",str(data))
            self.assertEqual(send.call_count,1)

    def test_chat_finder_exposes_chats_not_message_text(self):
        fixture={"ok":True,"result":[
          {"update_id":1,"message":{"chat":{"id":123,"first_name":"甲","type":"private"},"text":"sensitive text"}},
          {"update_id":2,"message":{"chat":{"id":-1001,"title":"量化群","type":"supergroup"}}},
          {"update_id":3,"message":{"chat":{"id":123,"first_name":"甲","type":"private"}}}
        ]}
        with patch.object(model_test.urllib.request,"urlopen",return_value=FakeResponse(fixture)):
            r=model_test.discover_chat_ids("dummy")
        self.assertTrue(r["ok"])
        self.assertEqual([c["id"] for c in r["chats"]],["123","-1001"])
        self.assertNotIn("sensitive text",json.dumps(r,ensure_ascii=False))


if __name__=="__main__":
    unittest.main()
