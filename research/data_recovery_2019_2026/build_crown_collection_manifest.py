#!/usr/bin/env python3
"""Create a deduplicated historical Crown collection queue, without fetching.

The input inventory is already deduplicated by FID. Supplemental TotalCorner
rows extend it while preserving their source-page hashes. Existing historical
captures are excluded per data layer; live receipts do not satisfy a historical
backfill. Identity conflicts are reported and excluded rather than guessed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import sqlite3
from collections import Counter, defaultdict

IDENTITY_FIELDS = ("provider_league_id", "home_id", "away_id")


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_inventory(path: pathlib.Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def first_source(row: dict) -> dict:
    for key in ("totalcorner_page_records", "supplemental_schedule_records",
                "M1_history_cache_records", "crown_fixture_metadata_records"):
        items = row.get(key) or []
        if items:
            return items[0]
    return {}


def normalize(fid: str, league_id: str, source: dict, source_kind: str,
              source_hash: str | None = None) -> dict:
    return {
        "match_id": fid,
        "provider_league_id": league_id,
        "provider_league_name": source.get("league_name") or source.get("provider_league_name"),
        "kickoff_utc": source.get("kickoff_utc") or source.get("totalcorner_kickoff_utc"),
        "home_id": source.get("home_id"),
        "away_id": source.get("away_id"),
        "home_name": source.get("home_name"),
        "away_name": source.get("away_name"),
        "status_raw": source.get("status") or source.get("status_raw"),
        "home_goals_raw": source.get("home_goals") if source.get("home_goals") is not None else source.get("home_goals_raw"),
        "away_goals_raw": source.get("away_goals") if source.get("away_goals") is not None else source.get("away_goals_raw"),
        "collection_source_kind": source_kind,
        "schedule_source_page_sha256": source_hash,
    }


def add_record(records: dict, conflicts: dict, kickoff_conflicts: dict, row: dict) -> None:
    fid = row["match_id"]
    previous = records.get(fid)
    if previous is None:
        records[fid] = row
        return
    mismatches = {field: [previous.get(field), row.get(field)] for field in IDENTITY_FIELDS
                  if previous.get(field) and row.get(field) and str(previous[field]) != str(row[field])}
    if mismatches:
        conflicts.setdefault(fid, []).append({"existing": previous, "conflicting": row,
                                               "mismatched_identity_fields": mismatches})
        return
    if previous.get("kickoff_utc") and row.get("kickoff_utc") and str(previous["kickoff_utc"]) != str(row["kickoff_utc"]):
        kickoff_conflicts.setdefault(fid, set()).update((str(previous["kickoff_utc"]), str(row["kickoff_utc"])))
    for key, value in row.items():
        if previous.get(key) in (None, "") and value not in (None, ""):
            previous[key] = value
    previous.setdefault("source_rows", []).append({
        "source_kind": row.get("collection_source_kind"),
        "schedule_source_page_sha256": row.get("schedule_source_page_sha256"),
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=pathlib.Path, required=True)
    parser.add_argument("--supplemental-ledger", type=pathlib.Path, required=True)
    parser.add_argument("--sqlite", type=pathlib.Path, required=True)
    parser.add_argument("--layer", choices=("summary", "movement"), required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--audit-output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    records: dict[str, dict] = {}
    conflicts: dict[str, list] = {}
    kickoff_conflicts: dict[str, set[str]] = {}
    for item in read_inventory(args.inventory):
        fid = str(item.get("fid") or "")
        if not fid.isdigit():
            continue
        source = first_source(item)
        row = normalize(fid, str(item.get("provider_league_id") or ""), source,
                        "reconciled_inventory", source.get("page_sha256"))
        for source_conflict in item.get("identity_conflicts", []):
            if source_conflict.get("type") == "totalcorner_kickoff_utc_conflict":
                kickoff_conflicts.setdefault(fid, set()).update(map(str, source_conflict.get("dates", [])))
        add_record(records, conflicts, kickoff_conflicts, row)

    supplemental_rows = 0
    with args.supplemental_ledger.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            fid = str(row.get("fid") or "")
            league_id = str(row.get("provider_league_id") or "")
            if not fid.isdigit() or not league_id:
                continue
            normalized = normalize(fid, league_id, row, "supplemental_TotalCorner_schedule",
                                   row.get("source_page_response_sha256"))
            add_record(records, conflicts, kickoff_conflicts, normalized)
            supplemental_rows += 1

    uri = f"file:{args.sqlite}?mode=ro"
    cx = sqlite3.connect(uri, uri=True)
    try:
        historical_captured = {str(row[0]) for row in cx.execute(
            "SELECT DISTINCT fixture_id FROM capture WHERE data_layer=? AND capture_mode='historical'",
            (args.layer,))}
    finally:
        cx.close()

    conflict_fids = set(conflicts)
    candidates = []
    for fid, row in records.items():
        if fid in historical_captured or fid in conflict_fids:
            continue
        row = dict(row)
        if fid in kickoff_conflicts:
            # The fixture ID/team identity is consistent but source kickoff
            # dates conflict. Avoid injecting a guessed time; the collector
            # will use the start field in the exact response it consumes.
            row["kickoff_utc_source_conflict_values"] = sorted(kickoff_conflicts[fid])
            row["kickoff_utc"] = None
        candidates.append(row)
    candidates.sort(key=lambda row: (row.get("provider_league_id", ""),
                                     row.get("kickoff_utc") or "", int(row["match_id"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in candidates:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    by_league_year = Counter()
    for row in candidates:
        year = str(row.get("kickoff_utc") or "")[:4] or "UNKNOWN_YEAR"
        by_league_year[(row.get("provider_league_id"), year)] += 1
    audit = {
        "generated_from_read_only_sources": True,
        "layer": args.layer,
        "capture_mode_for_next_run": "historical",
        "inventory": str(args.inventory),
        "inventory_sha256": sha256(args.inventory),
        "supplemental_ledger": str(args.supplemental_ledger),
        "supplemental_ledger_sha256": sha256(args.supplemental_ledger),
        "supplemental_ledger_rows_read": supplemental_rows,
        "sqlite": str(args.sqlite),
        "historical_layer_capture_fids_excluded": len(historical_captured),
        "unique_union_fids": len(records),
        "identity_conflict_fids_excluded": len(conflict_fids),
        "kickoff_conflict_fids_included_without_hint": len(set(kickoff_conflicts) - conflict_fids),
        "candidate_fids_without_historical_capture_for_layer": len(candidates),
        "candidates_by_provider_league_and_kickoff_year": [
            {"provider_league_id": league, "kickoff_utc_year": year, "fids": n}
            for (league, year), n in sorted(by_league_year.items())],
        "conflicts": conflicts,
        "manifest": str(args.output),
        "manifest_sha256": sha256(args.output),
        "network_requests": 0,
        "sqlite_writes": 0,
    }
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(json.dumps({key: audit[key] for key in (
        "layer", "supplemental_ledger_rows_read", "unique_union_fids",
        "historical_layer_capture_fids_excluded", "identity_conflict_fids_excluded",
        "candidate_fids_without_historical_capture_for_layer", "manifest_sha256",
        "network_requests", "sqlite_writes")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
