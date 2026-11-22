#!/usr/bin/env python3
"""Reconcile already-verified FT overlays without network or database writes.

This creates a one-row-per-FID provenance ledger from existing M1, M5, Crown
raw-response and archived ESPN evidence. Source-level response validation is
recorded in the individual source audits; this script cross-checks identity,
score consistency, inventory membership and the current unresolved queue.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
GAP = ROOT / "unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz"
SOURCES = {
    "M1_history_cache": ROOT / "m1_ft_evidence_in_unverified_ledger_20261122.jsonl",
    "M5_verified_result": ROOT / "m5_verified_ft_overlay_2019_2026_20261122.jsonl",
    "Crown_historical_raw_result": ROOT / "crown_capture_verified_ft_overlay_2019_2026_20261122.jsonl",
    "ESPN_full_time_archive": ROOT / "epl_laliga_espn_verified_ft_overlay_20261122.jsonl",
}
OUTPUT_ROWS = ROOT / "verified_ft_overlay_union_203962_20261122.jsonl.gz"
OUTPUT_SUMMARY = ROOT / "verified_ft_overlay_union_203962_20261122.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def jsonl(path: Path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def get_score(source: str, row: dict) -> tuple[int, int]:
    if source == "ESPN_full_time_archive":
        home, away = str(row["verified_FT"]).split(":", 1)
        return int(home), int(away)
    return int(row["home_goals"]), int(row["away_goals"])


def evidence_record(source: str, row: dict) -> dict:
    evidence = {
        "source_kind": source,
        "source_artifact": SOURCES[source].name,
        "source_status": row.get("status", row.get("response_status")),
        "raw_response_sha256": row.get("raw_response_sha256", row.get("source_raw_sha256", row.get("source_cache_sha256"))),
        "response_received_at_utc": row.get("response_received_at_utc"),
        "source_event_kickoff_utc": row.get("source_event_kickoff_utc"),
        "source_event_id": row.get("source_event_id"),
        "crosswalk": row.get("crosswalk", row.get("crosscheck", row.get("inventory_identity_crosscheck"))),
    }
    if source == "M1_history_cache":
        evidence["source_cache_file"] = row.get("source_cache_file")
        evidence["source_kickoff_utc"] = row.get("M1_kickoff_utc")
        evidence["inventory_kickoff_utc"] = row.get("inventory_kickoff_utc")
        evidence["kickoff_versions_differ"] = bool(row.get("kickoff_versions_differ"))
    elif source == "M5_verified_result":
        evidence["source_index_sha256"] = row.get("index_file_sha256")
        evidence["source_response_relative_path"] = row.get("raw_response_relative_path")
    elif source == "Crown_historical_raw_result":
        evidence["capture_key"] = row.get("capture_key")
        evidence["capture_mode"] = row.get("capture_mode")
        evidence["data_layer"] = row.get("data_layer")
        evidence["capture_status"] = row.get("capture_status")
        evidence["source_response_relative_path"] = row.get("raw_response_relative_path")
    elif source == "ESPN_full_time_archive":
        evidence["source_response_file"] = Path(str(row.get("source_raw_file", ""))).name
        evidence["response_status"] = row.get("response_status")
        evidence["crosswalk_kind"] = row.get("crosswalk_kind")
    return evidence


def main() -> int:
    inventory_rows = list(jsonl(INVENTORY))
    inventory = {str(row["fid"]): row for row in inventory_rows}
    gap_ids = {str(row["fid"]) for row in jsonl(GAP)}
    conflicts: list[dict] = []
    identity_errors: list[dict] = []
    evidence_by_fid: dict[str, list[dict]] = collections.defaultdict(list)
    scores_by_fid: dict[str, set[tuple[int, int]]] = collections.defaultdict(set)
    fixture_identity: dict[str, tuple] = {}
    source_rows: dict[str, int] = {}
    source_unique: dict[str, int] = {}

    for source, path in SOURCES.items():
        rows = list(jsonl(path))
        source_rows[source] = len(rows)
        seen: set[str] = set()
        for row in rows:
            fid = str(row["fid"])
            if fid in seen:
                continue
            seen.add(fid)
            if source == "M1_history_cache" and row.get("status") != "full":
                continue
            if source in ("M5_verified_result", "Crown_historical_raw_result") and row.get("status") != "full":
                continue
            if source == "ESPN_full_time_archive" and row.get("response_status") != "STATUS_FULL_TIME":
                continue
            source_unique[source] = source_unique.get(source, 0) + 1
            if fid not in inventory:
                identity_errors.append({"fid": fid, "source": source, "error": "FID_not_in_inventory"})
                continue
            inv = inventory[fid]
            league = str(row.get("provider_league_id", row.get("league_id", "")))
            inv_league = str(inv.get("provider_league_id", ""))
            if league and league != inv_league:
                identity_errors.append({"fid": fid, "source": source, "error": "league_id_mismatch"})
            h_id, a_id = str(row.get("home_id", "")), str(row.get("away_id", ""))
            inv_kickoff = str(inv.get("totalcorner_kickoff_utc") or "")
            source_kickoff = str(row.get("inventory_kickoff_utc") or row.get("kickoff_utc") or row.get("source_event_kickoff_utc") or "")
            if source_kickoff and inv_kickoff and source_kickoff.replace("+00:00", "Z") != inv_kickoff.replace("+00:00", "Z"):
                identity_errors.append({"fid": fid, "source": source, "error": "inventory_kickoff_mismatch", "source_kickoff": source_kickoff, "inventory_kickoff": inv_kickoff})
            identity = (league or inv_league, h_id, a_id, row.get("home_name"), row.get("away_name"))
            prior = fixture_identity.setdefault(fid, identity)
            if all(prior) and all(identity) and prior != identity:
                identity_errors.append({"fid": fid, "source": source, "error": "cross_source_identity_mismatch"})
            score = get_score(source, row)
            scores_by_fid[fid].add(score)
            evidence_by_fid[fid].append({"score": score, **evidence_record(source, row)})

    for fid, scores in scores_by_fid.items():
        if len(scores) != 1:
            conflicts.append({"fid": fid, "scores": sorted([list(s) for s in scores])})

    union_ids = set(scores_by_fid)
    rows_out = []
    for fid in sorted(union_ids, key=lambda x: (int(x) if x.isdigit() else 0, x)):
        if fid not in inventory:
            continue
        inv = inventory[fid]
        ev = evidence_by_fid[fid]
        # Identity comes from exact-FID source rows; keep source-specific timing
        # variants only inside evidence records rather than silently collapsing them.
        first = ev[0]
        rows_out.append({
            "fid": fid,
            "provider_league_id": str(inv["provider_league_id"]),
            "inventory_kickoff_utc": inv.get("totalcorner_kickoff_utc"),
            "home_goals": next(iter(scores_by_fid[fid]))[0],
            "away_goals": next(iter(scores_by_fid[fid]))[1],
            "evidence_record_count": len(ev),
            "evidence": ev,
        })

    inputs = {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in [INVENTORY, GAP, *SOURCES.values()]}
    with OUTPUT_ROWS.open("wb") as raw_out:
        with gzip.GzipFile(fileobj=raw_out, mode="wb", mtime=0) as zipped:
            for row in rows_out:
                zipped.write((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    summary = {
        "scope": "Existing verified FT evidence overlays reconciled against the 203,962-FID inventory and current unresolved queue",
        "read_only": True,
        "network_requests": 0,
        "database_writes": 0,
        "inventory_unique_fids": len(inventory),
        "current_unresolved_unique_fids": len(gap_ids),
        "current_resolved_fids_by_inventory_minus_gap": len(inventory) - len(gap_ids),
        "overlay_source_rows": source_rows,
        "verified_overlay_source_unique_fids": source_unique,
        "overlay_union_unique_fids": len(union_ids),
        "overlay_union_fids_already_absent_from_current_gap": len(union_ids - gap_ids),
        "overlay_union_fids_still_in_current_gap": len(union_ids & gap_ids),
        "source_overlap_rows_removed_by_fid_dedup": sum(source_unique.values()) - len(union_ids),
        "cross_source_score_conflicts": conflicts,
        "identity_errors": identity_errors,
        "result_file": OUTPUT_ROWS.name,
        "result_sha256": sha256(OUTPUT_ROWS),
        "input_manifest": inputs,
        "interpretation": "This is a provenance-preserving union of existing source audits, not a new network collection. Source-level raw SHA and result validation remain documented in each source audit. Historical Crown raw results are FT evidence only and do not substitute for Crown AH quotes.",
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in (
        "inventory_unique_fids", "current_unresolved_unique_fids", "current_resolved_fids_by_inventory_minus_gap",
        "overlay_source_rows", "verified_overlay_source_unique_fids", "overlay_union_unique_fids",
        "overlay_union_fids_already_absent_from_current_gap", "overlay_union_fids_still_in_current_gap",
        "source_overlap_rows_removed_by_fid_dedup", "cross_source_score_conflicts", "identity_errors",
        "result_sha256",
    )}, ensure_ascii=False, indent=2))
    return 1 if conflicts or identity_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
