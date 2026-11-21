#!/usr/bin/env python3
"""Time-forward test of red-card-adjusted team form against Crown AH.

Historical Crown prices and FT are replayed only. No network/API calls or
production writes. Card-missing histories remain explicitly unobserved.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import sqlite3
from zoneinfo import ZoneInfo

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')
OUT = pathlib.Path(__file__).resolve().parent
PATH49 = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
SCORES49 = WORK / 'm8_independent_score_strength_20261114.jsonl'
SCHEDULE_PAGES = DATA / 'm5-crown-authorized/schedules'
RAW_HIST = DATA / 'crown_quote_store/raw/historical'
SQLITE = DATA / 'crown_quote_store/crown_quotes.sqlite3'
RECEIPTS = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
FROZEN = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
EXPANDED = pathlib.Path(__file__).resolve().parent / 'expanded15_t1_path_input.jsonl.gz'
TZ = ZoneInfo('Asia/Shanghai')
UTC = dt.timezone.utc
LAG_DAYS = 3
WINDOW_DAYS = 365
ALPHA = 100.0
METHODS = ('market', 'market_plus_raw_form', 'market_plus_red_adjusted_form', 'market_plus_raw_and_red_context', 'low_price')


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def parse_ts(v):
    if not v:
        return None
    x = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00').replace(' ', 'T'))
    if x.tzinfo is None:
        x = x.replace(tzinfo=TZ)
    return x.astimezone(UTC)


def read_jsonl(path):
    with path.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def settle(line, side, gd, odds):
    handicap = float(line) if side == 'home' else -float(line)
    margin = int(gd) if side == 'home' else -int(gd)
    q = round(handicap * 4)
    if abs(handicap * 4 - q) > 1e-8:
        raise ValueError(f'AH line outside quarter grid: {line}')
    legs = [handicap] if q % 2 == 0 else [math.floor(handicap * 2) / 2, math.floor(handicap * 2) / 2 + .5]
    pnl = []
    states = []
    for leg in legs:
        z = margin + leg
        states.append('W' if z > 1e-9 else 'L' if z < -1e-9 else 'P')
        pnl.append(float(odds) - 1 if z > 1e-9 else -1. if z < -1e-9 else 0.)
    state = ('full_win' if all(x == 'W' for x in states) else 'full_loss' if all(x == 'L' for x in states)
             else 'push' if all(x == 'P' for x in states) else 'half_win' if 'W' in states else 'half_loss')
    return state, sum(pnl) / len(pnl)


def all_targets():
    rows = {}
    for p in read_jsonl(PATH49):
        fid = str(p['fid'])
        if fid in rows:
            raise ValueError(f'duplicate Original49 path FID {fid}')
        rows[fid] = {'fid': fid, 'league': str(p['league']), 'league_name': str(p['league']),
                     'line': float(p['end_line']), 'home_odds': float(p['home_price']),
                     'away_odds': float(p['away_price']), 'source_group': 'original49_T1',
                     'path_start_line': p.get('start_line')}
    if not EXPANDED.is_file():
        raise FileNotFoundError(f'Expected completed cross-league input from PR #68: {EXPANDED}')
    for p in (json.loads(x) for x in gzip.open(EXPANDED, 'rt', encoding='utf-8')):
        fid = str(p['fid'])
        if fid in rows:
            raise ValueError(f'Original49/expanded15 FID overlap: {fid}')
        rows[fid] = {'fid': fid, 'league': str(p['league']), 'league_name': str(p.get('league_name') or p['league']),
                     'line': float(p['end_line']), 'home_odds': float(p['home_price']),
                     'away_odds': float(p['away_price']), 'source_group': 'expanded15_T1',
                     'path_start_line': p.get('start_line')}
    return rows


def schedule_identity(target_fids, target_leagues):
    """Read-only provider IDs and FT from already cached TotalCorner pages."""
    found = collections.defaultdict(list)
    history = collections.defaultdict(list)
    pages = sorted(SCHEDULE_PAGES.glob('*/page-*.raw.json'))
    page_hashes = {}
    for page in pages:
        body = page.read_bytes()
        page_hashes[str(page)] = hashlib.sha256(body).hexdigest()
        try:
            matches = (json.loads(body).get('data') or {}).get('matches') or []
        except Exception:
            continue
        for m in matches:
            fid = str(m.get('id') or '')
            if str(m.get('l_id') or '') not in target_leagues or m.get('status') != 'full':
                continue
            try:
                ko = parse_ts(m['start'])
                rec = {'fid': fid, 'league': str(m['l_id']), 'home_id': str(m['h_id']), 'away_id': str(m['a_id']),
                       'home': str(m.get('h') or ''), 'away': str(m.get('a') or ''), 'hg': int(m['hg']), 'ag': int(m['ag']),
                       'kickoff_utc': ko.isoformat(), 'schedule_page_sha256': hashlib.sha256(body).hexdigest()}
                if not ko or not rec['home_id'] or not rec['away_id'] or rec['home_id'] == rec['away_id']:
                    continue
                history[fid].append(rec)
                if fid in target_fids:
                    found[fid].append(rec)
            except (TypeError, ValueError, KeyError):
                continue
    accepted = {}
    conflicts = set()
    for fid, vals in found.items():
        signatures = {(x['league'], x['home_id'], x['away_id'], x['hg'], x['ag'], x['kickoff_utc']) for x in vals}
        if len(signatures) == 1:
            accepted[fid] = vals[0]
        else:
            conflicts.add(fid)
    history_rows = {}
    history_conflicts = set()
    for fid, vals in history.items():
        signatures = {(x['league'], x['home_id'], x['away_id'], x['hg'], x['ag'], x['kickoff_utc']) for x in vals}
        if len(signatures) == 1:
            history_rows[fid] = vals[0]
        else:
            history_conflicts.add(fid)
    for fid in history_conflicts:
        history_rows.pop(fid, None)
    return accepted, {'cached_schedule_page_count': len(pages), 'cached_schedule_page_sha256': page_hashes,
                      'target_fids_seen': len(found), 'target_identity_conflicts': len(conflicts),
                      'target_complete_identity_fids': len(accepted),
                      'full_FT_history_fids': len(history_rows), 'full_FT_history_conflicts': len(history_conflicts)}, history_rows


def score_archive():
    out = {}
    for r in read_jsonl(SCORES49):
        fid = str(r['fid'])
        if fid in out:
            raise ValueError(f'duplicate score FID {fid}')
        out[fid] = r
    return out


def target_rows(targets, identity, scores, frozen_ids):
    rows = []
    counters = collections.Counter()
    for fid, p in targets.items():
        ident = identity.get(fid)
        s = scores.get(fid)
        if not ident:
            counters['no_cached_target_identity'] += 1
            continue
        if ident['league'] != p['league']:
            counters['target_league_mismatch'] += 1
            continue
        if s:
            if (str(s['league']), str(s['home']), str(s['away']), int(s['hg']), int(s['ag'])) != (
                    ident['league'], ident['home_id'], ident['away_id'], ident['hg'], ident['ag']):
                counters['score_identity_conflict'] += 1
                continue
        ko = parse_ts(ident['kickoff_utc'])
        local = ko.astimezone(TZ)
        if int(ident['hg']) < 0 or int(ident['ag']) < 0:
            counters['invalid_FT'] += 1
            continue
        for x in (p['line'], p['home_odds'], p['away_odds']):
            if not math.isfinite(float(x)):
                counters['invalid_Crown_price'] += 1
                break
        if p['home_odds'] <= 1 or p['away_odds'] <= 1 or abs(p['line'] * 4 - round(p['line'] * 4)) > 1e-8:
            counters['invalid_Crown_price'] += 1
            continue
        line, ho, ao = p['line'], p['home_odds'], p['away_odds']
        hstate, hu = settle(line, 'home', ident['hg'] - ident['ag'], ho)
        astate, au = settle(line, 'away', ident['hg'] - ident['ag'], ao)
        iso = local.date().isocalendar()
        rows.append({**ident, **p, 'year': local.year, 'date': local.date().isoformat(),
                     'kickoff_beijing': local.isoformat(), 'iso_week': f'{iso.year}-W{iso.week:02d}',
                     'gd': ident['hg'] - ident['ag'], 'frozen_eight_overlap': fid in frozen_ids,
                     'home_settlement': hstate, 'home_net_u': round(hu, 10),
                     'away_settlement': astate, 'away_net_u': round(au, 10),
                     'market_margin': -line + .25 * math.log(ao / ho)})
        counters['target_rows_with_T1_FT_identity'] += 1
    rows.sort(key=lambda r: (r['kickoff_beijing'], r['fid']))
    return rows, counters


def load_card_games(target_leagues):
    """Use existing historical Crown raw bodies; never infer missing cards as zero."""
    by_fid = {}
    conflicts = set()
    files = sorted(RAW_HIST.rglob('*.json'))
    stats = collections.Counter()
    for path in files:
        try:
            body = json.loads(path.read_bytes())
            d = body.get('data')
            d = d[0] if isinstance(d, list) and d else d
            if not isinstance(d, dict):
                stats['bad_body'] += 1
                continue
            league = str(d.get('l_id') or '')
            if league not in target_leagues:
                continue
            if d.get('status') != 'full':
                stats['not_full'] += 1
                continue
            fid = str(d.get('id') or '')
            ko = parse_ts(d.get('start'))
            if not fid or not ko:
                stats['missing_identity_or_time'] += 1
                continue
            try:
                hg, ag = int(d['hg']), int(d['ag'])
                rh, ra = int(d['hrc']), int(d['arc'])
            except (TypeError, ValueError, KeyError):
                stats['missing_goal_or_redcard'] += 1
                continue
            if min(hg, ag, rh, ra) < 0:
                stats['negative_goal_or_redcard'] += 1
                continue
            h, a = str(d.get('h_id') or ''), str(d.get('a_id') or '')
            if not h or not a or h == a:
                stats['missing_or_conflicting_team_id'] += 1
                continue
            record = {'fid': fid, 'league': league, 'home_id': h, 'away_id': a,
                      'date': ko.astimezone(TZ).date().isoformat(), 'kickoff_utc': ko.isoformat(),
                      'hg': hg, 'ag': ag, 'red_home': rh, 'red_away': ra,
                      'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'source_file': str(path)}
            old = by_fid.get(fid)
            signature = tuple(record[k] for k in ('league', 'home_id', 'away_id', 'date', 'hg', 'ag', 'red_home', 'red_away'))
            if old:
                old_sig = tuple(old[k] for k in ('league', 'home_id', 'away_id', 'date', 'hg', 'ag', 'red_home', 'red_away'))
                if signature != old_sig:
                    conflicts.add(fid)
                    stats['conflicting_duplicate_FID'] += 1
                else:
                    stats['identical_duplicate_FID'] += 1
                continue
            by_fid[fid] = record
        except Exception as e:
            stats[f'parse_error_{type(e).__name__}'] += 1
            continue
    for fid in conflicts:
        by_fid.pop(fid, None)
    stats['raw_historical_response_files_scanned'] = len(files)
    stats['unique_card_complete_fids'] = len(by_fid)
    stats['excluded_conflicting_fids'] = len(conflicts)
    return by_fid, dict(stats)


def histories(card_rows):
    out = collections.defaultdict(list)
    for r in card_rows.values():
        day = dt.date.fromisoformat(r['date']).toordinal()
        # Perspective feature: opponent sent-off minus this team sent-off.
        out[(r['league'], r['home_id'])].append((day, r['hg'] - r['ag'], r['red_away'] - r['red_home'], r['fid'], r['source_sha256']))
        out[(r['league'], r['away_id'])].append((day, r['ag'] - r['hg'], r['red_home'] - r['red_away'], r['fid'], r['source_sha256']))
    prepared = {}
    for key, seq in out.items():
        seq.sort(key=lambda x: (x[0], x[3]))
        days = [x[0] for x in seq]
        gd = np.cumsum([x[1] for x in seq], dtype=float)
        red = np.cumsum([x[2] for x in seq], dtype=float)
        prepared[key] = (seq, days, gd, red)
    return prepared


def get_card_stats(hist, league, team_id, target_date):
    if hist is None:
        return {'n': 0, 'gd_avg': None, 'red_adv_avg': None, 'last_gd': None, 'last_red_adv': None,
                'last_date': None, 'source_sha256': None}
    cutoff = dt.date.fromisoformat(target_date).toordinal() - LAG_DAYS
    start = cutoff - WINDOW_DAYS
    item = hist.get((str(league), str(team_id)))
    if not item:
        return {'n': 0, 'gd_avg': None, 'red_adv_avg': None, 'last_gd': None, 'last_red_adv': None,
                'last_date': None, 'source_sha256': None}
    seq, days, gd_c, red_c = item
    lo = int(np.searchsorted(days, start, side='left'))
    hi = int(np.searchsorted(days, cutoff, side='left'))
    n = hi - lo
    if n <= 0:
        return {'n': 0, 'gd_avg': None, 'red_adv_avg': None, 'last_gd': None, 'last_red_adv': None,
                'last_date': None, 'source_sha256': None}
    gd_sum = gd_c[hi - 1] - (gd_c[lo - 1] if lo else 0.)
    red_sum = red_c[hi - 1] - (red_c[lo - 1] if lo else 0.)
    last = seq[hi - 1]
    src = hashlib.sha256('\n'.join(f'{x[3]}:{x[4]}' for x in seq[lo:hi]).encode()).hexdigest()
    return {'n': n, 'gd_avg': float(gd_sum / n), 'red_adv_avg': float(red_sum / n),
            'last_gd': float(last[1]), 'last_red_adv': float(last[2]),
            'last_date': dt.date.fromordinal(last[0]).isoformat(), 'source_sha256': src}


def all_score_histories(schedule_rows, card_rows):
    """Use all already-cached completed schedule rows; card data remains separate."""
    matches = {}
    for r in schedule_rows.values():
        matches[r['fid']] = {'fid': r['fid'], 'league': r['league'], 'home_id': r['home_id'], 'away_id': r['away_id'],
                             'date': dt.datetime.fromisoformat(r['kickoff_utc']).astimezone(TZ).date().isoformat(),
                             'hg': r['hg'], 'ag': r['ag']}
    for fid, c in card_rows.items():
        old = matches.get(fid)
        if old and (old['league'], old['home_id'], old['away_id'], old['hg'], old['ag']) != (c['league'], c['home_id'], c['away_id'], c['hg'], c['ag']):
            continue
        if not old:
            matches[fid] = {'fid': fid, 'league': c['league'], 'home_id': c['home_id'], 'away_id': c['away_id'],
                            'date': c['date'], 'hg': c['hg'], 'ag': c['ag'], 'has_red': True}
    out = collections.defaultdict(list)
    for r in matches.values():
        day = dt.date.fromisoformat(r['date']).toordinal()
        out[(r['league'], r['home_id'])].append((day, r['hg'] - r['ag'], r['fid']))
        out[(r['league'], r['away_id'])].append((day, r['ag'] - r['hg'], r['fid']))
    return {k: sorted(v) for k, v in out.items()}, len(matches)


def get_raw_form(form_hist, league, team_id, target_date):
    cutoff = dt.date.fromisoformat(target_date).toordinal() - LAG_DAYS
    start = cutoff - WINDOW_DAYS
    seq = form_hist.get((str(league), str(team_id)), [])
    days = [x[0] for x in seq]
    lo = int(np.searchsorted(days, start, side='left'))
    hi = int(np.searchsorted(days, cutoff, side='left'))
    n = hi - lo
    if n <= 0:
        return {'n': 0, 'gd_avg': None, 'last_gd': None, 'last_date': None}
    return {'n': n, 'gd_avg': float(sum(x[1] for x in seq[lo:hi]) / n),
            'last_gd': float(seq[hi - 1][1]), 'last_date': dt.date.fromordinal(seq[hi - 1][0]).isoformat()}


def ridge_predict(x_train, y_train, x_test):
    x_train = np.asarray(x_train, float); x_test = np.asarray(x_test, float); y_train = np.asarray(y_train, float)
    mu = x_train.mean(0); sd = x_train.std(0); sd[sd < 1e-10] = 1.
    z = (x_train - mu) / sd; zt = (x_test - mu) / sd
    design = np.column_stack([np.ones(len(z)), z]); test = np.column_stack([np.ones(len(zt)), zt])
    penalty = np.eye(design.shape[1]) * ALPHA; penalty[0, 0] = 0.
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ y_train)
    return test @ coef, {'mean': mu.tolist(), 'scale': sd.tolist(), 'coef_intercept_first': coef.tolist(), 'train_n': len(y_train)}


def summarize(rows, method):
    bets = [r for r in rows if r.get('methods', {}).get(method, {}).get('side')]
    pnl = sum(r['methods'][method]['net_u'] for r in bets)
    byday = collections.defaultdict(float); weeks = collections.Counter(); leagues = collections.Counter(); years = collections.Counter()
    for r in bets:
        byday[r['date']] += r['methods'][method]['net_u']; weeks[r['iso_week']] += 1
        leagues[r['league_name']] += r['methods'][method]['net_u']; years[str(r['year'])] += r['methods'][method]['net_u']
    cum = peak = mdd = 0.
    for d in sorted(byday):
        cum += byday[d]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    n = len(bets)
    return {'orders': n, 'net_u': round(pnl, 6), 'roi_pct': round(100 * pnl / n, 6) if n else None,
            'mdd_u': round(mdd, 6), 'average_decimal_odds': round(sum(r['methods'][method]['odds'] for r in bets) / n, 6) if n else None,
            'settlements': dict(collections.Counter(r['methods'][method]['settlement'] for r in bets)),
            'active_iso_weeks': len(weeks), 'active_week_avg': round(n / len(weeks), 6) if weeks else 0.,
            'weekly': {k: {'n': v, 'net_u': round(sum(r['methods'][method]['net_u'] for r in bets if r['iso_week'] == k), 6)} for k, v in sorted(weeks.items())},
            'league': {k: round(v, 6) for k, v in sorted(leagues.items())},
            'year_net_u': dict(sorted(years.items()))}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    targets = all_targets(); target_fids = set(targets)
    target_leagues = {r['league'] for r in targets.values()}
    identity, schedule_audit, schedule_history = schedule_identity(target_fids, target_leagues)
    scores = score_archive()
    frozen_ids = {str(r['fid']) for r in read_jsonl(FROZEN)}
    target, target_audit = target_rows(targets, identity, scores, frozen_ids)
    target_leagues = {r['league'] for r in target}
    card_rows, card_audit = load_card_games(target_leagues)
    # Store a compact, independently auditable Crown raw source index.
    with gzip.open(OUT / 'red_card_history_source_index.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in sorted(card_rows.values(), key=lambda z: (z['date'], z['fid'])):
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    card_hist = histories(card_rows)
    form_hist, form_match_count = all_score_histories(schedule_history, card_rows)
    # Preserve all target rows with two prior score observations. Missing card
    # coverage is represented by null + explicit count and coverage flag.
    feature_rows = []
    feature_missing = collections.Counter()
    for r in target:
        hraw = get_raw_form(form_hist, r['league'], r['home_id'], r['date'])
        araw = get_raw_form(form_hist, r['league'], r['away_id'], r['date'])
        if hraw['n'] <= 0 or araw['n'] <= 0:
            feature_missing['no_prior_full_score_history_for_a_side'] += 1
            continue
        hc = get_card_stats(card_hist, r['league'], r['home_id'], r['date'])
        ac = get_card_stats(card_hist, r['league'], r['away_id'], r['date'])
        r['raw_form'] = {'home': hraw, 'away': araw}
        r['card_form'] = {'home': hc, 'away': ac}
        feature_rows.append(r)
    # Beta is fit separately inside each forward fold from prior card-complete
    # games only. It estimates score-margin association with net red-card
    # advantage; it is not claimed to be causal.
    folds = {}; scored = []
    for year in (2024, 2025, 2026):
        train = [r for r in feature_rows if 2019 <= r['year'] < year]
        test = [r for r in feature_rows if r['year'] == year]
        if not train or not test:
            continue
        prior_card_games = [r for r in card_rows.values() if 2019 <= int(r['date'][:4]) < year]
        red_adv = np.asarray([r['red_away'] - r['red_home'] for r in prior_card_games] +
                             [r['red_home'] - r['red_away'] for r in prior_card_games], float)
        goals = np.asarray([r['hg'] - r['ag'] for r in prior_card_games] +
                           [r['ag'] - r['hg'] for r in prior_card_games], float)
        denom = float(red_adv @ red_adv)
        beta = float(red_adv @ goals / denom) if denom > 0 else 0.
        def feature(r, kind):
            hr, ar = r['raw_form']['home'], r['raw_form']['away']
            hc, ac = r['card_form']['home'], r['card_form']['away']
            raw_h, raw_a = hr['gd_avg'], ar['gd_avg']
            delta_h = -beta * hc['red_adv_avg'] if hc['red_adv_avg'] is not None else 0.
            delta_a = -beta * ac['red_adv_avg'] if ac['red_adv_avg'] is not None else 0.
            n_h, n_a = hc['n'], ac['n']
            red_gap = (hc['red_adv_avg'] or 0.) - (ac['red_adv_avg'] or 0.)
            red_missing_h, red_missing_a = int(n_h == 0), int(n_a == 0)
            base = [r['market_margin'], r['line'], .25 * math.log(r['away_odds'] / r['home_odds'])]
            raw = [raw_h, raw_a, raw_h - raw_a, raw_h + raw_a,
                   hr['last_gd'], ar['last_gd'], math.log1p(hr['n']), math.log1p(ar['n'])]
            adjusted = [raw_h + delta_h, raw_a + delta_a, (raw_h + delta_h) - (raw_a + delta_a),
                        (raw_h + delta_h) + (raw_a + delta_a), delta_h, delta_a]
            context = [red_gap, math.log1p(n_h), math.log1p(n_a), red_missing_h, red_missing_a,
                       (n_h / max(hr['n'], 1)), (n_a / max(ar['n'], 1))]
            if kind == 'market': return base
            if kind == 'market_plus_raw_form': return base + raw
            if kind == 'market_plus_red_adjusted_form': return base + adjusted + context
            if kind == 'market_plus_raw_and_red_context': return base + raw + adjusted + context
            if kind == 'low_price': return base
            raise KeyError(kind)
        labels = {r['fid']: r['home_net_u'] - r['away_net_u'] for r in train + test}
        fold_info = {'year': year, 'train_n': len(train), 'test_n': len(test),
                     'training_years': sorted({r['year'] for r in train}), 'ridge_alpha': ALPHA,
                     'lag_days': LAG_DAYS, 'history_days': WINDOW_DAYS,
                     'beta_red_adv_to_goal_diff': beta, 'beta_training_card_games': len(prior_card_games),
                     'target_red_history_missing_home': sum(r['card_form']['home']['n'] == 0 for r in test),
                     'target_red_history_missing_away': sum(r['card_form']['away']['n'] == 0 for r in test),
                     'models': {}}
        for method in METHODS:
            if method == 'low_price':
                for r in test:
                    side = 'home' if r['home_odds'] <= r['away_odds'] else 'away'
                    odds = r[f'{side}_odds']
                    state = r[f'{side}_settlement']; pnl = r[f'{side}_net_u']
                    r.setdefault('methods', {})[method] = {'side': side, 'odds': odds, 'settlement': state, 'net_u': pnl}
                fold_info['models'][method] = {'status': 'fixed lower-decimal-price side baseline'}
                continue
            xtr = [feature(r, method) for r in train]
            xte = [feature(r, method) for r in test]
            preds, model = ridge_predict(xtr, [labels[r['fid']] for r in train], xte)
            fold_info['models'][method] = model
            for r, pred in zip(test, preds):
                side = 'home' if float(pred) > 0 else 'away'
                r.setdefault('methods', {})[method] = {'side': side, 'odds': r[f'{side}_odds'],
                                                       'settlement': r[f'{side}_settlement'],
                                                       'net_u': r[f'{side}_net_u'], 'predicted_home_minus_away_pnl': float(pred)}
        folds[str(year)] = fold_info
        scored.extend(test)
    scored.sort(key=lambda r: (r['kickoff_beijing'], r['fid']))
    outside = [r for r in scored if not r['frozen_eight_overlap']]
    page_hashes = schedule_audit.pop('cached_schedule_page_sha256')
    (OUT / 'schedule_page_sha256_manifest.json').write_text(json.dumps(page_hashes, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    summary = {'study': 'M8_RED_CARD_ADJUSTED_TEAM_FORM_CROWN_AH',
               'inputs': {str(p): sha(p) for p in (PATH49, SCORES49, FROZEN, EXPANDED, RECEIPTS)},
               'coverage': {'original49_path_fids': sum(r['source_group'] == 'original49_T1' for r in targets.values()),
                            'expanded15_complete_T6_T3_T1_fids': sum(r['source_group'] == 'expanded15_T1' for r in targets.values()),
                            'combined_unique_target_fids': len(targets), **schedule_audit, **target_audit,
                            'raw_history_unique_card_fids': len(card_rows), 'raw_history_card_audit': card_audit,
                            'score_form_match_count': form_match_count, 'schedule_page_sha256_manifest': sha(OUT / 'schedule_page_sha256_manifest.json'),
                            'feature_rows': len(feature_rows),
                            'feature_missing': dict(feature_missing), 'scored_2024_2026_rows': len(scored),
                            'outside_frozen_unique_candidate_fids': len(outside),
                            'candidate_receipt_overlap': None},
               'methodology': {'Crown_price': 'Original49 precomputed full-path T1; expanded15 exact T6/T3/T1 event replay T1; historical source-event replay only.',
                               'form': 'Trailing 365-day completed-match goal difference by provider league/team ID, cutoff before target Beijing date minus 3 days; 0 card matches is represented as missing delta plus explicit missing indicator, not as zero red cards.',
                               'red_adjustment': 'Per training fold, estimate beta from prior-year Crown card-complete records: sum(net red advantage * goal difference) / sum(net red advantage squared); adjust team form by subtracting beta times average opponent-red-minus-team-red. This is associational, not causal.',
                               'training': '2024 uses target rows before 2024; 2025 before 2025; 2026 before 2026. Ridge alpha=100, fold-local standardization; target label is home AH netU minus away AH netU at the actual Crown line and prices; choose larger predicted payoff, no EV gate.',
                               'AH settlement': 'Each side settled from Crown handicap and decimal price; quarter-lines split into two equal stakes.',
                               'time_status': 'Crown quotes are historical event-time replays. Card information has no verified historical publication/receipt time. No real receipt profit claim.'},
               'folds': folds,
               'outside_frozen_eight': {m: summarize(outside, m) for m in METHODS},
               'same_period_frozen_eight': {}, 'merged_with_frozen_eight': {},
               'formal_orders': 0, 'formal_ledger_writes': 0, 'production_changes': 0, 'crown_api_requests': 0}
    frozen_by_year = [r for r in read_jsonl(FROZEN) if int(r['year']) in (2024, 2025, 2026)]
    frozen_pnl = {str(r['fid']): {'date': str(r['date'])[:10], 'net_u': float(r['pnl'])} for r in frozen_by_year}
    summary['same_period_frozen_eight'] = {'orders': len(frozen_pnl), 'net_u': round(sum(r['net_u'] for r in frozen_pnl.values()), 6)}
    for method in METHODS:
        chosen = [r for r in outside if r['methods'][method]['side']]
        union = dict(frozen_pnl)
        duplicate = set(union) & {r['fid'] for r in chosen}
        if duplicate:
            raise ValueError(f'candidate overlap with frozen FIDs: {len(duplicate)}')
        union.update({r['fid']: {'date': r['date'], 'net_u': r['methods'][method]['net_u']} for r in chosen})
        summary['merged_with_frozen_eight'][method] = {'orders': len(union), 'net_u': round(sum(x['net_u'] for x in union.values()), 6),
                                                       'roi_pct': round(100 * sum(x['net_u'] for x in union.values()) / len(union), 6),
                                                       'incremental_net_u': round(sum(r['methods'][method]['net_u'] for r in chosen), 6),
                                                       'frozen_overlap': len(duplicate)}
    # Match target T1 prices to stored Crown source event and preserve receive time.
    cx = sqlite3.connect(f'file:{SQLITE}?mode=ro', uri=True); cx.row_factory = sqlite3.Row
    byfid = collections.defaultdict(list); fids = list(targets)
    for i in range(0, len(fids), 700):
        chunk = fids[i:i+700]; marks = ','.join('?' for _ in chunk)
        q = f'''SELECT q.fixture_id,q.handicap_home,q.home_decimal,q.away_decimal,q.quote_source_at_utc,
                       q.response_received_at_utc,c.capture_mode,c.response_sha256,c.prospective_observation
                FROM asian_quote q JOIN capture c USING(capture_key)
                WHERE q.fixture_id IN ({marks}) AND c.data_layer='movement' AND q.quote_kind='movement'
                ORDER BY q.fixture_id,q.quote_source_at_utc,q.response_received_at_utc'''
        for x in cx.execute(q, chunk):
            byfid[str(x['fixture_id'])].append(dict(x))
    cx.close()
    quote_audit = collections.Counter(); receipt_fids = set()
    for r in scored:
        ko = parse_ts(r['kickoff_utc']); cutoff = ko - dt.timedelta(hours=1)
        eligible = []
        for q in byfid.get(r['fid'], []):
            ts = parse_ts(q.get('quote_source_at_utc'))
            try:
                if ts and ts <= cutoff and abs(float(q['handicap_home']) * 4 - round(float(q['handicap_home']) * 4)) < 1e-8:
                    eligible.append((ts, q))
            except (TypeError, ValueError):
                continue
        if not eligible:
            r['t1_source_event_at_utc'] = None; r['t1_response_received_at_utc'] = None; r['t1_capture_mode'] = None
            quote_audit['no_sqlite_quote_at_or_before_T1'] += 1
        else:
            ts, q = eligible[-1]
            match = (abs(float(q['handicap_home']) - r['line']) < 1e-8 and abs(float(q['home_decimal']) - r['home_odds']) < 1e-8 and abs(float(q['away_decimal']) - r['away_odds']) < 1e-8)
            r['t1_source_event_at_utc'] = ts.isoformat(); r['t1_response_received_at_utc'] = q['response_received_at_utc']; r['t1_capture_mode'] = q['capture_mode']
            r['t1_source_response_sha256'] = q['response_sha256']; r['t1_quote_matches_path_price'] = bool(match)
            quote_audit['sqlite_T1_event_match' if match else 'sqlite_T1_price_mismatch'] += 1
            if q.get('prospective_observation'):
                receipt_fids.add(r['fid'])
    summary['coverage']['sqlite_t1_source_audit'] = dict(quote_audit)
    summary['coverage']['sqlite_prospective_candidate_fids'] = len(set(r['fid'] for r in outside) & receipt_fids)
    receipt_rows = [json.loads(line) for line in RECEIPTS.open(encoding='utf-8') if line.strip()]
    receipt_by_fid = collections.defaultdict(list)
    scored_by_fid = {r['fid']: r for r in scored}
    outside_ids = {r['fid'] for r in outside}
    t1_receipt_fids = set(); t1_exact_price_fids = set(); valid_receipt_fids = set()
    for receipt in receipt_rows:
        fid = str(receipt.get('fixture_id') or '')
        if fid not in scored_by_fid or 'AH' not in (receipt.get('markets') or {}):
            continue
        row = scored_by_fid[fid]
        received = parse_ts(receipt.get('received_utc')); kickoff = parse_ts(row['kickoff_utc'])
        if received is None or kickoff is None or received >= kickoff:
            continue
        valid_receipt_fids.add(fid); receipt_by_fid[fid].append(receipt)
        if receipt.get('snapshot_horizon') == 'T1' and fid in outside_ids:
            t1_receipt_fids.add(fid)
            q = receipt['markets']['AH']
            if (abs(float(q['line']) - row['line']) < 1e-8 and
                    abs(float(q['odds']['home']) - row['home_odds']) < 1e-8 and
                    abs(float(q['odds']['away']) - row['away_odds']) < 1e-8):
                t1_exact_price_fids.add(fid)
    summary['coverage']['candidate_receipt_overlap'] = len(outside_ids & valid_receipt_fids)
    summary['coverage']['actual_Crown_HTTP_receipt_audit'] = {
        'archive_path': str(RECEIPTS), 'archive_sha256': sha(RECEIPTS),
        'archive_rows': len(receipt_rows), 'archive_unique_fids': len({str(x.get('fixture_id')) for x in receipt_rows}),
        'OOS_target_receipt_fids_before_kickoff': len(valid_receipt_fids),
        'outside_frozen_eight_receipt_fids': len(outside_ids & valid_receipt_fids),
        'outside_frozen_eight_T1_receipt_fids': len(t1_receipt_fids),
        'outside_frozen_eight_T1_receipt_exact_path_price_fids': len(t1_exact_price_fids),
        'true_live_feature_snapshot_verified': 0,
    }
    # Export complete per-fixture features and settlement ledger (research only).
    with gzip.open(OUT / 'red_card_adjusted_form_per_fixture.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in scored:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    (OUT / 'red_card_adjusted_form_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'coverage': summary['coverage'], 'outside_frozen_eight': {m: {k: v[k] for k in ('orders','net_u','roi_pct','mdd_u','active_week_avg')} for m,v in summary['outside_frozen_eight'].items()}, 'merged': summary['merged_with_frozen_eight']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
