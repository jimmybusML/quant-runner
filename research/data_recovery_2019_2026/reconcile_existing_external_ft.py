#!/usr/bin/env python3
"""Validate already archived ESPN FT evidence against unresolved fixture IDs.

No network calls are made. A result is accepted only when the archived source
labels it verified, one ESPN event is present, the raw response SHA matches,
and event date, home/away names and FT score match the existing fixture row.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import pathlib
import unicodedata

OUT = pathlib.Path(__file__).resolve().parent
UNVERIFIED = OUT / 'unverified_FT_candidates.jsonl'
SOURCE = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work/m7/m7_remaining_FT_exact_id_20261110/espn/verified_external_espn_results.jsonl')
RAW_ROOT = SOURCE.parent / 'raw-dates'
DEST = OUT / 'external_verified_ft_2019_2026.jsonl'
SUMMARY = OUT / 'external_verified_ft_2019_2026.json'


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def norm(value: object) -> str:
    text = unicodedata.normalize('NFKD', str(value or '').casefold())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return ''.join(c for c in text if c.isalnum())


def parse_utc(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:
        return None


def main() -> None:
    unresolved = {}
    for line in UNVERIFIED.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            unresolved[str(row['match_id'])] = row
    # The inventory audit excludes accepted external FT rows from its current
    # unverified manifest. Seed prior accepted IDs so this audit remains
    # repeatable instead of dropping its own successful rows on the next run.
    if DEST.exists():
        for line in DEST.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            prior = json.loads(line)
            unresolved.setdefault(str(prior['match_id']), {
                'match_id': str(prior['match_id']),
                'provider_league_id': prior.get('provider_league_id'),
                'kickoff_utc': prior.get('kickoff_utc'),
                'home_id': prior.get('home_id'),
                'away_id': prior.get('away_id'),
                'home_name': prior.get('home_name'),
                'away_name': prior.get('away_name'),
            })
    status_counts = collections.Counter()
    output = []
    rejects = collections.Counter()
    rejected_rows = []

    def reject(fid: str, reason: str) -> None:
        rejects[reason] += 1
        rejected_rows.append({'match_id': fid, 'reason': reason})
    for line in SOURCE.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        status_counts[str(row.get('status'))] += 1
        if row.get('status') != 'ESPN_FT_VERIFIED':
            continue
        fid = str(row.get('fixture_id') or '')
        fixture = unresolved.get(fid)
        if fixture is None:
            continue
        matches = row.get('external_matches') or []
        if len(matches) != 1:
            reject(fid, 'not_unique_external_match')
            continue
        match = matches[0]
        raw_path = pathlib.Path(str(row.get('raw_result_file') or ''))
        expected_sha = row.get('raw_result_SHA256')
        if not raw_path.is_file() or not expected_sha or sha(raw_path) != expected_sha or match.get('raw_sha256') != expected_sha:
            reject(fid, 'raw_sha_mismatch_or_missing')
            continue
        try:
            raw = json.loads(raw_path.read_text(encoding='utf-8'))
        except Exception:
            reject(fid, 'raw_parse_error')
            continue
        events = [event for event in raw.get('events', []) if str(event.get('id')) == str(match.get('eid'))]
        if len(events) != 1:
            reject(fid, 'event_id_not_unique_in_raw')
            continue
        event = events[0]
        competitions = event.get('competitions') or []
        if len(competitions) != 1:
            reject(fid, 'competition_not_unique')
            continue
        comp = competitions[0]
        event_status = (comp.get('status') or {}).get('type') or {}
        if event_status.get('name') != 'STATUS_FULL_TIME' or not event_status.get('completed'):
            reject(fid, 'event_not_ft')
            continue
        competitors = comp.get('competitors') or []
        home = [c for c in competitors if c.get('homeAway') == 'home']
        away = [c for c in competitors if c.get('homeAway') == 'away']
        if len(home) != 1 or len(away) != 1:
            reject(fid, 'home_away_identity_not_unique')
            continue
        home_name = (home[0].get('team') or {}).get('displayName') or (home[0].get('team') or {}).get('name')
        away_name = (away[0].get('team') or {}).get('displayName') or (away[0].get('team') or {}).get('name')
        hg, ag = home[0].get('score'), away[0].get('score')
        ko = parse_utc(fixture.get('kickoff_utc'))
        ext_ko = parse_utc(event.get('date'))
        if not ko or not ext_ko or ko != ext_ko or parse_utc(row.get('Crown_kickoff')) != ko:
            reject(fid, 'kickoff_mismatch')
            continue
        if norm(home_name) != norm(fixture.get('home_name')) or norm(row.get('Crown_home')) != norm(fixture.get('home_name')):
            reject(fid, 'home_identity_mismatch')
            continue
        if norm(away_name) != norm(fixture.get('away_name')) or norm(row.get('Crown_away')) != norm(fixture.get('away_name')):
            reject(fid, 'away_identity_mismatch')
            continue
        if str(hg) != str(row.get('home_goals')) or str(ag) != str(row.get('away_goals')) or str(hg) != str(match.get('score_h')) or str(ag) != str(match.get('score_a')):
            reject(fid, 'score_mismatch')
            continue
        output.append({
            'match_id': fid,
            'provider_league_id': fixture.get('provider_league_id'),
            'kickoff_utc': fixture.get('kickoff_utc'),
            'home_id': fixture.get('home_id'),
            'away_id': fixture.get('away_id'),
            'home_name': fixture.get('home_name'),
            'away_name': fixture.get('away_name'),
            'verified_FT': f'{int(hg)}:{int(ag)}',
            'source': 'ESPN archived response; independently checked from raw event',
            'source_event_id': str(event.get('id')),
            'source_event_status': event_status.get('name'),
            'source_raw_sha256': expected_sha,
            'source_raw_file': f'raw-dates/{raw_path.name}',
            'source_event_home_name': home_name,
            'source_event_away_name': away_name,
            'crosswalk_method': 'exact TotalCorner FID row joined to one archived externally verified event; exact UTC kickoff; normalized exact home and away names',
            'observed_by_source_at_utc': row.get('FT_verified_after_utc'),
        })
    output.sort(key=lambda x: x['match_id'])
    DEST.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in output), encoding='utf-8')
    summary = {
        'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source_file': 'm7_remaining_FT_exact_id_20261110/espn/verified_external_espn_results.jsonl',
        'source_file_sha256': sha(SOURCE),
        'unverified_fixture_ids_input_count': len(unresolved),
        'source_status_counts': dict(status_counts),
        'verified_external_result_rows': status_counts.get('ESPN_FT_VERIFIED', 0),
        'strictly_reconciled_unverified_fixture_ids': len(output),
        'rejected_candidate_counts': dict(rejects),
        'rejected_candidates': rejected_rows,
        'output_file': DEST.name,
        'output_sha256': sha(DEST),
        'network_requests_made': 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
