import json
from pathlib import Path

import pytest

from research.m5.m5_crown_quote_loss_drivers import run, summary


def row(fid: str, market: str, pnl: float, quote_kind: str, kickoff_hour: str) -> dict:
    category = "win" if pnl > 0 else "loss"
    distribution = {"win": 0.8, "half_win": 0.0, "push": 0.0,
                    "half_loss": 0.0, "loss": 0.2}
    if category == "loss":
        distribution = {"win": 0.2, "half_win": 0.0, "push": 0.0,
                        "half_loss": 0.0, "loss": 0.8}
    return {
        "fixture_id": fid, "market": market, "pnl_units": pnl,
        "settlement": category, "settlement_distribution": distribution,
        "quote_kind": quote_kind, "league": "Test League",
        "kickoff_utc": f"2026-01-01T{kickoff_hour}:00:00Z",
        "prediction_asof_utc": "2025-12-01T00:00:00Z",
        "train_end_utc": "2025-11-30T00:00:00Z",
        "quote_event_utc": f"2026-01-01T{int(kickoff_hour) - 1:02d}:00:00Z",
        "quote_received_utc": "2026-01-02T00:00:00Z",
        "quote_received_pre_kickoff": False,
    }


def test_loss_driver_report_keeps_markets_and_all_disjoint_rows(tmp_path: Path):
    rows = [row("1", "AH", 0.9, "open", "12"),
            row("2", "AH", -1.0, "close", "13"),
            row("3", "OU", 0.8, "close", "12")]
    private = tmp_path / "private.jsonl"
    private.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    markets = {m: summary([r for r in rows if r["market"] == m]) for m in ("AH", "OU")}
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"markets": markets, "forecast_sha256": "a" * 64,
                                  "candidate_manifest_sha256": "b" * 64,
                                  "response_hash_set_sha256": "c" * 64}))
    output = tmp_path / "public.json"
    report = run(private, source, output)
    assert report["markets"]["AH"]["overall"]["unique_fixture_markets"] == 2
    assert report["markets"]["AH"]["by_quote_kind"]["open"]["unique_fixture_markets"] == 1
    assert report["markets"]["AH"]["by_quote_kind"]["close"]["unique_fixture_markets"] == 1
    assert report["markets"]["OU"]["overall"]["unique_fixture_markets"] == 1
    serialized = output.read_text()
    assert '"fixture_id"' not in serialized and '"prices"' not in serialized


def test_loss_driver_report_rejects_duplicate_fixture_market(tmp_path: Path):
    item = row("1", "AH", 0.9, "open", "12")
    private = tmp_path / "private.jsonl"
    private.write_text(json.dumps(item) + "\n" + json.dumps(item) + "\n")
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"markets": {}, "forecast_sha256": "a" * 64,
                                  "candidate_manifest_sha256": "b" * 64,
                                  "response_hash_set_sha256": "c" * 64}))
    with pytest.raises(ValueError, match="duplicate fixture-market"):
        run(private, source, tmp_path / "out.json")
