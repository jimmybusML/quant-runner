#!/usr/bin/env python3
"""Verify M1 full-time rows omitted from the current unresolved FT ledger."""
from __future__ import annotations

import collections
import gzip
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
UNVERIFIED = ROOT / "ft_reconciliation_targets_before_M1_M5_Crown_20261122.jsonl.gz"
OUT = ROOT / "m1_ft_evidence_in_unverified_ledger_20261122.jsonl"
SUMMARY = ROOT / "m1_ft_evidence_in_unverified_ledger_20261122.json"


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
    unresolved = {str(json.loads(line)["fid"]) for line in gzip.open(UNVERIFIED, "rt", encoding="utf-8") if line.strip()}
    hashes: dict[Path, str] = {}
    output = []
    failures = collections.Counter()
    for line in gzip.open(INVENTORY, "rt", encoding="utf-8"):
        fixture = json.loads(line)
        fid = str(fixture.get("fid"))
        if fid not in unresolved:
            continue
        for record in fixture.get("M1_history_cache_records", []):
            if str(record.get("status", "")).casefold() != "full":
                continue
            source = Path(str(record.get("source_file") or ""))
            if not source.is_file():
                failures["m1_source_file_missing"] += 1
                continue
            if source not in hashes:
                hashes[source] = sha256(source)
            doc = json.loads(source.read_text(encoding="utf-8"))
            raw = [x for x in doc.get("rows", []) if str(x.get("id")) == fid]
            if len(raw) != 1:
                failures["exact_fid_row_not_unique"] += 1
                continue
            event = raw[0]
            checks = {
                "provider_league_id": str(event.get("l_id")) == str(fixture.get("provider_league_id")),
                "home_id": str(event.get("h_id")) == str(record.get("home_id")),
                "away_id": str(event.get("a_id")) == str(record.get("away_id")),
                "home_name": norm(event.get("h")) == norm(record.get("home_name")),
                "away_name": norm(event.get("a")) == norm(record.get("away_name")),
                "full_status": str(event.get("status", "")).casefold() == "full",
                "score": (str(event.get("hg")), str(event.get("ag"))) == (str(record.get("home_goals")), str(record.get("away_goals"))),
                "source_start": str(event.get("start")) == str(record.get("kickoff_source")),
            }
            if not all(checks.values()):
                for key, passed in checks.items():
                    if not passed:
                        failures[f"source_row_{key}_mismatch"] += 1
                continue
            alt_kickoffs = sorted({str(x.get("kickoff_utc")) for x in fixture.get("totalcorner_page_records", []) if x.get("kickoff_utc")})
            official_kickoff = fixture.get("totalcorner_kickoff_utc")
            output.append({
                "fid": fid,
                "provider_league_id": str(fixture.get("provider_league_id")),
                "home_id": str(event.get("h_id")),
                "away_id": str(event.get("a_id")),
                "home_name": event.get("h"),
                "away_name": event.get("a"),
                "status": "full",
                "home_goals": int(event["hg"]),
                "away_goals": int(event["ag"]),
                "M1_kickoff_utc": record.get("kickoff_utc"),
                "inventory_kickoff_utc": official_kickoff,
                "kickoff_versions_differ": bool(official_kickoff and record.get("kickoff_utc") != official_kickoff),
                "schedule_kickoff_versions": alt_kickoffs,
                "source_cache_file": source.name,
                "source_cache_sha256": hashes[source],
                "crosscheck": "exact FID in saved M1 cache; exact league/team IDs and normalized team names; raw cache row has status full and numeric FT",
            })
    output.sort(key=lambda x: int(x["fid"]))
    OUT.write_text("".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in output), encoding="utf-8")
    summary = {
        "unverified_input_rows": len(unresolved),
        "unverified_input_sha256": sha256(UNVERIFIED),
        "inventory_sha256": sha256(INVENTORY),
        "raw_M1_cache_files_checked": len(hashes),
        "raw_M1_cache_file_sha256": {p.name: h for p, h in sorted(hashes.items(), key=lambda x: x[0].name)},
        "verified_unique_FIDs_found_in_M1_cache": len({x["fid"] for x in output}),
        "kickoff_version_disagreements": sum(x["kickoff_versions_differ"] for x in output),
        "failed_row_checks": dict(sorted(failures.items())),
        "output": OUT.name,
        "output_sha256": sha256(OUT),
        "network_requests": 0,
        "crown_sqlite_writes": 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
