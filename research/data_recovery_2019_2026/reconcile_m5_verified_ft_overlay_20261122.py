#!/usr/bin/env python3
"""Strictly reconcile archived M5 TotalCorner result responses to the FID inventory.

The raw responses remain in the authorized local data store. This script emits
only a sanitized evidence index with response hashes and exact fixture identity.
It does not make network requests or alter the Crown database.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
UNVERIFIED = ROOT / "ft_reconciliation_targets_before_M1_M5_Crown_20261122.jsonl.gz"
INDEX = Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/forward-shadow/verified-ft-index.jsonl")
RAW_ROOT = INDEX.parent
OUT = ROOT / "m5_verified_ft_overlay_2019_2026_20261122.jsonl"
SUMMARY = ROOT / "m5_verified_ft_overlay_2019_2026_20261122.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s if c.isalnum())


def main() -> None:
    asof = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    unresolved = {str(json.loads(line)["fid"]) for line in gzip.open(UNVERIFIED, "rt", encoding="utf-8") if line.strip()}
    inventory = {}
    with gzip.open(INVENTORY, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["fid"] in unresolved:
                inventory[str(row["fid"])] = row

    counts = collections.Counter()
    rejects = collections.Counter()
    accepted = {}
    for line in INDEX.open(encoding="utf-8"):
        row = json.loads(line)
        fid = str(row.get("match_id") or "")
        if fid not in unresolved:
            continue
        counts["index_rows_in_current_ft_gap"] += 1
        if row.get("status") != "verified_ft":
            rejects["index_not_verified_ft"] += 1
            continue
        raw_rel = str(row.get("raw_response_relative_path") or "")
        raw = RAW_ROOT / raw_rel
        expected_sha = row.get("response_sha256")
        if not raw.is_file() or not expected_sha or sha256(raw) != expected_sha:
            rejects["raw_missing_or_sha_mismatch"] += 1
            continue
        try:
            response = json.loads(raw.read_text(encoding="utf-8"))
        except Exception:
            rejects["raw_json_invalid"] += 1
            continue
        if response.get("success") not in (1, "1", True):
            rejects["raw_response_not_success"] += 1
            continue
        events = [x for x in response.get("data", []) if str(x.get("id")) == fid]
        if len(events) != 1:
            rejects["raw_fid_not_unique"] += 1
            continue
        event = events[0]
        fixture = inventory.get(fid)
        if fixture is None:
            rejects["fid_not_in_inventory"] += 1
            continue
        if str(event.get("l_id")) != str(fixture.get("provider_league_id")):
            rejects["provider_league_id_mismatch"] += 1
            continue
        if str(event.get("status", "")).casefold() != "full":
            rejects["raw_status_not_full"] += 1
            continue
        try:
            score = (int(event["hg"]), int(event["ag"]))
            indexed_score = (int(row["home_goals"]), int(row["away_goals"]))
        except (KeyError, TypeError, ValueError):
            rejects["score_not_numeric"] += 1
            continue
        if score != indexed_score:
            rejects["index_score_mismatch"] += 1
            continue
        source_rows = fixture.get("totalcorner_page_records", []) + fixture.get("M1_history_cache_records", [])
        identities = [x for x in source_rows
                      if str(x.get("provider_league_id") or x.get("league_id") or "") == str(fixture.get("provider_league_id"))
                      and str(x.get("home_id")) == str(event.get("h_id"))
                      and str(x.get("away_id")) == str(event.get("a_id"))
                      and norm(x.get("home_name")) == norm(event.get("h"))
                      and norm(x.get("away_name")) == norm(event.get("a"))]
        if not identities:
            rejects["team_or_id_identity_mismatch"] += 1
            continue
        if row.get("kickoff_utc") != fixture.get("totalcorner_kickoff_utc"):
            rejects["index_kickoff_mismatch"] += 1
            continue
        accepted[fid] = {
            "fid": fid,
            "provider_league_id": str(fixture["provider_league_id"]),
            "kickoff_utc": fixture.get("totalcorner_kickoff_utc"),
            "home_id": str(event.get("h_id")),
            "away_id": str(event.get("a_id")),
            "home_name": event.get("h"),
            "away_name": event.get("a"),
            "status": "full",
            "home_goals": score[0],
            "away_goals": score[1],
            "source": "authorized M5 archived TotalCorner /match/view response; result only, not Crown odds",
            "response_received_at_utc": row.get("captured_at_utc"),
            "raw_response_relative_path": raw_rel,
            "raw_response_sha256": expected_sha,
            "index_file_sha256": sha256(INDEX),
            "inventory_identity_crosscheck": "exact FID, provider league ID, home/away IDs and normalized names; UTC kickoff exact",
        }

    rows = [accepted[fid] for fid in sorted(accepted, key=int)]
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in rows), encoding="utf-8")
    summary = {
        "generated_at_utc": asof,
        "scope": "M5 verified-Ft index rows intersecting the 203,962-FID unresolved FT ledger",
        "unverified_input_sha256": sha256(UNVERIFIED),
        "inventory_sha256": sha256(INVENTORY),
        "M5_index_sha256": sha256(INDEX),
        "index_rows_intersecting_gap": counts["index_rows_in_current_ft_gap"],
        "accepted_unique_fids": len(rows),
        "reject_counts": dict(sorted(rejects.items())),
        "network_requests": 0,
        "crown_sqlite_writes": 0,
        "output_file": OUT.name,
        "output_sha256": sha256(OUT),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
