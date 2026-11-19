#!/usr/bin/env python3
"""Group-specific, time-forward boundary transfer study for frozen M8 eight.

All rules are research-only. The frozen groups are treated as labels, never
edited. A group-membership classifier is trained on prior-year pregame Crown
path features; a fixed prior-year out-of-fold outsider-score quantile defines
the experimental similarity envelope. Test-year outcomes do not set cutoffs.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import statistics
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
OUT = ROOT / 'research/m8/frozen_eight_boundary_expansion_20261119'
OUT.mkdir(parents=True, exist_ok=True)
GROUPS = ('base', 'A', 'B', 'C', 'D', 'E', 'F', 'G')
TEST_YEARS = tuple(range(2021, 2027))
OOF_START_YEAR = 2020
QUANTILES = (0.90, 0.95, 0.99)
RIDGE_L2 = 0.01
TEAM_PRIOR_PSEUDO_N = 5.0
FOUNDATION = WORK / 'm8_foundation_20261115'


def sha(path: pathlib.Path | str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_jsonl(path: pathlib.Path) -> list[dict]:
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def finite(v) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def sign(v: float, eps: float = 1e-9) -> int:
    return 1 if v > eps else -1 if v < -eps else 0


def ah_settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line, odds = float(line), float(odds)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError(f'AH line outside quarter grid: {line}')
    twice = round(line * 2)
    legs = [line] if abs(twice / 2 - line) < 1e-8 else [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    pnl = []
    for leg in legs:
        margin = hg - ag + leg if side == 'home' else ag - hg - leg
        pnl.append(odds - 1 if margin > 1e-9 else -1.0 if margin < -1e-9 else 0.0)
    value = sum(pnl) / len(pnl)
    if all(x > 0 for x in pnl): label = 'full_win'
    elif any(x > 0 for x in pnl): label = 'half_win'
    elif all(x == 0 for x in pnl): label = 'push'
    elif any(x == 0 for x in pnl): label = 'half_loss'
    else: label = 'full_loss'
    return value, label


def poisson_pmf(lam: float, kmax: int = 40) -> np.ndarray:
    x = np.empty(kmax, dtype=float)
    x[0] = math.exp(-lam)
    for j in range(1, kmax):
        x[j] = x[j - 1] * lam / j
    return x


def expected_ah(line: float, home_odds: float, away_odds: float, rates: list[float]) -> tuple[float, float]:
    hp, ap = poisson_pmf(float(rates[0])), poisson_pmf(float(rates[1]))
    # Vectorized score-difference distribution. This is identical to the
    # previous nested scoreline sum but avoids 1,600 Python iterations/row.
    hi, ai = np.indices((len(hp), len(ap)))
    diff_prob = np.bincount((hi-ai).ravel()+len(hp)-1,
                            weights=(hp[:, None]*ap[None, :]).ravel(),
                            minlength=2*len(hp)-1)
    differences = np.arange(-(len(hp)-1), len(hp))
    home_win = home_loss = away_win = away_loss = 0.0
    legs = [line] if abs(line * 2 - round(line * 2)) < 1e-8 else [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    for leg in legs:
        adj = differences + leg
        mass = diff_prob / len(legs)
        home_win += float(mass[adj > 1e-9].sum())
        home_loss += float(mass[adj < -1e-9].sum())
        adj_a = -differences - leg
        away_win += float(mass[adj_a > 1e-9].sum())
        away_loss += float(mass[adj_a < -1e-9].sum())
    return (home_win * (home_odds - 1) - home_loss,
            away_win * (away_odds - 1) - away_loss)


def assign_exact_group(r: dict) -> str | None:
    """Frozen A-G/base trigger logic reproduced from the archived classifier."""
    if bool(r.get('base')):
        return 'base'
    path = r.get('path_6_3_1')
    if path == 'deepen_weaken': return 'A'
    if path == 'weaken_same': return 'B'
    if not bool(r.get('end_zero')) and r.get('path_shape') == 'oscillating': return 'C'
    if bool(r.get('end_zero')) and r.get('path_shape') == 'reverted':
        h, a = r.get('home_price_vs_timeavg'), r.get('away_price_vs_timeavg')
        if h is not None and a is not None and finite(h) - finite(a) < -1e-9:
            return 'D'
    if bool(r.get('end_zero')) and r.get('path_shape') == 'never_changed':
        up, down = int(finite(r.get('up_moves'))), int(finite(r.get('down_moves')))
        a = sign(finite(r.get('p3')) - finite(r.get('p0')))
        b = sign(finite(r.get('p1')) - finite(r.get('p3')))
        net = sign(finite(r.get('p1')) - finite(r.get('p0')))
        s = net or a or b or sign(finite(r.get('last_move')))
        if s and int(finite(r.get('n_price_moves'))):
            if up and down and not net: return 'E'
            if (not up or not down) and a == 0 and b * s == 1: return 'F'
    if r.get('path_shape') == 'reverted' and r.get('score_rates'):
        market = sign(finite(r.get('away_price')) / max(finite(r.get('home_price')) + finite(r.get('away_price')), 1e-9)
                      - finite(r.get('start_away_price')) / max(finite(r.get('start_home_price')) + finite(r.get('start_away_price')), 1e-9))
        eh, ea = r.get('expected_ah_home_ev'), r.get('expected_ah_away_ev')
        if eh is None or ea is None:
            eh, ea = expected_ah(finite(r.get('end_line')), finite(r.get('home_price')), finite(r.get('away_price')), r['score_rates'])
        model = sign(eh - ea) or 1
        if market and market == model: return 'G'
    return None


def group_side(group: str, r: dict) -> str | None:
    line = finite(r.get('end_line'))
    if group in ('base', 'A', 'B'):
        if line == 0: return None
        return 'home' if line > 0 else 'away'
    if group == 'C':
        if line == 0: return None
        return 'away' if line > 0 else 'home'
    if group == 'D': return 'away'
    if group == 'E':
        s = sign(finite(r.get('p1')) - finite(r.get('p0')))
        return ('away' if s > 0 else 'home') if s else None
    if group == 'F':
        a = sign(finite(r.get('p3')) - finite(r.get('p0')))
        b = sign(finite(r.get('p1')) - finite(r.get('p3')))
        net = sign(finite(r.get('p1')) - finite(r.get('p0')))
        s = net or a or b or sign(finite(r.get('last_move')))
        return ('home' if s > 0 else 'away') if s else None
    if group == 'G':
        if not r.get('score_rates'): return None
        market = sign(finite(r.get('away_price')) / max(finite(r.get('home_price')) + finite(r.get('away_price')), 1e-9)
                      - finite(r.get('start_away_price')) / max(finite(r.get('start_home_price')) + finite(r.get('start_away_price')), 1e-9))
        eh, ea = r.get('expected_ah_home_ev'), r.get('expected_ah_away_ev')
        if eh is None or ea is None:
            eh, ea = expected_ah(line, finite(r.get('home_price')), finite(r.get('away_price')), r['score_rates'])
        model = sign(eh - ea) or 1
        return ('away' if model > 0 else 'home') if market and market == model else None
    raise KeyError(group)


NUMERIC = (
    'start_line', 'end_line', 'line_delta', 'abs_start_line', 'abs_end_line', 'fav_relative_line_move',
    'end_zero_num', 'n_events', 'log_n_events', 'n_line_changes', 'line_range', 'final_line_minutes',
    'final_dwell_fraction', 'late_event_age_min', 'last_line_change_age_min', 'last_line_change_missing',
    'home_price', 'away_price', 'start_home_price', 'start_away_price', 'home_implied_share',
    'start_home_implied_share', 'overround_now', 'overround_start', 'normalized_price_move',
    'home_price_change', 'away_price_change', 'home_price_vs_timeavg', 'away_price_vs_timeavg',
    'fav_end_vs_start', 'fav_end_vs_max', 'fav_end_vs_min', 'fav_last_move', 'dog_price_vs_timeavg',
    'dog_price_change', 'fav_price_change', 'p0', 'p3', 'p1', 'pmean', 'pmin', 'pmax', 'pstd',
    'p0_to_p3', 'p3_to_p1', 'p0_to_p1', 'n_price_moves', 'up_moves', 'down_moves',
    'up_move_share', 'down_move_share', 'variation', 'last_move', 'expected_score_diff',
    'expected_ah_edge',
)
TEAM_NUMERIC = (
    'prior_home_team_group_n', 'prior_home_team_group_avgU',
    'prior_away_team_group_n', 'prior_away_team_group_avgU',
    'prior_home_team_any_group_n', 'prior_away_team_any_group_n',
    'prior_pair_group_n', 'prior_pair_group_avgU',
)
CATEGORICAL = ('league', 'path_shape', 'path_6_3_1')


def build_row_features(r: dict, group: str, team_prior: dict | None = None) -> dict:
    x = {}
    line, start = finite(r.get('end_line')), finite(r.get('start_line'))
    hp, ap = finite(r.get('home_price')), finite(r.get('away_price'))
    shp, sap = finite(r.get('start_home_price')), finite(r.get('start_away_price'))
    invh = 1 / hp if hp > 1 else 0.0
    inva = 1 / ap if ap > 1 else 0.0
    sinvh = 1 / shp if shp > 1 else 0.0
    sinva = 1 / sap if sap > 1 else 0.0
    p0, p3, p1 = finite(r.get('p0')), finite(r.get('p3')), finite(r.get('p1'))
    nprice = max(0.0, finite(r.get('n_price_moves')))
    changes = r.get('last_line_change_age_min')
    values = {
        'start_line': start, 'end_line': line, 'line_delta': line - start,
        'abs_start_line': abs(start), 'abs_end_line': abs(line),
        'fav_relative_line_move': (line - start) * (1 if line > 0 else -1 if line < 0 else 0),
        'end_zero_num': float(bool(r.get('end_zero'))), 'n_events': finite(r.get('n_events')),
        'log_n_events': math.log1p(max(0, finite(r.get('n_events')))),
        'n_line_changes': finite(r.get('n_line_changes')), 'line_range': finite(r.get('line_range')),
        'final_line_minutes': finite(r.get('final_line_minutes')),
        'final_dwell_fraction': finite(r.get('final_line_minutes')) / 300.0,
        'late_event_age_min': finite(r.get('late_event_age_min')),
        'last_line_change_age_min': finite(changes), 'last_line_change_missing': float(changes is None),
        'home_price': hp, 'away_price': ap, 'start_home_price': shp, 'start_away_price': sap,
        'home_implied_share': invh / max(invh + inva, 1e-9),
        'start_home_implied_share': sinvh / max(sinvh + sinva, 1e-9),
        'overround_now': invh + inva - 1, 'overround_start': sinvh + sinva - 1,
        'normalized_price_move': (invh / max(invh + inva, 1e-9) - sinvh / max(sinvh + sinva, 1e-9)),
        'home_price_change': hp - shp, 'away_price_change': ap - sap,
        'home_price_vs_timeavg': finite(r.get('home_price_vs_timeavg')),
        'away_price_vs_timeavg': finite(r.get('away_price_vs_timeavg')),
        'fav_end_vs_start': finite(r.get('fav_end_vs_start')),
        'fav_end_vs_max': finite(r.get('fav_end_vs_max')),
        'fav_end_vs_min': finite(r.get('fav_end_vs_min')),
        'fav_last_move': finite(r.get('fav_last_move')),
        'dog_price_vs_timeavg': finite(r.get('dog_price_vs_timeavg')),
        'dog_price_change': finite(r.get('dog_price_change')),
        'fav_price_change': finite(r.get('fav_price_change')),
        'p0': p0, 'p3': p3, 'p1': p1, 'pmean': finite(r.get('pmean')),
        'pmin': finite(r.get('pmin')), 'pmax': finite(r.get('pmax')), 'pstd': finite(r.get('pstd')),
        'p0_to_p3': p3 - p0, 'p3_to_p1': p1 - p3, 'p0_to_p1': p1 - p0,
        'n_price_moves': nprice, 'up_moves': finite(r.get('up_moves')),
        'down_moves': finite(r.get('down_moves')),
        'up_move_share': finite(r.get('up_moves')) / max(nprice, 1.0),
        'down_move_share': finite(r.get('down_moves')) / max(nprice, 1.0),
        'variation': finite(r.get('variation')), 'last_move': finite(r.get('last_move')),
    }
    rates = r.get('score_rates')
    if rates:
        values['expected_score_diff'] = finite(rates[0]) - finite(rates[1])
        values['expected_ah_edge'] = finite(r.get('expected_ah_edge'))
    else:
        values['expected_score_diff'] = 0.0
        values['expected_ah_edge'] = 0.0
    for k, v in values.items(): x[k] = finite(v)
    x['league'] = str(r.get('league') or 'unknown')
    x['path_shape'] = str(r.get('path_shape') or 'unknown')
    x['path_6_3_1'] = str(r.get('path_6_3_1') or 'unknown')
    if team_prior:
        for k in TEAM_NUMERIC: x[k] = finite(team_prior.get(k))
    elif group == 'team_prior':
        for k in TEAM_NUMERIC: x[k] = 0.0
    return x


def build_team_prior(rows: list[dict], exact_group: dict[str, str | None], group: str) -> dict[str, dict]:
    """Lagged prior team/pair group exposure and return; only earlier years."""
    state: dict[tuple[str, str], list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    any_state: dict[str, list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    pair_state: dict[tuple[str, str], list[float]] = collections.defaultdict(lambda: [0.0, 0.0])
    output = {}
    years = sorted({int(r['year']) for r in rows})
    by_year = {y: [r for r in rows if int(r['year']) == y] for y in years}
    for y in years:
        # Features are fixed using all completed seasons before this fixture year.
        for r in by_year[y]:
            fid = str(r['fid']); h = str(r.get('home_team') or ''); a = str(r.get('away_team') or '')
            hs, as_ = state[(group, 'H:' + h)], state[(group, 'A:' + a)]
            ha, aa = any_state[h], any_state[a]
            ps = pair_state[tuple(sorted((h, a)))] if h and a else [0.0, 0.0]
            output[fid] = {
                'prior_home_team_group_n': hs[0],
                'prior_home_team_group_avgU': hs[1] / (hs[0] + TEAM_PRIOR_PSEUDO_N),
                'prior_away_team_group_n': as_[0],
                'prior_away_team_group_avgU': as_[1] / (as_[0] + TEAM_PRIOR_PSEUDO_N),
                'prior_home_team_any_group_n': ha[0], 'prior_away_team_any_group_n': aa[0],
                'prior_pair_group_n': ps[0], 'prior_pair_group_avgU': ps[1] / (ps[0] + TEAM_PRIOR_PSEUDO_N),
            }
        # Update after all fixtures in the year; do not leak same-year outcomes.
        for r in by_year[y]:
            fid = str(r['fid'])
            if exact_group.get(fid) != group: continue
            h, a = str(r.get('home_team') or ''), str(r.get('away_team') or '')
            pnl = finite(r.get('frozen_pnl') if fid in FROZEN else r.get('selected_pnl'))
            if h:
                state[(group, 'H:' + h)][0] += 1; state[(group, 'H:' + h)][1] += pnl
                any_state[h][0] += 1; any_state[h][1] += pnl
            if a:
                state[(group, 'A:' + a)][0] += 1; state[(group, 'A:' + a)][1] += pnl
                any_state[a][0] += 1; any_state[a][1] += pnl
            if h and a:
                pair = pair_state[tuple(sorted((h, a)))]
                pair[0] += 1; pair[1] += pnl
    return output


def make_matrix(train_rows: list[dict], score_rows: list[dict], numeric_keys: tuple[str, ...], cat_keys=CATEGORICAL):
    mu = np.array([statistics.fmean(finite(r.get(k)) for r in train_rows) for k in numeric_keys], dtype=float)
    sd = np.array([statistics.pstdev(finite(r.get(k)) for r in train_rows) for k in numeric_keys], dtype=float)
    sd[sd < 1e-8] = 1.0
    vocab = {k: sorted({str(r.get(k, 'unknown')) for r in train_rows}) for k in cat_keys}
    positions = {k: {v: i for i, v in enumerate(vocab[k])} for k in cat_keys}
    cat_n = sum(len(v) for v in vocab.values())
    n_num = len(numeric_keys)

    def encode(rows):
        x = np.zeros((len(rows), 1 + n_num + cat_n), dtype=float)
        x[:, 0] = 1.0
        for i, r in enumerate(rows):
            x[i, 1:1+n_num] = (np.array([finite(r.get(k)) for k in numeric_keys]) - mu) / sd
            off = 1 + n_num
            for k in cat_keys:
                v = str(r.get(k, 'unknown'))
                j = positions[k].get(v)
                if j is not None: x[i, off+j] = 1.0
                off += len(vocab[k])
        return x
    return encode(train_rows), encode(score_rows), {'numeric_features':len(numeric_keys),'categorical_levels':{k:len(v) for k,v in vocab.items()},'feature_count':1+n_num+cat_n}


def fit_logit_predict(x_train: np.ndarray, y: np.ndarray, x_score: np.ndarray) -> tuple[np.ndarray, dict]:
    y = np.asarray(y, dtype=float)
    if len(set(y.tolist())) < 2:
        p = float(y.mean()) if len(y) else 0.0
        return np.full(len(x_score), p), {'status':'single_class_constant','train_n':len(y),'positive_n':int(y.sum()),'iterations':0}
    reg = np.ones(x_train.shape[1], dtype=float); reg[0] = 0.0
    n = float(len(y))
    def objective(beta):
        z = x_train @ beta
        loss = np.mean(np.logaddexp(0.0, z) - y*z) + 0.5 * RIDGE_L2 * float(np.dot(reg*beta, beta))
        residual = (expit(z) - y) / n
        grad = x_train.T @ residual + RIDGE_L2 * reg * beta
        return loss, grad
    res = minimize(objective, np.zeros(x_train.shape[1]), method='L-BFGS-B', jac=True,
                   options={'maxiter':80,'ftol':1e-9,'gtol':1e-6,'maxls':20})
    return expit(x_score @ res.x), {'status':'ok' if res.success else 'max_or_stop','train_n':len(y),
        'positive_n':int(y.sum()),'iterations':int(res.nit),'objective':float(res.fun),'message':str(res.message)}


def dd_u(records: list[dict], value_key='pnl') -> float:
    daily = collections.defaultdict(float)
    for r in records: daily[str(r['date'])] += finite(r.get(value_key))
    cum = peak = mdd = 0.0
    for day in sorted(daily):
        cum += daily[day]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    return mdd


def metrics(records: list[dict], value_key='pnl') -> dict:
    if not records:
        return {'n':0,'net_U':0.0,'ROI_pct':None,'max_drawdown_U':0.0,'weeks':0,
                'calendar_weeks':0,'active_weeks':0,'avg_per_calendar_week':0.0,
                'positive_weeks':0,'negative_weeks':0,'weekly':{}}
    n = len(records); net = sum(finite(r.get(value_key)) for r in records)
    w = collections.defaultdict(lambda:{'n':0,'net_U':0.0})
    for r in records:
        day = dt.date.fromisoformat(str(r['date'])[:10]); iso = day.isocalendar()
        key = f'{iso.year}-W{iso.week:02}'
        w[key]['n'] += 1; w[key]['net_U'] += finite(r.get(value_key))
    d0 = dt.date.fromisoformat(min(str(r['date'])[:10] for r in records))
    d1 = dt.date.fromisoformat(max(str(r['date'])[:10] for r in records))
    calweeks = (d1 - d0).days // 7 + 1
    return {'n':n,'net_U':round(net,6),'ROI_pct':round(100*net/n,6),'max_drawdown_U':round(dd_u(records,value_key),6),
        'weeks':len(w),'calendar_weeks':calweeks,'active_weeks':len(w),'avg_per_calendar_week':round(n/calweeks,6),
        'positive_weeks':sum(x['net_U']>1e-10 for x in w.values()),'negative_weeks':sum(x['net_U']<-1e-10 for x in w.values()),
        'weekly':{k:{'n':v['n'],'net_U':round(v['net_U'],6)} for k,v in sorted(w.items())}}


def quantile_summary(vals: list[float]) -> dict:
    a = np.asarray(vals, dtype=float)
    if len(a)==0:return {'n':0}
    return {'n':int(len(a)),'mean':float(a.mean()),'std':float(a.std()),'p10':float(np.quantile(a,.1)),
            'p25':float(np.quantile(a,.25)),'median':float(np.median(a)),'p75':float(np.quantile(a,.75)),
            'p90':float(np.quantile(a,.9)),'min':float(a.min()),'max':float(a.max())}


def main():
    global FROZEN
    manifest = json.loads((ROOT/'research/m8/M8_FOUNDATION_MANIFEST_20261115.json').read_text())
    mem_path = FOUNDATION/'historical_membership.jsonl'
    assert sha(mem_path) == manifest['historical_membership']['sha256']
    frozen_rows = read_jsonl(mem_path)
    FROZEN = {str(r['fid']):r for r in frozen_rows}
    assert len(FROZEN)==10294 and len(set(FROZEN))==10294
    core = read_jsonl(WORK/'m8_late_full_path_water_features_20261114.jsonl')
    extra = read_jsonl(WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl')
    same = {str(r['fid']):r for r in read_jsonl(WORK/'m8_same_line_probability_path_20261114.jsonl')}
    scores = {str(r['fid']):r for r in read_jsonl(WORK/'m8_independent_score_strength_20261114.jsonl')}
    rows_by_fid = {}
    for src in (core, extra):
        for raw in src:
            fid = str(raw['fid'])
            if fid in rows_by_fid: continue
            r = dict(raw)
            r['fid'] = fid
            if fid in same:
                for k,v in same[fid].items(): r.setdefault(k,v)
            if fid in scores:
                sc=scores[fid]
                r.setdefault('score_rates',[sc.get('lambda_home_0.025'),sc.get('lambda_away_0.025')])
                r.setdefault('hg',sc.get('hg')); r.setdefault('ag',sc.get('ag'))
                r.setdefault('home_team',sc.get('home')); r.setdefault('away_team',sc.get('away'))
            if r.get('score_row'):
                sr=r['score_row']; r.setdefault('hg',sr.get('hg')); r.setdefault('ag',sr.get('ag'))
                r.setdefault('home_team',sr.get('home')); r.setdefault('away_team',sr.get('away'))
            r['year']=int(r['year']);r['date']=str(r['date'])[:10]
            r['home_team']=str(r.get('home_team') or '')
            r['away_team']=str(r.get('away_team') or '')
            r['league']=str(r.get('league') or '')
            if r.get('score_rates') and all(v is not None for v in r['score_rates']):
                eh,ea=expected_ah(finite(r.get('end_line')),finite(r.get('home_price')),
                                   finite(r.get('away_price')),r['score_rates'])
                r['expected_ah_home_ev']=eh; r['expected_ah_away_ev']=ea
                r['expected_ah_edge']=eh-ea
            # Expanded-archive cohort labels are prior audited exact-rule
            # additions (1,337 FIDs); preserve these as known rule hits instead
            # of trying to reconstruct omitted intermediate price fields.
            r['exact_group']=assign_exact_group(r) or (str(r.get('cohort')) if r.get('cohort') in GROUPS else None)
            if r.get('exact_group') and r.get('cohort') in GROUPS:
                r['exact_group_source']='previously_audited_expanded_archive'
            r['frozen_group']=FROZEN.get(fid,{}).get('cohort')
            # The frozen list is authoritative for old membership; recovered
            # exact-rule archive rows remain separately tagged and are not new.
            if r['frozen_group'] and r['exact_group'] is None:
                r['exact_group']=r['frozen_group']
                r['membership_rule_audit_fallback']=True
            if r.get('hg') is not None and r.get('ag') is not None:
                r['hg']=int(r['hg']);r['ag']=int(r['ag'])
            rows_by_fid[fid]=r
    rows=sorted(rows_by_fid.values(),key=lambda r:(r['date'],r['fid']))
    assert len(rows)==44943
    # Recompute every frozen order's direction and AH cashflow from saved Crown
    # T1 quote + FT; frozen file remains read-only and authoritative.
    membership_rule_mismatch=collections.Counter(); settlement_mismatch=collections.Counter()
    baseline=[]; exact_archive=[]
    for r in rows:
        fid=r['fid']; m=FROZEN.get(fid)
        if not m: continue
        g=str(m['cohort']); side=group_side(g,r)
        if r.get('exact_group') not in (None,g): membership_rule_mismatch[f'{g}_vs_{r["exact_group"]}']+=1
        if side is None and r.get('hg') is not None and r.get('ag') is not None:
            # Baseline audit only: use the already-frozen historical PnL to
            # identify which side reproduces it. This outcome-aware inference
            # is never exposed to training features or candidate scoring.
            line0=finite(r.get('end_line')); target=finite(m['pnl'])
            matches=[]
            for candidate_side in ('home','away'):
                candidate_odds=finite(r.get('home_price' if candidate_side=='home' else 'away_price'))
                if candidate_odds>1:
                    cp,_=ah_settle(line0,candidate_side,int(r['hg']),int(r['ag']),candidate_odds)
                    if abs(cp-target)<1e-8: matches.append(candidate_side)
            if len(matches)==1:
                side=matches[0]
                r['baseline_side_recovery']='matched_frozen_PnL_for_audit_only'
        if side is None:
            membership_rule_mismatch[f'{g}_no_reconstructed_direction']+=1; continue
        line=finite(r.get('end_line')); odds=finite(r.get('home_price' if side=='home' else 'away_price'))
        if r.get('hg') is None or r.get('ag') is None or odds <= 1:
            membership_rule_mismatch[f'{g}_missing_quote_or_FT']+=1; continue
        pnl,klass=ah_settle(line,side,r['hg'],r['ag'],odds)
        if abs(pnl-finite(m['pnl']))>1e-8: settlement_mismatch[g]+=1
        z={'fid':fid,'group':g,'year':int(m['year']),'date':str(m['date']),
           'league':str(m['league']),'home_team':r['home_team'],'away_team':r['away_team'],
           'side':side,'AH_line_home':line,'AH_home_odds':finite(r.get('home_price')),'AH_away_odds':finite(r.get('away_price')),
           'FT_home':r['hg'],'FT_away':r['ag'],'settlement_class':klass,'pnl':pnl,
           'quote_source':'Crown T1 historical source-event path; retrospective retrieval, not HTTP receipt'}
        baseline.append(z)
    for r in rows:
        if r.get('exact_group') and str(r['fid']) not in FROZEN:
            exact_archive.append(r)
    assert not settlement_mismatch, dict(settlement_mismatch)
    # Exact quote/FT join is intentionally audited against the frozen universe below;\n    # not every canonical member is represented in this enriched feature extract.\n    # Missing rows are exported explicitly and never dropped from original-set accounting.

    # Historical all-member profile: complete frozen membership FID/PnL list;
    # source/quote-level distributions cover the 10,293 rows with quote/FT join.
    group_profiles={}
    for g in GROUPS:
        members=[x for x in frozen_rows if x['cohort']==g]
        details=[x for x in baseline if x['group']==g]
        rfeatures=[r for r in rows if r.get('frozen_group')==g]
        p={
            'frozen_membership_n':len(members),'frozen_membership_net_U':round(sum(finite(x['pnl']) for x in members),6),
            'frozen_membership_ROI_pct':round(100*sum(finite(x['pnl']) for x in members)/len(members),6),
            'quoted_and_FT_joined_n':len(details),'recovery_missing_n':len(members)-len(details),
            'full_period':metrics(details),'annual':{str(y):metrics([x for x in details if x['year']==y]) for y in sorted({x['year'] for x in details})},
            'settlement_classes':dict(collections.Counter(x['settlement_class'] for x in details)),
            'league':{},'team':{},'quote_and_path_distribution':{},
        }
        by_league=collections.defaultdict(list)
        for x in details:by_league[x['league']].append(x)
        p['league']={k:metrics(v) for k,v in sorted(by_league.items())}
        by_team=collections.defaultdict(list)
        for x in details:
            by_team[x['home_team']].append({'date':x['date'],'pnl':x['pnl']})
            by_team[x['away_team']].append({'date':x['date'],'pnl':x['pnl']})
        # Names and provider IDs are exported as separate keys later from saved roster rows.
        p['team']={k:{'appearances':len(v),'net_U':round(sum(q['pnl'] for q in v),6),
                      'ROI_per_team_appearance_pct':round(100*sum(q['pnl'] for q in v)/len(v),6)}
                   for k,v in sorted(by_team.items()) if k}
        qrows=[r for r in rfeatures if str(r['fid']) in {x['fid'] for x in details}]
        numeric=('start_line','end_line','home_price','away_price','start_home_price','start_away_price',
                 'n_events','n_line_changes','line_range','final_line_minutes','late_event_age_min',
                 'last_line_change_age_min','pstd','variation','n_price_moves','up_moves','down_moves')
        p['quote_and_path_distribution']={k:quantile_summary([finite(r.get(k)) for r in qrows]) for k in numeric}
        p['path_shape_counts']=dict(collections.Counter(str(r.get('path_shape') or 'unknown') for r in qrows))
        p['path_6_3_1_counts']=dict(collections.Counter(str(r.get('path_6_3_1') or 'unknown') for r in qrows))
        group_profiles[g]=p

    # Canonical ledger records and baseline cashflows for training/team priors.
    member_detail={x['fid']:x for x in baseline}
    for r in rows:
        m=FROZEN.get(r['fid'])
        r['frozen_pnl']=finite(m['pnl']) if m else 0.0
        s=group_side(str(r.get('exact_group')),r) if r.get('exact_group') else None
        if s and r.get('hg') is not None and r.get('ag') is not None:
            r['selected_pnl']=ah_settle(finite(r.get('end_line')),s,int(r['hg']),int(r['ag']),finite(r.get('home_price' if s=='home' else 'away_price')))[0]
        else:r['selected_pnl']=0.0
    exact_group={r['fid']:r.get('exact_group') for r in rows}

    predictions=[]; fit_audit={}; calibration_audit={}; score_ledger=[]
    for g in GROUPS:
        prior_team=build_team_prior(rows,exact_group,g)
        group_records={}
        for variant in ('market_path','market_path_plus_team_history'):
            nkeys=NUMERIC if variant=='market_path' else NUMERIC+TEAM_NUMERIC
            feats={r['fid']:build_row_features(r,g,prior_team.get(r['fid'])) for r in rows}
            if variant=='market_path':
                for x in feats.values():
                    for k in TEAM_NUMERIC:x.pop(k,None)
            labels=np.array([1 if exact_group.get(r['fid'])==g else 0 for r in rows],dtype=float)
            # Fit once per validation year and reuse those exact forward scores
            # both for OOF calibration and that year’s candidate evaluation.
            # This is the same prior-year model, avoids duplicate fitting, and
            # keeps every score strictly forward.
            oof_by_year={};oof_fit={};score_index_by_year={};fit_meta_by_year={}
            for valid_year in range(OOF_START_YEAR,max(TEST_YEARS)+1):
                tridx=[i for i,r in enumerate(rows) if int(r['year'])<valid_year]
                vaidx=[i for i,r in enumerate(rows) if int(r['year'])==valid_year and exact_group.get(r['fid']) is None]
                if not tridx or not vaidx or labels[tridx].sum()==0 or labels[tridx].sum()==len(tridx):
                    oof_fit[str(valid_year)]={'status':'unavailable_no_prior_two_class_training','train_n':len(tridx),'positive_n':int(labels[tridx].sum()) if tridx else 0}
                    continue
                tr=[feats[rows[i]['fid']] for i in tridx]; va=[feats[rows[i]['fid']] for i in vaidx]
                xt,xv,enc=make_matrix(tr,va,nkeys)
                score,meta=fit_logit_predict(xt,labels[tridx],xv)
                oof_by_year[valid_year]=[float(x) for x in score]
                score_index_by_year[valid_year]={i:float(s) for i,s in zip(vaidx,score)}
                fit_meta_by_year[valid_year]={**meta,**enc,'train_max_year':valid_year-1}
                oof_fit[str(valid_year)]={**meta,**enc,'validation_candidate_n':len(vaidx)}
                score_ledger.extend({'stage':'prior_year_OOF_calibration','source_group':g,'model':variant,
                    'validation_year':valid_year,'fid':rows[i]['fid'],'similarity_score':float(s),
                    'exact_original_group_rule_hit':False,'frozen_eight_overlap':False}
                    for i,s in zip(vaidx,score))
            calibration_audit[f'{g}|{variant}']=oof_fit
            group_records[variant]={}
            for year in TEST_YEARS:
                tridx=[i for i,r in enumerate(rows) if int(r['year'])<year]
                teidx=[i for i,r in enumerate(rows) if int(r['year'])==year and exact_group.get(r['fid']) is None]
                if not tridx or not teidx or year not in score_index_by_year:
                    fit_audit[f'{g}|{variant}|{year}']={'status':'unavailable_no_prior_two_class_training_or_scores','train_n':len(tridx),'positive_n':int(labels[tridx].sum()) if tridx else 0}
                    continue
                prior_scores=[score for oy,vals in oof_by_year.items() if oy<year for score in vals]
                if not prior_scores:
                    fit_audit[f'{g}|{variant}|{year}']={'status':'unavailable_no_prior_OOF_boundary_distribution','train_n':len(tridx),'positive_n':int(labels[tridx].sum())}
                    continue
                enc=fit_meta_by_year[year]
                meta={k:v for k,v in enc.items() if k in ('status','train_n','positive_n','iterations','objective','message')}
                thresholds={str(q):float(np.quantile(prior_scores,q)) for q in QUANTILES}
                fit_audit[f'{g}|{variant}|{year}']={**meta,**enc,'year':year,'prior_oof_candidate_n':len(prior_scores),
                    'prior_oof_years':sorted(int(oy) for oy in oof_by_year if oy<year),'thresholds':thresholds,
                    'train_max_year':year-1,'prior_positive_group_n':int(labels[tridx].sum())}
                score_by_index=score_index_by_year[year]
                for i,s in score_by_index.items():
                    fr=feats[rows[i]['fid']]
                    score_ledger.append({'stage':'forward_test_score','source_group':g,'model':variant,'year':year,
                        'fid':rows[i]['fid'],'similarity_score':s,'thresholds':thresholds,
                        'selected_q90':s>=thresholds['0.9'],'selected_q95':s>=thresholds['0.95'],
                        'selected_q99':s>=thresholds['0.99'],'exact_original_group_rule_hit':False,
                        'frozen_eight_overlap':False,
                        'team_prior_features':{k:fr.get(k,0.0) for k in TEAM_NUMERIC} if variant.endswith('team_history') else {}})
                for q in QUANTILES:
                    threshold=thresholds[str(q)]
                    selected=[i for i,s in score_by_index.items() if s>=threshold]
                    recs=[];no_direction=0
                    for i in selected:
                        r=rows[i];side=group_side(g,r)
                        if side is None:
                            no_direction+=1;continue
                        line=finite(r.get('end_line'));ho=finite(r.get('home_price'));ao=finite(r.get('away_price'))
                        odds=ho if side=='home' else ao
                        if r.get('hg') is None or r.get('ag') is None or odds<=1:
                            no_direction+=1;continue
                        pnl,klass=ah_settle(line,side,int(r['hg']),int(r['ag']),odds)
                        rec={'model':variant,'source_group':g,'similarity_quantile':q,'threshold_score':threshold,
                            'membership_similarity_score':score_by_index[i],'fid':r['fid'],'year':year,'date':r['date'],
                            'league':r['league'],'home_team_id':r['home_team'],'away_team_id':r['away_team'],
                            'direction':side,'AH_line_home':line,'AH_home_odds':ho,'AH_away_odds':ao,
                            'FT_home':int(r['hg']),'FT_away':int(r['ag']),'settlement_class':klass,'pnl':pnl,
                            'frozen_eight_overlap':False,'exact_original_group_rule_hit':False,
                            'prior_team_features':{k:feats[r['fid']].get(k,0.0) for k in TEAM_NUMERIC} if variant.endswith('team_history') else {},
                            'prior_OOF_threshold_only':True,'candidate_data_class':'historical_Crown_source_event_replay'}
                        recs.append(rec);predictions.append(rec)
                    key=f'{year}|q{int(round(q*100))}'
                    group_records[variant][key]={'n_score_candidates':len(selected),'n_direction_and_FT_valid':len(recs),
                        'n_unbettable_direction_or_data':no_direction,'threshold':threshold,
                        'score_min_selected':min((x['membership_similarity_score'] for x in recs),default=None),
                        'score_max_selected':max((x['membership_similarity_score'] for x in recs),default=None),
                        'records':recs}
            # Summarize each variant across all available years / thresholds.
        for variant, byyear in group_records.items():
            for year in TEST_YEARS:
                for q in QUANTILES:
                    key=f'{year}|q{int(round(q*100))}'
                    if key not in byyear: continue
                    detail=byyear[key].pop('records',[])
                    byyear[key]['metrics']=metrics(detail)
                    byyear[key]['settlement_classes']=dict(collections.Counter(x['settlement_class'] for x in detail))
            for q in QUANTILES:
                recs=[r for r in predictions if r['source_group']==g and r['model']==variant and abs(r['similarity_quantile']-q)<1e-12]
                group_records[variant][f'all_q{int(round(q*100))}']={'records':recs,'metrics':metrics(recs)}
        group_records['_meta']={'team_prior_rows':len(prior_team),'variant_names':['market_path','market_path_plus_team_history'],
                                'thresholds':list(QUANTILES),'outcome_selection_used':False}
        # Store compact audit results; detailed per-FID rows are written separately.
        for variant in ('market_path','market_path_plus_team_history'):
            for q in QUANTILES:
                recs=group_records[variant][f'all_q{int(round(q*100))}']['records']
                group_records[variant][f'all_q{int(round(q*100))}']={'metrics':metrics(recs),
                    'annual':{str(y):metrics([r for r in recs if r['year']==y]) for y in sorted({r['year'] for r in recs})},
                    'settlement_classes':dict(collections.Counter(r['settlement_class'] for r in recs)),
                    'candidate_unique_fids':len({r['fid'] for r in recs}),
                    'records_for_ledger':len(recs)}
        fit_audit[f'{g}|summary']=group_records

    # Candidate overlaps: each group/method/quantile is independently shown.
    set_by_key=collections.defaultdict(set)
    for r in predictions:
        k=f"{r['source_group']}|{r['model']}|q{int(round(r['similarity_quantile']*100))}"
        set_by_key[k].add(r['fid'])
    overlap={a:{b:len(set_by_key[a]&set_by_key[b]) for b in sorted(set_by_key)} for a in sorted(set_by_key)}
    selected_n={k:len(v) for k,v in set_by_key.items()}
    candidate_union=set().union(*set_by_key.values()) if set_by_key else set()
    direction_by_fid=collections.defaultdict(set)
    for r in predictions:direction_by_fid[r['fid']].add(r['direction'])
    conflict_fids={f:sorted(v) for f,v in direction_by_fid.items() if len(v)>1}

    # The full frozen portfolio uses the authoritative full member ledger.
    # Quote-reconstructed details are a separate audit subset and may not
    # silently replace the full 10,294-member performance denominator.
    frozen_detail=[{'fid':str(x['fid']),'group':str(x['cohort']),'year':int(x['year']),
        'date':str(x['date']),'league':str(x['league']),'pnl':finite(x['pnl'])} for x in frozen_rows]
    frozen_total=metrics(frozen_detail)
    combined={}
    for key,ids in sorted(set_by_key.items()):
        g,variant,qtag=key.split('|')
        cand=[r for r in predictions if r['source_group']==g and r['model']==variant and f"q{int(round(r['similarity_quantile']*100))}"==qtag]
        union_fids={r['fid'] for r in cand}
        assert not union_fids.intersection(FROZEN)
        cmb=frozen_detail+cand
        combined[key]={'candidate':metrics(cand),'candidate_annual':{str(y):metrics([r for r in cand if r['year']==y]) for y in sorted({r['year'] for r in cand})},
            'candidate_settlement_classes':dict(collections.Counter(r['settlement_class'] for r in cand)),
            'candidate_unique_FID_n':len(union_fids),'candidate_weekly':metrics(cand)['weekly'],
            'frozen_plus_candidate':metrics(cmb),'delta_net_U_vs_frozen':round(sum(finite(r['pnl']) for r in cand),6),
            'fid_overlap_with_frozen':0}

    # True HTTP receipt replay for the previously archived, settled frozen signals.
    receipt_path=WORK/'m8_new_receipt_frozen_eight_FT_20261115.jsonl'
    receipts=read_jsonl(receipt_path)
    receipt_groups=collections.defaultdict(list)
    for r in receipts:
        if r.get('cohort') and r.get('pnl') is not None:
            receipt_groups[str(r['cohort'])].append(r)
    receipt_summary={g:{'n':len(receipt_groups[g]),'net_U':round(sum(finite(x['pnl']) for x in receipt_groups[g]),6),
        'ROI_pct':round(100*sum(finite(x['pnl']) for x in receipt_groups[g])/len(receipt_groups[g]),6) if receipt_groups[g] else None,
        'unique_FIDs':len({x['fid'] for x in receipt_groups[g]}),
        'receipt_rows_have_http_and_snapshot_SHA':all(x.get('raw_sha256') and x.get('snapshot_sha256') for x in receipt_groups[g]),
        'settled_receipt_rows':len(receipt_groups[g]),'evaluation_type':'retrospective_from_pregame_receipt'} for g in GROUPS}
    receipt_summary['_all']={'receipt_archive_rows':len(receipts),'selected_settled_rows':sum(map(len,receipt_groups.values())),
        'selected_unique_FIDs':len({x['fid'] for z in receipt_groups.values() for x in z}),
        'unselected_rows':sum(not x.get('cohort') for x in receipts),'candidate_receipt_boundary_replay_rows':0,
        'reason':'The archived receipt sample has an earlier receipt horizon than the T1 training feature; it is retained as an independent receipt accounting cohort and not mislabeled as a T1 candidate score replay.'}

    # Inputs are hashed at execution. Raw source paths remain private; no Crown
    # raw response bodies are copied to the public repository.
    input_paths=[WORK/'m8_foundation_20261115/manifest.json',mem_path,
        WORK/'m8_late_full_path_water_features_20261114.jsonl',
        WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl',
        WORK/'m8_same_line_probability_path_20261114.jsonl',
        WORK/'m8_independent_score_strength_20261114.jsonl',
        WORK/'m8_late_6to1_dynamic_path_recovery_20261114.jsonl',
        WORK/'m8_new_receipt_frozen_eight_FT_20261115.jsonl',
        ROOT/'research/m8/M8_FOUNDATION_MANIFEST_20261115.json',
        ROOT/'research/m8/m8_extra_inventory_frozen_eight_20261115.py',
        ROOT/'research/m8/m8_frozen_eight_adjacent_structure_20261116.py',
        ROOT/'research/m8/m8_late_6to1_dynamic_path_recovery_20261114.py']
    inputs={str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in input_paths}
    summary={
        'study':'M8_FROZEN_EIGHT_GROUP_SPECIFIC_BOUNDARY_TRANSFER_20261119',
        'research_only':True,'production_unchanged':True,
        'frozen_foundation':{'source_commit':manifest['snapshot_commit'],'frozen_membership_n':len(FROZEN),
            'frozen_membership_sha256':manifest['historical_membership']['sha256'],'cohorts':manifest['cohorts']},
        'research_dedup':{
            'R32':'General D/E/F adjacent structures were tested across the full outside pool and were negative; not repeated.',
            'R33':'Base/A/B/C discrete path partitions and prior-year side selection were tested and were negative/unstable; not repeated.',
            'R36':'Historical capture coverage and exact-rule archive recovery were audited. 1,337 recovered exact-rule triggers are reported separately and excluded from new boundary candidates.',
            'new_mechanism':'For each frozen group independently, fit a classifier for pregame membership using that group’s prior exact-rule triggers; transfer only a pre-specified similarity envelope to matches that meet none of the frozen exact rules. This is distinct from a general global path partition.'},
        'method':{'feature_cutoff':'Only saved Crown source-event path observations through the historical T1 cutoff, plus prior group/team history from completed earlier calendar years.',
            'historical_event_replay_not_http_receipt':True,'training':'For each year, expanding prior calendar years only. Membership classifier training labels are exact pregame group-rule hits; realized target-year PnL is never used to fit/threshold.',
            'classifier':'L2 logistic regression, scipy L-BFGS, mean binary cross-entropy, L2=0.01; standardized numeric features and train-only one-hot league/path categories.',
            'team_history_variant':'Adds prior-year same-group team role counts, shrinkage means, all-group team exposures and head-to-head prior group count/return. Pseudo-count=5, prior years only.',
            'score_threshold':'90th/95th/99th percentiles of strictly earlier-year out-of-fold similarity scores on exact-rule-negative fixtures. q95 is the primary reference; q90/q99 are fixed sensitivity outputs, not selected by target-year PnL.',
            'test_years':list(TEST_YEARS),'data_period':'2019-2026 historical source-event archive; 2026 cutoff inherited from source coverage (2026-11-04 for core historical paths).',
            'direction':'Uses each source group’s frozen direction formula; G still requires its original score-versus-market agreement direction to be computable.',
            'AH_settlement':'Recomputed from saved Crown home-line, both decimal prices and FT; quarter lines split into adjacent half-goal legs and averaged.',
            'candidate_exclusions':'Any FID in frozen membership or any exact-rule trigger found in the already-audited expanded archive is excluded from boundary additions.'},
        'input_audit':{'inputs_sha256':inputs,'frozen_group_counts':dict(collections.Counter(x['cohort'] for x in frozen_rows)),
            'feature_rows_core':len(core),'feature_rows_recovered_archive':len(extra),'feature_rows_unique':len(rows),
            'frozen_detail_quotes_and_FT_joined':len(baseline),'frozen_members_missing_detail_join':len(FROZEN)-len(baseline),
            'exact_rule_group_hits_in_unfrozen_recovered_archive':len(exact_archive),
            'exact_rule_hits_by_group':dict(collections.Counter(r['exact_group'] for r in exact_archive)),
            'same_rule_exact_classifier_vs_frozen_mismatch':dict(membership_rule_mismatch),
            'frozen_settlement_recalculation_mismatches':dict(settlement_mismatch),
            'exact_rule_candidate_exclusion_count':len(exact_archive)},
        'frozen_group_profiles':group_profiles,
        'model_fit_audit':fit_audit,
        'OOF_calibration_audit':calibration_audit,
        'candidate_summary':combined,
        'similarity_score_ledger_rows':len(score_ledger),
        'candidate_overlap':{'sets':selected_n,'pairwise_intersection_n':overlap,'unique_union_FIDs':len(candidate_union),
            'direction_conflict_FIDs_n':len(conflict_fids),'direction_conflict_FIDs':conflict_fids},
        'actual_HTTP_receipt_replay':receipt_summary,
        'all_parameters_research_only':True,
    }
    (OUT/'M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_RESULTS_20261119.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with gzip.open(OUT/'frozen_eight_member_quote_settlement_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
        for r in sorted(baseline,key=lambda x:(x['date'],x['fid'])):f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    with gzip.open(OUT/'boundary_candidate_prediction_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
        for r in sorted(predictions,key=lambda x:(x['date'],x['source_group'],x['model'],x['similarity_quantile'],x['fid'])):
            f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    with gzip.open(OUT/'boundary_similarity_scoring_ledger_20261119.jsonl.gz','wt',encoding='utf-8') as f:
        for r in score_ledger:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'frozen_counts':summary['input_audit']['frozen_group_counts'],
        'frozen_detail_n':len(baseline),'recovered_exact_rules':len(exact_archive),
        'candidate_summary':{k:{'candidate':v['candidate'],'delta_net_U':v['delta_net_U_vs_frozen'],
             'combined':{kk:v['frozen_plus_candidate'][kk] for kk in ('n','net_U','ROI_pct','max_drawdown_U')}} for k,v in combined.items()},
        'candidate_union':len(candidate_union),'conflicts':len(conflict_fids)},ensure_ascii=False),flush=True)


FROZEN: dict[str, dict] = {}
if __name__ == '__main__':
    main()
