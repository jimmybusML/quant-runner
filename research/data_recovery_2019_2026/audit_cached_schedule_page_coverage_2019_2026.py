#!/usr/bin/env python3
"""Audit local TotalCorner schedule-page continuity for the 2019+ time range.

This distinguishes pages omitted before the requested date range from actual
holes inside the pages containing fixtures dated 2019-01-01 through 2026-12-31.
It reads existing response files only and makes no network requests.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = ROOT / 'research/data_recovery_2019_2026/inventory_coverage_summary_2019_2026.json'
SCHEDULE_ROOT = pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
OUT = pathlib.Path(__file__).resolve().parent
START = '2019-01-01'
END = '2026-12-31'
PAGE_RE = re.compile(r'page-(\d+)(?:\.raw)?\.json$')


def load_matches(path: pathlib.Path) -> tuple[list[dict], dict]:
    body = json.loads(path.read_text(encoding='utf-8'))
    data = body.get('data') or body.get('payload', {}).get('data') or {}
    matches = data if isinstance(data, list) else data.get('matches') or []
    league = data.get('league') or {} if isinstance(data, dict) else {}
    pagination = body.get('pagination') or body.get('payload', {}).get('pagination') or {}
    return matches, {'league_id': str(league.get('league_id') or ''), 'pagination': pagination}


def main() -> None:
    baseline_bytes = BASELINE.read_bytes()
    baseline = json.loads(baseline_bytes)
    league_rows = []
    for expected in baseline['schedule_pages']['completeness']:
        lid = str(expected['provider_league_id'])
        directory = SCHEDULE_ROOT / lid
        files: dict[int, pathlib.Path] = {}
        for path in directory.iterdir() if directory.exists() else []:
            match = PAGE_RE.fullmatch(path.name)
            if not match:
                continue
            page_no = int(match.group(1))
            # Prefer the raw response file when both normalized variants exist.
            if page_no not in files or path.name.endswith('.raw.json'):
                files[page_no] = path

        pages = []
        page_parse_errors = []
        league_identity_mismatches = []
        for page_no, path in sorted(files.items()):
            try:
                matches, metadata = load_matches(path)
                if metadata['league_id'] and metadata['league_id'] != lid:
                    league_identity_mismatches.append({'page': page_no, 'reported_league_id': metadata['league_id']})
                dates = [str(row.get('start', ''))[:10] for row in matches if row.get('start')]
                valid_dates = [value for value in dates if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value)]
                pages.append({
                    'page': page_no,
                    'row_count': len(matches),
                    'min_source_date': min(valid_dates) if valid_dates else None,
                    'max_source_date': max(valid_dates) if valid_dates else None,
                    'response_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'response_file': path.name,
                    'reported_pages': metadata['pagination'].get('pages'),
                })
            except Exception as exc:  # record corrupt/unsupported files, never treat as an empty page
                page_parse_errors.append({'page': page_no, 'error_type': type(exc).__name__})

        relevant = [p for p in pages if p['max_source_date'] and p['max_source_date'] >= START and p['min_source_date'] and p['min_source_date'] <= END]
        last_relevant = max((p['page'] for p in relevant), default=0)
        relevant_holes = sorted(set(range(1, last_relevant + 1)) - set(files))
        first_pre_start = min((p['page'] for p in pages if p['max_source_date'] and p['max_source_date'] < START), default=0)
        boundary_holes = sorted(set(range(last_relevant + 1, first_pre_start)) - set(files)) if last_relevant and first_pre_start else []
        ordered_pages = [p for p in pages if p['max_source_date']]
        monotone_newest_first = all(
            later['max_source_date'] <= earlier['max_source_date']
            for earlier, later in zip(ordered_pages, ordered_pages[1:])
        )
        reported_pages = int(expected.get('reported_pages_max') or 0)
        all_pages_missing = sorted(set(range(1, reported_pages + 1)) - set(files)) if reported_pages else []
        league_rows.append({
            'provider_league_id': lid,
            'league_names': expected.get('league_names', []),
            'reported_total_pages_snapshot': reported_pages,
            'cached_page_numbers': len(files),
            'cached_page_files': len(files),
            'missing_page_count_any_date': len(all_pages_missing),
            'missing_pages_any_date': all_pages_missing,
            'last_page_with_2019_2026_fixture': last_relevant or None,
            'first_cached_page_wholly_before_2019': first_pre_start or None,
            'page_holes_before_last_relevant_page': relevant_holes,
            'missing_pages_at_target_to_pre2019_boundary': boundary_holes,
            'target_page_sequence_complete': not (relevant_holes or boundary_holes) and monotone_newest_first,
            'newest_first_date_order_consistent': monotone_newest_first,
            'page_parse_errors': page_parse_errors,
            'league_identity_mismatches': league_identity_mismatches,
            'oldest_cached_source_date': min((p['min_source_date'] for p in pages if p['min_source_date']), default=None),
            'newest_cached_source_date': max((p['max_source_date'] for p in pages if p['max_source_date']), default=None),
            'pages': pages,
        })

    summary = {
        'audit': 'cached_totalcorner_schedule_page_continuity_2019_2026',
        'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source_scope': 'existing local schedule response pages only; no API requests',
        'target_source_date_range': [START, END],
        'page_cache_root': str(SCHEDULE_ROOT),
        'baseline_coverage_generated_at_utc': baseline.get('generated_at_utc'),
        'baseline_coverage_sha256': hashlib.sha256(baseline_bytes).hexdigest(),
        'provider_league_count': len(league_rows),
        'unique_cached_page_number_count': sum(row['cached_page_numbers'] for row in league_rows),
        'provider_reported_all_history_page_count_sum': sum(row['reported_total_pages_snapshot'] for row in league_rows),
        'oldest_cached_source_date': min((row['oldest_cached_source_date'] for row in league_rows if row['oldest_cached_source_date']), default=None),
        'newest_cached_source_date': max((row['newest_cached_source_date'] for row in league_rows if row['newest_cached_source_date']), default=None),
        'leagues_with_holes_inside_2019_2026_page_prefix': sum(bool(row['page_holes_before_last_relevant_page']) for row in league_rows),
        'total_page_holes_inside_2019_2026_page_prefix': sum(len(row['page_holes_before_last_relevant_page']) for row in league_rows),
        'leagues_with_missing_page_at_2019_boundary': sum(bool(row['missing_pages_at_target_to_pre2019_boundary']) for row in league_rows),
        'total_missing_pages_at_2019_boundary': sum(len(row['missing_pages_at_target_to_pre2019_boundary']) for row in league_rows),
        'leagues_with_complete_target_page_sequence': sum(bool(row['target_page_sequence_complete']) for row in league_rows),
        'leagues_with_page_parse_errors': sum(bool(row['page_parse_errors']) for row in league_rows),
        'leagues_with_identity_mismatches': sum(bool(row['league_identity_mismatches']) for row in league_rows),
        'total_uncached_pages_in_provider_reported_all_history': sum(row['missing_page_count_any_date'] for row in league_rows),
        'interpretation': 'A page-count gap after a league has already crossed before 2019 is outside this target interval; a hole before the final cached page containing 2019-2026 fixtures is a target-period gap. Page chronology is reported and must be considered when interpreting page-prefix coverage.',
        'leagues': league_rows,
    }
    json_path = OUT / 'cached_schedule_page_continuity_2019_2026.json'
    csv_path = OUT / 'cached_schedule_page_continuity_2019_2026.csv'
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    columns = [
        'provider_league_id', 'league_names', 'reported_total_pages_snapshot', 'cached_page_numbers',
        'missing_page_count_any_date', 'last_page_with_2019_2026_fixture', 'first_cached_page_wholly_before_2019',
        'page_holes_before_last_relevant_page', 'missing_pages_at_2019_boundary', 'target_page_sequence_complete', 'newest_first_date_order_consistent',
        'oldest_cached_source_date', 'newest_cached_source_date', 'page_parse_errors', 'league_identity_mismatches',
    ]
    with csv_path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for row in league_rows:
            writer.writerow({
                'provider_league_id': row['provider_league_id'],
                'league_names': '|'.join(row['league_names']),
                'reported_total_pages_snapshot': row['reported_total_pages_snapshot'],
                'cached_page_numbers': row['cached_page_numbers'],
                'missing_page_count_any_date': row['missing_page_count_any_date'],
                'last_page_with_2019_2026_fixture': row['last_page_with_2019_2026_fixture'],
                'first_cached_page_wholly_before_2019': row['first_cached_page_wholly_before_2019'],
                'page_holes_before_last_relevant_page': '|'.join(map(str, row['page_holes_before_last_relevant_page'])),
                'missing_pages_at_2019_boundary': '|'.join(map(str, row['missing_pages_at_target_to_pre2019_boundary'])),
                'target_page_sequence_complete': row['target_page_sequence_complete'],
                'newest_first_date_order_consistent': row['newest_first_date_order_consistent'],
                'oldest_cached_source_date': row['oldest_cached_source_date'],
                'newest_cached_source_date': row['newest_cached_source_date'],
                'page_parse_errors': json.dumps(row['page_parse_errors'], separators=(',', ':')),
                'league_identity_mismatches': json.dumps(row['league_identity_mismatches'], separators=(',', ':')),
            })
    print(json.dumps({key: summary[key] for key in (
        'audit', 'generated_at_utc', 'provider_league_count',
        'unique_cached_page_number_count', 'provider_reported_all_history_page_count_sum', 'oldest_cached_source_date', 'newest_cached_source_date',
        'leagues_with_holes_inside_2019_2026_page_prefix', 'total_page_holes_inside_2019_2026_page_prefix',
        'leagues_with_missing_page_at_2019_boundary', 'total_missing_pages_at_2019_boundary', 'leagues_with_complete_target_page_sequence',
        'leagues_with_page_parse_errors', 'leagues_with_identity_mismatches',
        'total_uncached_pages_in_provider_reported_all_history',
    )}, ensure_ascii=False))


if __name__ == '__main__':
    main()
