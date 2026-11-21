#!/usr/bin/env python3
"""Build deduplicated Crown-collector inputs from recovered TotalCorner schedules.

This is a local data-preparation utility only. It performs no network requests
and never writes to the Crown SQLite store. It preserves schedule provenance in
each row while emitting the ``match_id`` field expected by the existing Crown
capture collector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections import Counter


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-ledger", type=pathlib.Path, required=True)
    parser.add_argument("--targets", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    target_doc = json.loads(args.targets.read_text(encoding="utf-8"))
    target_ids = {str(row["provider_league_id"]) for row in target_doc["competitions"]}
    fixtures: dict[str, dict] = {}
    by_league: Counter[str] = Counter()
    duplicate_rows = 0
    with args.fixture_ledger.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid fixture ledger JSON at line {line_number}: {exc}")
            league_id = str(row.get("provider_league_id") or "")
            if league_id not in target_ids:
                continue
            fid = str(row.get("fid") or "")
            if not fid.isdigit():
                raise SystemExit(f"non-numeric FID at line {line_number}: {fid!r}")
            normalized = {
                "match_id": fid,
                "provider_league_id": league_id,
                "provider_league_name": row.get("provider_league_name"),
                "kickoff_utc": row.get("kickoff_utc"),
                "home_id": row.get("home_id"),
                "away_id": row.get("away_id"),
                "home_name": row.get("home_name"),
                "away_name": row.get("away_name"),
                "status_raw": row.get("status_raw"),
                "home_goals_raw": row.get("home_goals_raw"),
                "away_goals_raw": row.get("away_goals_raw"),
                "schedule_source": row.get("source_platform"),
                "schedule_source_endpoint": row.get("source_endpoint"),
                "schedule_source_page": row.get("source_page"),
                "schedule_response_received_at_utc": row.get("response_received_at_utc"),
                "schedule_response_sha256": row.get("source_page_response_sha256"),
                "schedule_record_sha256": row.get("source_record_sha256"),
            }
            previous = fixtures.get(fid)
            if previous is not None:
                duplicate_rows += 1
                identity_keys = ("provider_league_id", "home_id", "away_id", "kickoff_utc")
                if any(previous.get(key) != normalized.get(key) for key in identity_keys):
                    raise SystemExit(f"conflicting fixture identity for FID {fid}")
                continue
            fixtures[fid] = normalized
            by_league[league_id] += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for fid in sorted(fixtures, key=int):
            stream.write(json.dumps(fixtures[fid], ensure_ascii=False, separators=(",", ":")) + "\n")

    report = {
        "fixture_ledger": str(args.fixture_ledger),
        "fixture_ledger_sha256": sha256(args.fixture_ledger),
        "targets": str(args.targets),
        "targets_sha256": sha256(args.targets),
        "target_provider_league_ids": len(target_ids),
        "unique_fixture_fids": len(fixtures),
        "duplicate_ledger_rows_skipped": duplicate_rows,
        "fids_by_provider_league_id": dict(sorted(by_league.items(), key=lambda item: int(item[0]))),
        "manifest": str(args.output),
        "manifest_sha256": sha256(args.output),
        "network_requests": 0,
        "crown_sqlite_writes": 0,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
