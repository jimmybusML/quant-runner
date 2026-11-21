#!/usr/bin/env python3
"""Walk-forward player-pair cohesion replay on mapped Original49+expanded15 data.

For this expansion test, the held-out target pool is the existing expanded15
complete Crown T6/T3/T1 inventory. Only leagues with strict, repeated,
bijective Crown/Transfermarkt identity anchors are eligible for features.
No Crown data is fetched or changed.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import sys
from typing import Any

import numpy as np

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[2]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')
SOURCE = WORK / 'm8_pregame_info_source_20261117'
GAMES = SOURCE / 'games.csv.gz'
LINEUPS = SOURCE / 'game_lineups.csv.gz'
APPEARANCES = SOURCE / 'appearances.csv.gz'
FOUNDATION = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPTS = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
EXPANDED = ROOT / 'research/m8/red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'
IDENTITY = OUT / 'identity_coverage_audit.json'
ALPHA = 100.0

# Reuse the already audited, fixed cohesion definition and AH payoff code.
sys.path.insert(0, str(ROOT / 'research/m8/player_pair_cohesion_20261121'))
from run_player_pair_cohesion import (  # noqa: E402
    choose, pair_features, predict, ridge_fit, settle, sha, stats, team_cohesion,
)


def read_jsonl(path: pathlib.Path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gz(path: pathlib.Path, rows) -> None:
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())


def load_lineup_history(crosswalk: dict[str, str], teammap: dict[tuple[str, str], str]):
    """Read complete prior XIs for every mapped team, even if its opponent is unmapped."""
    invcomp = {v: k for k, v in crosswalk.items()}
    invteam: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for (league, crown_id), tm_id in teammap.items():
        invteam[league][tm_id] = crown_id

    relevant: dict[str, dict[str, Any]] = {}
    audit = collections.Counter()
    with gzip.open(GAMES, 'rt', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            league = invcomp.get(str(row.get('competition_id') or ''))
            if league is None:
                continue
            home_club = str(row.get('home_club_id') or '')
            away_club = str(row.get('away_club_id') or '')
            if home_club not in invteam[league] and away_club not in invteam[league]:
                continue
            try:
                day = dt.date.fromisoformat(row['date'])
                int(row['home_club_goals'])
                int(row['away_club_goals'])
            except (ValueError, KeyError, TypeError):
                audit['bad_game_date'] += 1
                continue
            gid = str(row.get('game_id') or '')
            relevant[gid] = {'date': day, 'league': league, 'home_club': home_club,
                             'away_club': away_club, 'home_crown_id': invteam[league].get(home_club),
                             'away_crown_id': invteam[league].get(away_club)}
    audit['mapped_team_games'] = len(relevant)

    starts: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    with gzip.open(LINEUPS, 'rt', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row.get('type') != 'starting_lineup':
                continue
            gid = str(row.get('game_id') or '')
            game = relevant.get(gid)
            if game is None:
                continue
            club = str(row.get('club_id') or '')
            if club not in (game['home_club'], game['away_club']):
                audit['lineup_club_mismatch'] += 1
                continue
            starts[(gid, club)].append(str(row.get('player_id') or ''))

    positive_apps: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    with gzip.open(APPEARANCES, 'rt', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            gid = str(row.get('game_id') or '')
            game = relevant.get(gid)
            if game is None:
                continue
            club = str(row.get('player_club_id') or '')
            if club not in (game['home_club'], game['away_club']):
                continue
            try:
                minutes = float(row.get('minutes_played') or 0)
            except (ValueError, TypeError):
                continue
            if minutes > 0:
                positive_apps[(gid, club)].add(str(row.get('player_id') or ''))

    history: dict[tuple[str, str], list[tuple[dt.date, tuple[str, ...], str]]] = collections.defaultdict(list)
    for gid, game in relevant.items():
        for side in ('home', 'away'):
            crown_id = game[f'{side}_crown_id']
            if not crown_id:
                continue
            club = game[f'{side}_club']
            xi = starts.get((gid, club), [])
            if len(xi) != 11 or len(set(xi)) != 11:
                audit['incomplete_starting_eleven'] += 1
                continue
            if not set(xi) <= positive_apps.get((gid, club), set()):
                # The feature is pair co-start recurrence, not minutes or load.
                # Missing appearance-minute evidence is recorded but never
                # imputed as zero and does not erase an explicit 11-player XI.
                audit['complete_XI_missing_positive_appearance_evidence'] += 1
            else:
                audit['complete_XI_with_positive_appearance_evidence'] += 1
            history[(game['league'], crown_id)].append((game['date'], tuple(sorted(xi)), gid))
            audit['valid_team_match_lineups'] += 1
    for key in history:
        history[key].sort(key=lambda x: (x[0], x[2]))
    return history, audit


def mdd(rows):
    daily = collections.defaultdict(float)
    for row in rows:
        daily[row['date']] += float(row['net_u'])
    running = peak = drawdown = 0.0
    for day in sorted(daily):
        running += daily[day]
        peak = max(peak, running)
        drawdown = max(drawdown, peak - running)
    return round(drawdown, 6)


def summarize(rows, weeks=None):
    if not rows:
        return {'n': 0, 'net_U': 0.0, 'ROI_pct': None, 'MDD_U': 0.0, 'orders_per_week': 0.0, 'five_state': {}}
    n = len(rows)
    net = sum(float(row['net_u']) for row in rows)
    dates = [dt.date.fromisoformat(row['date']) for row in rows]
    week_span = weeks if weeks is not None else (max(dates) - min(dates)).days // 7 + 1
    return {'n': n, 'net_U': round(net, 6), 'ROI_pct': round(net / n * 100, 6),
            'MDD_U': mdd(rows), 'orders_per_week': round(n / week_span, 6) if week_span else 0.0,
            'five_state': dict(collections.Counter(row['settlement'] for row in rows))}


def group_rows(rows, key):
    groups = collections.defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {k: summarize(v) for k, v in sorted(groups.items())}


def main() -> None:
    identity = json.loads(IDENTITY.read_text(encoding='utf-8'))
    crosswalk = {str(k): str(v) for k, v in identity['coverage']['clear_competition_crosswalks'].items()}
    teammap = {}
    for key, tm_id in identity['team_mappings'].items():
        league, crown_id = key.split('|', 1)
        teammap[(league, crown_id)] = str(tm_id)
    history, history_audit = load_lineup_history(crosswalk, teammap)

    # Exact expanded15 raw-event replay pool, one row per FID.
    targets = []
    missing = collections.Counter()
    frozen = {str(row['fid']): row for row in read_jsonl(FOUNDATION)}
    receipt_ids = {str(row['fixture_id']) for row in read_jsonl(RECEIPTS)}
    schedule = {}
    schedule_dir = DATA / 'm5-crown-authorized/schedules'
    for league in identity['coverage']['target_leagues']:
        for page in sorted((schedule_dir / str(league)).glob('page-*.raw.json')):
            try:
                blob = json.loads(page.read_bytes())
            except (OSError, json.JSONDecodeError):
                continue
            for row in (blob.get('data') or {}).get('matches') or []:
                if str(row.get('l_id')) != str(league) or row.get('status') != 'full':
                    continue
                fid = str(row.get('id') or '')
                if fid:
                    schedule[fid] = {'league': str(league), 'home_id': str(row.get('h_id') or ''),
                        'away_id': str(row.get('a_id') or ''), 'home': row.get('h'), 'away': row.get('a'),
                        'hg': int(row['hg']), 'ag': int(row['ag'])}

    with gzip.open(EXPANDED, 'rt', encoding='utf-8') as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            fid, league = str(row['fid']), str(row['league'])
            sched = schedule.get(fid)
            if sched is None:
                missing['fixture_not_in_schedule_pages'] += 1
                continue
            if (sched['league'], sched['hg'], sched['ag']) != (league, int(row['hg']), int(row['ag'])):
                raise ValueError(f'Expanded-path / Crown schedule mismatch at {fid}')
            if fid in frozen:
                missing['unexpected_frozen_overlap'] += 1
                continue
            htm = teammap.get((league, sched['home_id']))
            atm = teammap.get((league, sched['away_id']))
            if not htm or not atm:
                missing['one_or_both_team_ids_unmapped'] += 1
                continue
            try:
                day = dt.date.fromisoformat(str(row['date']))
            except ValueError:
                missing['bad_target_date'] += 1
                continue
            hfeat = team_cohesion(history, (league, sched['home_id']), day)
            afeat = team_cohesion(history, (league, sched['away_id']), day)
            if hfeat is None or afeat is None:
                missing['insufficient_complete_prior_XI_history'] += 1
                continue
            line, ho, ao = float(row['end_line']), float(row['home_price']), float(row['away_price'])
            if min(ho, ao) <= 1 or abs(line * 4 - round(line * 4)) > 1e-7:
                missing['invalid_Crown_AH_contract'] += 1
                continue
            targets.append({'fid': fid, 'league': league, 'league_name': row.get('league_name'),
                'year': int(row['year']), 'date': day.isoformat(), 'home': sched['home'], 'away': sched['away'],
                'iso_week': f'{day.isocalendar().year}-W{day.isocalendar().week:02d}',
                'home_id': sched['home_id'], 'away_id': sched['away_id'], 'home_tm_club_id': htm,
                'away_tm_club_id': atm, 'hg': int(row['hg']), 'ag': int(row['ag']),
                'goal_difference': int(row['hg']) - int(row['ag']), 'Crown_T1_AH_home_line': line,
                'Crown_T1_home_odds': ho, 'Crown_T1_away_odds': ao,
                'T1_source_event_utc': (row.get('source_event_times') or [None])[-1],
                'T1_response_received_utc': (row.get('response_received_times') or [None])[-1],
                'T1_capture_mode': (row.get('capture_modes') or [None])[-1],
                'source_response_sha256': (row.get('source_sha256') or [None])[-1],
                'pair_features_home': hfeat, 'pair_features_away': afeat,
                'pair_features': pair_features(hfeat, afeat),
                'feature_cutoff_date': (day - dt.timedelta(days=3)).isoformat(),
                'frozen_overlap': False, 'actual_receipt_fid_overlap': fid in receipt_ids,
                'source_class': 'historical_Crown_source_event_replay'})

    targets.sort(key=lambda row: (row['date'], row['fid']))
    if len({row['fid'] for row in targets}) != len(targets):
        raise AssertionError('Duplicate expanded15 FIDs after team feature join')

    years = (2024, 2025, 2026)
    methods = ('market_only', 'pair_only', 'market_plus_pair')
    predictions = {method: [] for method in methods}
    folds = {}
    fits_2026 = {}
    for year in years:
        train = [row for row in targets if 2019 <= row['year'] < year and row['fid'] not in receipt_ids]
        test = [row for row in targets if row['year'] == year]
        if not test:
            folds[str(year)] = {'train_n': len(train), 'test_n': 0, 'train_max_year': max((r['year'] for r in train), default=None),
                                'receipt_fids_removed_from_training': True, 'ridge_alpha': ALPHA}
            continue
        for method in methods:
            def features(row):
                market = [-row['Crown_T1_AH_home_line'] + .25 * math.log(row['Crown_T1_away_odds'] / row['Crown_T1_home_odds']),
                          row['Crown_T1_AH_home_line'],
                          .25 * math.log(row['Crown_T1_away_odds'] / row['Crown_T1_home_odds'])]
                return market if method == 'market_only' else row['pair_features'] if method == 'pair_only' else market + row['pair_features']
            if not train:
                raise ValueError(f'No prior training rows for test year {year}')
            fit = ridge_fit([features(row) for row in train], [row['goal_difference'] for row in train])
            if year == 2026:
                fits_2026[method] = fit
            for row in test:
                mu = predict(fit, features(row))
                side, home_ev, away_ev = choose(row['Crown_T1_AH_home_line'], row['Crown_T1_home_odds'],
                                                 row['Crown_T1_away_odds'], mu, fit[3])
                if side is None:
                    state, net, odds = 'push', 0.0, None
                else:
                    odds = row['Crown_T1_home_odds'] if side == 'home' else row['Crown_T1_away_odds']
                    state, net = settle(row['Crown_T1_AH_home_line'], side, row['goal_difference'], odds)
                predictions[method].append({**row, 'method': method,
                    'predicted_home_goal_difference': round(mu, 8), 'train_sigma': round(fit[3], 8),
                    'home_EV_U': round(home_ev, 8), 'away_EV_U': round(away_ev, 8),
                    'chosen_side': side, 'chosen_odds': odds, 'settlement': state, 'net_u': round(net, 8),
                    'training_year_cutoff_exclusive': year, 'training_rows': len(train),
                    'training_max_year': max(r['year'] for r in train)})
        folds[str(year)] = {'train_n': len(train), 'train_years': sorted({r['year'] for r in train}),
            'train_max_year': max(r['year'] for r in train), 'test_n': len(test),
            'receipt_fids_removed_from_training': True, 'ridge_alpha': ALPHA,
            'models': {method: {'feature_count': (3 if method == 'market_only' else len(test[0]['pair_features'])
                        if method == 'pair_only' else 3 + len(test[0]['pair_features'])),
                        'residual_sigma': round(ridge_fit(
                            [[-r['Crown_T1_AH_home_line'] + .25 * math.log(r['Crown_T1_away_odds']/r['Crown_T1_home_odds']),
                              r['Crown_T1_AH_home_line'], .25*math.log(r['Crown_T1_away_odds']/r['Crown_T1_home_odds'])]
                             if method == 'market_only' else r['pair_features'] if method == 'pair_only' else
                             [-r['Crown_T1_AH_home_line'] + .25 * math.log(r['Crown_T1_away_odds']/r['Crown_T1_home_odds']),
                              r['Crown_T1_AH_home_line'], .25*math.log(r['Crown_T1_away_odds']/r['Crown_T1_home_odds'])] + r['pair_features']
                             for r in train], [r['goal_difference'] for r in train])[3], 8)} for method in methods}}

    frozen_rows = []
    for row in frozen.values():
        try:
            frozen_rows.append({'fid': str(row['fid']), 'date': str(row['date'])[:10], 'net_u': float(row['pnl']),
                                'year': int(row['year'])})
        except (KeyError, ValueError, TypeError):
            continue

    test_dates = [dt.date.fromisoformat(row['date']) for row in targets if row['year'] in years]
    weeks = (max(test_dates) - min(test_dates)).days // 7 + 1 if test_dates else 0
    summaries, annual, weekly, leagues, merged = {}, {}, {}, {}, {}
    for method, rows in predictions.items():
        incremental = [row for row in rows if not row['frozen_overlap']]
        summaries[method] = {'all_test': summarize(rows, weeks), 'incremental_outside_frozen': summarize(incremental, weeks)}
        annual[method] = {str(year): summarize([row for row in incremental if row['year'] == year]) for year in years}
        weekly[method] = group_rows(incremental, 'iso_week') if incremental and 'iso_week' in incremental[0] else {}
        leagues[method] = group_rows(incremental, 'league')
        if incremental:
            min_date, max_date = min(row['date'] for row in incremental), max(row['date'] for row in incremental)
            same_frozen = [row for row in frozen_rows if min_date <= row['date'] <= max_date]
        else:
            same_frozen = []
        both = same_frozen + incremental
        merged[method] = {'same_period_frozen_n': len(same_frozen), 'incremental_n': len(incremental),
                          'unique_n': len({row['fid'] for row in both}),
                          'net_U': round(sum(row['net_u'] for row in both), 6),
                          'ROI_pct': round(sum(row['net_u'] for row in both) / len(both) * 100, 6) if both else None,
                          'candidate_net_U': round(sum(row['net_u'] for row in incremental), 6)}

    # True HTTP receipts are checked separately. Expanded15 input rows are
    # historical capture-mode records even when quote event times precede FT.
    test_ids = {row['fid'] for row in targets if row['year'] in years}
    receipt_overlap = sorted(test_ids & receipt_ids)
    for method in methods:
        predictions[method].sort(key=lambda row: (row['date'], row['fid']))
    per_fixture = [row for method in methods for row in predictions[method]]
    write_gz(OUT / 'expanded15_pair_cohesion_per_fixture.jsonl.gz', per_fixture)
    write_gz(OUT / 'expanded15_pair_cohesion_actual_receipt_overlap.jsonl.gz',
             [{'fid': fid, 'note': 'Receipt FID intersection only; no model replay unless raw receipt price is separately available.'}
              for fid in receipt_overlap])

    summary = {'study': 'player-pair cohesion AH test on the existing expanded15 Crown T6/T3/T1 event replay inventory',
        'inputs_sha256': {str(path): sha(path) for path in (GAMES, LINEUPS, APPEARANCES, FOUNDATION, RECEIPTS, EXPANDED, IDENTITY)},
        'coverage': {'expanded15_complete_T6_T3_T1_FIDs': 6967, 'Crown_schedule_full_FIDs': len(schedule),
            'mapped_leagues': crosswalk, 'verified_team_id_mappings': len(teammap),
            'lineup_history_audit': dict(history_audit), 'expanded15_feature_complete_target_FIDs': len(targets),
            'feature_complete_by_league': dict(collections.Counter(row['league'] for row in targets)),
            'feature_complete_by_league_year': {f'{league}|{year}': sum(r['league'] == league and r['year'] == year for r in targets)
                for league in sorted({r['league'] for r in targets}, key=int) for year in years
                if any(r['league'] == league and r['year'] == year for r in targets)},
            'feature_missing_reasons': dict(missing), 'original_frozen_overlap': sum(r['fid'] in frozen for r in targets),
            'true_receipt_archive_intersection_test_fids': len(receipt_overlap),
            'actual_receipt_replay_orders': 0,
            'historical_quote_capture_mode_counts': dict(collections.Counter(str(r['T1_capture_mode']) for r in targets))},
        'methodology': {'target_contract': 'Crown AH T1 line and both decimal odds from expanded15 complete T6/T3/T1 historical event replay; no other bookmaker.',
            'features': 'Same pre-target 365-day player-pair co-start network as prior Original49 study; target date minus 3 days cutoff; a prior XI is complete when the completed-game archive explicitly records 11 distinct starting_lineup players. Appearance minutes are audited but not used or imputed because the feature is co-start identity, not minutes/load; target lineup unused.',
            'model': 'Expanding year Ridge; 2024 trains on 2019-2023, 2025 on 2019-2024, 2026 on 2019-2025; fixed alpha 100; methods market-only, pair-only and market+pair; one side chosen by larger expected Crown AH payout, no EV/no-bet threshold or parameter tuning.',
            'identity': identity['identity_method'],
            'time_status': 'Historical Crown source-event replay. Actual receipt archive intersection measured separately; no historical capture response time is treated as contemporaneous.'},
        'training_folds': folds, 'models': summaries, 'annual_incremental': annual, 'weekly_incremental': weekly,
        'league_incremental': leagues, 'same_period_frozen_eight_union': merged,
        'actual_receipt': {'intersection_test_fids': receipt_overlap, 'intersection_n': len(receipt_overlap), 'replay_order_n': 0},
        'formal_orders': 0, 'formal_ledger_writes': 0, 'production_changes': False}
    (OUT / 'expanded15_pair_cohesion_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'coverage': summary['coverage'], 'models': {m: x['incremental_outside_frozen'] for m, x in summaries.items()},
                      'annual': annual, 'same_period_frozen_eight_union': merged}, ensure_ascii=False, indent=2))


def group_rows(rows, key):
    grouped = collections.defaultdict(list)
    for row in rows:
        value = row.get(key)
        if value is not None:
            grouped[str(value)].append(row)
    return {k: summarize(v) for k, v in sorted(grouped.items())}


if __name__ == '__main__':
    main()
