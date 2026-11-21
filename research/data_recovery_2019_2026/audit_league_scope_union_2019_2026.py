#!/usr/bin/env python3
"""Reconcile the currently explicit provider-league scope without network calls.

The output is a moving source-union audit, not a claim that no further leagues
can ever be discovered. No fixture outcomes, odds, or strategy data are read.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[2]
QUANT = pathlib.Path('/Users/mac/QuantAsiaDesk')
OUT = REPO / 'research/data_recovery_2019_2026'
FORMAL = QUANT / 'data/m5-crown-authorized/m1-scope-leagues.json'
EXPANDED = QUANT / 'research-work/crown-drop-expanded-62/schedule_universe.jsonl'
INVENTORY = OUT / 'inventory_coverage_summary_2019_2026.json'
CANDIDATES = OUT / 'unresolved_schedule_competition_candidates_20261121.json'
OUTPUT = OUT / 'league_scope_union_2019_2026.json'


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    formal_doc = json.loads(FORMAL.read_text(encoding='utf-8'))
    formal = {str(k) for k in formal_doc}

    expanded_rows = collections.Counter()
    for line in EXPANDED.open(encoding='utf-8'):
        row = json.loads(line)
        lid = row.get('league_id') or row.get('l_id')
        if lid is not None:
            expanded_rows[str(lid)] += 1
    expanded = set(expanded_rows)

    inventory_doc = json.loads(INVENTORY.read_text(encoding='utf-8'))
    inventory_ids = {str(x) for x in inventory_doc['provider_league_ids']}
    source_counts = collections.defaultdict(collections.Counter)
    for row in inventory_doc['league_year_coverage']:
        lid = str(row['provider_league_id'])
        for col in ('totalcorner_schedule_fids', 'expanded_universe_fids',
                    'supplemental_schedule_fids', 'crown_fixture_metadata_fids',
                    'M1_history_cache_fids', 'T6_priced_inventory_fids'):
            source_counts[lid][col] += int(row.get(col, 0) or 0)

    candidate_doc = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    candidates = {str(x['provider_league_id']) for x in candidate_doc['competitions']}
    explicit_union = formal | expanded | candidates
    observed_m1_only = inventory_ids - (formal | expanded | candidates)
    expected_union = explicit_union | observed_m1_only
    missing = expected_union - inventory_ids
    unexpected = inventory_ids - expected_union

    result = {
        'audit': 'explicit provider league source union for 2019-2026 historical recovery',
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'network_requests': 0,
        'scope_is_exhaustive_forever': False,
        'scope_note': 'Union of the currently available formal M1 scope, expanded schedule universe, unresolved scoped schedule candidates, and observed M1-history-only provider IDs. New source discoveries can extend it.',
        'sources': {
            'formal_m1_scope': {'path': str(FORMAL), 'sha256': sha256(FORMAL), 'league_ids': len(formal), 'ids': sorted(formal, key=int)},
            'expanded_62_schedule_universe': {'path': str(EXPANDED), 'sha256': sha256(EXPANDED), 'league_ids': len(expanded), 'ids': sorted(expanded, key=int), 'rows_per_id': dict(sorted(expanded_rows.items(), key=lambda x: int(x[0])))},
            'scoped_schedule_candidates_with_prior_request_errors': {'path': str(CANDIDATES), 'sha256': sha256(CANDIDATES), 'league_ids': len(candidates), 'ids': sorted(candidates, key=int)},
            'current_reconciled_inventory': {'path': str(INVENTORY), 'sha256': sha256(INVENTORY), 'league_ids': len(inventory_ids), 'ids': sorted(inventory_ids, key=int)},
        },
        'observed_m1_history_only_ids': {
            'ids': sorted(observed_m1_only, key=int),
            'source_fids_by_id': {lid: dict(source_counts[lid]) for lid in sorted(observed_m1_only, key=int)},
        },
        'set_audit': {
            'formal_union_expanded': len(formal | expanded),
            'explicit_union_formal_expanded_candidates': len(explicit_union),
            'total_union_including_observed_m1_only': len(expected_union),
            'inventory_ids_missing_from_union': sorted(missing, key=int),
            'inventory_ids_outside_union': sorted(unexpected, key=int),
            'candidate_ids_already_in_inventory': sorted(candidates & inventory_ids, key=int),
            'candidate_ids_not_yet_in_inventory': sorted(candidates - inventory_ids, key=int),
            'formal_ids_not_in_inventory': sorted(formal - inventory_ids, key=int),
            'expanded_ids_not_in_inventory': sorted(expanded - inventory_ids, key=int),
        },
        'completion_status': 'incomplete' if missing else 'known_union_covered',
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'output': str(OUTPUT),
        'formal_ids': len(formal),
        'expanded_ids': len(expanded),
        'candidate_ids': len(candidates),
        'm1_history_only_ids': sorted(observed_m1_only, key=int),
        'known_union_ids': len(expected_union),
        'inventory_ids': len(inventory_ids),
        'missing_ids': sorted(missing, key=int),
        'unexpected_ids': sorted(unexpected, key=int),
        'network_requests': 0,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
