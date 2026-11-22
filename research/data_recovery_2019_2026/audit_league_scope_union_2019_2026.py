#!/usr/bin/env python3
"""Reconcile the currently explicit provider-league scope without network calls.

The output is a moving source-union audit, not a claim that no further leagues
can ever be discovered. No fixture outcomes, odds, or strategy data are read.
"""
from __future__ import annotations

import collections
import glob
import gzip
import hashlib
import json
import pathlib
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parents[2]
QUANT = pathlib.Path('/Users/mac/QuantAsiaDesk')
OUT = REPO / 'research/data_recovery_2019_2026'
FORMAL = QUANT / 'data/m5-crown-authorized/m1-scope-leagues.json'
EXPANDED = QUANT / 'research-work/crown-drop-expanded-62/schedule_universe.jsonl'
INVENTORY = OUT / 'fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz'
COVERAGE_SUMMARY = OUT / 'inventory_coverage_summary_2019_2026.json'
CANDIDATES = OUT / 'unresolved_schedule_competition_candidates_20261121.json'
M7_UNIVERSE = QUANT / 'repos/mr1/config/mr1-research-universe-v1.json'
RECOVERED_TOTALCORNER = (QUANT / 'research-work/recovered_factors_20261121/report-branch'
                         / 'research/shared_history/totalcorner')
M1_SCHEDULE_PAGES = QUANT / 'data/m5-crown-authorized/schedules'
M7_SCHEDULE_RAW = QUANT / 'research-work/m7/m7_current_approved_schedule_refresh_20261110/raw'
SUPPLEMENTAL_RAW = (QUANT / 'research-work/full_history_backfill_20261121'
                    / 'totalcorner_schedule_recovery/raw')
