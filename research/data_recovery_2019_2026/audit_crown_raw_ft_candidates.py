#!/usr/bin/env python3
"""Check whether saved Crown raw bodies can verify unresolved schedule FT.

Read-only: exact FID, league, UTC kickoff and team-name checks; no API calls,
no writes to the Crown SQLite database, and no inference from placeholder 0:0.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3
from zoneinfo import ZoneInfo

OUT = pathlib.Path(__file__).resolve().parent
CANDIDATES = OUT / 'unverified_FT_candidates.jsonl'
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SUMMARY = OUT / 'crown_raw_ft_candidate_audit_2019_2026.json'
LOCAL_TZ = ZoneInfo('Asia/Shanghai')


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def parse_utc(value: object, *, naive_is_local: bool = False) -> dt.datetime | None:
    if value is None:
        return None
    try:
        x = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if x.tzinfo is None:
        if not naive_is_local:
            return None
        x = x.replace(tzinfo=LOCAL_TZ)
    return x.astimezone(dt.timezone.utc)


def nonnegative_int(value: object) -> int | None:
    try:
        x = int(str(value))
    except (TypeError, ValueError):
        return None
    return x if x >= 0 and str(value).strip() == str(x) else None


def main() -> None:
    fixtures = {}
    for line in CANDIDATES.open(encoding='utf-8'):
        if line.strip():
            r = json.loads(line)
            fixtures[str(r['match_id'])] = r

    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=30)
    captures_by_fid = {}
    for fid in fixtures:
        captures_by_fid[fid] = cx.execute(
            '''select distinct data_layer,capture_mode,response_received_at_utc,
                      response_sha256,source_file
               from capture where fixture_id=? order by data_layer,capture_mode,response_sha256''',
            (fid,),
        ).fetchall()

    raw_status = collections.Counter()
    response_issues = collections.Counter()
    layer_counts = collections.Counter()
    mode_counts = collections.Counter()
    by_league_year = collections.defaultdict(collections.Counter)
    checked_responses = 0
    exact_full_fids = set()
    exact_full_responses = 0
    per_fid = []
    for fid, fixture in fixtures.items():
        captures = captures_by_fid[fid]
        key = (str(fixture.get('provider_league_id') or 'UNKNOWN'), str(fixture.get('calendar_year_utc') or 'UNKNOWN'))
        agg = by_league_year[key]
        agg['candidate_fids'] += 1
        if captures:
            agg['fids_with_capture'] += 1
        local_status = collections.Counter()
        local_reasons = collections.Counter()
        local_full_exact = False
        seen_raw_sha = set()
        for layer, mode, received, expected_sha, raw_path in captures:
            layer_counts[str(layer)] += 1
            mode_counts[str(mode)] += 1
            raw_key = (str(expected_sha), str(raw_path))
            if raw_key in seen_raw_sha:
                continue
            seen_raw_sha.add(raw_key)
            checked_responses += 1
            path = pathlib.Path(raw_path)
            try:
                body_bytes = path.read_bytes()
                actual_sha = hashlib.sha256(body_bytes).hexdigest()
                if actual_sha != str(expected_sha):
                    response_issues['response_sha_mismatch'] += 1
                    local_reasons['response_sha_mismatch'] += 1
                    continue
                body = json.loads(body_bytes)
                rows = body.get('data') if isinstance(body, dict) else None
                rows = rows if isinstance(rows, list) else []
                matches = [x for x in rows if str(x.get('id') or '') == fid]
                if len(matches) != 1:
                    reason = 'raw_fid_missing' if not matches else 'raw_fid_not_unique'
                    response_issues[reason] += 1
                    local_reasons[reason] += 1
                    continue
                match = matches[0]
                status = str(match.get('status') if match.get('status') is not None else 'missing')
                raw_status[status] += 1
                local_status[status] += 1
                if status != 'full':
                    continue
                checks = {
                    'league': str(match.get('l_id') or '') == str(fixture.get('provider_league_id') or ''),
                    'kickoff_utc': parse_utc(match.get('start'), naive_is_local=True) == parse_utc(fixture.get('kickoff_utc')),
                    'home_name_exact': str(match.get('h') or '') == str(fixture.get('home_name') or ''),
                    'away_name_exact': str(match.get('a') or '') == str(fixture.get('away_name') or ''),
                    'home_score_valid': nonnegative_int(match.get('hg')) is not None,
                    'away_score_valid': nonnegative_int(match.get('ag')) is not None,
                }
                if all(checks.values()):
                    local_full_exact = True
                    exact_full_responses += 1
                else:
                    reason = 'full_identity_or_score_check_failed'
                    response_issues[reason] += 1
                    local_reasons[reason] += 1
            except Exception as exc:  # preserve failures as diagnostics
                reason = 'exception_' + type(exc).__name__
                response_issues[reason] += 1
                local_reasons[reason] += 1
        if local_full_exact:
            exact_full_fids.add(fid)
        agg['capture_rows'] += len(captures)
        agg['raw_responses_checked'] += len(seen_raw_sha)
        agg['fids_with_full_exact_raw_ft'] += int(local_full_exact)
        per_fid.append({
            'fid': fid,
            'provider_league_id': fixture.get('provider_league_id'),
            'calendar_year_utc': fixture.get('calendar_year_utc'),
            'capture_rows': len(captures),
            'raw_fixture_status_counts': dict(local_status),
            'strict_full_ft_identity_match': local_full_exact,
            'response_issue_counts': dict(local_reasons),
        })
    cx.close()

    # Store only identity/provenance summaries, not raw HTTP bodies or private paths.
    rows_path = OUT / 'crown_raw_ft_candidate_audit_rows_2019_2026.jsonl.gz'
    import gzip
    with rows_path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as gz:
            for row in sorted(per_fid, key=lambda x: (str(x['provider_league_id']), str(x['calendar_year_utc']), x['fid'])):
                gz.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
    result = {
        'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
        'scope': 'Only currently unresolved FT candidates; Crown response status full is accepted only after exact FID, league, UTC kickoff, exact team names, and nonnegative integer scores match.',
        'inputs': {
            'unverified_FT_candidates_file_sha256': sha256(CANDIDATES),
            'unverified_FT_candidate_count': len(fixtures),
            'crown_sqlite_file_sha256': sha256(DB),
        },
        'crown_raw_responses': {
            'candidate_fids_with_any_capture': sum(bool(v) for v in captures_by_fid.values()),
            'distinct_raw_responses_checked': checked_responses,
            'capture_rows_by_layer': dict(layer_counts),
            'capture_rows_by_mode': dict(mode_counts),
            'fixture_status_counts': dict(raw_status),
            'strict_full_ft_fids': len(exact_full_fids),
            'strict_full_ft_responses': exact_full_responses,
            'issues': dict(response_issues),
        },
        'by_league_year': {f'{k[0]}|{k[1]}': dict(v) for k, v in sorted(by_league_year.items())},
        'per_fid_evidence_file': rows_path.name,
        'per_fid_evidence_sha256': sha256(rows_path),
        'api_requests': 0,
        'sqlite_writes': 0,
        'interpretation': 'Absence of a verified Crown raw full-time record remains unverified; source statuses and placeholder 0:0 values are not treated as final results.',
    }
    SUMMARY.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'candidate_fids': len(fixtures),
        'candidate_fids_with_capture': result['crown_raw_responses']['candidate_fids_with_any_capture'],
        'raw_status_counts': dict(raw_status),
        'strict_full_ft_fids': len(exact_full_fids),
        'issues': dict(response_issues),
        'summary': str(SUMMARY),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
