#!/usr/bin/env python3
"""Read-only per-league/year coverage for completed supplemental schedules.

This is an intermediate schedule-recovery audit, not a complete-universe claim.
Only TotalCorner targets already marked complete in the resumable collector's
progress file are summarized. Crown SQLite is opened read-only; source-event
time and actual response-received time remain separate.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
import pathlib
import re
import sqlite3

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / 'research/data_recovery_2019_2026'
PRIVATE = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery')
PROGRESS = PRIVATE / 'progress.json'
LEDGER = PRIVATE / 'fixtures_2019_2026.jsonl'
REQUESTS = PRIVATE / 'requests.jsonl'
TARGETS = OUT / 'm7_named_competition_schedule_targets_20261122.json'
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
OUTPUT = OUT / 'completed_schedule_league_year_coverage_2019_2026.json'
UTC = dt.timezone.utc


def sha(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_utc(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def valid_ft(row: dict) -> bool:
    if str(row.get('status_raw') or '').lower() != 'full':
        return False
    return all(re.fullmatch(r'\d+', str(row.get(key) or '')) for key in ('home_goals_raw', 'away_goals_raw'))


def page_matches(body: dict) -> list[dict]:
    data = body.get('data') or body.get('payload', {}).get('data') or {}
    return data if isinstance(data, list) else data.get('matches') or []


def new_bucket(lid: str, year: str, name: str | None) -> dict:
    return {
        'provider_league_id': lid, 'provider_league_name': name, 'utc_year': year,
        'unique_schedule_fids': 0, 'verified_full_ft_fids': 0,
        'unverified_or_nonfull_fids': 0, 'kickoff_missing_fids': 0,
        'status_counts': {}, 'season_counts': {}, 'source_page_count': 0,
        'source_page_sha256s': set(), 'source_record_versions': 0,
        'sqlite_capture_fids_any_layer': 0, 'sqlite_movement_capture_fids': 0,
        'sqlite_summary_capture_fids': 0, 'crown_movement_quote_fids': 0,
        'crown_movement_quote_rows': 0, 'crown_movement_distinct_source_events': 0,
        'crown_movement_valid_pregame_fids': 0, 'crown_movement_valid_pregame_rows': 0,
        'sqlite_summary_quote_fids': 0, 'sqlite_summary_quote_rows': 0,
        'historical_capture_fids': 0, 'live_capture_fids': 0,
    }


def main() -> None:
    progress = json.loads(PROGRESS.read_text(encoding='utf-8'))
    targets = json.loads(TARGETS.read_text(encoding='utf-8'))
    target_names = {str(row['provider_league_id']): row['league_name'] for row in targets['competitions']}
    complete = {
        str(lid): row for lid, row in progress['targets'].items()
        if row.get('pagination_status') == 'complete_to_2019_cutoff_or_provider_end'
    }

    fixture_versions: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for line in LEDGER.open(encoding='utf-8'):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # append-only ledger may have a partial last write while paging
        lid = str(row.get('provider_league_id') or '')
        if lid in complete and row.get('fid'):
            fixture_versions[(lid, str(row['fid']))].append(row)

    # Reopen the exact schedule response pages and inspect their full records.
    # The compact ledger omits some provider fields (including season on this
    # endpoint), so season coverage is sourced from SHA-verified raw pages.
    request_page_paths = {}
    for line in REQUESTS.open(encoding='utf-8'):
        try: item = json.loads(line)
        except json.JSONDecodeError: continue
        if item.get('event') != 'page_succeeded' or not item.get('success'): continue
        page_key = (str(item.get('league_id')), int(item.get('page') or 0), str(item.get('response_sha256') or ''))
        if all(page_key): request_page_paths[page_key] = item.get('raw_file')
    raw_page_cache = {}
    raw_page_errors = collections.Counter()
    raw_season_by_pair: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    raw_exact_records = 0
    page_fixture_versions: dict[tuple[str, int, str], list[tuple[tuple[str, str], list[dict]]]] = collections.defaultdict(list)
    for pair, versions in fixture_versions.items():
        page_keys = {
            (pair[0], int(row.get('source_page') or 0), str(row.get('source_page_response_sha256') or ''))
            for row in versions
        }
        for page_key in page_keys:
            page_fixture_versions[page_key].append((pair, versions))
    raw_page_keys = set(page_fixture_versions)
    shared_pages = pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
    for lid, page, digest in sorted(raw_page_keys):
        if (lid, page, digest) in raw_page_cache: continue
        raw_name = request_page_paths.get((lid, page, digest))
        candidates = [pathlib.Path(raw_name)] if raw_name else []
        candidates.append(PRIVATE / 'raw' / f'league-{lid}-page-{page}-{digest}.json')
        candidates.extend((shared_pages / lid / f'page-{page}.raw.json', shared_pages / lid / f'page-{page}.json'))
        source_path = next((path for path in candidates if path and path.is_file() and sha(path) == digest), None)
        if source_path is None:
            raw_page_errors['raw_page_missing_or_sha_mismatch'] += 1
            raw_page_cache[(lid, page, digest)] = None
            continue
        try:
            body = json.loads(source_path.read_text(encoding='utf-8'))
            if body.get('success', body.get('status')) not in (1, '1', True):
                raw_page_errors['provider_page_not_success'] += 1
                raw_page_cache[(lid, page, digest)] = None
                continue
            rows = page_matches(body)
            if any(str(row.get('l_id') or '') != lid for row in rows if row.get('l_id') is not None):
                raw_page_errors['page_league_identity_mismatch'] += 1
                raw_page_cache[(lid, page, digest)] = None
                continue
            by_id = {str(row.get('id')): row for row in rows if row.get('id') is not None}
            raw_page_cache[(lid, page, digest)] = by_id
            for (pair_lid, fid), versions in page_fixture_versions[(lid, page, digest)]:
                matching_versions = [v for v in versions if int(v.get('source_page') or 0) == page and str(v.get('source_page_response_sha256') or '') == digest]
                raw = by_id.get(fid)
                if raw is None:
                    raw_page_errors['ledger_fid_missing_from_raw_page'] += 1
                    continue
                compact = json.dumps(raw, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                raw_record_sha = hashlib.sha256(compact).hexdigest()
                if raw_record_sha not in {str(v.get('source_record_sha256') or '') for v in matching_versions}:
                    raw_page_errors['source_record_sha_mismatch'] += 1
                    continue
                raw_exact_records += 1
                season = raw.get('season')
                if season not in (None, ''):
                    raw_season_by_pair[(lid, fid)].add(str(season))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raw_page_errors['raw_page_parse_error'] += 1
            raw_page_cache[(lid, page, digest)] = None

    buckets: dict[tuple[str, str], dict] = {}
    fixture_bucket: dict[str, tuple[str, str] | None] = {}
    fixture_kickoff: dict[str, dt.datetime | None] = {}
    identity_version_conflicts = []
    fid_league_keys: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for (lid, fid), versions in fixture_versions.items():
        unique_versions = {str(row.get('source_record_sha256') or ''): row for row in versions}
        if len(unique_versions) > 1:
            identity_version_conflicts.append({
                'league_id': lid,
                'fid': fid,
                'source_record_sha256s': sorted(unique_versions),
            })
        row = sorted(unique_versions.values(), key=lambda item: str(item.get('source_record_sha256') or ''))[0]
        kickoff = parse_utc(row.get('kickoff_utc'))
        year = str(kickoff.year) if kickoff else 'UNKNOWN_KICKOFF'
        key = (lid, year)
        bucket = buckets.setdefault(key, new_bucket(lid, year, target_names.get(lid, complete[lid].get('expected_name'))))
        bucket['unique_schedule_fids'] += 1
        bucket['source_record_versions'] += len(unique_versions)
        bucket['source_page_sha256s'].add(str(row.get('source_page_response_sha256') or ''))
        bucket['status_counts'][str(row.get('status_raw') or 'MISSING_STATUS')] = bucket['status_counts'].get(str(row.get('status_raw') or 'MISSING_STATUS'), 0) + 1
        season_values = raw_season_by_pair.get((lid, fid), set())
        if not season_values:
            season_values = {'MISSING_SEASON_IN_VERIFIED_RAW_ROW'}
        for season in season_values:
            bucket['season_counts'][season] = bucket['season_counts'].get(season, 0) + 1
        if valid_ft(row):
            bucket['verified_full_ft_fids'] += 1
        else:
            bucket['unverified_or_nonfull_fids'] += 1
        if kickoff is None:
            bucket['kickoff_missing_fids'] += 1
            fixture_bucket[fid] = None
            fixture_kickoff[fid] = None
        else:
            fixture_bucket[fid] = key
            fixture_kickoff[fid] = kickoff
        fid_league_keys[fid].add(key)

    ambiguous_fid_keys = [
        {'fid': fid, 'league_year_keys': sorted(keys),
         'cross_league': len({key[0] for key in keys}) > 1,
         'cross_year_same_league': len({key[1] for key in keys}) > 1}
        for fid, keys in fid_league_keys.items() if len(keys) > 1
    ]
    for item in ambiguous_fid_keys:
        # Do not join an ambiguous provider FID to a single league/year's quote bucket.
        fixture_bucket[item['fid']] = None
        fixture_kickoff[item['fid']] = None

    # Emit explicit zero-row calendar-year buckets for each completed league.
    # A zero here means no fixture row in the verified source inventory, not a
    # claim that the competition did not exist or had no unindexed provider data.
    for lid in complete:
        name = target_names.get(lid, complete[lid].get('expected_name'))
        for year in range(2019, 2027):
            buckets.setdefault((lid, str(year)), new_bucket(lid, str(year), name))

    for bucket in buckets.values():
        bucket['source_page_count'] = len(bucket['source_page_sha256s'] - {''})
        bucket['source_page_sha256s'] = sorted(bucket['source_page_sha256s'] - {''})

    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row
    capture_fids = collections.defaultdict(set)
    movement_capture_fids = collections.defaultdict(set)
    summary_capture_fids = collections.defaultdict(set)
    historical_capture_fids = collections.defaultdict(set)
    live_capture_fids = collections.defaultdict(set)
    movement_fids = collections.defaultdict(set)
    summary_fids = collections.defaultdict(set)
    valid_pre_fids = collections.defaultdict(set)
    valid_pre_rows = collections.Counter()
    movement_row_count = collections.Counter()
    movement_source_times: dict[tuple, set] = collections.defaultdict(set)
    summary_row_count = collections.Counter()
    fids = sorted(fixture_bucket)
    for start in range(0, len(fids), 700):
        chunk = fids[start:start + 700]
        marks = ','.join('?' for _ in chunk)
        for row in cx.execute(
            f'''SELECT fixture_id,data_layer,capture_mode FROM capture WHERE fixture_id IN ({marks})''', chunk
        ):
            fid = str(row['fixture_id']); key = fixture_bucket.get(fid)
            if key is None: continue
            capture_fids[key].add(fid)
            if row['data_layer'] == 'movement': movement_capture_fids[key].add(fid)
            if row['data_layer'] == 'summary': summary_capture_fids[key].add(fid)
            if row['capture_mode'] == 'historical': historical_capture_fids[key].add(fid)
            if row['capture_mode'] == 'live': live_capture_fids[key].add(fid)
        for row in cx.execute(
            f'''SELECT q.fixture_id,c.data_layer,q.quote_kind,q.quote_source_at_utc,
                       q.handicap_home,q.home_decimal,q.away_decimal
                FROM asian_quote q JOIN capture c USING(capture_key)
                WHERE q.fixture_id IN ({marks})''', chunk
        ):
            fid = str(row['fixture_id']); key = fixture_bucket.get(fid)
            if key is None: continue
            if row['data_layer'] == 'movement' and row['quote_kind'] == 'movement':
                movement_fids[key].add(fid); movement_row_count[key] += 1
                source = parse_utc(row['quote_source_at_utc'])
                if source: movement_source_times[(key, fid)].add(source.isoformat())
                kickoff = fixture_kickoff.get(fid)
                try:
                    valid = bool(source and kickoff and source < kickoff
                                 and float(row['home_decimal']) > 1 and float(row['away_decimal']) > 1
                                 and math.isfinite(float(row['handicap_home']) * 4)
                                 and abs(float(row['handicap_home']) * 4 - round(float(row['handicap_home']) * 4)) < 1e-7)
                except (TypeError, ValueError): valid = False
                if valid:
                    valid_pre_fids[key].add(fid); valid_pre_rows[key] += 1
            elif row['data_layer'] == 'summary' and row['quote_kind'] in ('open','close'):
                summary_fids[key].add(fid); summary_row_count[key] += 1
    cx.close()
    for key, bucket in buckets.items():
        bucket['sqlite_capture_fids_any_layer'] = len(capture_fids[key])
        bucket['sqlite_movement_capture_fids'] = len(movement_capture_fids[key])
        bucket['sqlite_summary_capture_fids'] = len(summary_capture_fids[key])
        bucket['historical_capture_fids'] = len(historical_capture_fids[key])
        bucket['live_capture_fids'] = len(live_capture_fids[key])
        bucket['crown_movement_quote_fids'] = len(movement_fids[key])
        bucket['crown_movement_quote_rows'] = movement_row_count[key]
        bucket['crown_movement_distinct_source_events'] = sum(len(v) for (k, _), v in movement_source_times.items() if k == key)
        bucket['crown_movement_valid_pregame_fids'] = len(valid_pre_fids[key])
        bucket['crown_movement_valid_pregame_rows'] = valid_pre_rows[key]
        bucket['sqlite_summary_quote_fids'] = len(summary_fids[key])
        bucket['sqlite_summary_quote_rows'] = summary_row_count[key]

    results = [dict(value) for _, value in sorted(buckets.items(), key=lambda item: (int(item[0][0]), item[0][1]))]
    output = {
        'generated_at_utc': dt.datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'scope_note': 'Only targets marked pagination-complete in the live progress file are included; ongoing targets and queued IDs are not represented as complete.',
        'target_count_in_current_file': len(targets['competitions']),
        'completed_target_count': len(complete),
        'completed_target_leagues': [
            {'provider_league_id': lid, 'league_name': complete[lid].get('expected_name'),
             'unique_2019_2026_fids': complete[lid].get('unique_2019_2026_fids'),
             'pages_read': complete[lid].get('pages_read'),
             'reported_pages': complete[lid].get('reported_pages'),
             'pagination_status': complete[lid].get('pagination_status'),
             'failed_pages': complete[lid].get('failed_pages', [])}
            for lid in sorted(complete, key=int)
        ],
        'unique_schedule_fids': len(fid_league_keys),
        'league_fid_pairs': len(fixture_versions),
        'cross_league_fid_collision_count': sum(item['cross_league'] for item in ambiguous_fid_keys),
        'cross_year_same_league_fid_conflict_count': sum(item['cross_year_same_league'] for item in ambiguous_fid_keys),
        'ambiguous_fid_league_year_keys': ambiguous_fid_keys,
        'verified_full_ft_fids': sum(row['verified_full_ft_fids'] for row in buckets.values()),
        'unverified_or_nonfull_fids': sum(row['unverified_or_nonfull_fids'] for row in buckets.values()),
        'identity_version_conflict_count': len(identity_version_conflicts),
        'identity_version_conflicts': identity_version_conflicts,
        'raw_source_page_audit': {
            'distinct_referenced_pages': len(raw_page_keys),
            'source_record_rows_sha_verified': raw_exact_records,
            'errors': dict(raw_page_errors),
            'season_field_source': 'exact row in SHA-verified TotalCorner schedule page raw response',
        },
        'crown_crosscheck': {
            'database_opened_read_only': True,
            'database_sha256': sha(DB),
            'historical_capture_fids': sum(row['historical_capture_fids'] for row in buckets.values()),
            'live_capture_fids': sum(row['live_capture_fids'] for row in buckets.values()),
            'movement_quote_fids': sum(row['crown_movement_quote_fids'] for row in buckets.values()),
            'movement_quote_rows': sum(row['crown_movement_quote_rows'] for row in buckets.values()),
            'summary_quote_fids': sum(row['sqlite_summary_quote_fids'] for row in buckets.values()),
            'summary_quote_rows': sum(row['sqlite_summary_quote_rows'] for row in buckets.values()),
            'valid_pregame_movement_fids': sum(row['crown_movement_valid_pregame_fids'] for row in buckets.values()),
            'valid_pregame_movement_rows': sum(row['crown_movement_valid_pregame_rows'] for row in buckets.values()),
            'quote_source_time_and_http_receive_time_kept_as_separate_fields': True,
        },
        'by_league_year': results,
        'zero_year_bucket_note': 'A zero schedule count means no FID was present in the currently verified source rows for that completed provider pagination; it does not prove no competition season or unindexed source exists.',
        'input_sha256': {
            'progress': sha(PROGRESS), 'append_only_fixture_ledger': sha(LEDGER),
            'append_only_request_log': sha(REQUESTS), 'target_manifest': sha(TARGETS),
        },
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: output[key] for key in ('generated_at_utc','completed_target_count','unique_schedule_fids','verified_full_ft_fids','unverified_or_nonfull_fids','identity_version_conflict_count','crown_crosscheck','input_sha256')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
