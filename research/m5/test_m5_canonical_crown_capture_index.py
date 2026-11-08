import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m5_canonical_crown_capture_index import build_index, quote_rows


def test_quote_rows_keeps_only_post_asof_pre_kickoff_receipts():
    from research.m5.m5_canonical_crown_capture_index import instant

    asof = instant("2026-11-08T18:00:00Z")
    received = instant("2026-11-08T20:00:00Z")
    kickoff = instant("2026-11-08T21:00:00Z")
    book = {
        "asian": {
            "open": {"time": "2026-11-08T19:00:00Z", "line": -0.25, "home": 1.91, "away": 1.99},
            "close": {"time": "2026-11-08T20:01:00Z", "line": -0.5, "home": 1.95, "away": 1.95},
        },
        "goal": {
            "open": {"time": "2026-11-08T17:59:00Z", "line": 2.5, "over": 1.9, "under": 2.0},
            "close": {"time": "2026-11-08T19:30:00Z", "line": 2.5, "over": 1.92, "under": 1.98},
        },
    }
    assert quote_rows(book, "AH", asof, received, kickoff) == [
        {"quote_event_utc": "2026-11-08T19:00:00Z", "line": -0.25,
         "prices": [1.91, 1.99], "quote_kind": "open"}
    ]
    assert quote_rows(book, "OU", asof, received, kickoff) == [
        {"quote_event_utc": "2026-11-08T19:30:00Z", "line": 2.5,
         "prices": [1.92, 1.98], "quote_kind": "close"}
    ]


def test_build_index_verifies_live_identity_hash_and_both_markets(tmp_path: Path):
    kickoff = "2026-11-08T21:00:00Z"
    received = "2026-11-08T20:00:00Z"
    forecast = {
        "match_id": "12345", "league": "Test League", "home": "Home FC", "away": "Away FC",
        "kickoff_utc": kickoff, "prediction_asof_utc": "2026-11-08T18:00:00Z",
    }
    raw = {
        "success": 1,
        "data": [{
            "id": "12345", "l": "Test League", "h": "Home FC", "a": "Away FC", "start": kickoff,
            "bookmakers": [{"slug": "crown",
                "asian": {"open": {"time": "2026-11-08T19:00:00Z", "line": -0.25,
                                    "home": 1.91, "away": 1.99}},
                "goal": {"close": {"time": "2026-11-08T19:30:00Z", "line": 2.5,
                                    "over": 1.92, "under": 1.98}}}],
        }],
    }
    raw_bytes = json.dumps(raw).encode()
    raw_path = tmp_path / "raw.json"
    raw_path.write_bytes(raw_bytes)
    forecast_path = tmp_path / "forecast.jsonl"
    forecast_path.write_text(json.dumps(forecast) + "\n")
    database = tmp_path / "archive.sqlite3"
    with sqlite3.connect(database) as cx:
        cx.execute("""CREATE TABLE capture (
            fixture_id TEXT,response_received_at_utc TEXT,source_file TEXT,response_sha256 TEXT,
            kickoff_at_utc TEXT,prospective_observation INTEGER,capture_mode TEXT,data_layer TEXT)""")
        cx.execute("INSERT INTO capture VALUES (?,?,?,?,?,?,?,?)", (
            "12345", received, str(raw_path), hashlib.sha256(raw_bytes).hexdigest(),
            kickoff, 1, "live", "summary"))
    output = tmp_path / "normalized-index.jsonl"
    report = build_index(forecast_path, database, output)
    entry = json.loads(output.read_text().strip())
    assert report["verified_live_fixture_responses"] == 1
    assert report["AH_eligible_fixture_markets"] == 1
    assert report["OU_eligible_fixture_markets"] == 1
    assert entry["ah_qualified"] and entry["ou_qualified"]
    assert entry["captured_at_utc"] == received
    assert (output.stat().st_mode & 0o777) == 0o600


def test_instant_assumes_source_local_timezone_for_naive_timestamp():
    from research.m5.m5_canonical_crown_capture_index import instant

    assert instant("2026-11-09 04:00:00") == datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)
