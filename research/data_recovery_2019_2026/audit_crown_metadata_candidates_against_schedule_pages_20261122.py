#!/usr/bin/env python3
"""Exact-FID reconciliation of Crown capture metadata candidates to cached schedule pages.

Read-only: no network calls and no SQLite writes. The Crown source response and
cached TotalCorner page are retained as separate evidence with their own hashes.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, pathlib
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
CANDIDATES = HERE / "crown_only_fixture_identity_candidates_2019_2026.jsonl.gz"
PAGE_ROOT = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery/raw")
OUT_ROWS = HERE / "crown_metadata_schedule_page_reconciliation_20261122.jsonl.gz"
OUT_SUMMARY = HERE / "crown_metadata_schedule_page_reconciliation_20261122.json"
SH = ZoneInfo("Asia/Shanghai")
UTC = dt.timezone.utc

def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def utc_time(value: object) -> str | None:
    if not value:
        return None
    x = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=SH)
    return x.astimezone(UTC).isoformat().replace("+00:00", "Z")

def ident(row: dict) -> tuple[str, ...]:
    return (str(row.get("l_id") or ""), str(row.get("h_id") or ""),
            str(row.get("h") or ""), str(row.get("a_id") or ""),
            str(row.get("a") or ""), utc_time(row.get("start")) or "")

def main() -> None:
    candidates = {}
    with gzip.open(CANDIDATES, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            candidates[str(row["fid"])] = row
    found: dict[str, list[dict]] = collections.defaultdict(list)
    pages = sorted(PAGE_ROOT.glob("*.json"))
    pages_scanned = 0
    for path in pages:
        if path.name.endswith(".meta.json"):
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pages_scanned += 1
        rows = (doc.get("data") or {}).get("matches") or []
        for page_row in rows:
            fid = str(page_row.get("id") or "")
            if fid not in candidates:
                continue
            found[fid].append({"page_path": str(path), "page_sha256": sha(path),
                               "identity": ident(page_row), "status": page_row.get("status"),
                               "home_goals": page_row.get("hg"), "away_goals": page_row.get("ag"),
                               "page_league_name": page_row.get("l")})
    results = []
    classes = collections.Counter()
    years = collections.Counter()
    leagues = collections.Counter()
    for fid, crown in sorted(candidates.items()):
        expected = (str(crown.get("provider_league_id") or ""),
                    str(crown.get("home_id") or ""), str(crown.get("home_name") or ""),
                    str(crown.get("away_id") or ""), str(crown.get("away_name") or ""),
                    utc_time(crown.get("kickoff_utc")) or "")
        matches = found.get(fid, [])
        exact = [r for r in matches if r["identity"] == expected]
        conflicts = [r for r in matches if r["identity"] != expected]
        exact_full = [r for r in exact if r["status"] == "full"]
        full_scores = sorted({(str(r["home_goals"]), str(r["away_goals"])) for r in exact_full})
        if conflicts:
            cls = "source_identity_conflict"
        elif not matches:
            cls = "not_found_in_cached_schedule_pages"
        elif not exact:
            cls = "same_fid_identity_mismatch"
        elif len(full_scores) > 1:
            cls = "conflicting_full_scores"
        elif exact_full:
            cls = "exact_identity_full_ft"
        else:
            cls = "exact_identity_non_full_or_unknown_status"
        classes[cls] += 1
        year = str(crown.get("kickoff_utc", "")[:4])
        league = str(crown.get("provider_league_id") or "")
        years[(year, cls)] += 1
        leagues[(league, cls)] += 1
        results.append({"fid": fid, "provider_league_id": league, "provider_league_name": crown.get("provider_league_name"),
                        "kickoff_utc": crown.get("kickoff_utc"), "home_id": crown.get("home_id"),
                        "home_name": crown.get("home_name"), "away_id": crown.get("away_id"),
                        "away_name": crown.get("away_name"), "crown_source_status": crown.get("status_raw"),
                        "crown_source_score": [crown.get("home_goals_raw"), crown.get("away_goals_raw")],
                        "classification": cls, "schedule_page_rows": matches,
                        "exact_full_scores": [list(s) for s in full_scores],
                        "exact_full_ft_verified": bool(exact_full and len(full_scores) == 1),
                        "crown_response_references": crown.get("response_references"),
                        "identity_basis": "exact FID, provider league ID, home/away provider team IDs and names, UTC kickoff"})
    with OUT_ROWS.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for row in results:
                gz.write((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    summary = {"generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
               "candidate_input_sha256": sha(CANDIDATES), "candidate_rows": len(candidates),
               "schedule_page_root": str(PAGE_ROOT), "schedule_pages_scanned": pages_scanned,
               "network_requests": 0, "database_writes": 0,
               "classifications": dict(classes),
               "exact_identity_full_ft_rows": sum(r["exact_full_ft_verified"] for r in results),
               "year_class_counts": {"|".join(k): v for k, v in sorted(years.items())},
               "league_class_counts": {"|".join(k): v for k, v in sorted(leagues.items())},
               "output_rows": OUT_ROWS.name, "output_rows_sha256": sha(OUT_ROWS),
               "limitations": ["Only locally cached raw TotalCorner schedule pages were searched; no network requests were made.",
                               "Exact identity is required; same FID with conflicting metadata is not merged.",
                               "The audit does not itself mutate the canonical inventory or Crown SQLite."]}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
