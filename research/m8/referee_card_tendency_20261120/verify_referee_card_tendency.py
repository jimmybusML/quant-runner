#!/usr/bin/env python3
"""Independent audit of referee-card features, Crown quotes and AH cashflows."""
import collections, csv, datetime as dt, gzip, hashlib, json, math, pathlib, re, sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'research/m8/referee_card_tendency_20261120'
DATA = pathlib.Path('/Users/mac/QuantAsiaDesk/data')
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
RAW = DATA / 'crown_quote_store/raw/historical'
TM_GAMES = WORK / 'm8_pregame_info_source_20261117/games.csv.gz'
CARD_INDEX = OUT / 'referee_card_history_source_index.jsonl.gz'
LEDGER = OUT / 'referee_card_tendency_per_fixture.jsonl.gz'
SUMMARY = OUT / 'referee_card_tendency_summary.json'
FOUNDATION = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
MANAGER = ROOT / 'research/m8/m8_prior_manager_turnover_20261117.py'
PREV_VERIFY = ROOT / 'research/m8/referee_market_residual_20261120/independent_verification.json'
PREV_LEDGER = ROOT / 'research/m8/referee_market_residual_20261120/referee_market_residual_per_fixture.jsonl.gz'


def norm(v):
    import unicodedata
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode().lower())


def settle(line, side, gd, odds):
    handicap = float(line) if side == 'home' else -float(line)
    margin = int(gd) if side == 'home' else -int(gd)
    q = round(handicap * 4)
    if abs(handicap * 4 - q) > 1e-8: raise ValueError(f'bad quarter line {line}')
    legs = [handicap] if q % 2 == 0 else [math.floor(handicap * 2) / 2, math.floor(handicap * 2) / 2 + .5]
    pnl = []; labels = []
    for leg in legs:
        z = margin + leg; labels.append('W' if z > 1e-9 else 'L' if z < -1e-9 else 'P'); pnl.append(float(odds) - 1 if z > 1e-9 else -1. if z < -1e-9 else 0.)
    net = sum(pnl) / len(pnl)
    state = 'full_win' if all(x == 'W' for x in labels) else 'full_loss' if all(x == 'L' for x in labels) else 'push' if all(x == 'P' for x in labels) else 'half_win' if 'W' in labels else 'half_loss'
    return state, net


def metric(rows, method):
    bets = [r for r in rows if r['methods'][method]['side'] is not None]
    n = len(bets); u = sum(float(r['methods'][method]['net_u']) for r in bets); daily = collections.defaultdict(float)
    for r in bets: daily[r['date']] += float(r['methods'][method]['net_u'])
    cum = peak = mdd = 0.
    for d in sorted(daily): cum += daily[d]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    return {'orders': n, 'net_u': round(u, 6), 'roi_pct': round(100 * u / n, 6) if n else None, 'mdd_u': round(mdd, 6)}


