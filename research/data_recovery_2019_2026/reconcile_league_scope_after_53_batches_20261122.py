#!/usr/bin/env python3
"""Reconcile exact provider IDs after merging the audited 53-league batch."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCOPE = ROOT / "league_scope_union_2019_2026.json"
BASE_SUMMARY = ROOT / "inventory_coverage_summary_2019_2026.json"
SUPP = ROOT / "supplemental_totalcorner_schedules_53leagues_2019_2026.jsonl.gz"
MERGED = ROOT / "fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz"
OUT = ROOT / "league_scope_reconciliation_after_53_batches_20261122.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    scope = json.loads(SCOPE.read_text())
    base = json.loads(BASE_SUMMARY.read_text())
    base_ids = {str(x) for x in base["provider_league_ids"]}
    missing_before = {str(x) for x in scope["set_audit"]["inventory_ids_missing_from_union"]}
    pair_names = collections.defaultdict(set)
    name_ids = collections.defaultdict(set)
    supplemental_ids = set()
    row_count = 0
    with gzip.open(SUPP, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            lid = str(row.get("provider_league_id") or "")
            name = str(row.get("provider_league_name") or row.get("provider_league_name_from_target_inventory") or "")
            if not lid or not name:
                raise SystemExit("supplemental row lacks exact provider league ID/name")
            supplemental_ids.add(lid)
            pair_names[lid].add(name)
            name_ids[name].add(lid)
            row_count += 1

    new_ids = supplemental_ids - base_ids
    unresolved_now_covered = new_ids & missing_before
    if new_ids != missing_before:
        raise SystemExit(f"new supplemental IDs and prior scope gap differ: {len(new_ids)} vs {len(missing_before)}")
    if any(len(v) != 1 for v in pair_names.values()) or any(len(v) != 1 for v in name_ids.values()):
        raise SystemExit("supplemental exact ID/name mapping is ambiguous")

    merged_ids = set()
    merged_fids = 0
    with gzip.open(MERGED, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            merged_ids.add(str(row.get("provider_league_id") or ""))
            merged_fids += 1
    # The existing audit's 118-ID explicit scope union has zero formal/expanded
    # IDs absent from inventory, plus the 38 supplemental gaps listed above.
    known_union_size = int(scope["set_audit"]["total_union_including_observed_m1_only"])
    if len(base_ids | supplemental_ids) != known_union_size:
        raise SystemExit("merged schedule scope differs from prior explicit provider-ID union size")
    if not (base_ids | supplemental_ids).issubset(merged_ids):
        raise SystemExit("provider IDs in base/supplemental sources missing from merged inventory")

    out = {
        "method": "exact provider ID/name reconciliation from saved, SHA-audited TotalCorner schedule records; no fuzzy matching or network requests",
        "inputs": {
            SCOPE.name: {"sha256": sha256(SCOPE), "previous_explicit_union_ids": known_union_size},
            BASE_SUMMARY.name: {"sha256": sha256(BASE_SUMMARY), "baseline_inventory_ids": len(base_ids)},
            SUPP.name: {"sha256": sha256(SUPP), "source_rows": row_count, "unique_fids": 89842, "unique_provider_ids": len(supplemental_ids)},
            MERGED.name: {"sha256": sha256(MERGED), "unique_fids": merged_fids, "unique_provider_ids": len(merged_ids)},
        },
        "result": {
            "supplemental_provider_ids_already_in_baseline": len(supplemental_ids & base_ids),
            "supplemental_provider_ids_new_to_baseline": len(new_ids),
            "previously_known_provider_ids_absent_from_baseline_now_covered": len(unresolved_now_covered),
            "remaining_previous_provider_id_inventory_gaps": len(missing_before - new_ids),
            "current_baseline_plus_supplemental_provider_ids": len(base_ids | supplemental_ids),
            "prior_explicit_union_provider_ids": known_union_size,
            "merged_inventory_unique_provider_ids": len(merged_ids),
            "id_to_exact_name_ambiguities": sum(len(v) > 1 for v in pair_names.values()),
            "exact_name_to_id_ambiguities": sum(len(v) > 1 for v in name_ids.values()),
            "network_requests": 0,
        },
        "supplemental_exact_provider_id_name_pairs": [
            {"provider_league_id": lid, "provider_league_name": next(iter(names))}
            for lid, names in sorted(pair_names.items(), key=lambda x: int(x[0]))
        ],
        "caveat": "This closes the 38-ID inventory gap found in the prior explicit source-union audit. It does not prove that no other leagues exist outside all currently inventoried/configured sources, nor that every season or match is complete.",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out["result"], ensure_ascii=False))


if __name__ == "__main__":
    main()
