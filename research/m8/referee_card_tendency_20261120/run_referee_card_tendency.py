#!/usr/bin/env python3
"""Time-forward referee card-tendency features versus actual Crown AH prices.

The target match's referee is from a retrospective archive without a verified
pregame announcement timestamp. Results therefore remain historical diagnostics.
"""
from __future__ import annotations
import bisect, collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib, re, sys
from zoneinfo import ZoneInfo
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')
OUT = ROOT / 'research/m8/referee_card_tendency_20261120'
sys.path.insert(0, str(ROOT))
PATH = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
SCORES = WORK / 'm8_independent_score_strength_20261114.jsonl'
FOUNDATION = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPTS = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
MANAGER = ROOT / 'research/m8/m8_prior_manager_turnover_20261117.py'
TM_GAMES = WORK / 'm8_pregame_info_source_20261117/games.csv.gz'
RAW_HIST = DATA / 'crown_quote_store/raw/historical'
RIDGE_ALPHA = 100.0
LAG_DAYS = 3
WINDOW_DAYS = 365
SHRINKAGE = 5.0
METHODS = ('low_price', 'market_model', 'market_plus_yellow', 'market_plus_red', 'market_plus_cards', 'cards_only')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_jsonl(path):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def parse_utc(v):
    x = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00').replace(' ', 'T'))
    if x.tzinfo is None:
        x = x.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
    return x.astimezone(dt.timezone.utc)


def ref_norm(v):
    import unicodedata
    s = unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def settle(line, side, gd, odds):
    handicap = float(line) if side == 'home' else -float(line)
    margin = int(gd) if side == 'home' else -int(gd)
    q = round(handicap * 4)
    if abs(handicap * 4 - q) > 1e-8:
        raise ValueError(f'AH line outside quarter grid: {line}')
    legs = [handicap] if q % 2 == 0 else [math.floor(handicap * 2) / 2, math.floor(handicap * 2) / 2 + .5]
    pnl = []
    outcomes = []
    for leg in legs:
        z = margin + leg
        outcomes.append('W' if z > 1e-9 else 'L' if z < -1e-9 else 'P')
        pnl.append(float(odds) - 1 if z > 1e-9 else -1. if z < -1e-9 else 0.)
    net = sum(pnl) / len(pnl)
    if all(x == 'W' for x in outcomes): state = 'full_win'
    elif all(x == 'L' for x in outcomes): state = 'full_loss'
    elif all(x == 'P' for x in outcomes): state = 'push'
    elif 'W' in outcomes: state = 'half_win'
    else: state = 'half_loss'
    return state, net


