#!/usr/bin/env python3
"""Build a per-provider-league/UTC-year coverage snapshot from the current inventory.

The Crown database is queried read-only in one SQLite read transaction while the
authorized historical writer may still be active. The report is explicitly an
as-of snapshot; it is not a static database SHA or a claim that provider scope is
globally exhaustive.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
UNRESOLVED = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
DATABASE = pathlib.Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
MOVEMENT_QUEUE = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/queues_20261122/crown_missing_movement_2019_2026.jsonl")
SUMMARY_QUEUE = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/crown_quote_recovery/queues_20261122/crown_missing_summary_2019_2026.jsonl")
STAMP = "20261122T0413Z"
CSV_OUT = ROOT / f"league_year_quote_coverage_{STAMP}.csv"
JSON_OUT = ROOT / f"league_year_quote_coverage_{STAMP}.json"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows_gz(path: pathlib.Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def jsonl_rows(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main() -> int:
    started = dt.datetime.now(dt.timezone.utc)
    inventory = {}
    by_bucket: dict[tuple[str, int | None], dict] = {}
    names_by_bucket: dict[tuple[str, int | None], set[str]] = collections.defaultdict(set)
    identity_by_fid: dict[str, tuple[str, str, str]] = {}
    for row in rows_gz(INVENTORY):
        fid = str(row["fid"])
        lid = str(row["provider_league_id"])
        year = int(row["year"]) if row.get("year") is not None else None
        inventory[fid] = (lid, year)
        m1_evidence = row.get("M1_history_cache_records") or []
        if m1_evidence:
            identity_by_fid[fid] = (
                str(m1_evidence[0].get("home_id") or ""),
                str(m1_evidence[0].get("away_id") or ""),
                str(m1_evidence[0].get("league_id") or ""),
            )
        b = by_bucket.setdefault((lid, year), {
            "provider_league_id": lid, "utc_year": year if year is not None else "unknown", "fixtures": 0,
            "year_unknown_fids": 0,
            "verified_ft": 0, "unresolved_ft": 0,
            "movement_capture_fids": 0, "movement_capture_records": 0,
            "movement_missing_capture_fids": 0,
            "movement_historical_capture_fids": 0, "movement_historical_missing_capture_fids": 0,
            "movement_live_capture_fids": 0,
            "movement_saved_fids": 0, "movement_no_quote_fids": 0,
            "movement_quote_fids": 0, "movement_quote_rows": 0,
            "movement_historical_quote_fids": 0, "movement_historical_quote_rows": 0,
            "movement_live_quote_fids": 0, "movement_live_quote_rows": 0,
            "movement_fids_with_multiple_source_times": 0,
            "movement_quotes_before_kickoff_rows": 0,
            "movement_prospective_quote_rows": 0,
            "summary_capture_fids": 0, "summary_capture_records": 0,
            "summary_missing_capture_fids": 0,
            "summary_quote_fids": 0, "summary_quote_rows": 0,
            "summary_open_rows": 0, "summary_close_rows": 0,
            "summary_historical_capture_fids": 0, "summary_historical_missing_capture_fids": 0,
            "summary_historical_quote_fids": 0, "summary_historical_quote_rows": 0,
            "summary_historical_open_rows": 0, "summary_historical_close_rows": 0,
            "summary_live_capture_fids": 0, "summary_live_quote_fids": 0, "summary_live_quote_rows": 0,
            "live_capture_fids": 0, "live_capture_records": 0,
            "live_quote_rows": 0, "responses_without_receive_time": 0,
            "capture_records_all_layers": 0,
        })
        b["fixtures"] += 1
        b["year_unknown_fids"] += int(year is None)
        for collection in ("totalcorner_page_records", "supplemental_schedule_records", "crown_fixture_metadata_records", "M1_history_cache_records", "expanded_universe_records"):
            for evidence in row.get(collection) or []:
                for name_key in ("league_name", "source_league", "scope_item", "competition_name", "competition"):
                    name = evidence.get(name_key)
                    if isinstance(name, str) and name.strip():
                        names_by_bucket[(lid, year)].add(name.strip())

    # Some M1-only inventory rows carry exact FID/league/team identity but the
    # name is in the locally cached raw M1 row. Resolve only the relevant
    # SHA-pinned cache files, requiring exact FID, league ID and team IDs.
    m1_cache_sha256: dict[str, str] = {}
    missing_name_leagues = {
        lid for (lid, year) in by_bucket if not names_by_bucket[(lid, year)]
    }
    for lid in sorted(missing_name_leagues):
        source_path = pathlib.Path(f"/Users/mac/QuantAsiaDesk/repos/m1/data/m1_history_cache/{lid}.json")
        if not source_path.is_file():
            continue
        m1_cache_sha256[str(source_path)] = sha256(source_path)
        data = json.loads(source_path.read_text(encoding="utf-8"))
        if str(data.get("league_id")) != lid:
            raise RuntimeError(f"M1 cache league ID mismatch: {source_path}")
        for source_row in data.get("rows") or []:
            fid = str(source_row.get("id") or "")
            if fid not in inventory or inventory[fid][0] != lid:
                continue
            expected = identity_by_fid.get(fid)
            observed = (str(source_row.get("h_id") or ""), str(source_row.get("a_id") or ""), str(source_row.get("l_id") or ""))
            if expected is None or observed != expected or observed[2] != lid:
                raise RuntimeError(f"M1 exact identity mismatch for FID {fid}: {observed} != {expected}")
            league_name = str(source_row.get("l") or "").strip()
            if league_name:
                for bucket_key in by_bucket:
                    if bucket_key[0] == lid:
                        names_by_bucket[bucket_key].add(league_name)

    unresolved_ids = {str(r["fid"]) for r in rows_gz(UNRESOLVED)}
    movement_queue_ids = {str(r.get("match_id", r.get("fid"))) for r in jsonl_rows(MOVEMENT_QUEUE)}
    summary_queue_ids = {str(r.get("match_id", r.get("fid"))) for r in jsonl_rows(SUMMARY_QUEUE)}
    unknown_gap = unresolved_ids - inventory.keys()
    if unknown_gap:
        raise RuntimeError(f"unresolved FIDs outside inventory: {len(unknown_gap)}")
    for fid, (lid, year) in inventory.items():
        by_bucket[(lid, year)]["unresolved_ft"] += int(fid in unresolved_ids)
    for b in by_bucket.values():
        b["verified_ft"] = b["fixtures"] - b["unresolved_ft"]

    db = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("BEGIN")
    # The first read establishes the WAL snapshot for all later batches.
    capture_count = db.execute("SELECT count(*) FROM capture").fetchone()[0]
    max_received = db.execute("SELECT max(response_received_at_utc) FROM capture").fetchone()[0]
    data_version = db.execute("PRAGMA data_version").fetchone()[0]
    started_snapshot = dt.datetime.now(dt.timezone.utc)

    movement_quote_fids = set()
    movement_quote_fids_historical = set()
    movement_quote_fids_live = set()
    movement_saved_fids = set()
    movement_no_quote_fids = set()
    movement_multi_source_fids = set()
    summary_quote_fids = set()
    movement_capture_fids = set()
    movement_capture_fids_historical = set()
    movement_capture_fids_live = set()
    summary_capture_fids = set()
    summary_capture_fids_historical = set()
    summary_capture_fids_live = set()
    summary_quote_fids_historical = set()
    summary_quote_fids_live = set()
    live_capture_fids = set()
    errors = collections.Counter()
    fids = list(inventory)
    query = """SELECT c.fixture_id,c.data_layer,c.capture_mode,c.status,c.quote_count,
                      c.response_received_at_utc,c.prospective_observation,
                      COUNT(q.sequence_index) AS quote_rows,
                      COUNT(DISTINCT CASE WHEN q.quote_kind='movement' THEN q.quote_source_at_utc END) AS movement_source_times,
                      SUM(CASE WHEN q.quote_kind='movement' AND q.quote_before_kickoff=1 THEN 1 ELSE 0 END) AS movement_before_kickoff,
                      SUM(CASE WHEN q.quote_kind='movement' AND q.prospective_observation=1 THEN 1 ELSE 0 END) AS movement_prospective,
                      SUM(CASE WHEN q.quote_kind='open' THEN 1 ELSE 0 END) AS open_rows,
                      SUM(CASE WHEN q.quote_kind='close' THEN 1 ELSE 0 END) AS close_rows
               FROM capture c LEFT JOIN asian_quote q ON q.capture_key=c.capture_key
               WHERE c.fixture_id IN ({marks})
               GROUP BY c.capture_key"""
    for start in range(0, len(fids), 500):
        chunk = fids[start:start + 500]
        sql = query.format(marks=",".join("?" for _ in chunk))
        try:
            result_rows = db.execute(sql, chunk).fetchall()
        except sqlite3.Error as exc:
            errors[type(exc).__name__ + ":" + str(exc)] += 1
            raise
        for r in result_rows:
            fid = str(r["fixture_id"])
            if fid not in inventory:
                errors["unexpected_capture_fid"] += 1
                continue
            lid, year = inventory[fid]
            b = by_bucket[(lid, year)]
            layer, mode, status = str(r["data_layer"]), str(r["capture_mode"]), str(r["status"])
            nquote = int(r["quote_rows"] or 0)
            b["capture_records_all_layers"] += 1
            if r["response_received_at_utc"] is None:
                b["responses_without_receive_time"] += 1
            if mode == "live":
                b["live_capture_records"] += 1
                if nquote:
                    b["live_quote_rows"] += nquote
                live_capture_fids.add(fid)
            if layer == "movement":
                b["movement_capture_records"] += 1
                movement_capture_fids.add(fid)
                b["movement_quote_rows"] += nquote
                b["movement_quotes_before_kickoff_rows"] += int(r["movement_before_kickoff"] or 0)
                b["movement_prospective_quote_rows"] += int(r["movement_prospective"] or 0)
                if status in ("QUOTES_SAVED", "SAVED") and nquote:
                    movement_saved_fids.add(fid)
                if status == "NO_CROWN_AH_QUOTES":
                    movement_no_quote_fids.add(fid)
                if nquote:
                    movement_quote_fids.add(fid)
                    if mode == "historical":
                        movement_quote_fids_historical.add(fid)
                        b["movement_historical_quote_rows"] += nquote
                    elif mode == "live":
                        movement_quote_fids_live.add(fid)
                        b["movement_live_quote_rows"] += nquote
                    if int(r["movement_source_times"] or 0) > 1:
                        movement_multi_source_fids.add(fid)
                if mode == "historical":
                    movement_capture_fids_historical.add(fid)
                elif mode == "live":
                    movement_capture_fids_live.add(fid)
            elif layer == "summary":
                b["summary_capture_records"] += 1
                summary_capture_fids.add(fid)
                b["summary_quote_rows"] += nquote
                b["summary_open_rows"] += int(r["open_rows"] or 0)
                b["summary_close_rows"] += int(r["close_rows"] or 0)
                if mode == "historical":
                    summary_capture_fids_historical.add(fid)
                    b["summary_historical_quote_rows"] += nquote
                    b["summary_historical_open_rows"] += int(r["open_rows"] or 0)
                    b["summary_historical_close_rows"] += int(r["close_rows"] or 0)
                elif mode == "live":
                    summary_capture_fids_live.add(fid)
                    b["summary_live_quote_rows"] += nquote
                if nquote:
                    summary_quote_fids.add(fid)
                    if mode == "historical": summary_quote_fids_historical.add(fid)
                    elif mode == "live": summary_quote_fids_live.add(fid)

    # Unique-FID denominators are computed once after capture-level aggregation.
    movement_capture_fids_by_bucket = collections.Counter(inventory[fid] for fid in movement_capture_fids)
    movement_capture_fids_historical_by_bucket = collections.Counter(inventory[fid] for fid in movement_capture_fids_historical)
    movement_capture_fids_live_by_bucket = collections.Counter(inventory[fid] for fid in movement_capture_fids_live)
    summary_capture_fids_by_bucket = collections.Counter(inventory[fid] for fid in summary_capture_fids)
    summary_capture_fids_historical_by_bucket = collections.Counter(inventory[fid] for fid in summary_capture_fids_historical)
    summary_capture_fids_live_by_bucket = collections.Counter(inventory[fid] for fid in summary_capture_fids_live)
    live_capture_fids_by_bucket = collections.Counter(inventory[fid] for fid in live_capture_fids)
    movement_saved_fids_by_bucket = collections.Counter(inventory[fid] for fid in movement_saved_fids)
    movement_no_quote_fids_by_bucket = collections.Counter(inventory[fid] for fid in movement_no_quote_fids)
    movement_multi_source_fids_by_bucket = collections.Counter(inventory[fid] for fid in movement_multi_source_fids)
    movement_quote_fids_by_bucket = collections.Counter(inventory[fid] for fid in movement_quote_fids)
    summary_quote_fids_by_bucket = collections.Counter(inventory[fid] for fid in summary_quote_fids)
    movement_quote_fids_historical_by_bucket = collections.Counter(inventory[fid] for fid in movement_quote_fids_historical)
    movement_quote_fids_live_by_bucket = collections.Counter(inventory[fid] for fid in movement_quote_fids_live)
    summary_quote_fids_historical_by_bucket = collections.Counter(inventory[fid] for fid in summary_quote_fids_historical)
    summary_quote_fids_live_by_bucket = collections.Counter(inventory[fid] for fid in summary_quote_fids_live)
    for key, b in by_bucket.items():
        b["movement_capture_fids"] = movement_capture_fids_by_bucket[key]
        b["movement_missing_capture_fids"] = b["fixtures"] - b["movement_capture_fids"]
        b["movement_historical_capture_fids"] = movement_capture_fids_historical_by_bucket[key]
        b["movement_historical_missing_capture_fids"] = b["fixtures"] - b["movement_historical_capture_fids"]
        b["movement_live_capture_fids"] = movement_capture_fids_live_by_bucket[key]
        b["movement_quote_fids"] = movement_quote_fids_by_bucket[key]
        b["movement_historical_quote_fids"] = movement_quote_fids_historical_by_bucket[key]
        b["movement_live_quote_fids"] = movement_quote_fids_live_by_bucket[key]
        b["movement_saved_fids"] = movement_saved_fids_by_bucket[key]
        b["movement_no_quote_fids"] = movement_no_quote_fids_by_bucket[key]
        b["movement_fids_with_multiple_source_times"] = movement_multi_source_fids_by_bucket[key]
        b["summary_capture_fids"] = summary_capture_fids_by_bucket[key]
        b["summary_missing_capture_fids"] = b["fixtures"] - b["summary_capture_fids"]
        b["summary_historical_capture_fids"] = summary_capture_fids_historical_by_bucket[key]
        b["summary_historical_missing_capture_fids"] = b["fixtures"] - b["summary_historical_capture_fids"]
        b["summary_live_capture_fids"] = summary_capture_fids_live_by_bucket[key]
        b["summary_quote_fids"] = summary_quote_fids_by_bucket[key]
        b["summary_historical_quote_fids"] = summary_quote_fids_historical_by_bucket[key]
        b["summary_live_quote_fids"] = summary_quote_fids_live_by_bucket[key]
        b["live_capture_fids"] = live_capture_fids_by_bucket[key]
        names = sorted(names_by_bucket[key])
        b["league_names"] = " | ".join(names)
        b["league_name_variants"] = len(names)

    ended_snapshot = dt.datetime.now(dt.timezone.utc)
    db.rollback()
    db.close()
    ended = dt.datetime.now(dt.timezone.utc)

    bucket_rows = [by_bucket[k] for k in sorted(by_bucket, key=lambda x: (int(x[0]), x[1] if x[1] is not None else 0))]
    totals = collections.Counter()
    for row in bucket_rows:
        for key, value in row.items():
            if key not in ("provider_league_id", "utc_year", "league_names"):
                totals[key] += int(value)
    if sum(x["fixtures"] for x in bucket_rows) != len(inventory):
        raise RuntimeError("league/year fixtures do not sum to unique inventory")
    if sum(x["unresolved_ft"] for x in bucket_rows) != len(unresolved_ids):
        raise RuntimeError("league/year unresolved FT does not match the per-FID queue")
    missing_movement_historical = {fid for fid in inventory if fid not in movement_capture_fids_historical}
    missing_summary_historical = {fid for fid in inventory if fid not in summary_capture_fids_historical}
    movement_queue_audit = {
        "queue_sha256": sha256(MOVEMENT_QUEUE), "queue_rows": len(movement_queue_ids),
        "missing_historical_capture_fids_now": len(missing_movement_historical),
        "queue_fids_still_missing": len(movement_queue_ids & missing_movement_historical),
        "queue_fids_now_captured": len(movement_queue_ids - missing_movement_historical),
        "current_missing_fids_not_in_original_queue": len(missing_movement_historical - movement_queue_ids),
    }
    summary_queue_audit = {
        "queue_sha256": sha256(SUMMARY_QUEUE), "queue_rows": len(summary_queue_ids),
        "missing_historical_capture_fids_now": len(missing_summary_historical),
        "queue_fids_still_missing": len(summary_queue_ids & missing_summary_historical),
        "queue_fids_now_captured": len(summary_queue_ids - missing_summary_historical),
        "current_missing_fids_not_in_queue": len(missing_summary_historical - summary_queue_ids),
    }

    fieldnames = list(bucket_rows[0])
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader(); writer.writerows(bucket_rows)
    result = {
        "snapshot_created_at_utc": ended.isoformat().replace("+00:00", "Z"),
        "sqlite_read_snapshot_started_at_utc": started_snapshot.isoformat().replace("+00:00", "Z"),
        "sqlite_read_snapshot_ended_at_utc": ended_snapshot.isoformat().replace("+00:00", "Z"),
        "database": str(DATABASE),
        "database_read_only": True,
        "main_database_sha256": None,
        "database_capture_rows_in_snapshot": capture_count,
        "database_max_response_received_at_utc_in_snapshot": max_received,
        "sqlite_data_version": data_version,
        "network_requests": 0,
        "database_writes": 0,
        "inventory_fids": len(inventory),
        "provider_leagues": len({v[0] for v in inventory.values()}),
        "league_year_buckets": len(bucket_rows),
        "unresolved_ft_fids": len(unresolved_ids),
        "inventory_sha256": sha256(INVENTORY),
        "exact_m1_cache_sha256": m1_cache_sha256,
        "unresolved_queue_sha256": sha256(UNRESOLVED),
        "totals": dict(totals),
        "movement_queue_audit": movement_queue_audit,
        "summary_queue_audit": summary_queue_audit,
        "errors": dict(errors),
        "csv": CSV_OUT.name,
        "csv_sha256": sha256(CSV_OUT),
        "rows_by_provider_league_utc_year": bucket_rows,
        "limitations": [
            "This is a read-transaction snapshot while the historical collector may append to SQLite; the main database file SHA is intentionally omitted.",
            "Verified FT counts use the current explicit per-FID unresolved queue; provider status codes are not inferred as cancellation or finality.",
            "Historical source-event quotes, historical HTTP receive times and true prospective receipts remain distinct.",
            "The 118-league inventory is the current reconciled known-source union, not a proof of exhaustive global competition discovery.",
        ],
    }
    JSON_OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "snapshot_created_at_utc", "inventory_fids", "provider_leagues", "league_year_buckets",
        "unresolved_ft_fids", "database_capture_rows_in_snapshot", "database_max_response_received_at_utc_in_snapshot",
        "totals", "csv_sha256",
    )}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
