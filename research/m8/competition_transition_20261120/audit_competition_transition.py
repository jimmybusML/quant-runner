#!/usr/bin/env python3
"""Audit whether saved TotalCorner schedules support a pre-match league-move study.

This is a data-sufficiency audit, not a betting model. It tests for reliable
club transitions between domestic leagues using only prior completed fixtures.
It never reads the target FT or any target post-match field as a feature.
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import re
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SCHEDULES = pathlib.Path('/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/schedules')
PAGE_INDEX = pathlib.Path(__file__).resolve().parents[1] / 'red_card_adjusted_form_20261120/schedule_page_sha256_manifest.json'
PATH49 = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
EXPANDED = pathlib.Path(__file__).resolve().parents[1] / 'red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
OUT = HERE / 'competition_transition_audit_results.json'
LAG_DAYS = 3
LOOKBACK_DAYS = 365
EXCLUDE_COMP = ('cup', 'international', 'friendly', 'world', 'playoff', 'super cup',
                'nations league', 'champions league', 'europa league', 'conference league',
                'libertadores', 'sudamericana')


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def norm(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def is_domestic_league(name):
    low = str(name or '').lower()
    return bool(low) and not any(part in low for part in EXCLUDE_COMP)


def load_targets():
    targets = {}
    with PATH49.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                targets[str(r['fid'])] = {'source': 'original49', 'year': None}
    with gzip.open(EXPANDED, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                fid = str(r['fid'])
                if fid in targets:
                    raise ValueError(f'overlapping target FID {fid}')
                targets[fid] = {'source': 'expanded15', 'year': None}
    return targets


def main():
    target_ids = load_targets()
    page_hashes = json.loads(PAGE_INDEX.read_text())
    page_files = sorted(SCHEDULES.glob('*/page-*.raw.json'))
    if len(page_files) != len(page_hashes):
        raise SystemExit(f'cached page inventory changed: {len(page_files)} != {len(page_hashes)}')
    page_issues = []
    by_fid = collections.defaultdict(dict)
    target_records = collections.defaultdict(list)
    all_leagues = {}
    for path in page_files:
        pstr = str(path)
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if page_hashes.get(pstr) != digest:
            page_issues.append({'path': pstr, 'expected': page_hashes.get(pstr), 'actual': digest})
            continue
        try:
            matches = (json.loads(raw).get('data') or {}).get('matches') or []
        except Exception:
            continue
        for m in matches:
            fid = str(m.get('id') or '')
            if not fid or not m.get('start') or not m.get('l_id'):
                continue
            try:
                day = dt.date.fromisoformat(str(m['start'])[:10])
            except ValueError:
                continue
            league_id = str(m['l_id'])
            league_name = str(m.get('l') or '')
            all_leagues[league_id] = league_name
            # The identity signature intentionally excludes target scores. Full
            # status only establishes that a historical record had completed.
            sig = (league_id, str(m.get('h_id') or ''), str(m.get('a_id') or ''),
                   str(m.get('h') or ''), str(m.get('a') or ''), str(m.get('start') or ''))
            rec = {'fid': fid, 'date': day, 'league_id': league_id,
                   'league_name': league_name,
                   'home_id': str(m.get('h_id') or ''), 'away_id': str(m.get('a_id') or ''),
                   'home': str(m.get('h') or ''), 'away': str(m.get('a') or ''),
                   'completed': m.get('status') == 'full'}
            old = by_fid[fid].get(sig)
            if old is None or rec['completed']:
                by_fid[fid][sig] = rec
            if fid in target_ids and m.get('status') == 'full':
                target_records[fid].append({'fid': fid, 'date': day, 'league_id': league_id,
                                            'league_name': league_name,
                                            'home_id': str(m.get('h_id') or ''), 'away_id': str(m.get('a_id') or ''),
                                            'home': str(m.get('h') or ''), 'away': str(m.get('a') or '')})
    if page_issues:
        raise SystemExit(f'{len(page_issues)} cached schedule pages differ from saved SHA index')

    unique_games = {}
    conflict_fids = set()
    for fid, versions in by_fid.items():
        if len(versions) == 1:
            unique_games[fid] = next(iter(versions.values()))
        else:
            conflict_fids.add(fid)
    history = collections.defaultdict(list)
    for r in unique_games.values():
        if not r['completed'] or not is_domestic_league(r['league_name']):
            continue
        country_key = norm(r['league_name']).split(' ')[0] if norm(r['league_name']) else ''
        for side in ('home', 'away'):
            tid = r[f'{side}_id']
            team = r[side]
            if not tid or not team:
                continue
            history[tid].append((r['date'], r['league_id'], r['league_name'],
                                 country_key, norm(team), team, r['fid']))
    for events in history.values():
        events.sort(key=lambda x: (x[0], x[6]))

    candidate_rows = {}
    target_identity_conflicts = set()
    target_identity = {}
    target_seen = set()
    for fid, versions in target_records.items():
        signatures = {(x['league_id'], x['home_id'], x['away_id'], x['home'], x['away'], x['date']) for x in versions}
        if len(signatures) != 1:
            target_identity_conflicts.add(fid)
        else:
            target_identity[fid] = versions[0]
    coverage_by_year = collections.defaultdict(collections.Counter)
    for year in ('2024', '2025', '2026'):
        coverage_by_year[year]['target_teams_with_recent_same_country_name_other_league'] = 0
    team_cross_league = collections.defaultdict(set)
    for team_id, events in history.items():
        for e in events:
            team_cross_league[team_id].add((e[1], e[2], e[3], e[4]))
    multi_league_team_ids = {tid for tid, vals in team_cross_league.items() if len({x[0] for x in vals}) > 1}
    multi_league_diagnostics = []
    for tid in sorted(multi_league_team_ids):
        vals = sorted(team_cross_league[tid])
        multi_league_diagnostics.append({'team_id': tid, 'league_name_team_keys': [
            {'league_id': x[0], 'league_name': x[1], 'country_prefix': x[2], 'normalized_team_name': x[3]}
            for x in vals]})

    for fid, target in target_identity.items():
        if fid not in target_ids:
            continue
        target_seen.add(fid)
        year = str(target['date'].year)
        if not 2024 <= target['date'].year <= 2026:
            continue
        cutoff = target['date'] - dt.timedelta(days=LAG_DAYS)
        lower = cutoff - dt.timedelta(days=LOOKBACK_DAYS)
        league_id = target['league_id']
        league_name = target['league_name']
        country_key = norm(league_name).split(' ')[0] if norm(league_name) else ''
        coverage_by_year[year]['target_fids_with_completed_identity'] += 1
        team_results = {}
        for side in ('home', 'away'):
            team_id, team_name = target[f'{side}_id'], target[side]
            events = history.get(team_id, [])
            prior = [e for e in events if lower <= e[0] < cutoff]
            same_league = [e for e in prior if e[1] == league_id]
            other_league_same_identity = [e for e in prior if e[1] != league_id and
                                          e[3] == country_key and e[4] == norm(team_name)]
            other_league_same_id_any = [e for e in prior if e[1] != league_id]
            team_results[side] = {'prior_events': len(prior), 'same_league_events': len(same_league),
                                  'same_country_name_other_league_events': len(other_league_same_identity),
                                  'different_league_same_id_events': len(other_league_same_id_any)}
            if prior:
                coverage_by_year[year]['target_teams_with_prior_domestic_event'] += 1
            if same_league:
                coverage_by_year[year]['target_teams_with_prior_same_league_event'] += 1
            if other_league_same_id_any:
                coverage_by_year[year]['target_teams_with_different_league_same_id_event'] += 1
            if other_league_same_identity:
                coverage_by_year[year]['target_teams_with_recent_same_country_name_other_league'] += 1
            # Candidate definition: the team's recent domestic record contains
            # a same-country, same-name different-league event, and contains no
            # same-current-league event in the lagged 365-day window.
            if other_league_same_identity and not same_league:
                candidate_rows.setdefault(fid, {'fid': fid, 'year': int(year),
                    'date_beijing': target['date'].isoformat(), 'league_id': league_id,
                    'league_name': league_name, 'teams': {}})
                candidate_rows[fid]['teams'][side] = {
                    'team_id': team_id, 'team_name': team_name,
                    'prior_other_league_matches': [{'date': e[0].isoformat(), 'league_id': e[1],
                        'league_name': e[2], 'team_name': e[5], 'fid': e[6]} for e in other_league_same_identity]}
        coverage_by_year[year]['target_fids_with_any_prior_domestic_event'] += int(any(v['prior_events'] for v in team_results.values()))
        coverage_by_year[year]['target_fids_with_any_prior_same_league_event'] += int(any(v['same_league_events'] for v in team_results.values()))

    for r in candidate_rows.values():
        r['status'] = 'candidate_identity_signal_only_not_profit_tested'
    result = {
        'study': 'M8_CROWN_AH_DOMESTIC_COMPETITION_TRANSITION_DATA_AUDIT',
        'as_of_beijing': '2026-11-20',
        'hypothesis': 'A club newly appearing in a domestic Crown league after recent play in a different domestic league may be mispriced while Crown re-estimates its strength.',
        'candidate_definition': {'prior_window_days': LOOKBACK_DAYS, 'lag_days': LAG_DAYS,
            'same_country_prefix_and_normalized_team_name_required': True,
            'must_have_no_same_current_league_match_in_window': True,
            'domestic_competition_exclusions': list(EXCLUDE_COMP),
            'note': 'This is an exploratory identity/move label, not a confirmed promotion/relegation status.'},
        'coverage': {'cached_schedule_pages': len(page_files), 'page_sha_issues': len(page_issues),
            'unique_completed_fids_after_conflict_removal': sum(1 for r in unique_games.values() if r['completed']),
            'conflicting_schedule_fids_excluded': len(conflict_fids), 'league_ids_seen': len(all_leagues),
            'league_names': all_leagues, 'target_path_fids': len(target_ids),
            'target_fids_with_completed_identity': len(target_identity),
            'target_fids_missing_or_conflicting_identity': len(target_ids)-len(target_identity),
            'historical_team_ids_with_multiple_domestic_league_ids': len(multi_league_team_ids),
            'multi_league_team_id_diagnostics': multi_league_diagnostics,
            'candidate_unique_fids': len(candidate_rows),
            'candidate_unique_fids_by_year': {year: sum(1 for r in candidate_rows.values() if str(r['year']) == year)
                                               for year in ('2024', '2025', '2026')},
            'target_coverage_by_year': {k: dict(v) for k,v in sorted(coverage_by_year.items())}},
        'candidate_rows': sorted(candidate_rows.values(), key=lambda x:(x['date_beijing'],x['fid'])),
        'profit_test': {'status': 'not_estimable_no_verified_target_transition_fids' if not candidate_rows else 'requires_new_fixed_walkforward_research',
            'candidate_orders': 0, 'net_u': None, 'roi_pct': None,
            'reason': 'No FID met the identity-safe recent domestic competition transition definition; no return or ROI is computed.'},
        'time_and_price_scope': {'target_FT_used_for_features': False,
            'target_path_or_receipt_time_feature': False,
            'Crown_actual_price_profit_test': False,
            'receipt_replay': 'not run because candidate transition FID count is zero'},
        'inputs': {'path49_sha256': sha(PATH49), 'expanded15_t1_sha256': sha(EXPANDED),
                   'cached_schedule_page_sha_index_sha256': sha(PAGE_INDEX),
                   'schedule_page_hashes': page_hashes},
        'formal_changes': {'frozen_eight_changed': False, 'production_changed': False,
                           'telegram_orders': 0, 'formal_ledger_writes': 0}
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('candidate_rows','inputs')},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
