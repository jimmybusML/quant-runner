#!/usr/bin/env python3
"""Audit Crown-captured fixture metadata already present in the +53 inventory.

It compares the old base inventory with the current expanded inventory, then
cross-checks those added FIDs against exact TotalCorner raw-page identity and FT.
Read-only, with no API requests or SQLite writes.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, pathlib, sqlite3
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
OLD = HERE / "fixture_inventory_2019_2026.jsonl.gz"
FULL = HERE / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
UNVERIFIED = HERE / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
DB = pathlib.Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
PAGES = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery/raw")
OUT_ROWS = HERE / "crown_metadata_expanded_inventory_crosschecks_20261122.jsonl.gz"
OUT_SUMMARY = HERE / "crown_metadata_expanded_inventory_crosschecks_20261122.json"
SH = ZoneInfo("Asia/Shanghai")
UTC = dt.timezone.utc

def sha_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def utc(s: object) -> str | None:
    if not s:
        return None
    d = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=SH)
    return d.astimezone(UTC).isoformat().replace("+00:00", "Z")

def inventory_identity(row: dict) -> tuple[str, ...]:
    return (str(row.get("provider_league_id") or ""),
            str((row.get("supplemental_schedule_records") or [{}])[0].get("home_id") or ""),
            str((row.get("supplemental_schedule_records") or [{}])[0].get("home_name") or ""),
            str((row.get("supplemental_schedule_records") or [{}])[0].get("away_id") or ""),
            str((row.get("supplemental_schedule_records") or [{}])[0].get("away_name") or ""),
            str(row.get("totalcorner_kickoff_utc") or ""))

def raw_identity(r: dict) -> tuple[str, ...]:
    return (str(r.get("l_id") or ""), str(r.get("h_id") or ""), str(r.get("h") or ""),
            str(r.get("a_id") or ""), str(r.get("a") or ""), utc(r.get("start")) or "")

def page_identity(r: dict) -> tuple[str, ...]:
    return (str(r.get("l_id") or ""), str(r.get("h_id") or ""), str(r.get("h") or ""),
            str(r.get("a_id") or ""), str(r.get("a") or ""), utc(r.get("start")) or "")

def main() -> None:
    old_ids = {str(json.loads(x)["fid"]) for x in gzip.open(OLD, "rt", encoding="utf-8")}
    full = {str(r["fid"]): r for r in (json.loads(x) for x in gzip.open(FULL, "rt", encoding="utf-8"))}
    unresolved = {str(json.loads(x)["fid"]) for x in gzip.open(UNVERIFIED, "rt", encoding="utf-8")}
    cx = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    cx.row_factory = sqlite3.Row
    cx.execute("BEGIN")
    snapshot_at = dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")
    cap_count = cx.execute("select count(*) from capture").fetchone()[0]
    max_receive = cx.execute("select max(response_received_at_utc) from capture").fetchone()[0]
    captured_ids = {str(r[0]) for r in cx.execute("select distinct fixture_id from capture")}
    candidates = sorted((captured_ids - old_ids) & full.keys())
    captures = {}
    for start in range(0, len(candidates), 500):
        batch = candidates[start:start+500]
        marks = ",".join("?" for _ in batch)
        for r in cx.execute(f"""select capture_key,fixture_id,data_layer,capture_mode,status,quote_count,
                response_received_at_utc,response_sha256,source_file from capture where fixture_id in ({marks})""", batch):
            captures.setdefault(str(r["fixture_id"]), []).append(dict(r))
    quote_counts = {}
    for fid, caps in captures.items():
        keys = [r["capture_key"] for r in caps]
        marks = ",".join("?" for _ in keys)
        quote_counts[fid] = cx.execute(f"select count(*) from asian_quote where capture_key in ({marks})", keys).fetchone()[0]
    cx.close()

    page_rows: dict[str, list[dict]] = collections.defaultdict(list)
    page_paths = sorted(p for p in PAGES.glob("*.json") if not p.name.endswith(".meta.json"))
    for path in page_paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        matches = (doc.get("data") or {}).get("matches") or []
        relevant = [r for r in matches if str(r.get("id") or "") in set(candidates)]
        if not relevant:
            continue
        page_sha = sha_file(path)
        for r in relevant:
            page_rows[str(r["id"])].append({"path": str(path), "sha256": page_sha,
                "identity": page_identity(r), "status": r.get("status"),
                "home_goals": r.get("hg"), "away_goals": r.get("ag"), "league_name": r.get("l")})

    out_rows = []
    classes = collections.Counter()
    raw_statuses = collections.Counter()
    tc_statuses = collections.Counter()
    nonfull_unresolved = full_not_unresolved = 0
    for fid in candidates:
        inv = full[fid]
        expected = inventory_identity(inv)
        raw_evidence = []
        raw_errors = []
        for cap in captures.get(fid, []):
            p = pathlib.Path(cap["source_file"])
            if not p.is_file():
                raw_errors.append("missing_raw_file"); continue
            digest = sha_file(p)
            if digest != cap["response_sha256"]:
                raw_errors.append("raw_sha_mismatch"); continue
            obj = json.loads(p.read_text(encoding="utf-8"))
            match = next((m for m in obj.get("data", []) if str(m.get("id")) == fid), None)
            if match is None:
                raw_errors.append("raw_fid_missing"); continue
            raw_statuses[str(match.get("status"))] += 1
            raw_evidence.append({"capture_key": cap["capture_key"], "data_layer": cap["data_layer"],
                "capture_mode": cap["capture_mode"], "capture_status": cap["status"],
                "capture_quote_count": cap["quote_count"], "actual_asian_quote_rows": quote_counts[fid],
                "response_received_at_utc": cap["response_received_at_utc"],
                "response_sha256": digest, "raw_path": cap["source_file"],
                "fixture_status": match.get("status"), "fixture_score": [match.get("hg"), match.get("ag")],
                "identity": raw_identity(match), "identity_matches_inventory": raw_identity(match) == expected,
                "crown_bookmaker_present": any(b.get("slug") == "crown" for b in match.get("bookmakers", []))})
        pages = page_rows.get(fid, [])
        exact_pages = [r for r in pages if r["identity"] == expected]
        bad_pages = [r for r in pages if r["identity"] != expected]
        full_scores = sorted({(str(r["home_goals"]), str(r["away_goals"])) for r in exact_pages if r["status"] == "full"})
        crown_full = [r for r in raw_evidence if r.get("fixture_status") == "full"]
        crown_scores = sorted({tuple(str(x) for x in r["fixture_score"]) for r in crown_full})
        exact_both = bool(exact_pages and not bad_pages and len(full_scores) == 1 and
                          len(crown_scores) == 1 and full_scores[0] == crown_scores[0] and
                          all(r["identity_matches_inventory"] for r in raw_evidence))
        unresolved_now = fid in unresolved
        if exact_both and not unresolved_now:
            cls = "exact_full_ft_crown_tcorner_and_inventory_agree"
        elif exact_pages and not exact_both and unresolved_now:
            cls = "exact_identity_not_full_or_score_incomplete_remains_unresolved"
        elif not exact_pages:
            cls = "no_exact_cached_totalcorner_page"
        elif bad_pages:
            cls = "cached_totalcorner_identity_conflict"
        else:
            cls = "needs_manual_provenance_review"
        classes[cls] += 1
        tc_statuses.update(str(r["status"]) for r in exact_pages)
        if cls == "exact_full_ft_crown_tcorner_and_inventory_agree" and unresolved_now:
            full_not_unresolved += 1
        if cls == "exact_identity_not_full_or_score_incomplete_remains_unresolved" and not unresolved_now:
            nonfull_unresolved += 1
        out_rows.append({"fid": fid, "provider_league_id": inv.get("provider_league_id"),
            "utc_year": inv.get("year"), "kickoff_utc": inv.get("totalcorner_kickoff_utc"),
            "inventory_identity": expected, "classification": cls,
            "currently_in_unverified_ft_queue": unresolved_now,
            "crown_raw_capture_evidence": raw_evidence, "raw_evidence_errors": raw_errors,
            "exact_totalcorner_page_rows": exact_pages, "conflicting_totalcorner_page_rows": bad_pages,
            "exact_full_ft_score": list(full_scores[0]) if len(full_scores) == 1 else None,
            "crown_full_ft_score": list(crown_scores[0]) if len(crown_scores) == 1 else None,
            "full_score_sources_agree": exact_both,
            "inventory_source_records": inv.get("supplemental_schedule_records") or []})
    with OUT_ROWS.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for r in out_rows:
                gz.write((json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    summary = {"generated_at_utc": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sqlite_snapshot_started_at_utc": snapshot_at, "sqlite_capture_rows_in_snapshot": cap_count,
        "sqlite_max_response_received_at_utc_in_snapshot": max_receive,
        "old_base_inventory_sha256": sha_file(OLD), "expanded_inventory_sha256": sha_file(FULL),
        "unverified_ft_queue_sha256": sha_file(UNVERIFIED), "candidate_fids_added_since_old_base_and_captured": len(candidates),
        "candidate_fids_missing_from_totalcorner_pages": sum(not page_rows.get(fid) for fid in candidates),
        "candidate_fids_with_exact_full_score_match_across_crown_and_totalcorner": sum(r["full_score_sources_agree"] for r in out_rows),
        "unverified_full_ft_inconsistencies": full_not_unresolved,
        "nonfull_candidates_missing_from_unverified_queue": nonfull_unresolved,
        "raw_crown_fixture_status_counts": dict(raw_statuses), "exact_totalcorner_page_status_counts": dict(tc_statuses),
        "classifications": dict(classes), "page_files_scanned": len(page_paths),
        "network_requests": 0, "database_writes": 0,
        "output_rows": OUT_ROWS.name, "output_rows_sha256": sha_file(OUT_ROWS),
        "interpretation": "This audit rechecks schedule and FT provenance for FIDs added by the plus-53 inventory relative to the older base. It does not add FIDs or promote scores; every full score must agree across exact Crown response metadata, exact cached TotalCorner page, and the existing inventory status."}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
