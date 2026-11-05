import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

from research.m3 import totalcorner_crown_live_probe as probe


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps({
            "success": 1,
            "data": [{
                "id": "fixture-secret-id",
                "bookmakers": [{
                    "slug": "crown",
                    "asian_list": [["x", "x", "1.91", "1.99"]],
                    "goal_list": [["x", "x", "1.88", "2.02"]],
                }],
            }],
        }).encode()


class CrownLiveProbeTests(unittest.TestCase):
    def test_probe_only_requests_crown_and_redacts_ids_and_prices(self):
        requests = []

        def open_request(request, timeout):
            requests.append(request.full_url)
            return _Response()

        out = io.StringIO()
        with patch.dict(os.environ, {"TOTALCORNER_TOKEN": "do-not-print"}), \
                patch("sys.argv", ["probe", "--ids", "fixture-secret-id"]), \
                patch.object(probe.urllib.request, "urlopen", side_effect=open_request), \
                patch.object(probe.time, "sleep"), \
                contextlib.redirect_stdout(out):
            probe.main()

        self.assertEqual(len(requests), 1)
        self.assertIn("bookmaker=crown", requests[0])
        self.assertIn("bookmaker_odds/fixture-secret-id", requests[0])
        self.assertNotIn("match/odds/", requests[0])
        self.assertNotIn("fixture-secret-id", out.getvalue())
        self.assertNotIn("do-not-print", out.getvalue())
        self.assertNotIn("1.91", out.getvalue())
        self.assertEqual(json.loads(out.getvalue())["status"], "CROWN_IDENTIFIED")


if __name__ == "__main__":
    unittest.main()
