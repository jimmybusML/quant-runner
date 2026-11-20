#!/usr/bin/env python3
"""Time-forward M8 research: prior home-attendance/crowd information vs Crown AH.

This is an exploratory historical replay. It never reads target-match attendance,
target lineup, target manager, target outcome or future M8 membership as a feature.
The source archive has no per-row first-published/received timestamps, so this is
not a prospective-information claim or a production rule.
"""
from __future__ import annotations

import bisect
import collections
import csv
import datetime as dt
import difflib
import gzip
import hashlib
import json
import math
import pathlib
import re
import statistics
import sys
import unicodedata

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
sys.path.insert(0, str(ROOT))
DATA = WORK / 'm8_pregame_info_source_20261117'
GAME_FILE = DATA / 'games.csv.gz'
INVENTORY = WORK / 'm8_early_joint_market_inventory_20261115.jsonl'
FOUNDATION = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPT_ARCHIVE = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MARKET_BOOTSTRAP = WORK / 'm8_early_exact_cross_market_consistency_20261115.py'
COMPETITION_MAP = {
    '1':'GB1', '12':'IT1', '14':'ES1', '16':'L1', '25':'FR1', '29':'A1',
    '31':'BE1', '35':'TS1', '37':'NL1', '48':'PL1', '51':'PO1', '52':'RO1',
    '61':'C1', '62':'TR1', '66':'SE1', '70':'DK1', '73':'JAP1', '75':'RSK1',
    '88':'NO1', '141':'GR1', '262':'SC1', '290':'SA1', '303':'SER1',
    '319':'UKR1', '26540':'KR1',
}
YEAR_CUTOFF = (2024, 2025, 2026)
MIN_ATTENDANCE_MATCHES = 3
LOOKBACK_DAYS = 730
LAG_DAYS = 3
RIDGE_ALPHA = 100.0


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_jsonl(path: pathlib.Path) -> list[dict]:
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def quarter_settle(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[float, str]:
    line, odds = float(line), float(odds)
    if abs(line * 4 - round(line * 4)) > 1e-8:
        raise ValueError(f'line outside quarter grid: {line}')
    if abs(line * 2 - round(line * 2)) < 1e-8:
        legs = [line]
    else:
        legs = [math.floor(line * 2) / 2, math.ceil(line * 2) / 2]
    pnls = []
    for leg in legs:
        adj = hg - ag + leg if side == 'home' else ag - hg - leg
        pnls.append(odds - 1 if adj > 1e-9 else -1.0 if adj < -1e-9 else 0.0)
    pnl = sum(pnls) / len(pnls)
    if all(x > 0 for x in pnls): label = 'full_win'
    elif any(x > 0 for x in pnls): label = 'half_win'
    elif all(x == 0 for x in pnls): label = 'push'
    elif any(x == 0 for x in pnls): label = 'half_loss'
    else: label = 'full_loss'
    return pnl, label


def weekly_key(day: str) -> str:
    d = dt.date.fromisoformat(day)
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'


def normalize(s: str) -> str:
    x = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii').lower()
    x = re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|as)\b', ' ', x)
    return re.sub(r'[^a-z0-9]', '', x)


def sim(a: str, b: str) -> float:
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if min(len(a), len(b)) >= 6 and (a in b or b in a):
        return 0.91
    return difflib.SequenceMatcher(None, a, b).ratio()


def stats(rows: list[dict]) -> dict:
    if not rows:
        return {'n': 0, 'net_U': 0.0, 'ROI_pct': None, 'MDD_U': 0.0,
                'weekly': {}, 'weekly_n': 0, 'settlement': {}}
    daily = collections.defaultdict(float)
    weekly = collections.defaultdict(lambda: {'n': 0, 'net_U': 0.0})
    settlement = collections.Counter()
    for r in rows:
        daily[r['date']] += r['net_u']
        w = weekly[weekly_key(r['date'])]
        w['n'] += 1
        w['net_U'] += r['net_u']
        settlement[r['settlement']] += 1
    net = sum(r['net_u'] for r in rows)
    peak = balance = mdd = 0.0
    for day in sorted(daily):
        balance += daily[day]
        peak = max(peak, balance)
        mdd = max(mdd, peak - balance)
    weekly = {k: {'n': v['n'], 'net_U': round(v['net_U'], 6)} for k, v in sorted(weekly.items())}
    return {'n': len(rows), 'net_U': round(net, 6),
            'ROI_pct': round(net / len(rows) * 100, 6), 'MDD_U': round(mdd, 6),
            'weekly': weekly, 'weekly_n': len(weekly),
            'settlement': dict(settlement)}


