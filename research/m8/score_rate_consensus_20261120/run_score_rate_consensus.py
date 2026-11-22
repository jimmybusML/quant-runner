#!/usr/bin/env python3
"""Test whether agreement between two pre-existing online score-rate estimates
reduces Crown AH losses without selecting outcome-based thresholds.

Research only. Inputs are local archival Crown path and score-only forecasts.
Historical source-event prices are not contemporaneous HTTP receipts.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
WORK = Path('/Users/mac/QuantAsiaDesk/research-work')
PATH_FILE = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
SCORE_FILE = WORK / 'm8_independent_score_strength_20261114.jsonl'
FROZEN_FILE = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
RECEIPT_FILE = WORK / 'm8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def line_returns(line: float, side: str, hg: int, ag: int, odds: float) -> tuple[str, float]:
    """AH stake return in units; quarter lines split into two half stakes."""
    margin = hg - ag if side == 'home' else ag - hg
    handicap = line if side == 'home' else -line
    q = round(handicap * 4)
    if abs(handicap * 4 - q) > 1e-8:
        raise ValueError(f'unsupported AH line {handicap}')
    if q % 2:
        low = math.floor(handicap * 2) / 2
        legs = (low, low + .5)
    else:
        legs = (handicap,)
    profits = []
    labels = []
    for leg in legs:
        adjusted = margin + leg
        if adjusted > 1e-9:
            labels.append('W'); profits.append(odds - 1)
        elif adjusted < -1e-9:
            labels.append('L'); profits.append(-1.0)
        else:
            labels.append('P'); profits.append(0.0)
    net = sum(profits) / len(profits)
    state = ('full_' + ('win' if net > 0 else 'loss') if 'P' not in labels
             else 'push' if net == 0 else 'half_' + ('win' if net > 0 else 'loss'))
    return state, net


def poisson_pmf(lam: float, max_goal: int = 24) -> list[float]:
    if not (0 <= lam < 15):
        raise ValueError(f'invalid lambda {lam}')
    p = [math.exp(-lam)]
    for k in range(1, max_goal + 1):
        p.append(p[-1] * lam / k)
    mass = sum(p)
    return [x / mass for x in p]


def expected_ah_pair(line: float, home_odds: float, away_odds: float, lh: float, la: float) -> tuple[float, float]:
    ph, pa = poisson_pmf(lh), poisson_pmf(la)
    margin_mass = collections.defaultdict(float)
    for hg, pgh in enumerate(ph):
        for ag, pga in enumerate(pa):
            margin_mass[hg-ag] += pgh * pga
    total_home = total_away = 0.0
    for margin, prob in margin_mass.items():
        _, pnl_home = line_returns(line, 'home', margin, 0, home_odds)
        _, pnl_away = line_returns(line, 'away', 0, margin, away_odds)
        total_home += prob * pnl_home
        total_away += prob * pnl_away
    return total_home, total_away


def choice(r: dict, suffix: str) -> tuple[str | None, float, float]:
    tag = '025' if suffix == '0.025' else '060'
    lh, la = float(r['lambda' + tag + '_home']), float(r['lambda' + tag + '_away'])
    eh, ea = expected_ah_pair(float(r['line_home']), float(r['home_odds']), float(r['away_odds']), lh, la)
    if abs(eh - ea) < 1e-12:
        return None, eh, ea
    return ('home' if eh > ea else 'away'), eh, ea


def week_of(r: dict) -> str:
    day = dt.date.fromisoformat(r['date'])
    iso = day.isocalendar()
    return f'{iso.year}-W{iso.week:02d}'


def metrics(rows: list[dict], method: str) -> dict:
    bet = [r for r in rows if r['methods'][method]['side'] is not None]
    n = len(bet); u = sum(r['methods'][method]['net_u'] for r in bet)
    daily = collections.defaultdict(float)
    weeks = collections.defaultdict(lambda: [0, 0.0])
    league = collections.defaultdict(lambda: [0, 0.0])
    for r in bet:
        daily[r['date']] += r['methods'][method]['net_u']
        w = week_of(r); weeks[w][0] += 1; weeks[w][1] += r['methods'][method]['net_u']
        league[r['league']][0] += 1; league[r['league']][1] += r['methods'][method]['net_u']
    cum = peak = mdd = 0.0
    for d in sorted(daily):
        cum += daily[d]; peak = max(peak, cum); mdd = max(mdd, peak - cum)
    dates = [r['date'] for r in rows]
    span_weeks = ((dt.date.fromisoformat(max(dates)) - dt.date.fromisoformat(min(dates))).days // 7 + 1) if dates else 0
    return {
        'orders': n, 'no_bet': len(rows)-n, 'net_u': round(u, 6),
        'roi_pct': round(100*u/n, 6) if n else None, 'mdd_u': round(mdd, 6),
        'avg_orders_per_calendar_week': round(n/span_weeks, 6) if span_weeks else 0,
        'calendar_weeks': span_weeks,
        'settlements': dict(collections.Counter(r['methods'][method]['settlement'] for r in bet)),
        'weekly': {k:{'n':v[0], 'net_u':round(v[1],6)} for k,v in sorted(weeks.items())},
        'league': {k:{'n':v[0], 'net_u':round(v[1],6), 'roi_pct':round(100*v[1]/v[0],6)} for k,v in sorted(league.items())},
    }


def cashflow_metrics(rows: list[dict]) -> dict:
    n=len(rows); u=sum(float(r['net_u']) for r in rows)
    daily=collections.defaultdict(float); weeks=collections.defaultdict(lambda:[0,0.0])
    for r in rows:
        daily[r['date']]+=float(r['net_u'])
        day=dt.date.fromisoformat(r['date']); iso=day.isocalendar(); w=f'{iso.year}-W{iso.week:02d}'
        weeks[w][0]+=1; weeks[w][1]+=float(r['net_u'])
    cum=peak=mdd=0.0
    for d in sorted(daily): cum+=daily[d]; peak=max(peak,cum); mdd=max(mdd,peak-cum)
    dates=[r['date'] for r in rows]
    span=((dt.date.fromisoformat(max(dates))-dt.date.fromisoformat(min(dates))).days//7+1) if dates else 0
    return {'orders':n,'net_u':round(u,6),'roi_pct':round(100*u/n,6) if n else None,
            'mdd_u':round(mdd,6),'avg_orders_per_calendar_week':round(n/span,6) if span else 0,
            'calendar_weeks':span,'weekly':{k:{'n':v[0],'net_u':round(v[1],6)} for k,v in sorted(weeks.items())}}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    score = {}
    for line in SCORE_FILE.open():
        r = json.loads(line); score[str(r['fid'])] = r
    frozen_rows = [json.loads(line) for line in FROZEN_FILE.open() if line.strip()]
    frozen = {str(r['fid']):r for r in frozen_rows}
    if len(frozen) != 10294: raise AssertionError(len(frozen))
    receipt_ids=set()
    if RECEIPT_FILE.exists():
        for line in RECEIPT_FILE.open():
            try: receipt_ids.add(str(json.loads(line)['fixture_id']))
            except (KeyError,ValueError): continue
    path = {}
    for line in PATH_FILE.open():
        r = json.loads(line); path[str(r['fid'])] = r
    rows, qc = [], collections.Counter()
    for fid, p in path.items():
        s = score.get(fid)
        if not s: qc['no_score_forecast'] += 1; continue
        if any(k not in p for k in ('end_line','home_price','away_price')):
            qc['missing_crown_ft_fields'] += 1; continue
        row = {
            'fid': fid, 'year': int(p['year']), 'date': p['date'], 'iso_week': week_of(p),
            'league': str(p['league']), 'home': str(s['home']), 'away': str(s['away']), 'kickoff_utc':s['ko'],
            'hg': int(s['hg']), 'ag': int(s['ag']), 'line_home': float(p['end_line']),
            'home_odds': float(p['home_price']), 'away_odds': float(p['away_price']),
            'frozen_eight_overlap': fid in frozen,
            'historical_fid_overlaps_actual_receipt_archive': fid in receipt_ids,
            'source_type': 'historical Crown source-event T1 path; retrospective replay',
            'score_feature_cutoff_rule': 'online score-only estimates used prior fixtures ending at least two UTC calendar days earlier; no as-received timestamp exists',
            'lambda025_home': float(s['lambda_home_0.025']), 'lambda025_away': float(s['lambda_away_0.025']),
            'lambda060_home': float(s['lambda_home_0.06']), 'lambda060_away': float(s['lambda_away_0.06']),
            'methods': {},
        }
        for key, suff in [('rate_025','0.025'), ('rate_060','0.06')]:
            side, eh, ea = choice(row, suff)
            row['methods'][key] = {'side': side, 'ev_home_u': round(eh,9), 'ev_away_u': round(ea,9)}
        a, b = row['methods']['rate_025']['side'], row['methods']['rate_060']['side']
        row['rate_agreement'] = bool(a is not None and b is not None and a == b)
        row['methods']['rate_agreement'] = {'side': a if row['rate_agreement'] else None}
        row['methods']['lower_price'] = {'side': 'home' if row['home_odds'] <= row['away_odds'] else 'away'}
        for name, m in row['methods'].items():
            side = m['side']
            if side is None:
                m.update({'settlement':'no_bet','net_u':0.0}); continue
            odds = row['home_odds'] if side == 'home' else row['away_odds']
            state, pnl = line_returns(row['line_home'], side, row['hg'], row['ag'], odds)
            m.update({'settlement':state,'net_u':round(pnl,10)})
        rows.append(row)
    rows.sort(key=lambda x:(x['date'],x['fid']))
    methods = ['rate_025','rate_060','rate_agreement','lower_price']
    results = {'all':{},'outside_frozen_eight':{},'by_year':{},'outside_by_year':{},'agreement_diagnostic':{}}
    for method in methods:
        results['all'][method] = metrics(rows,method)
        results['outside_frozen_eight'][method] = metrics([r for r in rows if not r['frozen_eight_overlap']],method)
    for year in sorted({r['year'] for r in rows if r['year']>=2024}):
        cohort = [r for r in rows if r['year']==year]
        outside = [r for r in cohort if not r['frozen_eight_overlap']]
        results['by_year'][str(year)] = {m:metrics(cohort,m) for m in methods}
        results['outside_by_year'][str(year)] = {m:metrics(outside,m) for m in methods}
    for label, subset in [('agree',[r for r in rows if r['rate_agreement']]),('disagree',[r for r in rows if not r['rate_agreement']])]:
        outside = [r for r in subset if not r['frozen_eight_overlap']]
        results['agreement_diagnostic'][label] = {
            'all':{m:metrics(subset,m) for m in ('rate_025','rate_060','lower_price')},
            'outside_frozen_eight':{m:metrics(outside,m) for m in ('rate_025','rate_060','lower_price')},
        }
    candidate_ids={r['fid'] for r in rows if r['year']>=2024 and not r['frozen_eight_overlap']}
    target_rows=[r for r in rows if r['year']>=2024]
    target_years={2024,2025,2026}
    frozen_target=[{'fid':str(f['fid']),'date':str(f['date']),'year':int(f['year']),'net_u':float(f['pnl'])}
                   for f in frozen_rows if int(f['year']) in target_years]
    frozen_ids_target={r['fid'] for r in frozen_target}
    merged={}
    for method in methods:
        selected=[{'fid':r['fid'],'date':r['date'],'year':r['year'],'net_u':r['methods'][method]['net_u']}
                  for r in target_rows if not r['frozen_eight_overlap'] and r['methods'][method]['side'] is not None]
        cand_ids={r['fid'] for r in selected}
        union=[r for r in frozen_target]+selected
        merged[method]={'frozen_eight_target':cashflow_metrics(frozen_target),
                        'candidate_outside_frozen_eight':cashflow_metrics(selected),
                        'merged_unique_fid':cashflow_metrics(union),
                        'frozen_target_fids':len(frozen_ids_target),'candidate_unique_fids':len(cand_ids),
                        'candidate_frozen_overlap':len(cand_ids & frozen_ids_target)}
    summary={
        'study':'M8 pre-existing online score-estimator rate agreement for Crown AH side selection; historical event-time only',
        'scope':{'path_rows':len(path),'score_rows':len(score),'joined_rows':len(rows),'joined_years':dict(collections.Counter(r['year'] for r in rows)),'frozen_members':len(frozen),'unique_incremental_2024_2026':len(candidate_ids),'receipt_archive_unique_fid_overlap':len(candidate_ids & receipt_ids),'receipt_overlap_feature_rows_lacking_verified_as_received_score_snapshot':len(candidate_ids & receipt_ids),'coverage_issues':dict(qc)},
        'inputs':{str(p):sha(p) for p in (PATH_FILE,SCORE_FILE,FROZEN_FILE,RECEIPT_FILE) if p.exists()},
        'methodology':{
            'features':'Two pre-existing online attack/defense score-only rate configurations, learning rates 0.025 and 0.06; use only events at least two UTC calendar days earlier, same target FID joined to Crown AH T1 source-event line/odds/FT.',
            'decision':'For each model choose the side with the larger independent-Poisson expected AH net return at actual Crown line and odds; test each rate separately and place the same side only when both choose it. A disagreement is no bet. No threshold search.',
            'poisson_tail':'Goals 0..24 with probabilities renormalized; tail probability is numerically negligible for observed rates. Quarter lines are split into two half stakes.',
            'time_forward':'Forecasts are precomputed online without target match score; target reporting uses Crown local/Beijing year. Historical features have no first-received timestamp.',
            'selection_note':'The model family and target years were previously studied; this agreement policy is a retrospective diagnostic, not an unseen test.',
            'receipt_note':'Crown actual HTTP receipt archive is only used for FID intersection. Historical score features have no verified as-received snapshots; no valid live feature replay is claimed.',
        },
        'results':results,
        'merged_with_frozen_eight_2024_2026':merged,
        'production_changes':False,'formal_orders':0,'formal_ledger_writes':0,
    }
    (OUT/'score_rate_consensus_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    with io.TextIOWrapper(gzip.GzipFile(filename=str(OUT/'score_rate_consensus_per_fixture.jsonl.gz'),mode='wb',compresslevel=9,mtime=0),encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    compact=lambda x:{k:v for k,v in x.items() if k not in ('weekly','league','settlements')}
    print(json.dumps({'scope':summary['scope'],'outside_2024_2026':{m:compact(summary['results']['outside_frozen_eight'][m]) for m in methods},'annual_outside':{y:{m:compact(d[m]) for m in methods} for y,d in summary['results']['outside_by_year'].items()},'merged':{m:{k:compact(v) if isinstance(v,dict) and 'orders' in v else v for k,v in d.items()} for m,d in merged.items()}},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
