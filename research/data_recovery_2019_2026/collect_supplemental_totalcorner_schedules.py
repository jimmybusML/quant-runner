#!/usr/bin/env python3
"""Resumable, rate-aware schedule recovery for previously scoped extra leagues.

Reads only fixture schedules from TotalCorner. Exact response bodies are kept
under the private local research-work directory; this repository stores the
collector and sanitized results/digests only. The script does not collect odds
or alter any production model, job, Telegram flow, or ledger.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

import requests

REPO = pathlib.Path(__file__).resolve().parents[2]
QUANT_ROOT = pathlib.Path('/Users/mac/QuantAsiaDesk')
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121/totalcorner_schedule_recovery')
RAW = WORK / 'raw'
REQUEST_LOG = WORK / 'requests.jsonl'
FIXTURE_LEDGER = WORK / 'fixtures_2019_2026.jsonl'
CONFLICT_LOG = WORK / 'identity_conflicts.jsonl'
PROGRESS = WORK / 'progress.json'
DIAGNOSTICS = WORK.parent / 'totalcorner_schedule_diagnostics'
SHARED_SCHEDULES = QUANT_ROOT / 'data/m5-crown-authorized/schedules'
CANDIDATES = REPO / 'research/data_recovery_2019_2026/unresolved_schedule_competition_candidates_20261121.json'
MIN_GAP_SECONDS = 5.2  # stays below the provider's 5-request/10-second ceiling
TARGET_START_UTC = dt.datetime(2019, 1, 1, tzinfo=dt.timezone.utc)
TARGET_END_UTC = dt.datetime(2026, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)
UNSAFE_COMMANDS = (
    '/Users/mac/QuantAsiaDesk/scripts/unified_settlement.py',
    '/Users/mac/QuantAsiaDesk/scripts/local_rescheduled_results.py',
    '/Users/mac/QuantAsiaDesk/scripts/local_result_fallback.py',
    '/Users/mac/QuantAsiaDesk/repos/mr1/src/shadow-v23.js --scheduled',
)
PAGE_RE = re.compile(r'league-(\d+)-page-(\d+)-([0-9a-f]{64})\.json$')
SHANGHAI = ZoneInfo('Asia/Shanghai')


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_jsonl(path: pathlib.Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    with path.open('a', encoding='utf-8') as stream:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def load_token() -> str:
    value = os.environ.get('TOTALCORNER_TOKEN')
    if value:
        return value.strip()
    sys.path.insert(0, str(QUANT_ROOT))
    from mac_keychain import get
    value = get('QuantAsiaDesk.TOTALCORNER_TOKEN', os.environ.get('USER', 'mac'))
    if not value:
        raise RuntimeError('KEYCHAIN_TOKEN_UNAVAILABLE')
    return value


def active_scheduled_jobs() -> list[str]:
    result = subprocess.run(['/bin/ps', '-Ao', 'command='], capture_output=True, text=True, check=True)
    return [line.strip() for line in result.stdout.splitlines() if any(marker in line for marker in UNSAFE_COMMANDS)]


def wait_for_quiet_and_gap(last_start: float | None) -> float:
    while active_scheduled_jobs():
        time.sleep(2)
    if last_start is None:
        # Allow an already running scheduled process to leave its final requests behind.
        quiet_since = time.monotonic()
        while True:
            if active_scheduled_jobs():
                quiet_since = time.monotonic()
            elif time.monotonic() - quiet_since >= 12:
                break
            time.sleep(2)
    else:
        time.sleep(max(0.0, MIN_GAP_SECONDS - (time.monotonic() - last_start)))
    # Recheck immediately before the API call to avoid starting during a scheduled job.
    while active_scheduled_jobs():
        time.sleep(2)
    return time.monotonic()


def parse_source_start(value: object) -> tuple[dt.datetime | None, str | None]:
    if value is None:
        return None, None
    raw = str(value)
    try:
        parsed = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=SHANGHAI)
        return parsed.astimezone(dt.timezone.utc), raw
    except Exception:
        return None, raw


def page_payload(body: dict) -> tuple[list[dict], dict, dict]:
    data = body.get('data') or body.get('payload', {}).get('data') or {}
    if isinstance(data, list):
        matches = data
        league = {}
    else:
        matches = data.get('matches') or [] if isinstance(data, dict) else []
        league = data.get('league') or {} if isinstance(data, dict) else {}
    pagination = body.get('pagination') or body.get('payload', {}).get('pagination') or {}
    return matches, league, pagination


def existing_page(lid: str, page: int) -> tuple[dict, dict] | None:
    # Reuse the one-off API diagnostic page if it already exists.
    for directory in (RAW, DIAGNOSTICS):
        for path in directory.glob(f'league-{lid}-page-{page}-*.json'):
            if path.name.endswith('.meta.json') or path.suffix != '.json':
                continue
            match = PAGE_RE.fullmatch(path.name)
            if not match:
                continue
            digest = match.group(3)
            if sha_bytes(path.read_bytes()) != digest:
                continue
            meta_path = path.with_name(path.stem + '.meta.json')
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            if meta.get('http_status', 200) != 200 or meta.get('provider_success', 1) not in (1, '1', True):
                continue
            body = json.loads(path.read_text(encoding='utf-8'))
            return body, {
                'response_sha256': digest,
                'raw_path': str(path),
                'received_at_utc': meta.get('response_received_at_utc'),
                'reused_from_diagnostic': True,
            }

    # Reuse the existing 64-league page cache if this ID/page is already stored.
    directory = SHARED_SCHEDULES / lid
    for path in (directory / f'page-{page}.raw.json', directory / f'page-{page}.json'):
        if not path.exists():
            continue
        try:
            body = json.loads(path.read_text(encoding='utf-8'))
            matches, league, _ = page_payload(body)
            if body.get('success', body.get('status')) not in (1, '1', True):
                continue
            row_leagues = {str(row.get('l_id')) for row in matches if row.get('l_id') is not None}
            if league.get('league_id') and str(league['league_id']) != lid:
                continue
            if row_leagues and row_leagues != {lid}:
                continue
            digest = sha_bytes(path.read_bytes())
            return body, {'response_sha256': digest, 'raw_path': str(path), 'received_at_utc': None, 'reused_local_schedule_cache': True}
        except Exception:
            continue
    return None


def save_response(lid: str, page: int, response: requests.Response, received_at: str, token: str) -> tuple[dict, dict]:
    body_bytes = response.content
    digest = sha_bytes(body_bytes)
    secret_echo = bool(token) and token.encode('utf-8') in body_bytes
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        RAW.chmod(0o700)
    except OSError:
        pass
    body_path = RAW / f'league-{lid}-page-{page}-{digest}.json'
    tmp = body_path.with_suffix('.json.tmp')
    tmp.write_bytes(body_bytes)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(body_path)
    try:
        body = response.json()
    except Exception:
        body = {}
    err = body.get('error') if isinstance(body.get('error'), dict) else {}
    matches, league, pagination = page_payload(body if isinstance(body, dict) else {})
    message = str(err.get('message') or body.get('error_message') or body.get('message') or '')
    if token:
        message = message.replace(token, '[REDACTED]')
    meta = {
        'league_id': lid,
        'page': page,
        'endpoint_path': f'/v1/league/schedule/{lid}',
        'response_received_at_utc': received_at,
        'http_status': response.status_code,
        'provider_success': body.get('success', body.get('status')) if isinstance(body, dict) else None,
        'provider_error_code': err.get('code') or body.get('error_code') if isinstance(body, dict) else None,
        'provider_error_message': message[:500],
        'response_sha256': digest,
        'response_bytes': len(body_bytes),
        'raw_file': str(body_path),
        'secret_echo_detected_in_private_raw_response': secret_echo,
        'rate_limit_headers': {key: response.headers.get(key) for key in ('X-Rate-Limit-Limit', 'X-Rate-Limit-Remaining', 'X-Rate-Limit-Reset', 'Retry-After') if response.headers.get(key) is not None},
        'reported_league_id': str(league.get('league_id') or ''),
        'reported_league_name': league.get('name'),
        'match_count': len(matches) if isinstance(matches, list) else None,
        'pagination': {key: pagination.get(key) for key in ('current', 'pages', 'next', 'per_page') if key in pagination},
    }
    body_path.with_name(body_path.stem + '.meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    return body if isinstance(body, dict) else {}, meta


def request_page(session: requests.Session, token: str, lid: str, page: int, last_start: float | None) -> tuple[dict | None, dict, float]:
    endpoint = f'https://api.totalcorner.com/v1/league/schedule/{lid}'
    for attempt in range(1, 6):
        started_mono = wait_for_quiet_and_gap(last_start)
        started = utc_now()
        try:
            response = session.get(
                endpoint,
                params={'token': token, 'page': page, 'columns': 'events,attacks,dangerousAttacks,shotOn,shotOff,possession,asian,goalLine'},
                headers={'Accept': 'application/json', 'User-Agent': 'QuantAsiaDesk-history-recovery/1'},
                timeout=(15, 60),
            )
            received = utc_now()
            body, meta = save_response(lid, page, response, received, token)
            meta['request_started_at_utc'] = started
            meta['request_attempt'] = attempt
            last_start = started_mono
            matches, league, _ = page_payload(body)
            body_ok = response.status_code == 200 and body.get('success', body.get('status')) in (1, '1', True)
            row_leagues = {str(row.get('l_id')) for row in matches if row.get('l_id') is not None}
            identity_ok = (not league.get('league_id') or str(league.get('league_id')) == lid) and (not row_leagues or row_leagues == {lid})
            if body_ok and identity_ok:
                meta['success'] = True
                append_jsonl(REQUEST_LOG, {'event': 'page_succeeded', **meta})
                return body, meta, last_start
            meta['success'] = False
            meta['identity_ok'] = identity_ok
            meta['failure_kind'] = 'http_or_provider_error' if not body_ok else 'league_identity_mismatch'
            append_jsonl(REQUEST_LOG, {'event': 'page_failed', **meta})
            rate_limited = response.status_code == 429 or 'rate limit' in str(meta.get('provider_error_message', '')).lower() or 'too many request' in str(meta.get('provider_error_message', '')).lower()
            if rate_limited:
                retry = response.headers.get('Retry-After') or response.headers.get('X-Rate-Limit-Reset')
                try:
                    wait_seconds = max(10.0, float(retry))
                except (TypeError, ValueError):
                    wait_seconds = 12.0
                time.sleep(wait_seconds)
            else:
                time.sleep(min(5.0 * attempt, 30.0))
        except Exception as exc:
            last_start = started_mono
            append_jsonl(REQUEST_LOG, {
                'event': 'request_exception', 'league_id': lid, 'page': page,
                'request_started_at_utc': started, 'attempt': attempt,
                'error_type': type(exc).__name__,
                'error_message': 'request failed; URL and credential omitted',
            })
            time.sleep(min(5.0 * attempt, 30.0))
    return None, {'league_id': lid, 'page': page, 'success': False, 'failure_kind': 'retry_exhausted'}, last_start


def normalize_fixture(lid: str, expected_name: str, page: int, match: dict, meta: dict) -> dict | None:
    fid = str(match.get('id') or '')
    if not fid:
        return None
    kickoff_utc, kickoff_raw = parse_source_start(match.get('start'))
    if kickoff_utc and not (TARGET_START_UTC <= kickoff_utc <= TARGET_END_UTC):
        return None
    record_bytes = json.dumps(match, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    data = {
        'fid': fid,
        'provider_league_id': lid,
        'provider_league_name': str(match.get('l') or expected_name),
        'provider_league_name_from_target_inventory': expected_name,
        'source_platform': 'TotalCorner',
        'source_endpoint': f'/v1/league/schedule/{lid}',
        'source_page': page,
        'source_page_response_sha256': meta.get('response_sha256'),
        'response_received_at_utc': meta.get('response_received_at_utc') or meta.get('received_at_utc'),
        'source_record_sha256': hashlib.sha256(record_bytes).hexdigest(),
        'kickoff_source_raw': kickoff_raw,
        'kickoff_utc': kickoff_utc.isoformat().replace('+00:00', 'Z') if kickoff_utc else None,
        'home_id': str(match.get('h_id') or ''),
        'away_id': str(match.get('a_id') or ''),
        'home_name': match.get('h'),
        'away_name': match.get('a'),
        'status_raw': match.get('status'),
        'home_goals_raw': match.get('hg'),
        'away_goals_raw': match.get('ag'),
    }
    return data


def page_dates(matches: list[dict]) -> tuple[dt.datetime | None, dt.datetime | None]:
    values = [parse_source_start(row.get('start'))[0] for row in matches if row.get('start')]
    values = [value for value in values if value is not None]
    return (min(values), max(values)) if values else (None, None)


def load_done_pages() -> dict[tuple[str, int], dict]:
    done = {}
    if not REQUEST_LOG.exists():
        return done
    for line in REQUEST_LOG.open(encoding='utf-8'):
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get('event') != 'page_succeeded' or not row.get('success'):
            continue
        lid, page = row.get('league_id'), row.get('page')
        if lid is None or page is None or not row.get('response_sha256'):
            continue
        path = RAW / f"league-{lid}-page-{page}-{row['response_sha256']}.json"
        if not path.exists() or sha_bytes(path.read_bytes()) != row['response_sha256']:
            continue
        try:
            body = json.loads(path.read_text(encoding='utf-8'))
            matches, league, _ = page_payload(body)
            ids = {str(x.get('l_id')) for x in matches if x.get('l_id') is not None}
            if body.get('success', body.get('status')) not in (1, '1', True):
                continue
            if league.get('league_id') and str(league['league_id']) != str(lid):
                continue
            if ids and ids != {str(lid)}:
                continue
        except Exception:
            continue
        done[(str(lid), int(page))] = row
    return done


def load_existing_fixtures() -> dict[tuple[str, str], dict]:
    known: dict[tuple[str, str], dict] = {}
    if FIXTURE_LEDGER.exists():
        for line in FIXTURE_LEDGER.open(encoding='utf-8'):
            try:
                row = json.loads(line)
                known[(str(row['provider_league_id']), str(row['fid']))] = row
            except Exception:
                continue
    # Reuse the existing Spain Segunda rows so pagination does not duplicate
    # the 120 fixtures already persisted by the earlier scoped history run.
    legacy = pathlib.Path('/Users/mac/QuantAsiaDesk/repos/runner/research/shared_history/totalcorner/league-15.jsonl')
    if legacy.exists():
        for line in legacy.open(encoding='utf-8'):
            try:
                source = json.loads(line)
                match = source.get('match') or {}
                lid = str(source.get('league_id') or match.get('l_id') or '')
                fid = str(source.get('id') or match.get('id') or '')
                if not lid or not fid:
                    continue
                record_bytes = json.dumps(match, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
                known.setdefault((lid, fid), {
                    'provider_league_id': lid,
                    'fid': fid,
                    'source_record_sha256': hashlib.sha256(record_bytes).hexdigest(),
                    'source_page': None,
                    'legacy_source': str(legacy),
                    'kickoff_source_raw': match.get('start'),
                    'home_id': str(match.get('h_id') or ''),
                    'away_id': str(match.get('a_id') or ''),
                    'home_name': match.get('h'),
                    'away_name': match.get('a'),
                    'status_raw': match.get('status'),
                    'home_goals_raw': match.get('hg'),
                    'away_goals_raw': match.get('ag'),
                })
            except Exception:
                continue
    return known


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    token = load_token()
    targets = json.loads(CANDIDATES.read_text(encoding='utf-8'))['competitions']
    done = load_done_pages()
    known_fixtures = load_existing_fixtures()
    progress = {'started_at_utc': utc_now(), 'targets': {}, 'network_requests': 0, 'new_unique_fids': 0, 'identity_conflicts': 0}
    session = requests.Session()
    session.headers.update({'Accept': 'application/json', 'User-Agent': 'QuantAsiaDesk-history-recovery/1'})
    last_start: float | None = None
    try:
        for target in targets:
            lid = str(target['provider_league_id'])
            expected_name = str(target['league_name'])
            first_cached = existing_page(lid, 1)
            if first_cached:
                body, meta = first_cached
            elif (lid, 1) in done:
                meta = done[(lid, 1)]
                path = RAW / f"league-{lid}-page-1-{meta['response_sha256']}.json"
                body = json.loads(path.read_text(encoding='utf-8'))
            else:
                body, meta, last_start = request_page(session, token, lid, 1, last_start)
                progress['network_requests'] += int(meta.get('request_attempt') or meta.get('attempts_used') or 1)
                if body is None:
                    progress['targets'][lid] = {'expected_name': expected_name, 'status': 'page_1_retry_exhausted'}
                    PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')
                    continue

            matches, league, pagination = page_payload(body)
            reported_total = int(pagination.get('pages') or 0)
            if not reported_total:
                reported_total = 1 if not pagination.get('next') else 0
            if meta.get('response_sha256'):
                meta['success'] = True
                done[(lid, 1)] = meta
            fixture_counts = {'pages_read': 0, 'fixture_rows_in_target_range': 0, 'unique_2019_2026_fids': 0, 'new_fids': 0, 'conflicts': 0, 'empty_pages': 0, 'kickoff_missing_rows': 0, 'failed_pages': []}
            target_fids: set[str] = set()
            prior_page_max: dt.datetime | None = None
            order_consistent = True
            page = 1
            while True:
                if page == 1:
                    page_body, page_meta = body, meta
                elif (cached_page := existing_page(lid, page)):
                    page_body, page_meta = cached_page
                    if page_meta.get('reused_from_diagnostic') or page_meta.get('reused_local_schedule_cache'):
                        done[(lid, page)] = page_meta
                elif (lid, page) in done:
                    page_meta = done[(lid, page)]
                    page_path = RAW / f"league-{lid}-page-{page}-{page_meta['response_sha256']}.json"
                    page_body = json.loads(page_path.read_text(encoding='utf-8'))
                else:
                    page_body, page_meta, last_start = request_page(session, token, lid, page, last_start)
                    progress['network_requests'] += int(page_meta.get('request_attempt') or page_meta.get('attempts_used') or 1)
                    if page_body is None:
                        fixture_counts['failed_pages'].append(page)
                        page += 1
                        if reported_total and page > reported_total:
                            break
                        continue
                    done[(lid, page)] = page_meta

                rows, page_league, page_pagination = page_payload(page_body)
                reported_total = max(reported_total, int(page_pagination.get('pages') or 0))
                row_leagues = {str(row.get('l_id')) for row in rows if row.get('l_id') is not None}
                page_identity_ok = (not page_league.get('league_id') or str(page_league['league_id']) == lid) and (not row_leagues or row_leagues == {lid})
                if not page_identity_ok:
                    fixture_counts['failed_pages'].append(page)
                    append_jsonl(CONFLICT_LOG, {'event': 'page_identity_mismatch', 'provider_league_id': lid, 'page': page, 'reported_league_id': str(page_league.get('league_id') or ''), 'row_league_ids': sorted(row_leagues), 'response_sha256': page_meta.get('response_sha256')})
                    page += 1
                    if reported_total and page > reported_total:
                        break
                    continue
                if not rows:
                    fixture_counts['empty_pages'] += 1
                _, page_max = page_dates(rows)
                if page_max and prior_page_max and page_max > prior_page_max:
                    order_consistent = False
                if page_max:
                    prior_page_max = page_max
                for match in rows:
                    record = normalize_fixture(lid, expected_name, page, match, page_meta)
                    if not record:
                        continue
                    fixture_counts['fixture_rows_in_target_range'] += 1
                    key = (lid, record['fid'])
                    target_fids.add(record['fid'])
                    if not record.get('kickoff_utc'):
                        fixture_counts['kickoff_missing_rows'] += 1
                    old = known_fixtures.get(key)
                    if old:
                        if old['source_record_sha256'] != record['source_record_sha256']:
                            append_jsonl(CONFLICT_LOG, {'provider_league_id': lid, 'fid': record['fid'], 'existing_record_sha256': old['source_record_sha256'], 'new_record_sha256': record['source_record_sha256'], 'existing_page': old.get('source_page'), 'new_page': page, 'existing_kickoff_utc': old.get('kickoff_utc'), 'new_kickoff_utc': record.get('kickoff_utc')})
                            fixture_counts['conflicts'] += 1
                            progress['identity_conflicts'] += 1
                        continue
                    append_jsonl(FIXTURE_LEDGER, record)
                    known_fixtures[key] = record
                    fixture_counts['new_fids'] += 1
                    progress['new_unique_fids'] += 1
                fixture_counts['pages_read'] += 1
                fixture_counts['unique_2019_2026_fids'] = len(target_fids)
                progress['targets'][lid] = {
                    'expected_name': expected_name,
                    'api_name': page_league.get('name') or league.get('name'),
                    'reported_pages': reported_total or None,
                    **fixture_counts,
                    'page_order_consistent_so_far': order_consistent,
                    'latest_page': page,
                }
                PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')

                # Stop only when a successful, chronologically ordered page proves
                # the remaining older pages are before 2019. A failed page blocks this shortcut.
                if (page > 1 and page_max and page_max < TARGET_START_UTC and order_consistent
                        and not fixture_counts['failed_pages']):
                    break
                if reported_total and page >= reported_total:
                    break
                if not reported_total and page_pagination.get('next') is False:
                    break
                page += 1

            progress['targets'][lid].update(fixture_counts)
            progress['targets'][lid]['final_pages_reported'] = reported_total or None
            progress['targets'][lid]['pagination_status'] = 'complete_to_2019_cutoff_or_provider_end' if not fixture_counts['failed_pages'] else 'has_failed_pages_pending_retry'
            PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'league_id': lid, 'expected_name': expected_name, 'api_name': progress['targets'][lid].get('api_name'), 'pages': fixture_counts['pages_read'], 'new_fids': fixture_counts['new_fids'], 'failed_pages': fixture_counts['failed_pages'], 'status': progress['targets'][lid]['pagination_status']}, ensure_ascii=False), flush=True)
    finally:
        # Scrub the bearer from the in-memory session before exit.
        session.headers.pop('Authorization', None)
        del token
    progress['finished_at_utc'] = utc_now()
    PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'finished_at_utc': progress['finished_at_utc'], 'network_requests': progress['network_requests'], 'new_unique_fids': progress['new_unique_fids'], 'identity_conflicts': progress['identity_conflicts'], 'local_progress_file': str(PROGRESS)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