OUTPUT = OUT / 'league_scope_union_2019_2026.json'
RAW_RESPONSE_MAPPING = OUT / 'crown_raw_exact_league_name_mapping_2019_2026.json'
PAGE_MAPPING_TARGETS = OUT / 'm7_named_competition_schedule_targets_20261122.json'


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_totalcorner_matches(path: pathlib.Path):
    """Yield exact provider ID/name pairs from already saved TotalCorner JSON."""
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return
    matches = (doc.get('data') or {}).get('matches', [])
    for row in matches:
        lid, name = row.get('l_id'), row.get('l')
        if lid is not None and name:
            yield str(lid), str(name)


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

    # Use the current merged FID inventory, not the older 80-league summary
    # snapshot, so later supplemental schedules are included in the audit.
    inventory_ids = set()
    source_counts = collections.defaultdict(collections.Counter)
    with gzip.open(INVENTORY, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            lid = str(row.get('provider_league_id') or '')
            if not lid:
                continue
            inventory_ids.add(lid)
            for key, col in (('totalcorner_page_records', 'totalcorner_schedule_fids'),
                             ('expanded_universe_records', 'expanded_universe_fids'),
                             ('supplemental_schedule_records', 'supplemental_schedule_fids'),
                             ('crown_fixture_metadata_records', 'crown_fixture_metadata_fids'),
                             ('M1_history_cache_records', 'M1_history_cache_fids'),
                             ('priced_t6_records', 'T6_priced_inventory_fids')):
                if row.get(key):
                    source_counts[lid][col] += 1

    candidate_doc = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    candidates = {str(x['provider_league_id']) for x in candidate_doc['competitions']}

    # Exact competition labels found in SHA-verified archived TotalCorner
    # fixture responses. Do not infer IDs from similar competition names.
    raw_map_doc = json.loads(RAW_RESPONSE_MAPPING.read_text(encoding='utf-8')) if RAW_RESPONSE_MAPPING.exists() else None
    if raw_map_doc:
        # This map is immutable evidence anchored to its own historical
        # SQLite snapshot. The current database has since grown, so do not
        # compare its source SHA to the latest moving coverage snapshot.
        raw_mapped_ids = {str(lid) for row in raw_map_doc['mapped_exact_names'] for lid in row['provider_league_ids']}
        raw_mapped_names = {row['competition_name_exact'] for row in raw_map_doc['mapped_exact_names']}
    else:
        raw_mapped_ids=set();raw_mapped_names=set()

    # Build an exact-name map from actual saved provider records only. Do not
    # fuzzy-match translations or infer provider IDs from competition names.
    id_to_names = collections.defaultdict(set)
    for lid, name in formal_doc.items():
        id_to_names[str(lid)].add(str(name))
    for line in EXPANDED.open(encoding='utf-8'):
        row = json.loads(line)
        lid = row.get('league_id') or row.get('l_id')
        if lid is not None:
            for name in (row.get('source_league'), row.get('scope_item')):
                if name:
                    id_to_names[str(lid)].add(str(name))
    for row in candidate_doc['competitions']:
        id_to_names[str(row['provider_league_id'])].add(str(row['league_name']))
    name_to_ids = collections.defaultdict(set)
    for lid, names in id_to_names.items():
        for name in names:
            name_to_ids[name].add(lid)

    m7_doc = json.loads(M7_UNIVERSE.read_text(encoding='utf-8'))
    named_sources = {
        key: sorted({str(x) for x in m7_doc.get(key, [])})
        for key in ('first_tier_totalcorner_exact',
                    'opponent_observed_totalcorner_exact',
                    'deprecated_second_tier_totalcorner_exact')
    }
    name_sources = collections.defaultdict(set)
    for source, names in named_sources.items():
        for name in names:
            name_sources[name].add(source)
    named_competitions = sorted(name_sources)

    # Enrich the name map from already cached TotalCorner responses. For the
    # active supplemental archive, require the sidecar's response SHA and
    # league metadata to agree before using its ID/name pair. No network calls.
    mapping_evidence = collections.defaultdict(list)
    archive_inputs = {}
    m7_exact_names = set(named_competitions)
    evidence_seen = set()

    def add_cached_pair(path: pathlib.Path, source: str, require_sidecar: bool = False):
        pairs = [(lid, name) for lid, name in (read_totalcorner_matches(path) or ())
                 if name in m7_exact_names]
        if not pairs:
            return
        raw_digest = sha256(path)
        meta_path = path.with_suffix('.meta.json')
        meta = None
        if require_sidecar:
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                return
            if (meta.get('http_status') != 200 or meta.get('provider_success') != 1
                    or meta.get('response_sha256') != raw_digest):
                return
        for lid, name in sorted(set(pairs)):
            if meta is not None and str(meta.get('league_id')) != lid:
                continue
            if meta is not None and str(meta.get('reported_league_id')) != lid:
                continue
            name_to_ids[name].add(lid)
            evidence_key = (name, lid, source)
            if evidence_key in evidence_seen:
                continue
            evidence_seen.add(evidence_key)
            if meta is not None:
                archive_inputs[str(meta_path)] = sha256(meta_path)
            mapping_evidence[(name, lid)].append({
                'source': source,
                'path': str(path),
                'file_sha256': raw_digest,
                'sidecar_verified': meta is not None,
                'sidecar_path': str(meta_path) if meta is not None else None,
                'sidecar_sha256': sha256(meta_path) if meta is not None else None,
            })
            archive_inputs[str(path)] = raw_digest

    for pattern, source, sidecar in (
        (str(RECOVERED_TOTALCORNER / 'league-*.jsonl'), 'recovered_totalcorner_shared_history', False),
        (str(M1_SCHEDULE_PAGES / '*' / 'page-*.raw.json'), 'm1_cached_totalcorner_schedule_page', False),
        (str(M7_SCHEDULE_RAW / '**' / '*.json'), 'm7_cached_totalcorner_schedule_refresh', False),
        (str(SUPPLEMENTAL_RAW / 'league-*.json'), 'supplemental_totalcorner_schedule_response', True),
    ):
        for filename in sorted(glob.glob(pattern, recursive='**' in pattern)):
            path = pathlib.Path(filename)
            if path.suffix == '.jsonl':
                # Per-league JSONL exports have the source ID in each row;
                # hash the exact file and preserve the exact rows used.
                matching_rows = []
                for line in path.open(encoding='utf-8'):
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    lid, name = row.get('league_id'), row.get('league_name')
                    if lid is None or not name or str(name) not in m7_exact_names:
                        continue
                    matching_rows.append((str(lid), str(name)))
                if not matching_rows:
                    continue
                digest = sha256(path)
                for lid, name in sorted(set(matching_rows)):
                    name_to_ids[name].add(lid)
                    evidence_key = (name, lid, source)
                    if evidence_key in evidence_seen:
                        continue
                    evidence_seen.add(evidence_key)
                    mapping_evidence[(name, lid)].append({
                        'source': source, 'path': str(path), 'file_sha256': digest,
                        'sidecar_verified': False,
                    })
                    archive_inputs[str(path)] = digest
            else:
                add_cached_pair(path, source, require_sidecar=sidecar)

    if raw_map_doc:
        for row in raw_map_doc['mapped_exact_names']:
            name = str(row['competition_name_exact'])
            for evidence_row in row['evidence_by_id']:
                lid = str(evidence_row['provider_league_id'])
                name_to_ids[name].add(lid)
                mapping_evidence[(name,lid)].append({
                    'source':'sha_verified_saved_TotalCorner_match_view_response',
                    'source_sqlite_sha256':raw_map_doc['source_crown_sqlite_sha256'],
                    'distinct_fids':evidence_row['distinct_fids'],
                    'response_sha256_count':evidence_row['response_sha256_count'],
                    'response_sha256_sample':evidence_row['response_sha256_sample'],
                    'capture_layers':evidence_row['capture_layers'],
                    'capture_modes':evidence_row['capture_modes'],
                    'response_received_min_utc':evidence_row['response_received_min_utc'],
                    'response_received_max_utc':evidence_row['response_received_max_utc'],
                    'verification':'exact response l/l_id pair; raw_response_sha256 matched SQLite capture row',
                })

    # A small residual set had no matching archived Crown match-view response.
    # Accept only the separately recorded exact TotalCorner provider-page ID
    # checks; keep this evidence class separate from response-derived mapping.
    page_mapping_doc = json.loads(PAGE_MAPPING_TARGETS.read_text(encoding='utf-8')) if PAGE_MAPPING_TARGETS.exists() else {}
    page_mapped_ids = set()
    page_mapped_names = set()
    for row in page_mapping_doc.get('supplemental_exact_provider_page_mappings', []):
        name = str(row['league_name'])
        lid = str(row['provider_league_id'])
        url = row['provider_page_url']
        page_mapped_ids.add(lid)
        page_mapped_names.add(name)
        name_to_ids[name].add(lid)
        mapping_evidence[(name, lid)].append({
            'source': 'exact_TotalCorner_provider_league_page',
            'provider_page_url': url,
            'provider_page_name_matches_exact_M7_label': True,
            'verified_at_utc': page_mapping_doc.get('provider_page_mapping_verified_at_utc'),
            'verification': 'provider page path includes league ID and rendered page title exactly matches listed competition name',
        })

    mapped_name_rows = []
    unmapped_name_rows = []
    multiply_mapped_name_rows = []
    for name in named_competitions:
        ids = sorted(name_to_ids.get(name, set()), key=int)
        row = {'competition_name_exact': name,
               'listed_in': sorted(name_sources[name]),
               'provider_league_ids_in_current_id_sources': ids,
               'raw_source_evidence': [e for lid in ids
                                       for e in mapping_evidence.get((name, lid), [])]}
        if not ids:
            unmapped_name_rows.append(row)
        else:
            mapped_name_rows.append(row)
            if len(ids) > 1:
                multiply_mapped_name_rows.append(row)

    explicit_union = formal | expanded | candidates | raw_mapped_ids | page_mapped_ids
    observed_m1_only = inventory_ids - (formal | expanded | candidates | raw_mapped_ids | page_mapped_ids)
    expected_union = explicit_union | observed_m1_only
    missing = expected_union - inventory_ids
    unexpected = inventory_ids - expected_union

    result = {
        'audit': 'explicit provider league source union for 2019-2026 historical recovery',
        'generated_at_utc': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'network_requests': 0,
        'scope_is_exhaustive_forever': False,
        'scope_note': 'Provider-ID union is limited to explicit ID sources. M7 also contains exact-name research-universe lists; names not mapped by exact existing records remain unresolved and must be investigated. This is not a claim that no additional competition can be discovered.',
        'sources': {
            'formal_m1_scope': {'path': str(FORMAL), 'sha256': sha256(FORMAL), 'league_ids': len(formal), 'ids': sorted(formal, key=int)},
            'expanded_62_schedule_universe': {'path': str(EXPANDED), 'sha256': sha256(EXPANDED), 'league_ids': len(expanded), 'ids': sorted(expanded, key=int), 'rows_per_id': dict(sorted(expanded_rows.items(), key=lambda x: int(x[0])))},
            'scoped_schedule_candidates_with_prior_request_errors': {'path': str(CANDIDATES), 'sha256': sha256(CANDIDATES), 'league_ids': len(candidates), 'ids': sorted(candidates, key=int)},
            'm7_named_competitions_mapped_from_sha_verified_saved_responses': {
                'path': str(RAW_RESPONSE_MAPPING) if raw_map_doc else None,
                'sha256': sha256(RAW_RESPONSE_MAPPING) if raw_map_doc else None,
                'source_crown_sqlite_sha256': raw_map_doc.get('source_crown_sqlite_sha256') if raw_map_doc else None,
                'network_requests': 0,
                'mapped_exact_names': len(raw_mapped_names),
                'league_ids': len(raw_mapped_ids),
                'ids': sorted(raw_mapped_ids, key=int),
            },
            'm7_named_competitions_mapped_from_exact_TotalCorner_provider_pages': {
                'path': str(PAGE_MAPPING_TARGETS) if page_mapping_doc else None,
                'sha256': sha256(PAGE_MAPPING_TARGETS) if page_mapping_doc else None,
                'mapped_exact_names': len(page_mapped_names),
                'league_ids': len(page_mapped_ids),
                'ids': sorted(page_mapped_ids, key=int),
                'mappings': page_mapping_doc.get('supplemental_exact_provider_page_mappings', []),
            },
            'm7_research_universe_named_competitions': {
                'path': str(M7_UNIVERSE), 'sha256': sha256(M7_UNIVERSE),
                'production_scope_changed_field': m7_doc.get('production_scope_changed'),
                'interpretation': 'Historical source-scope evidence only. Deprecated second-tier entries are inventoried for data recovery; this audit does not apply them to production filtering.',
                'competition_counts_by_list': {key: len(values) for key, values in named_sources.items()},
                'unique_exact_names': len(named_competitions),
                'exact_name_to_id_mapping_sources': [
                    'formal M1 ID/name file', 'expanded schedule-universe rows',
                    'scoped schedule candidate records',
                    'saved TotalCorner shared-history JSONL',
                    'saved M1 and M7 TotalCorner schedule responses',
                    'active supplemental schedule responses with matching SHA sidecars',
                    'SHA-verified saved TotalCorner match-view responses embedded in Crown raw responses',
                    'exact TotalCorner provider pages for the three residual M7 competition names',
                ],
                'cached_mapping_input_files': archive_inputs,
                'mapped_exact_names': mapped_name_rows,
                'unmapped_exact_names': unmapped_name_rows,
                'multiply_mapped_exact_names': multiply_mapped_name_rows,
            },
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
            'raw_response_mapped_ids_not_yet_in_inventory': sorted(raw_mapped_ids - inventory_ids, key=int),
            'provider_page_mapped_ids_not_yet_in_inventory': sorted(page_mapped_ids - inventory_ids, key=int),
            'm7_exact_names_unmapped_to_provider_id': len(unmapped_name_rows),
            'm7_exact_names_mapped_to_multiple_provider_ids': len(multiply_mapped_name_rows),
            'formal_ids_not_in_inventory': sorted(formal - inventory_ids, key=int),
            'expanded_ids_not_in_inventory': sorted(expanded - inventory_ids, key=int),
        },
        'completion_status': 'incomplete' if missing or unmapped_name_rows or multiply_mapped_name_rows else 'known_union_covered',
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
        'm7_named_competitions': len(named_competitions),
        'm7_named_competitions_unmapped_to_id': len(unmapped_name_rows),
        'unmapped_names': [x['competition_name_exact'] for x in unmapped_name_rows],
        'unexpected_ids': sorted(unexpected, key=int),
        'network_requests': 0,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
