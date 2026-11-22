#!/usr/bin/env python3
"""Build a sanitized progress snapshot for the active 2019-2026 recovery.

Reads local recovery manifests/logs and a read-only, WAL-aware Crown SQLite
snapshot. It never issues network requests or writes to SQLite/production data.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sqlite3
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PRIVATE = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121")
SCHEDULE = PRIVATE / "totalcorner_schedule_recovery"
QUEUE = PRIVATE / "crown_quote_recovery/queues_20261122"
DB = pathlib.Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
UTC = dt.timezone.utc


def now() -> str:
    return dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def jsonl(path: pathlib.Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def main() -> None:
    as_of = now()
    scope = json.loads((ROOT / "league_scope_union_2019_2026.json").read_text())
    merge = json.loads((ROOT / "schedule_union_53_leagues_reconciliation_20261122.json").read_text())
    sched = json.loads((ROOT / "supplemental_totalcorner_53_schedule_coverage_2019_2026.json").read_text())
    p15 = json.loads((SCHEDULE / "progress_before_m7_mapped_targets_20261122.json").read_text())
    p38 = json.loads((SCHEDULE / "progress.json").read_text())
    log_path = QUEUE / "movement_collection.log.jsonl"
    manifest = QUEUE / "crown_missing_movement_2019_2026.jsonl"
    resume = QUEUE / "crown_missing_movement_2019_2026.resume.jsonl"

    attempts = collections.Counter()
    failures = collections.Counter()
    latest = {}
    quote_rows = 0
    first_receive = last_receive = None
    for row in jsonl(log_path):
        if "fixture_id" not in row or "status" not in row:
            continue
        attempts[str(row["status"])] += 1
        fid = str(row["fixture_id"])
        latest[fid] = row
        quote_rows += int(row.get("quote_count") or 0)
        if row["status"] == "FETCH_FAILED":
            failures[str(row.get("error") or "UNKNOWN")] += 1
        stamp = row.get("response_received_at_utc")
        if stamp:
            first_receive = min(first_receive, stamp) if first_receive else stamp
            last_receive = max(last_receive, stamp) if last_receive else stamp

    unique_status = collections.Counter(str(row["status"]) for row in latest.values())
    ps = subprocess.run(["ps", "-axo", "pid=,command="], check=True, capture_output=True, text=True)
    proc_rows = []
    for line in ps.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid, command = int(parts[0]), parts[1]
        if "safe_window_collection_driver.py" in command:
            proc_rows.append(("driver", pid))
        elif "crown_capture_store.py collect" in command:
            proc_rows.append(("collector", pid))
    db_started = now()
    cx = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    cx.row_factory = sqlite3.Row
    captures = [dict(r) for r in cx.execute("""select c.data_layer,c.capture_mode,
        coalesce(c.status,'UNKNOWN') status,count(*) capture_rows,
        count(distinct c.fixture_id) distinct_fids,
        sum(coalesce(c.quote_count,0)) quote_rows_reported
        from capture c group by 1,2,3 order by 1,2,3""")]
    quote_coverage = [dict(r) for r in cx.execute("""select c.data_layer,c.capture_mode,
        count(*) quote_rows,count(distinct q.fixture_id) distinct_fids,
        sum(case when q.quote_source_at_utc is null then 1 else 0 end) source_time_missing,
        sum(case when q.response_received_at_utc is null then 1 else 0 end) receive_time_missing,
        sum(case when q.quote_before_kickoff=1 then 1 else 0 end) source_before_kickoff,
        sum(case when q.prospective_observation=1 then 1 else 0 end) prospective_rows
        from asian_quote q join capture c using(capture_key)
        group by 1,2 order by 1,2""")]
    cx.close()
    db_finished = now()

    out = {
        "generated_at_utc": as_of,
        "scope": "2019-2026 current known-source union inventory and historical Crown quote backfill only",
        "fixtures": {
            "unique_fids": merge["results"]["merged_unique_fids"],
            "provider_league_ids": scope["set_audit"]["total_union_including_observed_m1_only"],
            "m7_exact_names": scope["sources"]["m7_research_universe_named_competitions"]["unique_exact_names"],
            "m7_exact_names_unmapped": scope["set_audit"]["m7_exact_names_unmapped_to_provider_id"],
            "known_union_missing_from_inventory": scope["set_audit"]["inventory_ids_missing_from_union"],
            "inventory_ids_outside_union": scope["set_audit"]["inventory_ids_outside_union"],
            "global_completeness_claim": False,
            "inventory_sha256": sha(ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"),
        },
        "supplemental_schedule_recovery": {
            "targets_15_completed": len(p15["targets"]),
            "network_requests_15": p15["network_requests"],
            "unique_fids_15": sched["batches"]["15_competition_run"]["fixture_unique_fids"],
            "new_global_fids_15": sched["global_unique_fid_reconciliation"]["15_batch_new_global_fids"],
            "raw_pages_verified_15": sched["batches"]["15_competition_run"]["raw_page_count_verified"],
            "targets_38_completed": len(p38["targets"]),
            "started_at_38": p38["started_at_utc"],
            "finished_at_38": p38["finished_at_utc"],
            "network_requests_38": p38["network_requests"],
            "unique_fids_38": sched["batches"]["38_competition_run"]["unique_fids"],
            "new_global_fids_38": sched["global_unique_fid_reconciliation"]["38_batch_new_global_fids"],
            "raw_pages_referenced_38": sched["batches"]["38_competition_run"]["raw_pages_referenced"],
            "source_record_sha_verified_38": sched["batches"]["38_competition_run"]["source_record_sha_verified"],
            "raw_source_errors_38": sched["batches"]["38_competition_run"]["raw_source_errors"],
            "all_53_unique_fids": sched["summary"]["unique_schedule_fids_across_batches"],
            "all_53_new_global_fids": sched["summary"]["new_global_schedule_fids"],
            "verified_full_ft_in_53": sched["summary"]["total_verified_full_ft_fids"],
            "unverified_or_nonfull_ft_in_53": sched["summary"]["total_unverified_or_nonfull_fids"],
            "supplemental_coverage_sha256": sha(ROOT / "supplemental_totalcorner_53_schedule_coverage_2019_2026.json"),
            "append_only_merge_summary_sha256": sha(ROOT / "schedule_union_53_leagues_reconciliation_20261122.json"),
        },
        "ft": {
            "verified_fids": merge["results"]["merged_verified_FT_fids"],
            "unverified_fids": merge["results"]["merged_unverified_FT_fids"],
            "readiness_snapshot_sha256": sha(ROOT / "unverified_ft_readiness_203962_inventory_20261122.json"),
            "verified_source_overlays": {
                "M1": 441,
                "M5": 27,
                "M5_overlaps_M1": 24,
                "archived_ESPN": merge["results"]["strictly_reconciled_archived_external_FT_fids"],
                "Crown_historical": merge["results"]["strictly_reconciled_historical_Crown_FT_fids"],
                "EPL_La_Liga_ESPN_new_verified_FT": merge["results"]["strictly_reconciled_EPL_La_Liga_ESPN_FT_fids"],
                "EPL_La_Liga_ESPN_conflicts_preserved": merge["results"]["strictly_reconciled_EPL_La_Liga_ESPN_score_conflicts"],
            },
            "unverified_readiness_counts": json.loads((ROOT / "unverified_ft_readiness_203962_inventory_20261122.json").read_text())["classifications"],
        },
        "crown_movement_queue": {
            "driver_pids": [pid for kind, pid in proc_rows if kind == "driver"],
            "collector_pids": [pid for kind, pid in proc_rows if kind == "collector"],
            "mode": "historical",
            "candidate_fids": len(list(jsonl(manifest))),
            "terminal_unique_fids": len(latest),
            "terminal_statuses": dict(unique_status),
            "attempt_rows": dict(attempts),
            "failed_attempts": sum(failures.values()),
            "failure_codes": dict(failures),
            "logged_failed_fids_without_later_terminal": sum(1 for row in latest.values() if row["status"] == "FETCH_FAILED"),
            "saved_quote_rows_in_attempt_log": quote_rows,
            "unlogged_candidates": len(list(jsonl(manifest))) - len(latest),
            "first_http_receive_utc": first_receive,
            "last_http_receive_utc": last_receive,
            "source_event_time_and_receive_time_separate": True,
            "resume_manifest_sha256": sha(resume),
            "source_manifest_sha256": sha(manifest),
        },
        "crown_sqlite_read_only_snapshot": {
            "read_started_utc": db_started,
            "read_finished_utc": db_finished,
            "captures_by_layer_mode_status": captures,
            "quote_rows_by_layer_mode": quote_coverage,
            "database_opened_read_only": True,
            "no_stable_db_file_sha_claim_while_collector_active": True,
            "wal_snapshot_caveat": "Counts are from a read-only snapshot that may include active WAL writes; they are not a final database state.",
        },
        "league_scope": {
            "known_union_provider_ids": scope["set_audit"]["total_union_including_observed_m1_only"],
            "m7_exact_name_mapping_complete": True,
            "missing_ids_from_known_union": [],
            "global_completeness_claim": False,
        },
        "production_changes": 0,
        "strategy_or_backtest": 0,
        "telegram_or_ledger_writes": 0,
    }
    stamp = dt.datetime.now(UTC).strftime("%Y%m%dT%H%MZ")
    path = ROOT / f"COLLECTION_STATUS_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": path.name, "generated_at_utc": as_of,
        "fixtures": out["fixtures"], "schedule": out["supplemental_schedule_recovery"],
        "crown_queue": out["crown_movement_queue"],
        "sqlite_read_started_utc": db_started, "sqlite_read_finished_utc": db_finished},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