def fit_ridge(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    mu = x.mean(0); sd = x.std(0); sd[sd < 1e-10] = 1.
    z = (x - mu) / sd
    design = np.column_stack([np.ones(len(z)), z])
    penalty = np.eye(design.shape[1]) * RIDGE_ALPHA; penalty[0, 0] = 0.
    coef = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    err = y - design @ coef
    return {'mean': mu, 'scale': sd, 'coef': coef, 'sigma': max(.35, float(np.sqrt(np.mean(err ** 2)))), 'n': len(y)}


def predict(model, features):
    z = (np.asarray(features, float) - model['mean']) / model['scale']
    return float(np.r_[1., z] @ model['coef'])


def normal_cdf(x):
    return .5 * (1. + math.erf(x / math.sqrt(2.)))


def margin_distribution(mu, sigma):
    sigma = max(float(sigma), .35)
    vals = []
    for gd in range(-12, 13):
        p = normal_cdf((gd + .5 - mu) / sigma) - normal_cdf((gd - .5 - mu) / sigma)
        vals.append((gd, max(0., p)))
    total = sum(p for _, p in vals)
    return [(gd, p / total) for gd, p in vals]


def ev_side(line, odds, side, dist):
    return sum(p * settle(line, side, gd, odds)[1] for gd, p in dist)


def metrics(rows, method):
    bets = [r for r in rows if r['methods'][method]['side'] is not None]
    n = len(bets); u = sum(float(r['methods'][method]['net_u']) for r in bets)
    daily = collections.defaultdict(float); weekly = collections.defaultdict(lambda: [0, 0.]); league = collections.defaultdict(lambda: [0, 0.]); states = collections.Counter()
    for r in bets:
        m = r['methods'][method]; daily[r['date']] += float(m['net_u']); weekly[r['iso_week']][0] += 1; weekly[r['iso_week']][1] += float(m['net_u']); league[r['league']][0] += 1; league[r['league']][1] += float(m['net_u']); states[m['settlement']] += 1
    cum = peak = mdd = 0.
    for day in sorted(daily):
        cum += daily[day]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    span = (dt.date.fromisoformat(max(r['date'] for r in rows)) - dt.date.fromisoformat(min(r['date'] for r in rows))).days // 7 + 1 if rows else 0
    return {'orders': n, 'no_bet': len(rows) - n, 'net_u': round(u, 6), 'roi_pct': round(100 * u / n, 6) if n else None, 'mdd_u': round(mdd, 6), 'calendar_weeks': span, 'avg_orders_per_calendar_week': round(n / span, 6) if span else 0,
            'settlements': dict(states), 'weekly': {k: {'n': v[0], 'net_u': round(v[1], 6)} for k, v in sorted(weekly.items())}, 'league': {k: {'n': v[0], 'net_u': round(v[1], 6), 'roi_pct': round(100 * v[1] / v[0], 6)} for k, v in sorted(league.items())}}


def aggregate(rows):
    n = len(rows); u = sum(float(r['net_u']) for r in rows); daily = collections.defaultdict(float)
    for r in rows: daily[r['date']] += float(r['net_u'])
    cum = peak = mdd = 0.
    for day in sorted(daily): cum += daily[day]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    span = (dt.date.fromisoformat(max(r['date'] for r in rows)) - dt.date.fromisoformat(min(r['date'] for r in rows))).days // 7 + 1 if rows else 0
    return {'orders': n, 'net_u': round(u, 6), 'roi_pct': round(100 * u / n, 6) if n else None, 'mdd_u': round(mdd, 6), 'calendar_weeks': span, 'avg_orders_per_calendar_week': round(n / span, 6) if span else 0}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = MANAGER.read_text(); marker = '# Build historical coach timeline'
    if marker not in src: raise RuntimeError('identity bridge prefix not found')
    ns = {'__file__': str(MANAGER), '__name__': 'referee_card_identity_bridge'}
    exec(compile(src[:src.index(marker)], str(MANAGER) + '[audited identity bridge prefix]', 'exec'), ns)
    teammap, allft, cm, compdate, tmrec = ns['teammap'], ns['allft'], ns['cm'], ns['compdate'], ns['tmrec']
    paths = {str(r['fid']): r for r in read_jsonl(PATH)}; scores = {str(r['fid']): r for r in read_jsonl(SCORES)}
    frozen = {str(r['fid']): r for r in read_jsonl(FOUNDATION)}; receipt_ids = {str(r['fixture_id']) for r in read_jsonl(RECEIPTS)}
    issues = collections.Counter(); games = []
    for fid, p in paths.items():
        s = scores.get(fid); ft = allft.get(fid)
        if not s or ft is None: issues['missing_score_or_Crown_schedule_FT'] += 1; continue
        lid, hid, aid, hn, an, hg, ag, _ = ft
        if (str(lid), str(hid), str(aid), str(hg), str(ag)) != (str(s['league']), str(s['home']), str(s['away']), str(s['hg']), str(s['ag'])):
            issues['Crown_score_identity_conflict'] += 1; continue
        ht, at, comp = teammap.get((str(lid), str(hid))), teammap.get((str(lid), str(aid))), cm.get(str(lid))
        if not ht or not at or not comp: issues['unmapped_team_or_competition'] += 1; continue
        local = parse_utc(s['ko']).astimezone(ZoneInfo('Asia/Shanghai')); day = local.date(); cands = []
        for ordinal in (day.toordinal() - 1, day.toordinal(), day.toordinal() + 1):
            for t in compdate.get((comp, ordinal), []):
                if t[2] == ht and t[3] == at and t[4] == int(s['hg']) and t[5] == int(s['ag']): cands.append(t)
        if len(cands) != 1: issues['TM_fixture_' + ('unmatched' if not cands else 'ambiguous')] += 1; continue
        tm = tmrec[cands[0][-1]]; referee = str(tm.get('referee') or '').strip(); rkey = ref_norm(referee)
        if not referee or not rkey: issues['missing_or_invalid_referee'] += 1; continue
        line = float(p['end_line']); ho = float(p['home_price']); ao = float(p['away_price']); gd = int(s['hg']) - int(s['ag'])
        uh = settle(line, 'home', gd, ho)[1]; ua = settle(line, 'away', gd, ao)[1]
        if abs(uh - float(p['end_home_U'])) > 1e-8 or abs(ua - float(p['end_away_U'])) > 1e-8: issues['Crown_path_settlement_mismatch'] += 1; continue
        iso = day.isocalendar()
        games.append({'fid': fid, 'date': day.isoformat(), 'year': day.year, 'iso_week': f'{iso.year}-W{iso.week:02d}', 'kickoff_beijing': local.isoformat(), 'league': str(lid), 'league_name': str(p['league']), 'home': str(s['home']), 'away': str(s['away']), 'home_tm_id': ht, 'away_tm_id': at, 'tm_game_id': str(tm['game_id']), 'referee': referee, 'referee_key': (str(lid), rkey), 'hg': int(s['hg']), 'ag': int(s['ag']), 'gd': gd, 'line': line, 'home_odds': ho, 'away_odds': ao, 'market_margin': -line + .25 * math.log(ao / ho), 'frozen_eight_overlap': fid in frozen, 'receipt_archive_fid_overlap': fid in receipt_ids, 'methods': {}})
    games.sort(key=lambda r: (r['date'], r['fid']))

    # Read Crown raw historical responses. Require a unique Crown/TM identity,
    # complete nonnegative card counts, and a stable per-FID card record.
    raw_stats = collections.Counter(); card_by_fid = {}; card_conflicts = set()
    raw_files = sorted(RAW_HIST.rglob('*.json'))
    for f in raw_files:
        try:
            b = f.read_bytes(); body = json.loads(b); d = body.get('data'); d = d[0] if isinstance(d, list) and d else d
            if not isinstance(d, dict): raw_stats['bad_json_shape'] += 1; continue
            fid = str(d.get('id')); ft = allft.get(fid)
            if not ft or ft is None: raw_stats['not_in_schedule_FT'] += 1; continue
            lid, hid, aid, _, _, hg, ag, src_day = ft
            if (str(lid), str(hid), str(aid), str(hg), str(ag)) != (str(d.get('l_id')), str(d.get('h_id')), str(d.get('a_id')), str(d.get('hg')), str(d.get('ag'))): raw_stats['raw_vs_schedule_conflict'] += 1; continue
            ht, at = teammap.get((str(lid), str(hid))), teammap.get((str(lid), str(aid))); comp = cm.get(str(lid))
            if not ht or not at or not comp: raw_stats['unmapped_team'] += 1; continue
            cands = []
            for ordinal in (dt.date.fromisoformat(src_day).toordinal() - 1, dt.date.fromisoformat(src_day).toordinal(), dt.date.fromisoformat(src_day).toordinal() + 1):
                for t in compdate.get((comp, ordinal), []):
                    if t[2] == ht and t[3] == at and t[4] == int(hg) and t[5] == int(ag): cands.append(t)
            if len(cands) != 1: raw_stats['TM_fixture_' + ('unmatched' if not cands else 'ambiguous')] += 1; continue
            tm = tmrec[cands[0][-1]]; referee = str(tm.get('referee') or '').strip(); key = (str(lid), ref_norm(referee))
            if not referee or not key[1]: raw_stats['missing_referee'] += 1; continue
            try: cards = [int(d[k]) for k in ('hyc', 'ayc', 'hrc', 'arc')]
            except (TypeError, ValueError): raw_stats['missing_card_count'] += 1; continue
            if any(x < 0 for x in cards): raw_stats['invalid_card_count'] += 1; continue
            source_sha = hashlib.sha256(b).hexdigest()
            row = {'fid': fid, 'date': str(tm['date']), 'league': str(lid), 'referee': referee, 'referee_key': key, 'tm_game_id': str(tm['game_id']), 'home_tm_id': ht, 'away_tm_id': at, 'hg': int(hg), 'ag': int(ag), 'yellow_home': cards[0], 'yellow_away': cards[1], 'red_home': cards[2], 'red_away': cards[3], 'raw_response_sha256': source_sha}
            old = card_by_fid.get(fid)
            if old:
                raw_stats['duplicate_raw_FID'] += 1
                comparable = ('date', 'league', 'referee_key', 'tm_game_id', 'home_tm_id', 'away_tm_id', 'hg', 'ag', 'yellow_home', 'yellow_away', 'red_home', 'red_away')
                if any(old[k] != row[k] for k in comparable): card_conflicts.add(fid); raw_stats['conflicting_raw_FID'] += 1
                continue
            card_by_fid[fid] = row
        except Exception as e:
            raw_stats['parse_error_' + type(e).__name__] += 1
    for fid in card_conflicts: card_by_fid.pop(fid, None)
    card_rows = sorted(card_by_fid.values(), key=lambda r: (r['date'], r['fid']))
    raw_stats['unique_mapped_complete_card_FID'] = len(card_rows)
    card_hash = {r['fid']: r['raw_response_sha256'] for r in card_rows}
    # Keep a compact source index so each card feature history can be audited
    # back to a Crown response hash without publishing full response bodies.
    with gzip.open(OUT / 'referee_card_history_source_index.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in card_rows:
            f.write(json.dumps({k: v for k, v in r.items() if k != 'referee_key'}, ensure_ascii=False, sort_keys=True) + '\n')

    ref_hist = collections.defaultdict(list); comp_hist = collections.defaultdict(list)
    for r in card_rows:
        ydiff = r['yellow_home'] - r['yellow_away']; rdiff = r['red_home'] - r['red_away']
        key = r['referee_key']; comp = r['league']; day = dt.date.fromisoformat(r['date'])
        ref_hist[key].append((day, ydiff, rdiff, r['fid']))
        comp_hist[comp].append((day, ydiff, rdiff, r['fid']))
    for seq in list(ref_hist.values()) + list(comp_hist.values()): seq.sort(key=lambda x: (x[0], x[3]))
    ref_dates = {k: [x[0] for x in v] for k, v in ref_hist.items()}; comp_dates = {k: [x[0] for x in v] for k, v in comp_hist.items()}
    card_target_coverage = collections.Counter()
    for r in games:
        day = dt.date.fromisoformat(r['date']); cutoff = day - dt.timedelta(days=LAG_DAYS); start = cutoff - dt.timedelta(days=WINDOW_DAYS); key = r['referee_key']; comp = r['league']
        rs = ref_hist.get(key, []); rd = ref_dates.get(key, []); cs = comp_hist.get(comp, []); cd = comp_dates.get(comp, [])
        rhi = bisect.bisect_left(rd, cutoff); rlo = bisect.bisect_left(rd, start); chi = bisect.bisect_left(cd, cutoff); clo = bisect.bisect_left(cd, start)
        prior = rs[rlo:rhi]; cp = cs[clo:chi]; n = len(prior)
        if n:
            ym = sum(x[1] for x in prior) / n; rm = sum(x[2] for x in prior) / n
            yn = len(cp); cy = sum(x[1] for x in cp) / yn if yn else 0.; cr = sum(x[2] for x in cp) / yn if yn else 0.
            shrink = n / (n + SHRINKAGE)
            r['yellow_bias_prior'] = shrink * (ym - cy); r['red_bias_prior'] = shrink * (rm - cr)
            r['ref_card_prior_n_365'] = n; r['ref_card_prior_max_date'] = max(x[0] for x in prior).isoformat()
            r['comp_card_prior_n_365'] = yn
            source_material = '\n'.join(f'{x[3]}:{card_hash[x[3]]}' for x in prior).encode()
            r['ref_card_prior_source_sha256'] = hashlib.sha256(source_material).hexdigest()
            source_material = '\n'.join(f'{x[3]}:{next((q["raw_response_sha256"] for q in card_rows if q["fid"] == x[3]), "")}' for x in prior).encode()
            r['ref_card_prior_source_sha256'] = hashlib.sha256(source_material).hexdigest()
            card_target_coverage[f'{r["year"]}_with_prior_referee_cards'] += 1
        else:
            r['yellow_bias_prior'] = None; r['red_bias_prior'] = None; r['ref_card_prior_n_365'] = 0; r['ref_card_prior_max_date'] = None; r['comp_card_prior_n_365'] = len(cp); r['ref_card_prior_source_sha256'] = None
            card_target_coverage[f'{r["year"]}_without_prior_referee_cards'] += 1
        r['card_feature_cutoff'] = 'prior completed records only; date < target Beijing date - 3 days; trailing 365 days'
    eligible = [r for r in games if r['ref_card_prior_n_365'] > 0]
    target_test = [r for r in eligible if r['year'] in (2024, 2025, 2026)]
    outside_test = [r for r in target_test if not r['frozen_eight_overlap']]

    def market_features(r): return [r['market_margin'], r['line'], .25 * math.log(r['away_odds'] / r['home_odds'])]
    def yellow_features(r): return [r['yellow_bias_prior'], math.log1p(r['ref_card_prior_n_365'])]
    def red_features(r): return [r['red_bias_prior'], math.log1p(r['ref_card_prior_n_365'])]
    def cards_features(r): return [r['yellow_bias_prior'], r['red_bias_prior'], math.log1p(r['ref_card_prior_n_365'])]
    feature_functions = {'market_model': market_features, 'market_plus_yellow': lambda r: market_features(r) + yellow_features(r), 'market_plus_red': lambda r: market_features(r) + red_features(r), 'market_plus_cards': lambda r: market_features(r) + cards_features(r), 'cards_only': cards_features}
    folds = {}; scored = []; prediction_quality = {}
    for year in (2024, 2025, 2026):
        train = [r for r in eligible if 2019 <= r['year'] < year]; test = [r for r in eligible if r['year'] == year]
        if not train or not test: continue
        models = {name: fit_ridge([fn(r) for r in train], [r['gd'] for r in train]) for name, fn in feature_functions.items()}
        folds[str(year)] = {'train_n': len(train), 'test_n': len(test), 'training_years': sorted({r['year'] for r in train}), 'ridge_alpha': RIDGE_ALPHA, 'referee_card_window_days': WINDOW_DAYS, 'same_competition_shrinkage': SHRINKAGE, 'target_lag_days': LAG_DAYS, 'sigma': {k: round(v['sigma'], 8) for k, v in models.items()}, 'coefficients': {k: {'mean': np.round(v['mean'], 8).tolist(), 'scale': np.round(v['scale'], 8).tolist(), 'coef_intercept_first': np.round(v['coef'], 8).tolist()} for k, v in models.items()}}
        for r in test:
            r['methods'] = {}
            r['model_predictions'] = {}
            for name, model in models.items():
                mu = predict(model, feature_functions[name](r)); dist = margin_distribution(mu, model['sigma'])
                eh = ev_side(r['line'], r['home_odds'], 'home', dist); ea = ev_side(r['line'], r['away_odds'], 'away', dist)
                side = 'home' if eh > ea else 'away'
                r['methods'][name] = {'side': side, 'settlement': None, 'net_u': None, 'predicted_home_margin': round(mu, 8), 'ev_home_u': round(eh, 8), 'ev_away_u': round(ea, 8)}
                r['model_predictions'][name] = mu
            low = 'home' if r['home_odds'] <= r['away_odds'] else 'away'
            r['methods']['low_price'] = {'side': low, 'settlement': None, 'net_u': None}
            for name in METHODS:
                m = r['methods'][name]; odds = r['home_odds'] if m['side'] == 'home' else r['away_odds']
                state, u = settle(r['line'], m['side'], r['gd'], odds); m['settlement'] = state; m['net_u'] = round(u, 10)
            scored.append(r)
        prediction_quality[str(year)] = {}
        for name in feature_functions:
            e = np.asarray([r['gd'] - r['model_predictions'][name] for r in test], float)
            prediction_quality[str(year)][name] = {'n': len(test), 'mae': round(float(np.mean(np.abs(e))), 8), 'rmse': round(float(np.sqrt(np.mean(e ** 2))), 8)}
    scored.sort(key=lambda r: (r['date'], r['fid']))
    scored_incremental = [r for r in scored if not r['frozen_eight_overlap']]
    results = {'eligible_same_cohort': {m: metrics(scored, m) for m in METHODS}, 'outside_frozen_eight': {m: metrics(scored_incremental, m) for m in METHODS}, 'outside_by_year': {}, 'all_by_year': {}}
    for y in (2024, 2025, 2026):
        all_y = [r for r in scored if r['year'] == y]; out_y = [r for r in all_y if not r['frozen_eight_overlap']]
        if all_y:
            results['all_by_year'][str(y)] = {m: metrics(all_y, m) for m in METHODS}
            results['outside_by_year'][str(y)] = {m: metrics(out_y, m) for m in METHODS}
    frozen_target = [{'fid': fid, 'date': str(x['date'])[:10], 'net_u': float(x['pnl'])} for fid, x in frozen.items() if int(x['year']) in (2024, 2025, 2026)]
    merged = {}
    for method in METHODS:
        candid = [r for r in scored_incremental if r['methods'][method]['side'] is not None]
        candidate_ids = {r['fid'] for r in candid}; frozen_ids = {r['fid'] for r in frozen_target}
        union = {r['fid']: {'date': r['date'], 'net_u': r['methods'][method]['net_u']} for r in candid}
        union.update({r['fid']: {'date': r['date'], 'net_u': r['net_u']} for r in frozen_target})
        merged[method] = {'frozen_target': aggregate(frozen_target), 'incremental_outside_frozen': aggregate([{'date': r['date'], 'net_u': r['methods'][method]['net_u']} for r in candid]), 'merged_unique_fid': aggregate([{'date': v['date'], 'net_u': v['net_u']} for v in union.values()]), 'candidate_overlap_frozen': len(candidate_ids & frozen_ids)}
    year_source = collections.Counter(r['date'][:4] for r in card_rows)
    summary = {'study': 'M8_REFEREE_PRIOR_CARD_TENDENCY_CROWN_AH', 'inputs': {str(p): sha(p) for p in (PATH, SCORES, FOUNDATION, RECEIPTS, TM_GAMES, MANAGER)}, 'data': {'path_rows': len(paths), 'score_rows': len(scores), 'frozen_unique_fids': len(frozen), 'mapped_target_rows': len(games), 'mapped_test_rows_2024_2026': sum(r['year'] in (2024, 2025, 2026) for r in games), 'eligible_rows_with_prior_referee_card_record': len(eligible), 'eligible_incremental_test_rows': len(scored_incremental), 'card_history_unique_complete_fids': len(card_rows), 'card_history_rows_by_year': dict(sorted(year_source.items())), 'card_history_unique_referee_competition_pairs': len({r['referee_key'] for r in card_rows}), 'card_raw_inventory_files': len(raw_files), 'card_raw_mapping_and_duplicate_audit': dict(raw_stats), 'mapped_target_referee_receipt_intersection': len({r['fid'] for r in games if r['receipt_archive_fid_overlap']}), 'scored_receipt_intersection': len({r['fid'] for r in scored if r['receipt_archive_fid_overlap']}), 'target_card_prior_coverage': dict(card_target_coverage), 'mapping_issues': dict(issues)}, 'methodology': {'feature': 'within league/referee, prior 365-day home-minus-away yellow/red-card differential minus league prior differential, shrunk n/(n+5); only dates strictly earlier than target Beijing date minus 3 days; card counts must be present and nonnegative; same-day feature snapshots precede daily updates', 'time_forward': '2024 train 2019-2023, 2025 train 2019-2024, 2026 train 2019-2025; fixed Ridge alpha 100 after fold-local standardization; all train/test observations require at least one observed earlier referee card match; same target cohort for all methods', 'AH_direction': 'Ridge predicts home goal difference. A discretized normal margin distribution with training residual RMSE is settled against the actual Crown AH line and both decimal prices; choose higher model-expected net AH return. Low-price side is a diagnostic baseline.', 'temporal_limit': 'target referee is sourced retrospectively from games.csv.gz; no verified referee assignment announcement/receipt timestamp. All Crown path prices are historical source-event replays, not actual received prices.'}, 'folds': folds, 'prediction_quality_outside_frozen': prediction_quality, 'results': results, 'merged_with_frozen_eight': merged, 'formal_orders': 0, 'formal_ledger_writes': 0, 'production_changes': 0, 'crown_api_requests': 0}
    (OUT / 'referee_card_tendency_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with gzip.open(OUT / 'referee_card_tendency_per_fixture.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in scored:
            clean = dict(r); clean.pop('referee_key', None)
            f.write(json.dumps(clean, ensure_ascii=False, sort_keys=True) + '\n')
    print(json.dumps({'data': summary['data'], 'outside_frozen_eight': {k: {m: {x: v[m][x] for x in ('orders', 'net_u', 'roi_pct', 'mdd_u', 'avg_orders_per_calendar_week')} for m in METHODS} for k, v in [('all', results['outside_frozen_eight']), *results['outside_by_year'].items()]}, 'merged': {m: v['merged_unique_fid'] for m, v in merged.items()}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
