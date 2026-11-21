#!/usr/bin/env python3
"""Prepare a historical Crown refresh queue for past-due unresolved FT rows.

This offline helper does not infer a score or issue requests. It excludes rows
classified as future/not due and carries exact FID/schedule provenance into the
existing Crown collector input. A refreshed response may still remain unverified.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import sqlite3
from collections import Counter


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_for(row: dict) -> dict:
    for key in ("totalcorner_page_records", "supplemental_schedule_records",
                "M1_history_cache_records", "crown_fixture_metadata_records"):
        if row.get(key):
            return row[key][0]
    return {}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--inventory", type=pathlib.Path, required=True)
    p.add_argument("--readiness", type=pathlib.Path, required=True)
    p.add_argument("--sqlite", type=pathlib.Path,
                   help="Read-only Crown store used with --only-existing-movement-capture")
    p.add_argument("--only-existing-movement-capture", action="store_true",
                   help="Leave FIDs without a historical movement capture to the movement-missing queue")
    p.add_argument("--output", type=pathlib.Path, required=True)
    p.add_argument("--audit-output", type=pathlib.Path, required=True)
    args = p.parse_args()

    inventory = {}
    with gzip.open(args.inventory, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            inventory[str(row.get("fid") or "")] = row

    movement_captured = None
    if args.only_existing_movement_capture:
        if args.sqlite is None:
            raise SystemExit("--sqlite is required with --only-existing-movement-capture")
        cx = sqlite3.connect(f"file:{args.sqlite}?mode=ro", uri=True)
        try:
            movement_captured = {str(row[0]) for row in cx.execute(
                "SELECT DISTINCT fixture_id FROM capture WHERE data_layer='movement' AND capture_mode='historical'")}
        finally:
            cx.close()

    readiness_rows = []
    excluded_no_movement_capture = 0
    with args.readiness.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            state = str(row.get("ft_readiness") or "")
            if state in {"future_fixture_not_due", "future_or_not_due", "future_not_due", "not_due"}:
                continue
            if state not in {"past_kickoff_status_missing_or_unknown", "provider_reports_non_full_status"}:
                continue
            fid = str(row.get("fid") or "")
            source_row = inventory.get(fid)
            if not fid.isdigit() or source_row is None:
                continue
            if movement_captured is not None and fid not in movement_captured:
                excluded_no_movement_capture += 1
                continue
            source = source_for(source_row)
            readiness_rows.append({
                "match_id": fid,
                "provider_league_id": str(row.get("provider_league_id") or source_row.get("provider_league_id") or ""),
                "kickoff_utc": row.get("kickoff_utc") or source_row.get("totalcorner_kickoff_utc"),
                "home_id": source.get("home_id"),
                "away_id": source.get("away_id"),
                "home_name": source.get("home_name"),
                "away_name": source.get("away_name"),
                "ft_readiness_before_refresh": state,
                "observed_statuses": row.get("observed_statuses"),
                "observed_scores": row.get("observed_scores"),
                "placeholder_0_0_present": row.get("placeholder_0_0_present"),
                "source_schedule_page_sha256": source.get("page_sha256"),
            })

    readiness_rows.sort(key=lambda r: (r.get("provider_league_id", ""),
                                       r.get("kickoff_utc") or "", int(r["match_id"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for row in readiness_rows:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    by_league_year = Counter((r["provider_league_id"], str(r.get("kickoff_utc") or "")[:4] or "UNKNOWN_YEAR")
                             for r in readiness_rows)
    audit = {
        "inventory": str(args.inventory), "inventory_sha256": sha256(args.inventory),
        "readiness_source": str(args.readiness), "readiness_source_sha256": sha256(args.readiness),
        "purpose": "request refreshed historical TotalCorner/Crown match response to seek current FT/status and preserve any available AH movement; not a score inference",
        "future_or_not_due_excluded": True,
        "only_existing_historical_movement_capture": args.only_existing_movement_capture,
        "excluded_to_movement_missing_capture_queue": excluded_no_movement_capture,
        "candidate_fids": len(readiness_rows),
        "candidates_by_provider_league_and_kickoff_year": [
            {"provider_league_id": league, "kickoff_utc_year": year, "fids": n}
            for (league, year), n in sorted(by_league_year.items())],
        "manifest": str(args.output), "manifest_sha256": sha256(args.output),
        "network_requests": 0, "sqlite_writes": 0,
    }
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in (
        "candidate_fids", "future_or_not_due_excluded",
        "only_existing_historical_movement_capture",
        "excluded_to_movement_missing_capture_queue", "manifest_sha256",
        "network_requests", "sqlite_writes")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
