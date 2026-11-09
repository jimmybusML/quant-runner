import hashlib
import json
import sqlite3
from pathlib import Path

from research.m5.m5_canonical_crown_summary_replay import (
    instant, market_quotes, run, valid_grid,
)


def test_summary_quote_window_separates_event_and_receipt_times():
    asof = instant("2026-11-08T18:00:00Z")
    received = instant("2026-11-08T22:00:00Z")
    kickoff = instant("2026-11-08T21:00:00Z")
    book = {"asian": {
        "open": {"time": "2026-11-08T17:00:00Z", "line": -0.25, "home": 1.91, "away": 1.99},
        "close": {"time": "2026-11-08T20:00:00Z", "line": -0.5, "home": 1.95, "away": 1.95},
    }}
    quotes = market_quotes(book, "AH", asof, received, kickoff, "Asia/Shanghai")
    assert quotes == [{"quote_kind": "close", "quote_event_utc": "2026-11-08T20:00:00Z",
                       "line": -0.5, "prices": [1.95, 1.95]}]


def test_valid_grid_requires_finite_normalized_probabilities():
    assert valid_grid([[0.5, 0.5], [0.0, 0.0]])
    assert not valid_grid([[0.4, 0.4], [0.0, 0.0]])
    assert not valid_grid([[float("nan")]])


def test_run_verifies_canonical_response_and_keeps_public_report_aggregate_only(tmp_path: Path):
    kickoff = "2026-11-08T21:00:00Z"
    forecast = {
        "match_id": "12345", "league": "Test League", "home": "Home FC", "away": "Away FC",
        "home_goals": 1, "away_goals": 0, "prediction_asof_utc": "2026-11-08T18:00:00Z",
        "train_end_utc": "2026-11-01T00:00:00Z",
        "prediction": {"grid": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]},
    }
    fixture = {"match_id": "12345", "league": "Test League", "home": "Home FC", "away": "Away FC",
               "home_goals": 1, "away_goals": 0, "kickoff_utc": kickoff}
    raw = {"success": 1, "data": [{
        "id": "12345", "l": "Test League", "h": "Home FC", "a": "Away FC",
        "hg": 1, "ag": 0, "start": kickoff,
        "bookmakers": [{"slug": "crown",
            "asian": {"close": {"time": "2026-11-08T20:00:00Z", "line": -0.5,
                                 "home": 1.95, "away": 1.95}},
            "goal": {"close": {"time": "2026-11-08T20:00:00Z", "line": 2.5,
                                "over": 1.9, "under": 2.0}},
        }],
    }]}
    raw_bytes = json.dumps(raw).encode()
    raw_path = tmp_path / "raw.json"
    raw_path.write_bytes(raw_bytes)
    forecast_path = tmp_path / "forecast.jsonl"
    forecast_path.write_text(json.dumps(forecast) + "\n")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"rows": [fixture]}))
    database = tmp_path / "archive.sqlite3"
    with sqlite3.connect(database) as cx:
        cx.execute("""CREATE TABLE capture (
            fixture_id TEXT,response_received_at_utc TEXT,source_file TEXT,response_sha256 TEXT,
            kickoff_at_utc TEXT,capture_mode TEXT,data_layer TEXT)""")
        cx.execute("INSERT INTO capture VALUES (?,?,?,?,?,?,?)", (
            "12345", "2026-11-08T22:00:00Z", str(raw_path), hashlib.sha256(raw_bytes).hexdigest(),
            kickoff, "historical", "summary"))
    private_rows = tmp_path / "private" / "rows.jsonl"
    report_path = tmp_path / "public-report.json"
    report = run(forecast_path, manifest_path, database, private_rows, report_path)
    assert report["unique_fixture_markets"] == {"AH": 1, "OU": 1}
    assert report["integrity"]["time_order_passed"] is True
    assert report["integrity"]["training_end_before_prediction_asof_before_kickoff"] is True
    assert report["audit_counts"].get("invalid_forecast_chronology", 0) == 0
    assert report["markets"]["AH"]["actual_response_receipt_timing"] == {"post_kickoff": 1}
    assert private_rows.exists() and (private_rows.stat().st_mode & 0o777) == 0o600
    public = json.loads(report_path.read_text())
    serialized = json.dumps(public)
    assert '"match_id"' not in serialized and '"prices"' not in serialized and '"score_grid"' not in serialized
