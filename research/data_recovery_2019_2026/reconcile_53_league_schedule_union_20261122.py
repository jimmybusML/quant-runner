#!/usr/bin/env python3
"""Append the audited 53-league TotalCorner schedule batch to the inventory.

This is an offline, append-only reconciliation artifact. It does not modify the
baseline inventory, contact Crown/TotalCorner, or infer seasons from dates.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "fixture_inventory_2019_2026.jsonl.gz"
SUPP = ROOT / "supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz"
OUT = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
SUMMARY = ROOT / "schedule_union_53_leagues_reconciliation_20261122.json"
UNVERIFIED = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
UTC = dt.timezone.utc


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def scope_year(row):
    value = row.get("kickoff_utc")
    if not value:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if x.tzinfo is None:
            return None
        x = x.astimezone(UTC)
        return x.year if 2019 <= x.year <= 2026 else None
    except (ValueError, TypeError):
        return None


def normalize(row):
    y = scope_year(row)
    supplemental = {
        "source_file": str(SUPP),
        "source_record_sha256": row.get("source_record_sha256"),
        "source_response_sha256": row.get("source_page_response_sha256"),
        "provider_league_id": str(row.get("provider_league_id") or ""),
        "league_name": row.get("provider_league_name"),
        "kickoff_source": row.get("kickoff_source_raw"),
        "kickoff_utc": row.get("kickoff_utc"),
        "home_id": str(row.get("home_id") or ""),
        "away_id": str(row.get("away_id") or ""),
        "home_name": row.get("home_name"),
        "away_name": row.get("away_name"),
        "status": row.get("status_raw"),
        "home_goals": row.get("home_goals_raw"),
        "away_goals": row.get("away_goals_raw"),
        "season": row.get("season_raw"),
        "observed_at_utc": row.get("response_received_at_utc"),
        "source_page": row.get("source_page"),
        "capture_mode": row.get("capture_mode"),
    }
    return {
        "fid": str(row["fid"]),
        "provider_league_id": str(row.get("provider_league_id") or ""),
        "year": y,
        "totalcorner_kickoff_utc": row.get("kickoff_utc"),
        "totalcorner_page_records": [],
        "supplemental_schedule_records": [supplemental],
        "crown_fixture_metadata_records": [],
        "M1_history_cache_records": [],
        "expanded_universe_records": [],
        "priced_t6_records": [],
        "crown_captures": [],
        "crown_quote_groups": [],
        "external_ft_evidence": [],
        "failed_attempts": {},
        "identity_conflicts": [],
    }


def has_verified_ft(row):
    if row.get("external_ft_evidence"):
        return True
    sources = []
    for key in ("totalcorner_page_records", "m1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
        sources.extend(row.get(key, []))
    return any(
        x.get("status") == "full"
        and str(x.get("home_goals", "")).isdigit()
        and str(x.get("away_goals", "")).isdigit()
        for x in sources
    )
def main():
    existing = {}
    for row in read_gz(BASE):
        fid = str(row.get("fid") or "")
        if fid:
            existing[fid] = row
    baseline_ids = set(existing)
    source_rows = 0
    source_by_fid = collections.defaultdict(list)
    source_identity_conflicts = []
    counts = collections.defaultdict(lambda: collections.Counter())
    for row in read_gz(SUPP):
        fid = str(row.get("fid") or "")
        if not fid:
            continue
        source_rows += 1
        lid = str(row.get("provider_league_id") or "")
        year = scope_year(row)
        key = (lid, year if year is not None else "UNKNOWN_KICKOFF_YEAR")
        d = counts[key]
        d["supplemental_source_rows"] += 1
        if row.get("status_raw") == "full" and str(row.get("home_goals_raw", "")).isdigit() and str(row.get("away_goals_raw", "")).isdigit():
            d["verified_full_time_rows"] += 1
        else:
            d["unverified_or_nonfull_rows"] += 1
        if not row.get("kickoff_utc"):
            d["missing_kickoff_timestamp_rows"] += 1
        source_by_fid[fid].append(row)

    new_ids = set(source_by_fid) - baseline_ids
    overlap_ids = set(source_by_fid) & baseline_ids
    new_status_by_year = collections.defaultdict(collections.Counter)
    new_status_by_league = collections.defaultdict(collections.Counter)
    for fid in new_ids:
        for row in source_by_fid[fid]:
            y = scope_year(row)
            year_key = str(y) if y is not None else "UNKNOWN_KICKOFF_YEAR"
            lid = str(row.get("provider_league_id") or "")
            status = row.get("status_raw") == "full" and str(row.get("home_goals_raw", "")).isdigit() and str(row.get("away_goals_raw", "")).isdigit()
            for counter in (new_status_by_year[year_key], new_status_by_league[lid]):
                counter["new_unique_source_rows"] += 1
                counter["verified_full_time"] += int(status)
                counter["unverified_or_nonfull"] += int(not status)
                counter["missing_kickoff"] += int(not row.get("kickoff_utc"))
    for fid, versions in source_by_fid.items():
        if fid in existing:
            target = existing[fid]
            target.setdefault("supplemental_schedule_records", [])
            for row in versions:
                target["supplemental_schedule_records"].append(normalize(row)["supplemental_schedule_records"][0])
            # Preserve the original canonical year/kickoff; source discrepancies
            # remain explicit in the record-version provenance.
        else:
            normalized = normalize(versions[0])
            # Preserve every source version for a FID, not only the first.
            normalized["supplemental_schedule_records"] = [normalize(v)["supplemental_schedule_records"][0] for v in versions]
            if len(versions) > 1:
                source_identity_conflicts.append({"fid": fid, "source_versions": len(versions), "resolution": "all_versions_preserved_no_overwrite"})
            existing[fid] = normalized

    with OUT.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for fid in sorted(existing, key=lambda z: (existing[z].get("provider_league_id", ""), existing[z].get("year") or 9999, z)):
                gz.write((json.dumps(existing[fid], ensure_ascii=False, separators=(",", ":")) + "\n").encode())

    # Uniqueness and integrity checks on the persisted output.
    seen = set()
    persisted = 0
    for row in read_gz(OUT):
        fid = str(row.get("fid") or "")
        if fid in seen:
            raise SystemExit(f"duplicate FID in output: {fid}")
        seen.add(fid)
        persisted += 1
    if persisted != len(existing) or len(seen) != len(existing):
        raise SystemExit("persisted inventory count mismatch")
    merged_verified_ft = sum(has_verified_ft(row) for row in existing.values())
    unverified_by_league_year = collections.defaultdict(collections.Counter)
    unverified_count = 0
    with UNVERIFIED.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for fid in sorted(existing, key=lambda z: (existing[z].get("provider_league_id", ""), existing[z].get("year") or 9999, z)):
                row = existing[fid]
                if has_verified_ft(row):
                    continue
                unverified_count += 1
                sources = []
                for key in ("totalcorner_page_records", "m1_history_cache_records", "supplemental_schedule_records", "crown_fixture_metadata_records"):
                    for x in row.get(key, []):
                        sources.append({k: x.get(k) for k in ("status", "home_goals", "away_goals", "kickoff_utc", "provider_league_id", "league_name", "source_file", "page_file", "source_response_sha256", "source_record_sha256") if k in x})
                year = row.get("year") if row.get("year") is not None else "UNKNOWN_KICKOFF_YEAR"
                key = (str(row.get("provider_league_id") or ""), str(year))
                unverified_by_league_year[key]["unverified_FT_fids"] += 1
                candidate = {"fid": fid, "provider_league_id": row.get("provider_league_id"), "utc_year": row.get("year"), "kickoff_utc": row.get("totalcorner_kickoff_utc"), "evidence_records": sources, "resolution_status": "no_verified_full_time_score_in_reconciled_sources"}
                gz.write((json.dumps(candidate, ensure_ascii=False, separators=(",", ":")) + "\n").encode())

    years = collections.defaultdict(collections.Counter)
    for fid, versions in source_by_fid.items():
        for row in versions:
            y = scope_year(row)
            years[y if y is not None else "UNKNOWN_KICKOFF_YEAR"]["unique_fids"] += int(row is versions[0])
    summary = {
        "generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "method": "baseline inventory plus FID-deduplicated 53-league schedule artifact; append-only provenance; no Crown requests",
        "inputs": {
            str(BASE.name): {"sha256": sha256(BASE), "bytes": BASE.stat().st_size, "unique_fids": len(baseline_ids)},
            str(SUPP.name): {"sha256": sha256(SUPP), "bytes": SUPP.stat().st_size, "source_rows": source_rows, "unique_fids": len(source_by_fid)},
        },
        "results": {
            "baseline_unique_fids": len(baseline_ids),
            "supplemental_source_rows": source_rows,
            "supplemental_unique_fids": len(source_by_fid),
            "supplemental_overlap_fids": len(overlap_ids),
            "supplemental_new_unique_fids": len(new_ids),
            "merged_unique_fids": len(existing),
            "merged_verified_FT_fids": merged_verified_ft,
            "merged_unverified_FT_fids": len(existing) - merged_verified_ft,
            "unverified_queue_rows": unverified_count,
            "identity_conflicts_overwritten": 0,
            "source_fids_with_multiple_versions_preserved": len(source_identity_conflicts),
            "unknown_kickoff_year_unique_fids": sum(1 for fid, rows in source_by_fid.items() if all(scope_year(r) is None for r in rows)),
            "new_unique_status_by_utc_year": {k: dict(v) for k, v in sorted(new_status_by_year.items())},
            "new_unique_status_by_provider_league": {k: dict(v) for k, v in sorted(new_status_by_league.items())},
        },
        "source_by_league_utc_year": [
            {"provider_league_id": lid, "utc_year": year, **dict(counter)}
            for (lid, year), counter in sorted(counts.items(), key=lambda x: (x[0][0], str(x[0][1])))
        ],
        "source_unique_fids_by_utc_year": {str(k): v["unique_fids"] for k, v in sorted(years.items(), key=lambda x: str(x[0]))},
        "unverified_FT_by_provider_league_utc_year": [
            {"provider_league_id": lid, "utc_year": year, **dict(counter)}
            for (lid, year), counter in sorted(unverified_by_league_year.items())
        ],
        "source_identity_conflicts": source_identity_conflicts,
        "output": {"file": OUT.name, "sha256": sha256(OUT), "bytes": OUT.stat().st_size, "unique_fids": persisted},
        "unverified_ft_queue": {"file": UNVERIFIED.name, "sha256": sha256(UNVERIFIED), "bytes": UNVERIFIED.stat().st_size, "unique_fids": unverified_count},
        "scope_caveat": "This reconciles the audited 53-league schedule batch with the committed baseline only; it does not claim all leagues, FT gaps, or Crown history are complete. Missing kickoff dates remain unassigned to a UTC year; season metadata absent at source remains absent.",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"results": summary["results"], "output": summary["output"], "summary": str(SUMMARY)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
