#!/usr/bin/env python3
"""Retrospective referee-history upper-bound study against Crown T12 AH.

Target referee assignments come from a retrospective Transfermarkt games file
without assignment publication timestamps. Results are explicitly not a
verified pre-match information or live-receipt test.
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
import re
import unicodedata

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
SRC = WORK / 'm8_pregame_info_source_20261117'
MARKET_FILE = WORK / 'm8_early_joint_market_inventory_20261115.jsonl'
GAMES_FILE = SRC / 'games.csv.gz'
FROZEN_FILE = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPT_FILE = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
PLAYER_BOOTSTRAP = ROOT / 'research/m8/m8_player_load_rotation_crown_20261119.py'
PRIOR_BOOTSTRAP = ROOT / 'research/m8/m8_prior_manager_turnover_20261117.py'
YEAR_TESTS = (2024, 2025, 2026)
RIDGE_ALPHA = 100.0
REF_PRIOR_MATCHES = 20.0
UTC = dt.timezone.utc
CHINA = dt.timezone(dt.timedelta(hours=8))

COMP_MAP = {
    '1': 'GB1', '12': 'IT1', '14': 'ES1', '16': 'L1', '25': 'FR1',
    '29': 'A1', '31': 'BE1', '35': 'TS1', '37': 'NL1', '48': 'PL1',
    '51': 'PO1', '52': 'RO1', '61': 'C1', '62': 'TR1', '66': 'SE1',
    '70': 'DK1', '73': 'JAP1', '75': 'RSK1', '88': 'NO1', '141': 'GR1',
    '262': 'SC1', '290': 'SA1', '303': 'SER1', '319': 'UKR1',
    '26540': 'KR1',
}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def norm_referee(value: str) -> str:
    s = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', s)


def settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line = float(line)
    if abs(line * 4 - round(line * 4)) > 1e-7:
        raise ValueError(f'AH line outside quarter grid: {line}')
    legs = [line] if abs(line * 2 - round(line * 2)) < 1e-8 else [
        math.floor(line * 2) / 2, math.ceil(line * 2) / 2,
    ]
    results = []
    for leg in legs:
        margin = hg - ag + leg if side == 'home' else ag - hg - leg
        results.append(float(odds) - 1 if margin > 1e-9 else -1.0 if margin < -1e-9 else 0.0)
    pnl = sum(results) / len(results)
    state = (
        'full_win' if all(v > 0 for v in results) else
        'half_win' if any(v > 0 for v in results) else
        'push' if all(v == 0 for v in results) else
        'half_loss' if any(v == 0 for v in results) else 'full_loss'
    )
    return pnl, state


def read_crown_history() -> tuple[list[dict], dict]:
    """Reuse the audited historical T12 builder and its local team crosswalk."""
    text = PLAYER_BOOTSTRAP.read_text(encoding='utf-8')
    prefix = text[:text.index('foundation_root=')]
    ns = {'__file__': str(PLAYER_BOOTSTRAP)}
    exec(compile(prefix, str(PLAYER_BOOTSTRAP) + '[read-only-prefix]', 'exec'), ns)
    rows = [dict(r) for r in ns['H']]
    teammap = ns['teammap']
    if len(rows) != 38_846 or len({str(x['fid']) for x in rows}) != len(rows):
        raise AssertionError('unexpected paired Crown T12 history inventory')
    if any(int(x['T']) != 12 for x in rows):
        raise AssertionError('expected the historical T12 quote leg')
    return rows, teammap


def match_referees(crown_rows: list[dict], teammap: dict) -> tuple[list[dict], dict]:
    tm_index = collections.defaultdict(list)
    with gzip.open(GAMES_FILE, 'rt', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            try:
                key = (
                    str(row['competition_id']), dt.date.fromisoformat(str(row['date'])),
                    str(row['home_club_id']), str(row['away_club_id']),
                )
                tm_index[key].append(row)
            except (KeyError, ValueError):
                continue
    coverage = collections.Counter()
    matched = []
    for row in crown_rows:
        lid = str(row['league'])
        competition = COMP_MAP.get(lid)
        home_tm = teammap.get((lid, str(row['home_id'])))
        away_tm = teammap.get((lid, str(row['away_id'])))
        day = dt.date.fromisoformat(str(row['date']))
        if not competition:
            coverage['no_competition_crosswalk'] += 1
            continue
        if not home_tm or not away_tm:
            coverage['one_or_both_teams_unmapped'] += 1
            continue
        candidates = []
        for d in (day - dt.timedelta(days=1), day, day + dt.timedelta(days=1)):
            candidates.extend(tm_index.get((competition, d, home_tm, away_tm), []))
        candidates = list({str(x['game_id']): x for x in candidates}.values())
        if not candidates:
            coverage['no_exact_team_date_match'] += 1
            continue
        if len(candidates) != 1:
            coverage['ambiguous_team_date_match'] += 1
            continue
        target = candidates[0]
        if (str(target['home_club_goals']), str(target['away_club_goals'])) != (str(row['hg']), str(row['ag'])):
            coverage['FT_identity_conflict'] += 1
            continue
        referee = str(target.get('referee') or '').strip()
        referee_key = norm_referee(referee)
        if not referee_key:
            coverage['missing_referee_name'] += 1
            continue
        enriched = dict(row)
        enriched.update({
            'tm_game_id': str(target['game_id']),
            'tm_competition_id': competition,
            'tm_date': str(target['date']),
            'tm_home_id': str(target['home_club_id']),
            'tm_away_id': str(target['away_club_id']),
            'referee_raw': referee,
            'referee_key': referee_key,
            'referee_name_time_proven': False,
        })
        matched.append(enriched)
        coverage['matched_with_retrospective_referee'] += 1
    rows = matched
    if len({r['fid'] for r in rows}) != len(rows):
        raise AssertionError('duplicate FID after referee match')
    return rows, dict(coverage)


def make_features(rows: list[dict]) -> list[dict]:
    by_ref = collections.defaultdict(list)
    by_league = collections.defaultdict(list)
    # Histories only use Crown-matched prior fixtures. The date-only source is
    # conservatively embargoed by three calendar days for every target.
    for r in rows:
        day = dt.date.fromisoformat(r['date']).toordinal()
        residual = float(r['hg']) - float(r['ag']) + float(r['al'])
        r['home_margin_residual'] = residual
        by_ref[(str(r['league']), r['referee_key'])].append((day, residual))
        by_league[str(r['league'])].append((day, residual))
    for seq in list(by_ref.values()) + list(by_league.values()):
        seq.sort(key=lambda x: x[0])
    ref_days = {k: [x[0] for x in v] for k, v in by_ref.items()}
    league_days = {k: [x[0] for x in v] for k, v in by_league.items()}
    ref_cum = {k: np.cumsum([x[1] for x in v]) for k, v in by_ref.items()}
    league_cum = {k: np.cumsum([x[1] for x in v]) for k, v in by_league.items()}
    out = []
    for r in rows:
        day = dt.date.fromisoformat(r['date']).toordinal()
        cutoff = day - 3
        rk = (str(r['league']), r['referee_key'])
        lk = str(r['league'])
        ri = __import__('bisect').bisect_right(ref_days[rk], cutoff)
        li = __import__('bisect').bisect_right(league_days[lk], cutoff)
        if ri == 0 or li == 0:
            r.update({'prior_ref_n': ri, 'prior_ref_bias': None, 'prior_league_margin_residual': None})
            continue
        ref_mean = float(ref_cum[rk][ri - 1] / ri)
        league_mean = float(league_cum[lk][li - 1] / li)
        bias = ri / (ri + REF_PRIOR_MATCHES) * (ref_mean - league_mean)
        r.update({
            'prior_ref_n': ri,
            'prior_ref_mean_margin_residual': ref_mean,
            'prior_league_mean_margin_residual': league_mean,
            'prior_ref_bias': bias,
            'prior_ref_cutoff_date': dt.date.fromordinal(cutoff).isoformat(),
        })
        out.append(r)
    return out


def crown_features(row: dict) -> list[float]:
    home, away, line = float(row['ah']), float(row['aa']), float(row['al'])
    return [line, abs(line), math.log(home / away), math.log((home + away) / 2), 1 / home + 1 / away - 1]


def ridge_predict(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray) -> np.ndarray:
    mu = train_x.mean(axis=0)
    sd = train_x.std(axis=0)
    sd[sd < 1e-10] = 1.0
    x = (train_x - mu) / sd
    z = (test_x - mu) / sd
    x = np.column_stack((np.ones(len(x)), x))
    z = np.column_stack((np.ones(len(z)), z))
    penalty = np.eye(x.shape[1]) * RIDGE_ALPHA
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(x.T @ x + penalty, x.T @ train_y)
    return z @ beta


def iso(date: str) -> str:
    x = dt.date.fromisoformat(date).isocalendar()
    return f'{x.year}-W{x.week:02}'


def metrics(rows: list[dict], date_span: list[str] | None = None) -> dict:
    n = len(rows)
    units = sum(float(x['net_u']) for x in rows)
    states = collections.Counter(x.get('settlement', 'membership_pnl_only') for x in rows)
    daily = collections.defaultdict(float)
    weekly = collections.defaultdict(lambda: {'orders': 0, 'net_u': 0.0})
    league = collections.defaultdict(lambda: {'orders': 0, 'net_u': 0.0})
    for x in rows:
        daily[x['date']] += float(x['net_u'])
        w = weekly[iso(x['date'])]
        w['orders'] += 1
        w['net_u'] += float(x['net_u'])
        l = league[str(x['league'])]
        l['orders'] += 1
        l['net_u'] += float(x['net_u'])
    cumulative = peak = mdd = 0.0
    for _, value in sorted(daily.items()):
        cumulative += value
        peak = max(peak, cumulative)
        mdd = max(mdd, peak - cumulative)
    span = date_span or [x['date'] for x in rows]
    if span:
        lo, hi = min(dt.date.fromisoformat(x) for x in span), max(dt.date.fromisoformat(x) for x in span)
        weeks = set()
        for offset in range((hi - lo).days + 1):
            weeks.add(iso((lo + dt.timedelta(days=offset)).isoformat()))
    else:
        weeks = set()
    return {
        'orders': n,
        'net_u': round(units, 6),
        'roi_pct': round(units / n * 100, 6) if n else None,
        'mdd_u': round(mdd, 6),
        'settlements': dict(states),
        'mean_decimal_odds': round(sum(float(x['price']) for x in rows if 'price' in x) / sum('price' in x for x in rows), 6) if n and any('price' in x for x in rows) else None,
        'observation_iso_weeks': len(weeks),
        'weekly_avg_orders': round(n / len(weeks), 6) if weeks else 0,
        'active_iso_weeks': len(weekly),
        'orders_per_active_week': round(n / len(weekly), 6) if weekly else 0,
        'weekly': {k: {'orders': v['orders'], 'net_u': round(v['net_u'], 6)} for k, v in sorted(weekly.items())},
        'by_league': {k: {'orders': v['orders'], 'net_u': round(v['net_u'], 6), 'roi_pct': round(v['net_u'] / v['orders'] * 100, 6)} for k, v in sorted(league.items(), key=lambda z: int(z[0]))},
    }


def main() -> None:
    crown_rows, teammap = read_crown_history()
    tm_rows, coverage = match_referees(crown_rows, teammap)
    features = make_features(tm_rows)
    test = [x for x in features if x['year'] in YEAR_TESTS and x.get('prior_ref_bias') is not None]
    if not test:
        raise AssertionError('no forward-test rows have a prior referee history')

    frozen = {}
    for line in FROZEN_FILE.open(encoding='utf-8'):
        r = json.loads(line)
        frozen[str(r['fid'])] = r
    if len(frozen) != 10_294:
        raise AssertionError(f'unexpected frozen membership size: {len(frozen)}')
    overlap = {str(x['fid']) for x in test} & set(frozen)
    for r in features:
        for side in ('home', 'away'):
            pnl, state = settle(r['al'], side, int(r['hg']), int(r['ag']), r['ah'] if side == 'home' else r['aa'])
            if abs(pnl - float(r[f'{side}_U'])) > 1e-7:
                raise AssertionError(f'Crown payout mismatch {r["fid"]} {side}')
            r[f'{side}_independent_u'] = pnl
            r[f'{side}_settlement'] = state
        r['payout_diff_y'] = r['home_independent_u'] - r['away_independent_u']
    for r in test:
        r['frozen_eight_overlap_posthoc'] = str(r['fid']) in frozen

    model_names = ('CROWN_ONLY', 'REF_ONLY', 'CROWN_PLUS_REF')
    predictions = {m: {} for m in model_names}
    annual_train = {}
    for year in YEAR_TESTS:
        train = [r for r in features if int(r['year']) < year and r.get('prior_ref_bias') is not None]
        target = [r for r in test if int(r['year']) == year]
        if not train or not target:
            annual_train[str(year)] = {'train_n': len(train), 'test_n': len(target)}
            continue
        y = np.array([float(r['payout_diff_y']) for r in train])
        train_crown = np.array([crown_features(r) for r in train])
        test_crown = np.array([crown_features(r) for r in target])
        train_ref = np.array([[float(r['prior_ref_bias']), math.log1p(float(r['prior_ref_n']))] for r in train])
        test_ref = np.array([[float(r['prior_ref_bias']), math.log1p(float(r['prior_ref_n']))] for r in target])
        pred = {
            'CROWN_ONLY': ridge_predict(train_crown, y, test_crown),
            'REF_ONLY': ridge_predict(train_ref, y, test_ref),
            'CROWN_PLUS_REF': ridge_predict(np.column_stack((train_crown, train_ref)), y, np.column_stack((test_crown, test_ref))),
        }
        annual_train[str(year)] = {'train_n': len(train), 'test_n': len(target), 'training_years': f'<{year}', 'ridge_alpha': RIDGE_ALPHA}
        for name, vals in pred.items():
            for row, value in zip(target, vals):
                side = 'home' if value >= 0 else 'away'
                row[f'{name}_predicted_home_minus_away_u'] = float(value)
                predictions[name][str(row['fid'])] = {
                    'side': side,
                    'price': float(row['ah'] if side == 'home' else row['aa']),
                    'net_u': float(row[f'{side}_independent_u']),
                    'settlement': row[f'{side}_settlement'],
                    'date': row['date'],
                    'league': str(row['league']),
                    'year': int(row['year']),
                    'fid': str(row['fid']),
                }
        for row in target:
            cheaper = 'home' if float(row['ah']) <= float(row['aa']) else 'away'
            predictions.setdefault('LOWER_PRICE', {})[str(row['fid'])] = {
                'side': cheaper,
                'price': float(row['ah'] if cheaper == 'home' else row['aa']),
                'net_u': float(row[f'{cheaper}_independent_u']),
                'settlement': row[f'{cheaper}_settlement'],
                'date': row['date'], 'league': str(row['league']), 'year': int(row['year']), 'fid': str(row['fid']),
            }

    target_dates = [r['date'] for r in test]
    common_fids = {str(r['fid']) for r in test}
    candidate_fids = common_fids - set(frozen)
    result = {
        'study': 'M8 referee-history vs Crown T12 AH; retrospective assignment upper-bound diagnostic, not proof of pre-match availability',
        'method': {
            'target': 'home one-unit net AH payout minus away one-unit net AH payout',
            'time_split': '2024/2025/2026 test folds train only on earlier calendar years; prior referee features exclude target day and previous two calendar days',
            'referee_feature': 'within-league historical mean(home goals - away goals + Crown home AH line) minus prior within-league mean residual, shrunk n/(n+20); plus log(1+n)',
            'models': ['CROWN_ONLY', 'REF_ONLY', 'CROWN_PLUS_REF', 'LOWER_PRICE'],
            'ridge_alpha': RIDGE_ALPHA,
            'referee_name_join': 'strict exact Crown league/team crosswalk, date +/-1 day, exact FT check, normalized name as league-scoped key',
            'stake': '1U per selected AH side; Crown quarter-lines split into two equal half-line stakes',
            'frozen_membership': 'FID exclusion is post-hoc incremental attribution only; not a model feature',
            'threshold_search': False,
        },
        'source_audit': {
            'crown_t12_inventory_rows': len(crown_rows),
            'crown_t12_unique_fids': len({str(x['fid']) for x in crown_rows}),
            'crown_t12_years': dict(collections.Counter(str(x['year']) for x in crown_rows)),
            'matched_referee_fids': len(tm_rows),
            'matched_referee_by_year': dict(collections.Counter(str(x['year']) for x in tm_rows)),
            'unique_normalized_referees_within_league': len({(str(x['league']), x['referee_key']) for x in tm_rows}),
            'coverage_reasons': coverage,
            'test_rows_with_prior_referee_history': len(test),
            'test_year_fids': dict(collections.Counter(str(x['year']) for x in test)),
            'test_frozen_overlap_fids': len(overlap),
            'incremental_unique_candidate_fids': len(candidate_fids),
            'test_date_range': [min(target_dates), max(target_dates)],
            'source_games_max_date': max(str(x['tm_date']) for x in tm_rows),
            'referee_assignment_timestamp_available': False,
            'referee_publication_or_receipt_field_present': False,
        },
        'training': annual_train,
        'models': {},
        'weekly_bootstrap': {},
        'frozen_baseline': {},
        'combined_same_horizon': {},
        'actual_receipt': {},
        'inputs_sha256': {
            str(GAMES_FILE): sha256(GAMES_FILE),
            str(MARKET_FILE): sha256(MARKET_FILE),
            str(FROZEN_FILE): sha256(FROZEN_FILE),
            str(RECEIPT_FILE): sha256(RECEIPT_FILE),
            str(PLAYER_BOOTSTRAP): sha256(PLAYER_BOOTSTRAP),
            str(PRIOR_BOOTSTRAP): sha256(PRIOR_BOOTSTRAP),
        },
    }

    byfid = {str(x['fid']): x for x in test}
    for name in (*model_names, 'LOWER_PRICE'):
        all_rows = list(predictions[name].values())
        increment = [x for x in all_rows if x['fid'] not in frozen]
        yearly = {}
        for year in YEAR_TESTS:
            yr = [x for x in increment if x['year'] == year]
            year_dates = [r['date'] for r in test if r['year'] == year]
            yearly[str(year)] = metrics(yr, year_dates)
        result['models'][name] = {
            'same_referee_eligible_test_sample': metrics(all_rows, target_dates),
            'incremental_outside_frozen_eight': metrics(increment, target_dates),
            'incremental_by_year': yearly,
            'overlap_with_frozen_eight': len(set(x['fid'] for x in all_rows) & set(frozen)),
            'unique_incremental_fids': len({x['fid'] for x in increment}),
            'selected_fids': len({x['fid'] for x in all_rows}),
        }
    for year in YEAR_TESTS:
        fr = [
            {'fid': str(x['fid']), 'date': str(x['date']), 'year': int(x['year']), 'league': str(x['league']), 'net_u': float(x['pnl'])}
            for x in frozen.values() if int(x['year']) == year
        ]
        result['frozen_baseline'][str(year)] = metrics(fr)
        for name in model_names:
            inc = [x for x in predictions[name].values() if x['fid'] not in frozen and x['year'] == year]
            comb = fr + inc
            result['combined_same_horizon'].setdefault(name, {})[str(year)] = metrics(comb)
    result['frozen_baseline']['2024_2026'] = metrics([
        {'fid': str(x['fid']), 'date': str(x['date']), 'year': int(x['year']), 'league': str(x['league']), 'net_u': float(x['pnl'])}
        for x in frozen.values() if int(x['year']) in YEAR_TESTS
    ])
    for name in model_names:
        inc = [x for x in predictions[name].values() if x['fid'] not in frozen]
        fr = [{'fid': str(x['fid']), 'date': str(x['date']), 'year': int(x['year']), 'league': str(x['league']), 'net_u': float(x['pnl'])} for x in frozen.values() if int(x['year']) in YEAR_TESTS]
        result['combined_same_horizon'][name]['2024_2026'] = metrics(fr + inc)

    # Use the already audited actual Crown receipt archive only for a strict FID
    # overlap diagnostic. It contains HTTP receipt times, but no referee assignment
    # snapshots; the provider games source ends before the receipt window.
    receipt_fids = set()
    receipt_rows = 0
    receipt_dates = []
    for line in RECEIPT_FILE.open(encoding='utf-8'):
        x = json.loads(line)
        receipt_rows += 1
        receipt_fids.add(str(x['fixture_id']))
        receipt_dates.append(str(x.get('kickoff_utc', ''))[:10])
    result['actual_receipt'] = {
        'receipt_rows': receipt_rows,
        'unique_receipt_fids': len(receipt_fids),
        'receipt_kickoff_range': [min(receipt_dates), max(receipt_dates)],
        'receipt_fids_matching_referee_model_targets': len(receipt_fids & set(byfid)),
        'receipt_rows_with_assignment_time_evidence': 0,
        'model_replay_status': 'not evaluable as a true pre-match referee-information test; target assignment has no publication/receipt timestamp and source data ends before the 2026-10/11 receipt window',
    }

    # Convert per-model fixture predictions to a common flat, reproducible ledger.
    ledger = []
    for row in test:
        for name in (*model_names, 'LOWER_PRICE'):
            p = predictions[name][str(row['fid'])]
            ledger.append({
                'fid': str(row['fid']), 'year': int(row['year']), 'date': row['date'],
                'iso_week': iso(row['date']), 'league': str(row['league']),
                'home_id': str(row['home_id']), 'away_id': str(row['away_id']),
                'home_team_tm_id': str(row.get('tm_home_id', '')),
                'away_team_tm_id': str(row.get('tm_away_id', '')),
                'tm_game_id': row['tm_game_id'], 'referee_raw': row['referee_raw'],
                'referee_key': row['referee_key'],
                'referee_assignment_timestamp_verified': False,
                'prior_ref_n': row['prior_ref_n'],
                'prior_ref_bias': row['prior_ref_bias'],
                'prior_ref_cutoff_date': row.get('prior_ref_cutoff_date'),
                'Crown_T12_AH_home_line': float(row['al']),
                'Crown_T12_home_odds': float(row['ah']), 'Crown_T12_away_odds': float(row['aa']),
                'side': p['side'], 'price': p['price'], 'FT_home': int(row['hg']), 'FT_away': int(row['ag']),
                'settlement': p['settlement'], 'net_u': round(p['net_u'], 6),
                'frozen_eight_overlap_posthoc': str(row['fid']) in frozen,
                'method': name, 'historical_event_time_replay': True, 'true_pregame_referee_information': False,
                'predicted_home_minus_away_u': row.get(f'{name}_predicted_home_minus_away_u'),
            })

    (OUT / 'm8_referee_history_results_20261120.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with gzip.open(OUT / 'referee_history_per_fixture_20261120.jsonl.gz', 'wt', encoding='utf-8') as f:
        for row in ledger:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps({
        'coverage': result['source_audit'],
        'models_incremental': {k: v['incremental_outside_frozen_eight'] for k, v in result['models'].items()},
        'by_year': {k: v['incremental_by_year'] for k, v in result['models'].items()},
        'actual_receipt': result['actual_receipt'],
    }, ensure_ascii=False, default=str), flush=True)


if __name__ == '__main__':
    main()
