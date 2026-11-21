#!/usr/bin/env python3
"""Consolidate verified supplemental TotalCorner schedule pages.

Private raw HTTP bodies remain under QuantAsiaDesk research-work. This script
emits a deterministic, sanitized fixture ledger with source and receipt
provenance, retaining competing source versions instead of guessing identity.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery')
RAW = ROOT / 'raw'
DIAGNOSTICS = ROOT.parent / 'totalcorner_schedule_diagnostics'
REQUESTS = ROOT / 'requests.jsonl'
OUT = ROOT / 'fixtures_2019_2026.verified.jsonl.gz'
PAGE_RE = re.compile(r'league-(\d+)-page-(\d+)-([0-9a-f]{64})\.json$')


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def page_matches(body: dict) -> tuple[list, dict, dict]:
    data = body.get('data') or body.get('payload', {}).get('data') or {}
    if isinstance(data, list):
        return data, {}, body.get('pagination') or {}
    return data.get('matches') or [], data.get('league') or {}, body.get('pagination') or body.get('payload', {}).get('pagination') or {}


def main() -> int:
    successful: dict[tuple[str, int], dict] = {}
    if not REQUESTS.exists():
        raise SystemExit(f'missing request log: {REQUESTS}')
    for line in REQUESTS.read_text(encoding='utf-8').splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get('event') != 'page_succeeded' or not item.get('success'):
            continue
        lid, page, digest = str(item['league_id']), int(item['page']), item['response_sha256']
        candidates = [base / f'league-{lid}-page-{page}-{digest}.json' for base in (RAW, DIAGNOSTICS)]
        path = next((candidate for candidate in candidates if candidate.is_file() and sha(candidate) == digest), None)
        if path is None:
            continue
        body = json.loads(path.read_text(encoding='utf-8'))
        matches, league, _ = page_matches(body)
        if body.get('success', body.get('status')) not in (1, '1', True):
            continue
        row_leagues = {str(x.get('l_id')) for x in matches if x.get('l_id') is not None}
        if (league.get('league_id') and str(league['league_id']) != lid) or (row_leagues and row_leagues != {lid}):
            continue
        successful[(lid, page)] = {'meta': item, 'body': body}

    # The verified one-off league-57 page-1 diagnostic predates the append-only
    # request log. Include any such SHA-valid successful diagnostic page too.
    if DIAGNOSTICS.exists():
        for path in DIAGNOSTICS.glob('league-*-page-*.json'):
            match = PAGE_RE.fullmatch(path.name)
            if not match:
                continue
            lid, page, digest = match.group(1), int(match.group(2)), match.group(3)
            if (lid, page) in successful or sha(path) != digest:
                continue
            meta_path = path.with_name(path.stem + '.meta.json')
            if not meta_path.is_file():
                continue
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            request = meta.get('request') or {}
            if (str(request.get('league_id')) != lid or int(request.get('page') or 0) != page
                    or meta.get('http_status') != 200 or meta.get('provider_success') not in (1, '1', True)
                    or meta.get('response_sha256') != digest):
                continue
            body = json.loads(path.read_text(encoding='utf-8'))
            successful[(lid, page)] = {'meta': {
                'league_id': lid,
                'page': page,
                'response_sha256': digest,
                'response_received_at_utc': meta.get('response_received_at_utc'),
                'request_started_at_utc': meta.get('request_started_at_utc'),
                'source_diagnostic_file': path.name,
            }, 'body': body}

    versions: dict[tuple[str, str, str], dict] = {}
    for (lid, page), source in sorted(successful.items()):
        meta, body = source['meta'], source['body']
        matches, league, _ = page_matches(body)
        for match in matches:
            fid = str(match.get('id') or '')
            if not fid:
                continue
            raw_start = str(match.get('start') or '')
            kickoff = None
            if raw_start:
                try:
                    parsed = dt.datetime.fromisoformat(raw_start.replace('Z', '+00:00'))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
                    kickoff = parsed.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
                except ValueError:
                    pass
            if kickoff and not ('2019-01-01T00:00:00Z' <= kickoff <= '2026-12-31T23:59:59Z'):
                continue
            compact = json.dumps(match, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
            record_sha = hashlib.sha256(compact).hexdigest()
            row = {
                'fid': fid,
                'provider_league_id': lid,
                'provider_league_name': str(match.get('l') or league.get('name') or ''),
                'source_platform': 'TotalCorner',
                'source_endpoint_path': f'/v1/league/schedule/{lid}',
                'source_page': page,
                'source_page_response_sha256': meta['response_sha256'],
                'response_received_at_utc': meta.get('response_received_at_utc'),
                'source_record_sha256': record_sha,
                'kickoff_source_raw': raw_start or None,
                'kickoff_utc': kickoff,
                'home_id': str(match.get('h_id') or ''),
                'away_id': str(match.get('a_id') or ''),
                'home_name': match.get('h'),
                'away_name': match.get('a'),
                'status_raw': match.get('status'),
                'home_goals_raw': match.get('hg'),
                'away_goals_raw': match.get('ag'),
                'season_raw': match.get('season'),
            }
            versions[(lid, fid, record_sha)] = row

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(OUT.suffix + '.tmp')
    with tmp.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as zipped:
            for key in sorted(versions, key=lambda x: (x[0], x[1], x[2])):
                zipped.write((json.dumps(versions[key], ensure_ascii=False, separators=(',', ':')) + '\n').encode())
    tmp.replace(OUT)
    digest = sha(OUT)
    print(json.dumps({
        'verified_pages': len(successful),
        'distinct_fixture_versions': len(versions),
        'distinct_fids': len({(lid, fid) for lid, fid, _ in versions}),
        'output': str(OUT),
        'bytes': OUT.stat().st_size,
        'sha256': digest,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
