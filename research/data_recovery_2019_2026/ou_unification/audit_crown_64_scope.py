#!/usr/bin/env python3
"""Reconcile the fixed 64 Provider League IDs with the 2023-2026 fixture file."""
from __future__ import annotations
import collections, hashlib, importlib.util, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEDULE = Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
COLLECTOR = HERE / 'collect_crown_ah_ou_64.py'
OUT = HERE / 'crown_64_scope_reconciliation_20261122.json'

spec = importlib.util.spec_from_file_location('crown_collector', COLLECTOR)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
fixed_ids = set(collector.IDS)
all_rows = 0
all_schedule_ids: set[int] = set()
scoped_ids_any_year: set[int] = set()
all_rows_by_scope_year: collections.Counter[int] = collections.Counter()
rows_by_league_year: collections.Counter[tuple[int, int]] = collections.Counter()
id314_names: set[tuple[str | None, str | None]] = set()
scoped_fids: set[str] = set()
score_values_present = 0
score_values_missing = 0
with SCHEDULE.open(encoding='utf-8') as fh:
    for line in fh:
        row = json.loads(line)
        all_rows += 1
        league = int(row['league_id'])
        year = int(row.get('season_year') or 0)
        all_schedule_ids.add(league)
        if league == 314:
            id314_names.add((row.get('source_league'), row.get('scope_item')))
        if league not in fixed_ids:
            continue
        scoped_ids_any_year.add(league)
        rows_by_league_year[(league, year)] += 1
        if 2023 <= year <= 2026:
            fid = str(row.get('match_id') or '')
            if fid:
                scoped_fids.add(fid)
                all_rows_by_scope_year[year] += 1
                if isinstance(row.get('home_goals'), int) and isinstance(row.get('away_goals'), int):
                    score_values_present += 1
                else:
                    score_values_missing += 1
result = {
    'scope': 'fixed 64 Provider League IDs; years 2023-2026',
    'schedule_path': str(SCHEDULE),
    'schedule_sha256': hashlib.sha256(SCHEDULE.read_bytes()).hexdigest(),
    'collector_code_path': str(COLLECTOR),
    'fixed_provider_league_ids': sorted(fixed_ids),
    'fixed_id_count': len(fixed_ids),
    'schedule_row_count_all_years': all_rows,
    'schedule_provider_ids_all_years': sorted(all_schedule_ids),
    'schedule_provider_id_count_all_years': len(all_schedule_ids),
    'fixed_ids_equal_all_schedule_ids': fixed_ids == all_schedule_ids,
    'fixed_ids_present_in_schedule': sorted(scoped_ids_any_year),
    'all_fixed_ids_present_in_schedule': fixed_ids == scoped_ids_any_year,
    'target_unique_fids': len(scoped_fids),
    'target_fids_by_year': {str(y): all_rows_by_scope_year[y] for y in range(2023, 2027)},
    'target_fids_with_numeric_score_fields': score_values_present,
    'target_fids_missing_numeric_score_fields': score_values_missing,
    'fixed_ids_with_zero_target_fixtures': sorted(
        league for league in fixed_ids if sum(n for (lid, yr), n in rows_by_league_year.items()
                                                if lid == league and 2023 <= yr <= 2026) == 0
    ),
    'id_314_history': {
        'identity_in_schedule': sorted(id314_names),
        'fixture_counts_by_year': {str(y): rows_by_league_year[(314, y)]
                                   for y in range(2019, 2027) if rows_by_league_year[(314, y)]},
    },
    'caveat': 'Zero target fixtures for an in-scope Provider League ID is reported as inventory state; the ID is not removed and no replacement league is added.'
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
