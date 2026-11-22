#!/usr/bin/env python3
"""Prepare exact-SHA historical Crown summary-layer rows already in raw cache.

Read-only preparation only. It does not call the API or write Crown SQLite.
The actual append is intentionally left to a non-overlapping safe window.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
BASE = pathlib.Path('/Users/mac/QuantAsiaDesk')
AUDIT_LEDGER = ROOT / 'offline_raw_Crown_response_index_audit_2019_2026_20261122T0410Z.jsonl.gz'
INVENTORY = ROOT / 'fixture_inventory_2019_2026_plus_53_leagues.jsonl.gz'
DATABASE = BASE / 'data/crown_quote_store/crown_quotes.sqlite3'
RAW_HIST = BASE / 'data/crown_quote_store/raw/historical'
STAMP = '20261122T0410Z'
OUT_LEDGER = ROOT / f'unindexed_summary_layer_reuse_candidates_{STAMP}.jsonl.gz'
OUT_SUMMARY = ROOT / f'unindexed_summary_layer_reuse_candidates_{STAMP}.json'


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def read_gz(path: pathlib.Path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    started = dt.datetime.now(dt.timezone.utc)
    fixtures = {}
    for row in read_gz(INVENTORY):
        fixtures[str(row['fid'])] = row
    raw_candidates = [
        row for row in read_gz(AUDIT_LEDGER)
        if int(row.get('raw_summary_rows') or 0) > 0
        and not row.get('summary_sha_indexed')
    ]
    keys = [(str(row['fid']), str(row['response_sha256'])) for row in raw_candidates]
    if len(keys) != len(set(keys)):
        raise RuntimeError('duplicate FID+SHA candidate in source audit')

    cx = sqlite3.connect(f'file:{DATABASE}?mode=ro', uri=True, timeout=30)
    cx.row_factory = sqlite3.Row
    cx.execute('PRAGMA query_only=ON')
    cx.execute('PRAGMA busy_timeout=30000')
    cx.execute('BEGIN')
    max_received = cx.execute('SELECT max(response_received_at_utc) FROM capture').fetchone()[0]
    prepared = []
    failures = collections.Counter()
    for source in raw_candidates:
        fid = str(source['fid'])
        digest = str(source['response_sha256'])
        fixture = fixtures.get(fid)
        if fixture is None:
            failures['fid_missing_from_inventory'] += 1
            continue
        raw_path = RAW_HIST / fid / source['cache_file_basename']
        if not raw_path.is_file():
            failures['raw_file_missing'] += 1
            continue
        if sha(raw_path) != digest:
            failures['raw_sha_mismatch'] += 1
            continue
        body = json.loads(raw_path.read_text(encoding='utf-8'))
        data = body.get('data')
        match = data[0] if isinstance(data, list) and len(data) == 1 else data
        if not isinstance(match, dict) or str(match.get('id')) != fid:
            failures['raw_fid_mismatch'] += 1
            continue
        crown = next((b for b in (match.get('bookmakers') or [])
                      if str(b.get('slug') or '').lower() == 'crown'), None)
        if crown is None:
            failures['crown_bookmaker_missing'] += 1
            continue
        asian = crown.get('asian') or {}
        summary_rows = [kind for kind in ('open', 'close') if isinstance(asian.get(kind), dict)]
        if len(summary_rows) != int(source['raw_summary_rows']):
            failures['summary_row_count_changed'] += 1
            continue
        if not source.get('movement_sha_indexed') or not source.get('db_sha_indexed_any_layer'):
            failures['exact_source_capture_missing'] += 1
            continue
        existing = cx.execute(
            'SELECT DISTINCT response_received_at_utc FROM capture '
            'WHERE fixture_id=? AND response_sha256=? AND capture_mode=?',
            (fid, digest, 'historical'),
        ).fetchall()
        receipts = sorted({str(r['response_received_at_utc']) for r in existing
                           if r['response_received_at_utc']})
        if len(receipts) != 1:
            failures['receipt_not_unique'] += 1
            continue
        already_summary = cx.execute(
            'SELECT 1 FROM capture WHERE fixture_id=? AND data_layer=? '
            'AND capture_mode=? AND response_sha256=? LIMIT 1',
            (fid, 'summary', 'historical', digest),
        ).fetchone()
        if already_summary:
            failures['summary_layer_already_indexed'] += 1
            continue
        prepared.append({
            'fid': fid,
            'provider_league_id': str(fixture['provider_league_id']),
            'utc_year': fixture.get('year'),
            'data_layer_to_add': 'summary',
            'capture_mode': 'historical',
            'response_sha256': digest,
            'raw_response_path': str(raw_path),
            'summary_row_kinds_present': summary_rows,
            'summary_row_count': len(summary_rows),
            'response_received_at_utc': receipts[0],
            'receipt_provenance': 'exact same FID+response SHA already stored in Crown historical capture',
            'existing_layer_with_same_sha': 'movement',
        })
    cx.rollback()
    cx.close()
    if failures:
        raise RuntimeError(f'candidate verification failures: {dict(failures)}')

    with OUT_LEDGER.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as gz:
            for row in sorted(prepared, key=lambda r: (r['provider_league_id'], r['utc_year'] or 0, r['fid'])):
                gz.write((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode())
    finished = dt.datetime.now(dt.timezone.utc)
    summary = {
        'audit': 'read-only exact-SHA preparation of uncatalogued Crown historical summary rows',
        'started_at_utc': started.isoformat().replace('+00:00', 'Z'),
        'finished_at_utc': finished.isoformat().replace('+00:00', 'Z'),
        'network_requests': 0,
        'sqlite_database_writes': 0,
        'inventory_path': str(INVENTORY),
        'inventory_sha256': sha(INVENTORY),
        'source_raw_audit_ledger': str(AUDIT_LEDGER),
        'source_raw_audit_ledger_sha256': sha(AUDIT_LEDGER),
        'sqlite_snapshot_max_response_received_at_utc': max_received,
        'candidate_fid_sha_pairs': len(prepared),
        'unique_fids': len({row['fid'] for row in prepared}),
        'summary_quote_rows_available': sum(row['summary_row_count'] for row in prepared),
        'receipt_timestamp_missing_or_ambiguous': 0,
        'response_sha_identity_mismatches': 0,
        'summary_layer_already_indexed': 0,
        'output_ledger': OUT_LEDGER.name,
        'output_ledger_sha256': sha(OUT_LEDGER),
        'note': 'Prepared for later append-only reuse via existing Crown parser after current shared SQLite writer is idle; no values or receive times were inferred.',
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
