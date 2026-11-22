#!/usr/bin/env python3
"""Audit full-time scores embedded in existing historical Crown captures.

Reads the local Crown SQLite and raw responses only. No network requests or
database writes are performed. The output contains result evidence only; quote
prices remain separate and are not modified.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
UNVERIFIED = ROOT / "ft_reconciliation_targets_before_crown_20261122.jsonl.gz"
DB = Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
DATA_ROOT = Path("/Users/mac/QuantAsiaDesk/data")
OUT = ROOT / "crown_capture_verified_ft_overlay_2019_2026_20261122.jsonl"
SUMMARY = ROOT / "crown_capture_verified_ft_overlay_2019_2026_20261122.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text if c.isalnum())


def main() -> None:
    unresolved = {str(json.loads(line)["fid"]): json.loads(line)
                  for line in gzip.open(UNVERIFIED, "rt", encoding="utf-8") if line.strip()}
    inventory = {}
    for line in gzip.open(INVENTORY, "rt", encoding="utf-8"):
        row = json.loads(line)
        if str(row["fid"]) in unresolved:
            inventory[str(row["fid"])] = row

    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    db.execute("BEGIN")
    captures = [row for row in db.execute(
        "SELECT capture_key,fixture_id,data_layer,capture_mode,status,response_received_at_utc,source_file,response_sha256,kickoff_at_utc,quote_count "
        "FROM capture") if str(row[1]) in unresolved]
    reject = collections.Counter()
    accepted = {}
    conflicting_fids: set[str] = set()
    for key, fid_raw, layer, mode, capture_status, received, source_file, digest, kickoff, quote_count in captures:
        fid = str(fid_raw)
        if fid in conflicting_fids:
            reject["additional_row_for_conflicting_verified_crown_score"] += 1
            continue
        if mode != "historical":
            reject["not_historical_capture"] += 1
            continue
        raw_path = Path(str(source_file or ""))
        try:
            rel = raw_path.relative_to(DATA_ROOT)
        except ValueError:
            reject["raw_path_outside_authorized_data_root"] += 1
            continue
        if not raw_path.is_file() or not digest or sha256(raw_path) != digest:
            reject["raw_missing_or_sha_mismatch"] += 1
            continue
        try:
            response = json.loads(raw_path.read_text(encoding="utf-8"))
        except Exception:
            reject["raw_json_invalid"] += 1
            continue
        if response.get("success") not in (1, "1", True):
            reject["raw_response_not_success"] += 1
            continue
        events = [row for row in response.get("data", []) if str(row.get("id")) == fid]
        if len(events) != 1:
            reject["raw_fid_not_unique"] += 1
            continue
        event = events[0]
        if str(event.get("status", "")).casefold() != "full":
            reject["raw_status_not_full"] += 1
            continue
        try:
            hg, ag = int(event["hg"]), int(event["ag"])
        except (KeyError, TypeError, ValueError):
            reject["raw_score_not_numeric"] += 1
            continue
        fixture = inventory[fid]
        if str(event.get("l_id")) != str(fixture.get("provider_league_id")):
            reject["provider_league_id_mismatch"] += 1
            continue
        if str(kickoff or "") != str(fixture.get("totalcorner_kickoff_utc") or ""):
            reject["inventory_kickoff_mismatch"] += 1
            continue
        sources = []
        for name in ("totalcorner_page_records", "M1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
            sources.extend(fixture.get(name, []))
        exact_identity = any(
            str(src.get("home_id")) == str(event.get("h_id"))
            and str(src.get("away_id")) == str(event.get("a_id"))
            and norm(src.get("home_name")) == norm(event.get("h"))
            and norm(src.get("away_name")) == norm(event.get("a"))
            for src in sources
        )
        if not exact_identity:
            reject["home_away_identity_mismatch"] += 1
            continue
        row = {
            "fid": fid,
            "provider_league_id": str(fixture["provider_league_id"]),
            "kickoff_utc": kickoff,
            "home_id": str(event.get("h_id")),
            "away_id": str(event.get("a_id")),
            "home_name": event.get("h"),
            "away_name": event.get("a"),
            "status": "full",
            "home_goals": hg,
            "away_goals": ag,
            "source": "Crown historical raw fixture response; full-time result only, not an odds source substitution",
            "capture_key": key,
            "data_layer": layer,
            "capture_mode": mode,
            "capture_status": capture_status,
            "quote_count": quote_count,
            "response_received_at_utc": received,
            "raw_response_relative_path": rel.as_posix(),
            "raw_response_sha256": digest,
        }
        old = accepted.get(fid)
        if old is not None and (old["home_goals"], old["away_goals"]) != (hg, ag):
            reject["conflicting_verified_crown_scores"] += 1
            accepted.pop(fid, None)
            conflicting_fids.add(fid)
            continue
        if old is None:
            accepted[fid] = row

    rows = [accepted[fid] for fid in sorted(accepted, key=int)]
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    summary = {
        "unverified_input_fids": len(unresolved),
        "unverified_input_sha256": sha256(UNVERIFIED),
        "inventory_sha256": sha256(INVENTORY),
        "crown_database_read_only": True,
        "capture_rows_intersecting_current_gap": len(captures),
        "verified_ft_unique_fids": len(rows),
        "verified_ft_by_layer": dict(sorted(collections.Counter(row["data_layer"] for row in rows).items())),
        "verified_ft_by_capture_status": dict(sorted(collections.Counter(row["capture_status"] for row in rows).items())),
        "conflicting_verified_score_fids_excluded": len(conflicting_fids),
        "rejected_capture_rows": dict(sorted(reject.items())),
        "database_sha256_stability": "not asserted while historical collector is writing; retain capture_key, raw SHA and response receive timestamp per row",
        "network_requests": 0,
        "database_writes": 0,
        "output_file": OUT.name,
        "output_sha256": sha256(OUT),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