def model_predict(X: np.ndarray, y: np.ndarray, years: np.ndarray, league_ids: list[str],
                  features: list[int], use_market: bool) -> tuple[np.ndarray, dict]:
    pred = np.full(len(y), np.nan)
    meta = {}
    for year in YEAR_CUTOFF:
        tr = years < year
        te = years == year
        if tr.sum() == 0 or not te.any():
            continue
        xtr = X[tr][:, features]
        xte = X[te][:, features]
        mu = xtr.mean(axis=0)
        sd = xtr.std(axis=0)
        sd[sd < 1e-12] = 1.0
        a = (xtr - mu) / sd
        b = (xte - mu) / sd
        # Fixed ridge penalty inherited from prior M8 independent-info work;
        # alpha is documented and not selected using target-year results.
        penalty = np.eye(a.shape[1]) * RIDGE_ALPHA
        beta = np.linalg.solve(a.T @ a + penalty, a.T @ y[tr])
        pred[te] = b @ beta
        meta[str(year)] = {'train_n': int(tr.sum()), 'test_n': int(te.sum()),
                           'feature_n': len(features), 'uses_market': use_market,
                           'league_levels_train': sorted(set(np.array(league_ids, dtype=object)[tr]))}
    return pred, meta


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not all(p.exists() for p in (GAME_FILE, INVENTORY, FOUNDATION, MARKET_BOOTSTRAP)):
        raise FileNotFoundError('required local existing M8 input missing')

    # Load the already-used M8/Crown and M5 identity bridge without executing its
    # model loop/output section. This recreates fixture identity only; our features
    # below never use score or target-match attendance to resolve predictions.
    market_src = MARKET_BOOTSTRAP.read_text(encoding='utf-8')
    market_prefix = market_src.split('C=collections.Counter();rows=[]')[0]
    bootstrap_ns = {'__name__': '__m8_attendance_bootstrap__'}
    exec(compile(market_prefix, str(MARKET_BOOTSTRAP) + '[prefix]', 'exec'), bootstrap_ns)
    crown_jobs = bootstrap_ns['jobs']
    cm = COMPETITION_MAP

    # Static team identity crosswalk: fuzzy-match names within an explicit
    # league/competition pair, with uniqueness and margin requirements. No score,
    # result or target-date outcome participates in this research crosswalk.
    ext_games = list(csv.DictReader(gzip.open(GAME_FILE, 'rt', encoding='utf-8')))
    comp_club_names: dict[str, dict[str, set[str]]] = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in ext_games:
        comp = str(r.get('competition_id') or '')
        if comp not in set(cm.values()):
            continue
        for side in ('home', 'away'):
            cid = str(r.get(side + '_club_id') or '')
            name = str(r.get(side + '_club_name') or '').strip()
            if cid and name:
                comp_club_names[comp][cid].add(name)

    crown_team_names: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    inventory_rows = load_jsonl(INVENTORY)
    raw_errors = collections.Counter()
    raw_fixture_identity: dict[str, dict] = {}
    raw_quote_audit = collections.Counter()
    for r in inventory_rows:
        if int(r.get('T', -1)) != 12:
            continue
        fid = str(r['fid'])
        job = crown_jobs.get(fid)
        if not job:
            raw_errors['no_M5_raw_response_index'] += 1
            continue
        file, expected_sha, expected_league = job
        try:
            raw_bytes = file.read_bytes()
            if expected_sha and hashlib.sha256(raw_bytes).hexdigest() != expected_sha:
                raw_errors['raw_sha_mismatch'] += 1
                continue
            matches = json.loads(raw_bytes)['data']
            x = next(q for q in matches if str(q.get('id')) == fid)
            if str(x.get('l_id')) != str(r['league']) or str(expected_league) != str(r['league']):
                raw_errors['league_identity_mismatch'] += 1
                continue
            if str(x.get('h_id')) != str(r['home_id']) or str(x.get('a_id')) != str(r['away_id']):
                raw_errors['team_id_mismatch'] += 1
                continue
            if x.get('status') != 'full' or int(x.get('hg')) != int(r['hg']) or int(x.get('ag')) != int(r['ag']):
                raw_errors['FT_mismatch'] += 1
                continue
            # Reconstruct T-12 AH independently from the original Crown payload.
            kickoff_utc = bootstrap_ns['dt'](x['start'])
            cut = kickoff_utc - dt.timedelta(hours=12)
            bookmaker = next(q for q in x.get('bookmakers', []) if q.get('slug') == 'crown')
            quote_path = []
            for q in bookmaker.get('asian_list') or []:
                try:
                    source_time = bootstrap_ns['dt'](q[4])
                    line, hprice, aprice = map(float, q[1:4])
                    if source_time < kickoff_utc and source_time <= cut and hprice > 1 and aprice > 1 and abs(line*4-round(line*4)) < 1e-7:
                        quote_path.append((source_time, True, line, hprice, aprice, 'movement'))
                except Exception:
                    continue
            asian_dict = bookmaker.get('asian') or {}
            for tag in ('open', 'close'):
                q = asian_dict.get(tag)
                if not isinstance(q, dict):
                    continue
                try:
                    source_time = bootstrap_ns['dt'](q['time'])
                    line, hprice, aprice = float(q['line']), float(q['home']), float(q['away'])
                    if source_time < kickoff_utc and source_time <= cut and hprice > 1 and aprice > 1 and abs(line*4-round(line*4)) < 1e-7:
                        quote_path.append((source_time, False, line, hprice, aprice, tag))
                except Exception:
                    continue
            quote_path.sort(key=lambda v: (v[0], v[1]))
            if not quote_path:
                raw_quote_audit['no_t12_or_earlier_crown_AH'] += 1
                continue
            selected_quote = quote_path[-1]
            source_time, _, raw_line, raw_home_odds, raw_away_odds, quote_kind = selected_quote
            if (abs(raw_line-float(r['al'])) > 1e-8 or abs(raw_home_odds-float(r['ah'])) > 1e-8 or
                    abs(raw_away_odds-float(r['aa'])) > 1e-8):
                raw_quote_audit['T12_contract_mismatch'] += 1
                continue
            raw_quote_audit['T12_contract_match'] += 1
            if str(x.get('h') or '').strip():
                crown_team_names[(str(r['league']), str(r['home_id']))].add(str(x['h']).strip())
            if str(x.get('a') or '').strip():
                crown_team_names[(str(r['league']), str(r['away_id']))].add(str(x['a']).strip())
            raw_fixture_identity[fid] = {
                'raw_sha256': hashlib.sha256(raw_bytes).hexdigest(),
                'league_id': str(x['l_id']), 'home_id': str(x['h_id']), 'away_id': str(x['a_id']),
                'kickoff_source': str(x.get('start') or ''),
                'home_ft': int(x['hg']), 'away_ft': int(x['ag']),
                't12_line_home': raw_line, 't12_home_decimal': raw_home_odds,
                't12_away_decimal': raw_away_odds, 't12_source_event_utc': source_time.isoformat(),
                't12_quote_kind': quote_kind,
                'home_name': str(x.get('h') or ''), 'away_name': str(x.get('a') or ''),
                'raw_path': str(file),
            }
        except Exception as e:
            raw_errors['raw_read_' + type(e).__name__] += 1

    candidate_maps: dict[tuple[str, str], tuple[str, float, float]] = {}
    map_reasons = collections.Counter()
    for (league, crown_id), names in crown_team_names.items():
        comp = cm.get(league)
        if not comp:
            map_reasons['unmapped_crown_league'] += 1
            continue
        scores = []
        for tm_id, tm_names in comp_club_names.get(comp, {}).items():
            s = max((sim(a, b) for a in names for b in tm_names), default=0.0)
            scores.append((s, tm_id))
        scores.sort(reverse=True)
        if not scores or scores[0][0] < 0.91:
            map_reasons['no_name_match'] += 1
            continue
        second = scores[1][0] if len(scores) > 1 else -1.0
        if scores[0][0] - second < 0.04:
            map_reasons['ambiguous_name_match'] += 1
            continue
        candidate_maps[(league, crown_id)] = (scores[0][1], float(scores[0][0]), float(second))
    reverse_map: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for (league, crown_id), (tm_id, _, _) in candidate_maps.items():
        reverse_map[(league, tm_id)].add(crown_id)
    team_map = {k: v for k, v in candidate_maps.items() if len(reverse_map[(k[0], v[0])]) == 1}
    map_reasons['non_bijective_excluded'] = len(candidate_maps) - len(team_map)

    # Prior home-match crowd records; target match attendance is never read here.
    attendance_history: dict[str, list[tuple[int, int, str, str]]] = collections.defaultdict(list)
    invalid_attendance = collections.Counter()
    for r in ext_games:
        try:
            day = dt.date.fromisoformat(r['date']).toordinal()
            club = str(r['home_club_id'] or '')
            att_s = str(r.get('attendance') or '').strip()
            if not club or not att_s:
                invalid_attendance['missing'] += 1
                continue
            att = int(att_s)
            if att <= 0:
                invalid_attendance['nonpositive'] += 1
                continue
            attendance_history[club].append((day, att, str(r.get('stadium') or ''), str(r.get('competition_id') or '')))
        except Exception:
            invalid_attendance['invalid_row'] += 1
    for vals in attendance_history.values():
        vals.sort(key=lambda x: x[0])
    hist_days = {k: [x[0] for x in vals] for k, vals in attendance_history.items()}

    def team_crowd(tm_id: str, target_day: int) -> dict | None:
        vals = attendance_history.get(tm_id, [])
        days = hist_days.get(tm_id, [])
        cutoff = target_day - LAG_DAYS
        end = bisect.bisect_right(days, cutoff)
        start = bisect.bisect_left(days, target_day - LOOKBACK_DAYS, 0, end)
        prior = vals[start:end]
        if len(prior) < MIN_ATTENDANCE_MATCHES:
            return None
        last3 = prior[-3:]
        prev3 = prior[-6:-3] if len(prior) >= 6 else None
        recent = [math.log1p(x[1]) for x in last3]
        out = {
            'log_mean_last3': float(np.mean(recent)),
            'log_last_attendance': math.log1p(prior[-1][1]),
            'log_count_prior_365d': math.log1p(sum(x[0] >= target_day - 365 for x in prior)),
            'venue_repeat_last3': sum(1 for x in last3 if x[2] and x[2] == last3[-1][2]) / 3.0 if last3[-1][2] else 0.0,
            'feature_age_days': target_day - prior[-1][0],
            'n_prior_home_with_attendance_730d': len(prior),
        }
        if prev3 is not None:
            out['log_trend_3v3'] = float(np.mean(recent) - np.mean([math.log1p(x[1]) for x in prev3]))
        return out

    # Read one T12 row per FID and attach exact verified raw quote/identity facts.
    raw_rows = {}
    for r in inventory_rows:
        if int(r.get('T', -1)) != 12 or str(r['fid']) not in raw_fixture_identity:
            continue
        fid = str(r['fid'])
        raw_rows[fid] = r
    frozen = {str(r.get('fid') or r.get('match_id')) for r in load_jsonl(FOUNDATION)}
    fixture_rows = []
    coverage_reasons = collections.Counter()
    for fid, r in raw_rows.items():
        ident = raw_fixture_identity[fid]
        date = str(r['date'])
        target_day = dt.date.fromisoformat(date).toordinal()
        league = str(r['league'])
        hm = team_map.get((league, str(r['home_id'])))
        am = team_map.get((league, str(r['away_id'])))
        reason = None
        hf = team_crowd(hm[0], target_day) if hm else None
        af = team_crowd(am[0], target_day) if am else None
        if not hm or not am:
            reason = 'team_name_crosswalk_missing'
        elif hf is None or af is None:
            reason = 'insufficient_prior_home_attendance'
        market_line = float(r['al'])
        home_odds, away_odds = float(r['ah']), float(r['aa'])
        if market_line == 0.0:
            market_side = 'home' if home_odds <= away_odds else 'away'
        else:
            market_side = 'home' if market_line < 0 else 'away'
        # Independent re-settlement directly from the raw Crown FT and T12 price.
        raw_home, label_home = quarter_settle(market_line, 'home', ident['home_ft'], ident['away_ft'], home_odds)
        raw_away, label_away = quarter_settle(market_line, 'away', ident['home_ft'], ident['away_ft'], away_odds)
        if abs(raw_home - float(r['home_U'])) > 1e-9 or abs(raw_away - float(r['away_U'])) > 1e-9:
            raise AssertionError(f'AH T12 settlement mismatch {fid}')
        row = {
            'fid': fid, 'date': date, 'year': int(r['year']), 'iso_week': weekly_key(date),
            'league_id': league, 'home_id': str(r['home_id']), 'away_id': str(r['away_id']),
            'home_name': ident['home_name'], 'away_name': ident['away_name'],
            'crown_t12_line_home': market_line, 'crown_t12_home_decimal': home_odds,
            'crown_t12_away_decimal': away_odds, 't12_quote_age_hours': float(r['age_ah']),
            'crown_t12_source_event_utc': ident['t12_source_event_utc'],
            'crown_t12_quote_kind': ident['t12_quote_kind'],
            'ft': [ident['home_ft'], ident['away_ft']], 'market_raw_sha256': ident['raw_sha256'],
            'market_raw_path': ident['raw_path'], 'settle_home_u': raw_home,
            'settle_home_class': label_home, 'settle_away_u': raw_away,
            'settle_away_class': label_away, 'market_favorite_side': market_side,
            'frozen_eight_overlap': fid in frozen,
            'home_crowd_source_club_id': hm[0] if hm else None,
            'away_crowd_source_club_id': am[0] if am else None,
            'home_crowd_match_score': hm[1] if hm else None,
            'away_crowd_match_score': am[1] if am else None,
            'home_attendance_features': hf, 'away_attendance_features': af,
            'feature_coverage_reason': reason or 'complete',
        }
        if reason:
            coverage_reasons[reason] += 1
        else:
            coverage_reasons['complete'] += 1
            crowd_keys = ['log_mean_last3', 'log_last_attendance', 'log_count_prior_365d', 'venue_repeat_last3']
            hval = [hf[k] for k in crowd_keys]
            aval = [af[k] for k in crowd_keys]
            row['crowd_features'] = [*hval, *aval, *[x-y for x, y in zip(hval, aval)],
                                     *[x+y for x, y in zip(hval, aval)]]
            row['trend_feature_coverage'] = 'complete' if 'log_trend_3v3' in hf and 'log_trend_3v3' in af else 'missing'
            if row['trend_feature_coverage'] == 'complete':
                htr, atr = hf['log_trend_3v3'], af['log_trend_3v3']
                row['crowd_trend_features'] = [htr, atr, htr-atr, htr+atr]
        fixture_rows.append(row)

    # Create models on the feature-covered rows; select one side only to compare
    # information value. This action is an experiment and not a strategy filter.
    eligible = [r for r in fixture_rows if r['feature_coverage_reason'] == 'complete' and not r['frozen_eight_overlap'] and r['year'] in YEAR_CUTOFF]
    if not eligible:
        raise RuntimeError('No test rows with complete attendance features')
    eligible.sort(key=lambda r: (r['date'], r['fid']))
    league_levels = sorted(set(r['league_id'] for r in fixture_rows if r['year'] < 2027))
    league_index = {l: i for i, l in enumerate(league_levels)}
    market_base_names = ['line', 'abs_line', 'home_log_odds', 'away_log_odds', 'implied_home_share', 'overround']
    crowd_names = [f'attendance_{i}' for i in range(16)]
    all_names = market_base_names + crowd_names + [f'league_{l}' for l in league_levels]
    X, y, years, leagues = [], [], [], []
    for r in fixture_rows:
        if r['feature_coverage_reason'] != 'complete':
            continue
        line, ho, ao = r['crown_t12_line_home'], r['crown_t12_home_decimal'], r['crown_t12_away_decimal']
        invh, inva = 1/ho, 1/ao
        market = [line, abs(line), math.log(ho), math.log(ao), invh/(invh+inva), invh+inva-1]
        cats = [1.0 if r['league_id'] == l else 0.0 for l in league_levels]
        X.append(market + list(r['crowd_features']) + cats)
        y.append(r['settle_home_u'] - r['settle_away_u'])
        years.append(r['year'])
        leagues.append(r['league_id'])
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    years = np.asarray(years, dtype=int)
    model_row_index = {(r['fid']): i for i, r in enumerate([q for q in fixture_rows if q['feature_coverage_reason'] == 'complete'])}
    market_idx = list(range(0, len(market_base_names))) + list(range(6+16, X.shape[1]))
    crowd_idx = list(range(6, 6+16)) + list(range(6+16, X.shape[1]))
    full_idx = list(range(X.shape[1]))
    pred_market, meta_market = model_predict(X, y, years, leagues, market_idx, True)
    pred_crowd, meta_crowd = model_predict(X, y, years, leagues, crowd_idx, False)
    pred_combined, meta_combined = model_predict(X, y, years, leagues, full_idx, True)

    method_predictions = {'market_only_ridge': (pred_market, meta_market),
                          'attendance_only_ridge': (pred_crowd, meta_crowd),
                          'crown_plus_attendance_ridge': (pred_combined, meta_combined)}
    for r in eligible:
        idx = model_row_index[r['fid']]
        for name, (pred, meta) in method_predictions.items():
            score_diff = float(pred[idx])
            side = 'home' if score_diff >= 0 else 'away'
            pnl = r['settle_home_u'] if side == 'home' else r['settle_away_u']
            r.setdefault('models', {})[name] = {
                'predicted_home_minus_away_net_u': score_diff,
                'selected_side': side, 'net_u': pnl,
                'settlement': r['settle_home_class'] if side == 'home' else r['settle_away_class'],
            }

    def ledger(rows: list[dict], method: str) -> list[dict]:
        out = []
        for r in rows:
            m = r.get('models', {}).get(method)
            if not m:
                continue
            out.append({**{k: r[k] for k in ('fid','date','year','iso_week','league_id','home_id','away_id','home_name','away_name','crown_t12_line_home','crown_t12_home_decimal','crown_t12_away_decimal','ft','market_raw_sha256','market_raw_path')},
                        'method': method, 'side': m['selected_side'], 'net_u': m['net_u'], 'settlement': m['settlement']})
        return out

    ledgers = {name: ledger(eligible, name) for name in method_predictions}
    summary = {
        'study': 'M8_PREVIOUS_HOME_ATTENDANCE_CROWD_INFORMATION_VS_CROWN_AH',
        'execution_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'status': 'research-only retrospective source-event replay; no production behavior changed',
        'mechanism': 'Use only attendance from each club previous home matches; compare market-only, crowd-only, Crown plus crowd. The target fixture attendance is excluded. Historical archive rows have dates but no first-publication or received timestamps.',
        'input_sha256': {str(p): sha(p) for p in (GAME_FILE, INVENTORY, FOUNDATION, MARKET_BOOTSTRAP, RECEIPT_ARCHIVE)},
        'fixed_method': {'years': list(YEAR_CUTOFF), 'training': 'expanding calendar-year; test year excluded; earlier years only',
                         'attendance_prior_cutoff_days': LAG_DAYS, 'attendance_lookback_days': LOOKBACK_DAYS,
                         'minimum_prior_home_attendance_records_per_team': MIN_ATTENDANCE_MATCHES,
                         'ridge_alpha': RIDGE_ALPHA, 'side_selection': 'argmax of predicted net AH return difference; every feature-complete test FID receives one experimental side; no EV threshold'},
        'scope': {'inventory_T12_rows': sum(int(r.get('T', -1)) == 12 for r in inventory_rows),
                  'raw_quote_ft_identity_verified': len(raw_fixture_identity),
                  'raw_quote_identity_errors': dict(raw_errors),
                  'raw_crown_T12_contract_audit': dict(raw_quote_audit),
                  'outside_frozen_test_inventory': len([r for r in fixture_rows if r['year'] in YEAR_CUTOFF and not r['frozen_eight_overlap']]),
                  'feature_complete_unique_fids': len({r['fid'] for r in eligible}),
                  'frozen_overlap_feature_complete_all_years': sum(r['frozen_eight_overlap'] for r in fixture_rows if r['feature_coverage_reason']=='complete'),
                  'candidate_frozen_overlap': sum(r['frozen_eight_overlap'] for r in eligible),
                  'date_range': [min(r['date'] for r in fixture_rows), max(r['date'] for r in fixture_rows)] if fixture_rows else None,
                  'target_year_n': {str(y): sum(r['year']==y for r in eligible) for y in YEAR_CUTOFF},
                  'feature_coverage_reason_counts': dict(coverage_reasons),
                  'test_feature_coverage_reason_counts': {
                      str(y): dict(collections.Counter(r['feature_coverage_reason'] for r in fixture_rows
                                                       if r['year'] == y and not r['frozen_eight_overlap']))
                      for y in YEAR_CUTOFF},
                  'feature_age_days_by_year': {
                      str(y): {
                          'n': sum(1 for r in eligible if r['year']==y),
                          'home_median': round(float(np.median([r['home_attendance_features']['feature_age_days'] for r in eligible if r['year']==y])),3) if any(r['year']==y for r in eligible) else None,
                          'home_p90': round(float(np.percentile([r['home_attendance_features']['feature_age_days'] for r in eligible if r['year']==y],90)),3) if any(r['year']==y for r in eligible) else None,
                          'away_median': round(float(np.median([r['away_attendance_features']['feature_age_days'] for r in eligible if r['year']==y])),3) if any(r['year']==y for r in eligible) else None,
                          'away_p90': round(float(np.percentile([r['away_attendance_features']['feature_age_days'] for r in eligible if r['year']==y],90)),3) if any(r['year']==y for r in eligible) else None,
                      } for y in YEAR_CUTOFF},
                  'identity_crosswalk': {'crown_team_keys': len(crown_team_names), 'accepted_one_to_one_keys': len(team_map),
                                         'name_match_scores': {'mean': round(statistics.mean(v[1] for v in team_map.values()),6) if team_map else None,
                                                               'min': round(min(v[1] for v in team_map.values()),6) if team_map else None},
                                         'unmatched_or_ambiguous': dict(map_reasons)},
                  'attendance_source': {'games_rows': len(ext_games), 'teams_with_home_attendance': len(attendance_history),
                                        'rows_with_attendance': sum(len(v) for v in attendance_history.values()),
                                        'source_max_date': max(r['date'] for r in ext_games),
                                        'missing_or_invalid': dict(invalid_attendance)}},
        'models': {}, 'receipt_audit': {'actual_crown_receipts_replayed': 0,
                                        'reason': 'The Transfermarkt source is a retrospective bulk snapshot with no contemporaneous row-level received/published timestamps. It stops before late-2026 actual receipt dates; no record is treated as a verified live-time feature.'},
        'frozen_baseline': {'n': 10294, 'net_U': 236.015, 'ROI_pct': 2.293},
        'merged_with_frozen': {},
    }
    frozen_rows = load_jsonl(FOUNDATION)
    frozen_pnl = {str(r.get('fid') or r.get('match_id')): float(r.get('pnl', r.get('net_u', 0.0))) for r in frozen_rows}
    frozen_date = {str(r.get('fid') or r.get('match_id')): str(r.get('date') or r.get('kickoff_beijing') or '')[:10] for r in frozen_rows}
    for name, rows in ledgers.items():
        summary['models'][name] = {
            'all_test': stats(rows),
            'annual': {str(y): stats([r for r in rows if r['year']==y]) for y in YEAR_CUTOFF},
            'league': {l: stats([r for r in rows if r['league_id']==l]) for l in sorted({r['league_id'] for r in rows})},
        }
        for y in YEAR_CUTOFF:
            subset = [r for r in rows if r['year']==y]
            frozen_y = [p for fid,p in frozen_pnl.items() if frozen_date.get(fid,'')[:4] == str(y)]
            merged_rows = subset + [{'fid':fid, 'date':frozen_date.get(fid,''), 'year':int(y), 'net_u':p, 'settlement':'frozen'} for fid,p in frozen_pnl.items() if frozen_date.get(fid,'')[:4] == str(y) and fid not in {r['fid'] for r in subset}]
            st = stats(merged_rows)
            summary['merged_with_frozen'].setdefault(name,{})[str(y)] = {
                'new_n': len(subset), 'new_net_U': round(sum(r['net_u'] for r in subset),6),
                'frozen_n': len(frozen_y), 'frozen_net_U': round(sum(frozen_y),6),
                'merged_n': st['n'], 'merged_net_U': st['net_U'], 'merged_ROI_pct': st['ROI_pct'],
                'merged_MDD_U': st['MDD_U'], 'new_weekly': subset and stats(subset)['weekly'] or {},
            }
        new_2426 = [r for r in rows if r['year'] in YEAR_CUTOFF]
        candidate_ids = {r['fid'] for r in new_2426}
        frozen_2426 = [{'fid': fid, 'date': frozen_date.get(fid,''), 'year': int(frozen_date[fid][:4]),
                        'net_u': pnl, 'settlement': 'frozen'}
                       for fid,pnl in frozen_pnl.items()
                       if frozen_date.get(fid,'')[:4] in {str(y) for y in YEAR_CUTOFF} and fid not in candidate_ids]
        merged_2426 = stats(new_2426 + frozen_2426)
        summary['merged_with_frozen'][name]['2024_2026'] = {
            'new_n': len(new_2426), 'new_net_U': round(sum(r['net_u'] for r in new_2426),6),
            'frozen_n': len(frozen_2426), 'frozen_net_U': round(sum(r['net_u'] for r in frozen_2426),6),
            'merged_n': merged_2426['n'], 'merged_net_U': merged_2426['net_U'],
            'merged_ROI_pct': merged_2426['ROI_pct'], 'merged_MDD_U': merged_2426['MDD_U'],
            'merged_weekly': merged_2426['weekly'],
        }
    method_ids = {name: {r['fid'] for r in rows} for name, rows in ledgers.items()}
    summary['method_fid_overlap'] = {
        a: {b: len(method_ids[a] & method_ids[b]) for b in method_ids}
        for a in method_ids
    }
    summary['frozen_membership_audit'] = {
        'unique_fids': len(frozen_pnl), 'net_U': round(sum(frozen_pnl.values()),6),
        'all_candidate_fid_intersections': {name: len(ids & set(frozen_pnl)) for name,ids in method_ids.items()},
    }
    # receipt FID overlap is a coverage diagnostic only; it is not a receipt replay.
    receipt_ids = set()
    actual_receipt_archive = RECEIPT_ARCHIVE
    if actual_receipt_archive.exists():
        receipt_ids.update(str(r.get('fixture_id')) for r in load_jsonl(actual_receipt_archive) if r.get('fixture_id'))
    summary['receipt_audit']['receipt_inventory_fid_overlap'] = len(receipt_ids & {r['fid'] for r in fixture_rows})
    summary['receipt_audit']['receipt_inventory_ids_checked'] = len(receipt_ids)
    summary['receipt_audit']['receipt_archive_path'] = str(actual_receipt_archive)
    summary['receipt_audit']['receipt_archive_sha256'] = sha(actual_receipt_archive) if actual_receipt_archive.exists() else None
    full_test_inventory = [r for r in fixture_rows if r['year'] in YEAR_CUTOFF and not r['frozen_eight_overlap']]
    observed_weeks = {str(y): len({r['iso_week'] for r in full_test_inventory if r['year']==y}) for y in YEAR_CUTOFF}
    summary['scope']['observed_market_inventory_weeks_by_year'] = observed_weeks
    summary['scope']['candidate_avg_orders_per_observed_inventory_week'] = {
        name: {str(y): round(len([r for r in rows if r['year']==y]) / observed_weeks[str(y)], 6) if observed_weeks[str(y)] else None
               for y in YEAR_CUTOFF} for name, rows in ledgers.items()}

    with gzip.open(OUT/'attendance_crowd_per_fixture_20261121.jsonl.gz', 'wt', encoding='utf-8', compresslevel=6) as f:
        for r in fixture_rows:
            f.write(json.dumps(r, ensure_ascii=False, separators=(',',':'))+'\n')
    with gzip.open(OUT/'attendance_crowd_orders_20261121.jsonl.gz', 'wt', encoding='utf-8', compresslevel=6) as f:
        for method, rows in ledgers.items():
            for r in rows:
                f.write(json.dumps({**r, 'method': method}, ensure_ascii=False, separators=(',',':'))+'\n')
    (OUT/'attendance_crowd_summary_20261121.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    compact = {
        'scope': {k: v for k, v in summary['scope'].items() if k not in ('identity_crosswalk','attendance_source')},
        'models': {k: {'all_test': {m: v['all_test'][m] for m in ('n','net_U','ROI_pct','MDD_U','weekly_n','settlement')},
                       'annual': {y: {m: v['annual'][y][m] for m in ('n','net_U','ROI_pct','MDD_U','weekly_n')} for y in v['annual']}}
                   for k,v in summary['models'].items()},
        'merged_with_frozen': {k: {y:{m:z[m] for m in ('new_n','new_net_U','merged_n','merged_net_U','merged_ROI_pct','merged_MDD_U')}
                                  for y,z in v.items()} for k,v in summary['merged_with_frozen'].items()},
        'receipt_audit': summary['receipt_audit'],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
