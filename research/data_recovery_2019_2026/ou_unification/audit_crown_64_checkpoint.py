#!/usr/bin/env python3
"""Audit the latest completed safe-window increment for the fixed 64-league run.

This is an offline evidence audit: it does not call the API or modify the
database. It matches collection-log rows to their SHA-addressed raw responses
and to the approved fixture schedule, then writes checkpoint artifacts.
"""
from __future__ import annotations

import collections
import datetime as dt
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEDULE = Path('/Users/mac/QuantAsiaDesk/research-work/crown-drop-expanded-62/schedule_universe.jsonl')
IDS = {1,10,12,14,16,25,29,31,33,35,37,40,43,45,46,47,48,51,52,55,60,61,62,66,68,70,73,75,85,88,109,116,129,141,145,152,177,262,290,297,298,299,303,314,319,328,330,332,345,378,670,779,979,1439,8172,8293,10480,10714,11498,19290,26540,27388,27389,27390}
COLLECTION = ROOT / 'crown_64_combined_collection.jsonl'
EVENTS = ROOT / 'crown_64_combined_driver_events.jsonl'
QUEUE = ROOT / 'crown_64_combined_missing_queue.jsonl'


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def iso(value: str):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def schedule_index():
    by_fid = {}
    leagues = set()
    with SCHEDULE.open() as stream:
        for line in stream:
            row = json.loads(line)
            league = int(row['league_id'])
            if league not in IDS:
                continue
            leagues.add(league)
            year = int(row.get('season_year') or 0)
            fid = str(row.get('match_id') or '')
            if fid and 2023 <= year <= 2026:
                by_fid[fid] = row
    if leagues != IDS:
        raise RuntimeError(f'league scope mismatch: missing={sorted(IDS-leagues)} extra={sorted(leagues-IDS)}')
    return by_fid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--after-utc', help='start at an earlier authoritative queue_checkpoint; useful to roll several brief windows into one published increment')
    args = parser.parse_args()
    events = read_jsonl(EVENTS)
    checkpoints = [(i, e) for i, e in enumerate(events) if e.get('event') == 'queue_checkpoint']
    if len(checkpoints) < 2:
        raise RuntimeError('need at least two authoritative queue checkpoints')
    latest_i, latest = checkpoints[-1]
    if args.after_utc:
        selected = [(i,e) for i,e in checkpoints[:-1] if e.get('at_utc') == args.after_utc]
        if not selected:
            raise RuntimeError(f'no prior authoritative checkpoint matches --after-utc={args.after_utc}')
        prev_i, prev = selected[-1]
    else:
        prev_i, prev = checkpoints[-2]
    pauses = [e for e in events[prev_i + 1:latest_i] if e.get('event') == 'collection_paused_for_scheduled_job']
    pause = pauses[-1] if pauses else None
    if pause is None:
        raise RuntimeError('no scheduled-job pause between the last two queue checkpoints')
    start = iso(prev['at_utc'])
    end = iso(pause['at_utc']) + dt.timedelta(seconds=20)  # include a response already in flight when SIGTERM arrives
    queue_counts = collections.Counter()
    if QUEUE.exists():
        for queued in read_jsonl(QUEUE):
            queue_counts[str(queued.get('year'))] += 1

    all_rows = read_jsonl(COLLECTION)
    rows = [r for r in all_rows if r.get('response_received_at_utc') and start < iso(r['response_received_at_utc']) <= end]
    # Failed attempts have no response-received timestamp. Attribute them to a
    # safe-window by their actual request start time so they remain auditable
    # and are never silently treated as completed quotes.
    failed_rows = []
    for row in all_rows:
        if row.get('status') != 'FETCH_FAILED':
            continue
        starts = [a.get('started_at_utc') for a in row.get('request_attempts') or [] if a.get('started_at_utc')]
        if any(start < iso(value) <= end for value in starts):
            failed_rows.append(row)
    schedule = schedule_index()
    seen = set()
    identity_records = []
    sha_mismatches = []
    identity_mismatches = []
    for row in rows:
        fid = str(row.get('match_id') or '')
        duplicate = fid in seen
        seen.add(fid)
        raw_path = Path(row.get('raw_file') or '')
        logged_sha = row.get('sha256')
        actual_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest() if raw_path.is_file() else None
        raw_obj = json.loads(raw_path.read_text()) if raw_path.is_file() else {}
        payload = raw_obj.get('data') or []
        if isinstance(payload, dict):
            payload = [payload]
        item = next((x for x in payload if str(x.get('id') or '') == fid), None)
        schedule_row = schedule.get(fid)
        raw_league = int(item['l_id']) if item and str(item.get('l_id') or '').isdigit() else None
        reported_league = int(row['league_id']) if str(row.get('league_id') or '').isdigit() else None
        schedule_league = int(schedule_row['league_id']) if schedule_row else None
        year = int(row.get('year') or 0)
        identity_ok = bool(item and schedule_row and raw_league == reported_league == schedule_league and year == int(schedule_row.get('season_year') or 0) and raw_league in IDS and 2023 <= year <= 2026)
        if actual_sha != logged_sha:
            sha_mismatches.append(fid)
        if not identity_ok:
            identity_mismatches.append(fid)
        identity_records.append({
            'fid': fid,
            'reported_league_id': reported_league,
            'raw_league_id': raw_league,
            'schedule_league_id': schedule_league,
            'year': year,
            'status': row.get('status'),
            'received_at_utc': row.get('response_received_at_utc'),
            'raw_sha256': actual_sha,
            'logged_sha256': logged_sha,
            'sha_match': actual_sha == logged_sha,
            'response_identity_matches': identity_ok,
            'duplicate_fid': duplicate,
            'capture_mode': 'historical',
        })

    statuses = collections.Counter(r.get('status') for r in rows)
    attempts = [a for r in rows + failed_rows for a in (r.get('request_attempts') or [])]
    outcomes = collections.Counter(a.get('outcome') for a in attempts)
    http_statuses = collections.Counter(str(a.get('http_status')) for a in attempts if a.get('http_status') is not None)
    elapsed = [float(r['request_seconds']) for r in rows if r.get('request_seconds') is not None]
    mean = (sum(elapsed) / len(elapsed)) if elapsed else None
    ordered = sorted(elapsed)
    median = ((ordered[(len(ordered)-1)//2] + ordered[len(ordered)//2]) / 2) if ordered else None
    market_rows = {k: sum(int(r.get(k) or 0) for r in rows) for k in ('ah_summary_n','ah_movement_n','ou_summary_n','ou_movement_n')}
    market_fids = {k: sum(int(r.get(k) or 0) > 0 for r in rows) for k in market_rows}
    stamp = iso(latest['at_utc']).strftime('%Y%m%dT%H%MZ')

    increment = {
        'after_authoritative_checkpoint_utc': prev['at_utc'],
        'through_scheduled_pause_utc': pause['at_utc'],
        'through_last_response_received_at_utc': max((r['response_received_at_utc'] for r in rows), default=None),
        'records': len(rows),
        'unique_fids': len(seen),
        'fetch_failed_records': len(failed_rows),
        'fetch_failed_fids': sorted(str(r.get('match_id') or '') for r in failed_rows),
        'statuses': dict(statuses),
        'market_rows': market_rows,
        'market_fids': market_fids,
        'request_attempts': len(attempts),
        'attempt_outcomes': dict(outcomes),
        'http_statuses': dict(http_statuses),
        'failures': sum(n for k,n in outcomes.items() if k != 'success'),
        'request_seconds_mean': round(mean, 4) if mean is not None else None,
        'request_seconds_median': round(median, 4) if median is not None else None,
        'raw_sha_checked': sum(r['raw_sha256'] is not None for r in identity_records),
        'raw_sha_mismatches': sha_mismatches,
        'identity_scope_mismatches': identity_mismatches,
        'duplicate_fids': len(rows) - len(seen),
        'capture_mode': 'historical',
        'queue_checkpoint_utc': latest['at_utc'],
        'queue_after_rebuild': dict(sorted(queue_counts.items())),
        'queue_count_matches_rebuild': sum(queue_counts.values()) == latest.get('queue_count'),
        'queue_count': latest.get('queue_count'),
        'queue_delta_since_previous_checkpoint': (latest.get('queue_count') or 0) - (prev.get('queue_count') or 0),
        'queue_year_basis': 'actual safe-window rebuilt queue',
    }
    transport = {
        'interval_scope': {'after_utc': prev['at_utc'], 'through_pause_utc': pause['at_utc']},
        'unique_fids': len(seen),
        'records': len(rows),
        'statuses': dict(statuses),
        'attempts': len(attempts),
        'attempt_outcomes': dict(outcomes),
        'http_statuses': dict(http_statuses),
        'failures': increment['failures'],
        'request_seconds_mean': increment['request_seconds_mean'],
        'request_seconds_median': increment['request_seconds_median'],
    }
    driver_slice = events[prev_i + 1:latest_i + 1]
    files = {
        f'crown_64_collection_checkpoint_{stamp}.jsonl': rows,
        f'crown_64_failures_checkpoint_{stamp}.jsonl': failed_rows,
        f'crown_64_driver_checkpoint_{stamp}.jsonl': driver_slice,
        f'crown_64_verified_increment_{stamp}.json': increment,
        f'crown_64_increment_identity_sha_audit_{stamp}.json': {
            'scope': 'fixed 64 Provider League IDs, 2023-2026',
            'interval_after_utc': prev['at_utc'],
            'through_utc': increment['through_last_response_received_at_utc'],
            'records': identity_records,
        },
        f'crown_64_transport_audit_{stamp}.json': transport,
        f'crown_64_coverage_snapshot_{stamp}.json': latest,
    }
    for name, value in files.items():
        path = ROOT / name
        with path.open('w') as stream:
            if name.endswith('.jsonl'):
                for item in value:
                    stream.write(json.dumps(item, ensure_ascii=False) + '\n')
            else:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
    manifest = ROOT / f'CROWN_AH_OU_64_CHECKPOINT_SHA256_{stamp}.txt'
    with manifest.open('w') as stream:
        for name in files:
            digest = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            stream.write(f'{digest}  {name}\n')
    print(json.dumps(increment, ensure_ascii=False, indent=2))
    print(f'artifacts={len(files)+1} stamp={stamp}')


if __name__ == '__main__':
    main()
