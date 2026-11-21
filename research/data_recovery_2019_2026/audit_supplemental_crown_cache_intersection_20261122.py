#!/usr/bin/env python3
"""Read-only Crown raw-cache FID intersection for supplemental schedule batches."""
from __future__ import annotations

import gzip
import hashlib
import json
import pathlib
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "research/data_recovery_2019_2026"
SCHEDULE = OUT / "supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz"
RAW_HIST = pathlib.Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/raw/historical")
LEGACY_M5 = pathlib.Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses")
LEGACY_EPL = pathlib.Path("/Users/mac/QuantAsiaDesk/data/epl_laliga_crown_5seasons/raw_crown")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_schedule() -> dict[str, dict]:
    rows = {}
    with gzip.open(SCHEDULE, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            fid = str(row["fid"])
            rows[fid] = row
    return rows


def scan(root: pathlib.Path, *, parent_fid: bool) -> tuple[set[str], int, int]:
    fids: set[str] = set()
    file_count = 0
    non_json = 0
    if not root.exists():
        return fids, file_count, non_json
    for path in root.rglob("*.json"):
        if not path.is_file():
            continue
        file_count += 1
        fid = path.parent.name if parent_fid else path.stem
        if fid.isdigit():
            fids.add(fid)
        else:
            non_json += 1
    return fids, file_count, non_json


def main() -> None:
    schedule = read_schedule()
    all_fids = set(schedule)
    batch15 = {fid for fid, row in schedule.items() if str(row.get("provider_league_id")) in {
        "15", "57", "63", "121", "128", "210", "252", "270", "337", "542",
        "765", "10808", "10989", "11958", "11959"}}
    batch38 = all_fids - batch15
    sources = {}
    union = set()
    for name, root, parent in (
        ("crown_historical_raw", RAW_HIST, True),
        ("m5_authorized_legacy", LEGACY_M5, False),
        ("epl_laliga_legacy", LEGACY_EPL, False),
    ):
        fids, files, non_json = scan(root, parent_fid=parent)
        union |= fids
        overlap = all_fids & fids
        sources[name] = {
            "directory": str(root),
            "json_files_scanned": files,
            "files_without_numeric_fid_name": non_json,
            "numeric_fids": len(fids),
            "matched_53_batch_fids": len(overlap),
            "matched_batch15_fids": len(batch15 & fids),
            "matched_batch38_fids": len(batch38 & fids),
            "matched_fid_sha256": hashlib.sha256("\n".join(sorted(overlap)).encode()).hexdigest(),
        }
    result = {
        "study": "read-only filename/parent-FID lookup of existing raw Crown response caches; no API calls or writes",
        "schedule_file": str(SCHEDULE.relative_to(REPO)),
        "schedule_sha256": sha256(SCHEDULE),
        "unique_schedule_fids": len(all_fids),
        "batch15_unique_fids": len(batch15),
        "batch38_unique_fids": len(batch38),
        "raw_cache_source_results": sources,
        "union_of_raw_cache_fid_sets": {
            "unique_fids": len(union),
            "matched_53_batch_fids": len(all_fids & union),
            "matched_batch15_fids": len(batch15 & union),
            "matched_batch38_fids": len(batch38 & union),
        },
        "interpretation": "A filename/parent FID match establishes a local cache candidate only; response identity, bookmaker, AH content, raw SHA, and receive-time provenance require the corresponding cache index and response audit.",
    }
    (OUT / "supplemental_crown_raw_cache_intersection_20261122.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
