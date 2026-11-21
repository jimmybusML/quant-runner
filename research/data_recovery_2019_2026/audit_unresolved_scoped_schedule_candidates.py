#!/usr/bin/env python3
"""Reconcile recorded scoped-schedule attempts against the 65-ID inventory."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/mac/QuantAsiaDesk/repos/runner/research/shared_history/totalcorner")
SCRIPT = ROOT.parent / "collect_scoped_history.py"
SUMMARY = ROOT / "latest_collection_summary.json"
INVENTORY = Path("/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/fixture_inventory_2019_2026.jsonl.gz")
OUT = Path(__file__).resolve().parent / "unresolved_schedule_competition_candidates_20261121.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_targets(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TARGETS" for t in node.targets):
            value = ast.literal_eval(node.value)
            return {str(k): str(v) for k, v in value.items()}
    raise ValueError("TARGETS dictionary not found")


def main() -> None:
    targets = read_targets(SCRIPT)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    inventory_fids: set[str] = set()
    inventory_leagues: set[str] = set()
    with gzip.open(INVENTORY, "rt", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("fid"):
                inventory_fids.add(str(row["fid"]))
            if row.get("provider_league_id"):
                inventory_leagues.add(str(row["provider_league_id"]))

    errors_by_id: dict[str, list[dict]] = {}
    for error in summary.get("errors", []):
        errors_by_id.setdefault(str(error.get("league_id")), []).append(error)
    per_name = summary.get("per_league", {})
    out: list[dict] = []
    for lid, name in targets.items():
        path = ROOT / f"league-{lid}.jsonl"
        rows: dict[str, dict] = {}
        if path.exists():
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                fid = str(row.get("id") or "")
                if fid:
                    rows[fid] = row
        p = per_name.get(name, {})
        out.append({
            "provider_league_id": lid,
            "league_name": name,
            "inside_65_id_master_inventory": lid in inventory_leagues,
            "stored_source_rows": len(rows),
            "fids_overlapping_65_id_master_inventory": len(set(rows) & inventory_fids),
            "pages_reported_read": p.get("pages_read", 0),
            "last_run_added_rows": p.get("added", 0),
            "request_errors": errors_by_id.get(lid, []),
            "status": "partial_schedule_present_page_failure" if rows and errors_by_id.get(lid)
                      else "schedule_rows_present" if rows
                      else "no_rows_saved_request_failed" if errors_by_id.get(lid)
                      else "no_saved_rows_no_recorded_error",
            "source_file": str(path) if path.exists() else None,
            "source_file_sha256": sha256(path) if path.exists() else None,
        })

    result = {
        "audit_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "purpose": "Data-source scope reconciliation only; no Crown collection and no strategy/model work.",
        "master_inventory": {
            "unique_fids": len(inventory_fids),
            "provider_league_ids": len(inventory_leagues),
            "source_file": str(INVENTORY),
            "source_file_sha256": sha256(INVENTORY),
        },
        "scoped_schedule_attempt_source": {
            "script": str(SCRIPT),
            "script_sha256": sha256(SCRIPT),
            "summary": str(SUMMARY),
            "summary_sha256": sha256(SUMMARY),
            "generated_utc": summary.get("generated_utc"),
            "market_history_verified": summary.get("market_history_verified"),
        },
        "candidate_competition_count": len(out),
        "candidate_ids_outside_master_inventory": sum(not x["inside_65_id_master_inventory"] for x in out),
        "competitions_with_saved_rows": sum(x["stored_source_rows"] > 0 for x in out),
        "competitions_with_request_errors": sum(bool(x["request_errors"]) for x in out),
        "total_unique_saved_source_fids": sum(x["stored_source_rows"] for x in out),
        "competitions": out,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "master_inventory", "candidate_competition_count", "candidate_ids_outside_master_inventory",
        "competitions_with_saved_rows", "competitions_with_request_errors", "total_unique_saved_source_fids"
    )}, ensure_ascii=False, indent=2))
    for row in out:
        if row["request_errors"] or row["stored_source_rows"]:
            print(row["provider_league_id"], row["league_name"], row["status"], row["stored_source_rows"], row["request_errors"])


if __name__ == "__main__":
    main()