def main():
    summary = json.loads(SUMMARY.read_text(encoding='utf-8'))
    rows = [json.loads(x) for x in gzip.open(LEDGER, 'rt', encoding='utf-8')]
    cards = [json.loads(x) for x in gzip.open(CARD_INDEX, 'rt', encoding='utf-8')]
    errors = collections.Counter(); examples = []; card_sha_checked = 0
    src = MANAGER.read_text(); marker = '# Build historical coach timeline'
    ns = {'__file__': str(MANAGER), '__name__': 'referee_card_audit_bridge'}
    exec(compile(src[:src.index(marker)], str(MANAGER) + '[identity bridge verifier prefix]', 'exec'), ns)
    teammap, compmap = ns['teammap'], ns['cm']
    frozen = {str(json.loads(x)['fid']) for x in FOUNDATION.open(encoding='utf-8') if x.strip()}
    # Re-open each raw Crown card response by its SHA and verify card, score,
    # team and league fields against the public compact source index.
    games = {}
    with gzip.open(TM_GAMES, 'rt', encoding='utf-8') as f:
        for g in csv.DictReader(f): games[str(g['game_id'])] = g
    for c in cards:
        p = RAW / str(c['fid']) / (str(c['raw_response_sha256']) + '.json')
        if not p.is_file(): errors['card_raw_missing'] += 1; continue
        b = p.read_bytes(); h = hashlib.sha256(b).hexdigest()
        if h != c['raw_response_sha256']: errors['card_raw_sha_mismatch'] += 1; continue
        try:
            body = json.loads(b); d = body.get('data'); d = d[0] if isinstance(d, list) and d else d
        except Exception: errors['card_raw_json_error'] += 1; continue
        if (str(d.get('id')), str(d.get('l_id')), int(d.get('hg')), int(d.get('ag'))) != (c['fid'], c['league'], c['hg'], c['ag']): errors['card_raw_fixture_ft_mismatch'] += 1; continue
        mapped_h = teammap.get((c['league'], str(d.get('h_id')))); mapped_a = teammap.get((c['league'], str(d.get('a_id'))))
        if (mapped_h, mapped_a) != (str(c['home_tm_id']), str(c['away_tm_id'])): errors['card_raw_team_crosswalk_mismatch'] += 1; continue
        try: counts = tuple(int(d[k]) for k in ('hyc', 'ayc', 'hrc', 'arc'))
        except Exception: errors['card_raw_counts_missing'] += 1; continue
        if counts != (c['yellow_home'], c['yellow_away'], c['red_home'], c['red_away']): errors['card_raw_counts_mismatch'] += 1
        g = games.get(str(c['tm_game_id']))
        if not g: errors['card_tm_game_missing'] += 1; continue
        if (str(g['competition_id']), str(g['home_club_id']), str(g['away_club_id']), int(g['home_club_goals']), int(g['away_club_goals']), str(g['referee']).strip()) != (str(compmap.get(c['league'])), str(c['home_tm_id']), str(c['away_tm_id']), c['hg'], c['ag'], c['referee']):
            errors['card_tm_identity_or_referee_mismatch'] += 1; continue
        day = dt.date.fromisoformat(c['date']); tmday = dt.date.fromisoformat(g['date'])
        if abs((day - tmday).days) > 1: errors['card_tm_date_mismatch'] += 1; continue
        card_sha_checked += 1
    # Independent time-forward reconstruction from the compact source records.
    ref_hist = collections.defaultdict(list); comp_hist = collections.defaultdict(list)
    for c in cards:
        d = dt.date.fromisoformat(c['date']); y = c['yellow_home'] - c['yellow_away']; r = c['red_home'] - c['red_away']; key = (c['league'], norm(c['referee']))
        ref_hist[key].append((d, y, r, c['fid'], c['raw_response_sha256'])); comp_hist[c['league']].append((d, y, r, c['fid'], c['raw_response_sha256']))
    for x in list(ref_hist.values()) + list(comp_hist.values()): x.sort(key=lambda z: (z[0], z[3]))
    for row in rows:
        day = dt.date.fromisoformat(row['date']); cutoff = day - dt.timedelta(days=3); start = cutoff - dt.timedelta(days=365)
        prior = [x for x in ref_hist[(row['league'], norm(row['referee']))] if start <= x[0] < cutoff and x[3] != row['fid']]
        comp = [x for x in comp_hist[row['league']] if start <= x[0] < cutoff and x[3] != row['fid']]
        if len(prior) != row['ref_card_prior_n_365']: errors['feature_prior_n_mismatch'] += 1
        if prior:
            n = len(prior); cn = len(comp); shrink = n / (n + 5.)
            yy = sum(x[1] for x in prior) / n - (sum(x[1] for x in comp) / cn if cn else 0.)
            rr = sum(x[2] for x in prior) / n - (sum(x[2] for x in comp) / cn if cn else 0.)
            yhat = shrink * yy; rhat = shrink * rr
            src = hashlib.sha256('\n'.join(f'{x[3]}:{x[4]}' for x in prior).encode()).hexdigest()
            if abs(yhat - row['yellow_bias_prior']) > 1e-10 or abs(rhat - row['red_bias_prior']) > 1e-10: errors['feature_card_value_mismatch'] += 1
            if row['ref_card_prior_max_date'] != max(x[0] for x in prior).isoformat(): errors['feature_latest_date_mismatch'] += 1
            if src != row['ref_card_prior_source_sha256']: errors['feature_raw_history_sha_mismatch'] += 1
        elif row['ref_card_prior_source_sha256'] is not None or row['yellow_bias_prior'] is not None or row['red_bias_prior'] is not None:
            errors['feature_missing_history_not_null'] += 1
        if prior and max(x[0] for x in prior) >= cutoff: errors['feature_time_leakage'] += 1
        for method, m in row['methods'].items():
            odds = row['home_odds'] if m['side'] == 'home' else row['away_odds']
            state, u = settle(float(row['line']), m['side'], int(row['gd']), odds)
            if state != m['settlement'] or abs(u - float(m['net_u'])) > 1e-8:
                errors['settlement_mismatch'] += 1
                if len(examples) < 8: examples.append({'fid': row['fid'], 'method': method, 'expected': [state, u], 'saved': [m['settlement'], m['net_u']]})
    incremental = [r for r in rows if not r['frozen_eight_overlap']]
    for r in rows:
        if bool(r['frozen_eight_overlap']) != (str(r['fid']) in frozen): errors['frozen_membership_flag_mismatch'] += 1
    if len({r['fid'] for r in rows}) != len(rows): errors['duplicate_scored_FID'] += 1
    for method in summary['results']['outside_frozen_eight']:
        got = metric(incremental, method); exp = summary['results']['outside_frozen_eight'][method]
        for k in ('orders', 'net_u', 'roi_pct', 'mdd_u'):
            if got[k] != exp[k]: errors[f'summary_{method}_{k}'] += 1
        candidate = [r for r in incremental if r['methods'][method]['side'] is not None]
        if {r['fid'] for r in candidate} & frozen: errors[f'candidate_frozen_overlap_{method}'] += 1
        baseline = {str(json.loads(x)['fid']): json.loads(x) for x in FOUNDATION.open(encoding='utf-8') if x.strip() and int(json.loads(x)['year']) in (2024, 2025, 2026)}
        union = dict(baseline)
        for r in candidate:
            if r['fid'] in union: errors[f'union_duplicate_{method}'] += 1
            union[r['fid']] = {'date': r['date'], 'pnl': r['methods'][method]['net_u']}
        msum = round(sum(float(v.get('pnl', v.get('net_u'))) for v in union.values()), 6)
        expected = summary['merged_with_frozen_eight'][method]['merged_unique_fid']
        if len(union) != expected['orders'] or msum != expected['net_u']: errors[f'merged_summary_{method}'] += 1
    previous = json.loads(PREV_VERIFY.read_text(encoding='utf-8'))
    prev_ids = {json.loads(x)['fid'] for x in gzip.open(PREV_LEDGER, 'rt', encoding='utf-8')}
    tested = {r['fid'] for r in rows if r['year'] in (2024, 2025, 2026)}
    if not previous.get('pass') or previous.get('raw_crown_t1_audit', {}).get('raw_quote_verified') != 7081 or not tested <= prev_ids: errors['prior_raw_Crown_T1_verification_missing'] += 1
    result = {'study': 'M8_REFEREE_CARD_TENDENCY_INDEPENDENT_AUDIT', 'raw_card_source_rows': len(cards), 'raw_card_source_sha_verified': card_sha_checked, 'test_ledger_rows': len(rows), 'test_unique_fids': len({r['fid'] for r in rows}), 'outside_frozen_test_fids': len(incremental), 'method_settlement_rows': sum(len(r['methods']) for r in rows), 'all_test_target_fids_with_prior_Crown_T1_raw_audit': len(tested), 'inherited_raw_Crown_T1_audit_fids': 7081, 'errors': dict(errors), 'settlement_mismatch_examples': examples, 'input_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (LEDGER, SUMMARY, CARD_INDEX, TM_GAMES, FOUNDATION, PREV_VERIFY, PREV_LEDGER)}, 'pass': not errors and card_sha_checked == len(cards)}
    (OUT / 'independent_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_sha256', 'settlement_mismatch_examples')}, ensure_ascii=False, indent=2))
    if errors or card_sha_checked != len(cards): raise SystemExit('independent validation failed')


if __name__ == '__main__': main()
