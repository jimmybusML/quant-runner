#!/usr/bin/env python3
"""Build source-faithful league/season coverage without inferring seasons.

Season labels are taken only from exact expanded-universe source records. FIDs
without a supplied season, or with conflicting supplied labels, stay separate.
The Crown SQLite is read-only and mode/layer counts remain distinct.
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
INVENTORY = ROOT / 'fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz'
UNRESOLVED = ROOT / 'unverified_FT_candidates_plus_53_leagues_2019_2026.jsonl.gz'
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
STAMP = '20261122T0426Z'
CSV_OUT = ROOT / f'league_season_inventory_coverage_{STAMP}.csv'
JSON_OUT = ROOT / f'league_season_inventory_coverage_{STAMP}.json'


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read_gz(path: pathlib.Path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    started = dt.datetime.now(dt.timezone.utc)
    fixtures = {}
    seasons_by_fid: dict[str, set[str]] = collections.defaultdict(set)
    season_source_fids = set()
    for row in read_gz(INVENTORY):
        fid = str(row['fid'])
        lid = str(row['provider_league_id'])
        fixtures[fid] = (lid, int(row['year']) if row.get('year') is not None else None)
        for source in row.get('expanded_universe_records') or []:
            source_lid = str(source.get('league_id') or source.get('l_id') or '')
            season = str(source.get('season') or '').strip()
            if source_lid != lid or not season:
                continue
            seasons_by_fid[fid].add(season)
            season_source_fids.add(fid)
    unresolved = {str(row['fid']) for row in read_gz(UNRESOLVED)}
    if not unresolved <= fixtures.keys():
        raise RuntimeError('unresolved FT queue has FIDs outside inventory')

    db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA busy_timeout=30000')
    db.execute('BEGIN')
    capture_rows = db.execute('SELECT count(*) FROM capture').fetchone()[0]
    max_received = db.execute('SELECT max(response_received_at_utc) FROM capture').fetchone()[0]
    by_fid: dict[str, dict] = collections.defaultdict(lambda: collections.defaultdict(int))
    for r in db.execute('''SELECT fixture_id,data_layer,capture_mode,status,COUNT(*) AS captures,
                                  SUM(quote_count) AS quote_rows
                           FROM capture GROUP BY fixture_id,data_layer,capture_mode,status'''):
        fid = str(r['fixture_id'])
        if fid not in fixtures:
            continue
        layer = str(r['data_layer'])
        mode = str(r['capture_mode'])
        status = str(r['status'])
        by_fid[fid][f'{layer}_{mode}_capture_records'] += int(r['captures'] or 0)
        by_fid[fid][f'{layer}_{mode}_quote_rows'] += int(r['quote_rows'] or 0)
        if int(r['quote_rows'] or 0) > 0:
            by_fid[fid][f'{layer}_{mode}_has_quotes'] = 1
        if status == 'NO_CROWN_AH_QUOTES':
            by_fid[fid][f'{layer}_{mode}_no_quote_status_records'] += int(r['captures'] or 0)
    db.rollback()
    db.close()

    by_bucket: dict[tuple[str, str], dict] = {}
    for fid, (lid, _) in fixtures.items():
        labels = seasons_by_fid.get(fid, set())
        label = next(iter(labels)) if len(labels) == 1 else ('season_conflict' if len(labels) > 1 else 'season_not_provided')
        key = (lid, label)
        row = by_bucket.setdefault(key, {
            'provider_league_id': lid, 'source_season_label': label,
            'fids_with_source_season_label': 0,
            'fids_without_source_season_label': 0,
            'fids_with_conflicting_source_season_labels': 0,
            'unique_fids': 0, 'verified_ft_fids': 0, 'unresolved_ft_fids': 0,
            'movement_historical_capture_fids': 0, 'movement_historical_quote_fids': 0,
            'movement_historical_quote_rows': 0, 'movement_no_quote_response_records': 0,
            'summary_historical_capture_fids': 0, 'summary_historical_quote_fids': 0,
            'summary_historical_quote_rows': 0, 'summary_no_quote_response_records': 0,
            'summary_live_capture_fids': 0, 'summary_live_quote_fids': 0,
            'summary_live_quote_rows': 0,
        })
        row['unique_fids'] += 1
        if label == 'season_not_provided':
            row['fids_without_source_season_label'] += 1
        elif label == 'season_conflict':
            row['fids_with_conflicting_source_season_labels'] += 1
        else:
            row['fids_with_source_season_label'] += 1
        if fid in unresolved:
            row['unresolved_ft_fids'] += 1
        else:
            row['verified_ft_fids'] += 1
        facts = by_fid.get(fid, {})
        if facts.get('movement_historical_capture_records'):
            row['movement_historical_capture_fids'] += 1
        if facts.get('movement_historical_has_quotes'):
            row['movement_historical_quote_fids'] += 1
        row['movement_historical_quote_rows'] += facts.get('movement_historical_quote_rows', 0)
        row['movement_no_quote_response_records'] += facts.get('movement_historical_no_quote_status_records', 0)
        if facts.get('summary_historical_capture_records'):
            row['summary_historical_capture_fids'] += 1
        if facts.get('summary_historical_has_quotes'):
            row['summary_historical_quote_fids'] += 1
        row['summary_historical_quote_rows'] += facts.get('summary_historical_quote_rows', 0)
        row['summary_no_quote_response_records'] += facts.get('summary_historical_no_quote_status_records', 0)
        if facts.get('summary_live_capture_records'):
            row['summary_live_capture_fids'] += 1
        if facts.get('summary_live_has_quotes'):
            row['summary_live_quote_fids'] += 1
        row['summary_live_quote_rows'] += facts.get('summary_live_quote_rows', 0)

    rows = [by_bucket[k] for k in sorted(by_bucket, key=lambda x: (int(x[0]), x[1]))]
    totals = collections.Counter()
    for row in rows:
        for key, value in row.items():
            if key not in ('provider_league_id', 'source_season_label'):
                totals[key] += int(value)
    if totals['unique_fids'] != len(fixtures):
        raise RuntimeError('league/season buckets do not partition inventory FIDs')
    if totals['verified_ft_fids'] != len(fixtures) - len(unresolved):
        raise RuntimeError('FT totals do not reconcile to unresolved queue')

    with CSV_OUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    finished = dt.datetime.now(dt.timezone.utc)
    summary = {
        'snapshot_created_at_utc': finished.isoformat().replace('+00:00', 'Z'),
        'sqlite_read_only': True,
        'network_requests': 0,
        'database_writes': 0,
        'inventory_fids': len(fixtures),
        'provider_leagues': len({lid for lid, _ in fixtures.values()}),
        'explicit_season_fids': len(season_source_fids),
        'season_not_provided_fids': sum(not seasons_by_fid.get(fid) for fid in fixtures),
        'season_conflict_fids': sum(len(v) > 1 for v in seasons_by_fid.values()),
        'distinct_source_season_labels': len({s for values in seasons_by_fid.values() for s in values}),
        'league_season_buckets': len(rows),
        'inventory_sha256': sha(INVENTORY),
        'unresolved_ft_queue_sha256': sha(UNRESOLVED),
        'sqlite_capture_records_in_snapshot': capture_rows,
        'sqlite_max_response_received_at_utc': max_received,
        'totals': dict(totals),
        'csv': CSV_OUT.name,
        'csv_sha256': sha(CSV_OUT),
        'rows_by_provider_league_and_source_season': rows,
        'limitations': [
            'Season labels are used only when supplied by an exact expanded-universe source record; UTC year is not substituted for season.',
            'The source season field is absent for much of the recovered supplemental schedule inventory, so those FIDs remain in season_not_provided.',
            'The current inventory is a reconciled known-source union, not proof that no other provider competitions exist.',
            'Crown counts are a read-only transaction snapshot during append-only historical collection; database main-file SHA is not claimed stable.',
        ],
    }
    JSON_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('snapshot_created_at_utc','inventory_fids','provider_leagues','explicit_season_fids','season_not_provided_fids','season_conflict_fids','distinct_source_season_labels','league_season_buckets','totals')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
