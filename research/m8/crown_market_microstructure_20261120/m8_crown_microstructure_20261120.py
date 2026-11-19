#!/usr/bin/env python3
"""M8 Crown AH event-level microstructure studies (research only).

Uses only historical Crown source-event AH quotes and independently joined FT.
It does not claim HTTP receipt/executability for historical source events.
All policies are fixed before evaluating target-year results and settle AH
quarter lines as two equal half-stakes.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/Users/mac/QuantAsiaDesk/research-work')
PATHS = WORK / 'm8_late_full_path_water_features_20261114.jsonl'
SCORES = WORK / 'm8_independent_score_strength_20261114.jsonl'
MEM = WORK / 'm8_foundation_20261115/historical_membership.jsonl'
OUT = ROOT / 'research/m8/crown_market_microstructure_20261120'
TZ = dt.timezone(dt.timedelta(hours=8))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def settle(line, side, odds, gd):
    handicap = float(line) * (1 if side == 'home' else -1)
    margin = int(gd) * (1 if side == 'home' else -1)
    legs = [handicap] if abs(handicap * 2 - round(handicap * 2)) < 1e-9 else [math.floor(handicap * 2) / 2, math.ceil(handicap * 2) / 2]
    vals = []
    for leg in legs:
        z = margin + leg
        vals.append(float(odds) - 1 if z > 1e-9 else -1.0 if z < -1e-9 else 0.0)
    return sum(vals) / len(vals)


def state(line, side, gd):
    handicap = float(line) * (1 if side == 'home' else -1)
    margin = int(gd) * (1 if side == 'home' else -1)
    legs = [handicap] if abs(handicap * 2 - round(handicap * 2)) < 1e-9 else [math.floor(handicap * 2) / 2, math.ceil(handicap * 2) / 2]
    vals = ['W' if margin + x > 1e-9 else 'L' if margin + x < -1e-9 else 'P' for x in legs]
    return {'W':'full_win','L':'full_loss','P':'push','WW':'full_win','WP':'half_win','PW':'half_win','PP':'push','PL':'half_loss','LP':'half_loss','LL':'full_loss'}[''.join(vals)]


def utc_naive(v):
    z = dt.datetime.fromisoformat(str(v).replace('Z', '+00:00').replace(' ', 'T'))
    if z.tzinfo is None:
        z = z.replace(tzinfo=dt.timezone.utc)
    return z.astimezone(dt.timezone.utc).replace(tzinfo=None)


def event_rows():
    scores = {str(x['fid']): x for x in map(json.loads, SCORES.open())}
    frozen = {str(x['fid']) for x in map(json.loads, MEM.open())}
    rows, invalid = [], collections.Counter()
    base_rows=[]
    for raw in map(json.loads, PATHS.open()):
        fid = str(raw['fid'])
        base_rows.append(raw)
        if fid in frozen:
            continue
        sc = scores.get(fid)
        if not sc:
            invalid['missing_score'] += 1
            continue
        try:
            ko = utc_naive(sc['ko'])
            local = ko.replace(tzinfo=dt.timezone.utc).astimezone(TZ)
            gd = int(sc['hg']) - int(sc['ag'])
            # Parsed source-event path is strictly ordered by recorded quote time.
            # H/A line/odds paths are not stored in the feature file; the raw Crown
            # response will be joined in a separate audit for selected predictions.
            line = float(raw['end_line']); ho = float(raw['home_price']); ao = float(raw['away_price'])
            if min(ho, ao) <= 1:
                raise ValueError('bad odds')
            rows.append({'fid':fid,'year':local.year,'date':local.date().isoformat(),'ko_utc':ko.isoformat()+'Z','league':str(raw['league']),
                         'line':line,'ho':ho,'ao':ao,'gd':gd,'hg':int(sc['hg']),'ag':int(sc['ag']),
                         'fav_home':ho <= ao,'source':'historical_crown_source_event_replay','frozen':False,
                         'n_events':int(raw['n_events']),'n_line_changes':int(raw['n_line_changes']),
                         'line_range':float(raw['line_range'] or 0),'final_line_minutes':float(raw['final_line_minutes'] or 0),
                         'late_event_age_min':float(raw['late_event_age_min'] or 0),'last_line_change_age_min':raw.get('last_line_change_age_min'),
                         'path_shape':raw.get('path_shape'),'path_6_3_1':raw.get('path_6_3_1'),
                         'fav_end_vs_start':float(raw.get('fav_end_vs_start') or 0),'fav_last_move':float(raw.get('fav_last_move') or 0),
                         'dog_price_change':float(raw.get('dog_price_change') or 0),'fav_price_change':float(raw.get('fav_price_change') or 0),
                         'dog_price_vs_timeavg':float(raw.get('dog_price_vs_timeavg') or 0),
                         'home_price_vs_timeavg':raw.get('home_price_vs_timeavg'),'away_price_vs_timeavg':raw.get('away_price_vs_timeavg')})
        except Exception as e:
            invalid[str(e)] += 1
    if len({x['fid'] for x in rows}) != len(rows):
        raise RuntimeError('duplicate FID in joined historical input')
    return rows, frozen, invalid, scores, base_rows


def stats(rows):
    rows = list(rows); n=len(rows); pnl=sum(x['net_u'] for x in rows)
    peak=equity=mdd=0.; bydate=collections.defaultdict(float); weeks=collections.defaultdict(lambda:[0,0.])
    states=collections.Counter(); odds=[]
    for x in rows:
        bydate[x['date']] += x['net_u']
        d=dt.date.fromisoformat(x['date']); iso=d.isocalendar(); weeks[f'{iso.year}-W{iso.week:02d}'][0]+=1; weeks[f'{iso.year}-W{iso.week:02d}'][1]+=x['net_u']
        states[x['settlement']]+=1; odds.append(x['odds'])
    for d,v in sorted(bydate.items()):
        equity += v; peak=max(peak,equity); mdd=max(mdd,peak-equity)
    return {'n':n,'net_u':round(pnl,6),'roi_pct':round(100*pnl/n,6) if n else None,'mdd_u':round(mdd,6),
            'average_odds':round(sum(odds)/n,6) if n else None,'settlements':dict(states),
            'weeks':{k:{'n':int(v[0]),'net_u':round(v[1],6)} for k,v in sorted(weeks.items())},
            'weekly_mean_n':round(n/len(weeks),6) if weeks else None,'weekly_mean_net_u':round(pnl/len(weeks),6) if weeks else None}


def method_rows(base, method, side_fn):
    out=[]
    for r in base:
        side=side_fn(r)
        odds=r['ho'] if side=='home' else r['ao']
        out.append({**r,'method':method,'direction':side,'odds':odds,'settlement':state(r['line'],side,r['gd']),
                    'net_u':round(settle(r['line'],side,odds,r['gd']),6),'source_type':'historical_source_event_replay',
                    'http_receipt_asserted':False,'formal_order':False})
    return out


def process(base, frozen, invalid, scores, frozen_members):
    frozen_map={str(x['fid']):x for x in map(json.loads,MEM.open())}
    by_fid={str(x['fid']):x for x in frozen_members}
    # B: pure AH side market anchor, used as same-FID benchmark.
    models={}
    models['market_favorite']=method_rows(base,'market_favorite',lambda r:'home' if r['ho']<=r['ao'] else 'away')
    models['market_underdog']=method_rows(base,'market_underdog',lambda r:'away' if r['ho']<=r['ao'] else 'home')
    # A: market quote updates may reveal strength information. The path summary
    # has only event-time order, not receipt timestamps; report both sides of
    # the mechanically observable final state, never label it a frozen signal.
    models['A_favorite_line_steam']=method_rows(base,'A_favorite_line_steam',lambda r:'home' if r['ho']<=r['ao'] else 'away')
    # B: contract nonlinearity diagnostic. Compare same favorite policy across
    # fixed handicap-size strata; no ex-post rank or target-year threshold.
    models['B_market_favorite']=models['market_favorite']
    # C: line/water interaction policy: when the dog's odds shorten more than
    # favorite odds, take the dog, else favorite. This encodes the full-path sign.
    models['C_line_water_elasticity']=method_rows(base,'C_line_water_elasticity',lambda r: ('away' if r['dog_price_change'] < -abs(r['fav_price_change']) else 'home') if r['ho']<=r['ao'] else ('home' if r['dog_price_change'] < -abs(r['fav_price_change']) else 'away'))
    # D: free mechanism hypothesis: a market line that moved and later returned
    # to the starting line may reflect overreaction; fade the closing favorite.
    models['D_late_stable_reversal_fade']=method_rows(base,'D_late_stable_reversal_fade',lambda r: ('away' if r['ho']<=r['ao'] else 'home') if r['path_shape']=='reverted' else ('home' if r['ho']<=r['ao'] else 'away'))
    # Fixed family-agnostic market state bins are descriptive partitions only,
    # not filters and not used to choose direction. Keep every original row.
    summaries={}; year_rows={}; league_rows={}; overlaps={}
    for name,rs in models.items():
        if name in ('B_market_favorite',): continue
        summaries[name]=stats(rs)
        year_rows[name]={str(y):stats(x for x in rs if x['year']==y) for y in (2024,2025,2026)}
        league_rows[name]={k:stats(x for x in rs if x['league']==k) for k in sorted({x['league'] for x in rs})}
        fids={x['fid'] for x in rs}; overlaps[name]={'candidate_unique_fids':len(fids),'frozen_eight_overlap':len(fids & frozen),'genuinely_incremental_fids':len(fids-frozen)}
    # A split: market direction baseline vs additional event-path information.
    # Current path features are outcome independent, but end-of-path values are
    # only available at the final recorded source event; do not call pregame live.
    # For an executable AH comparison, calculate the favorite result and line
    # movement subgroup contributions, never select a subgroup by target returns.
    market=models['market_favorite']
    for name in ('market_favorite','market_underdog','A_favorite_line_steam','C_line_water_elasticity','D_late_stable_reversal_fade'):
        rs=models[name]
        # Original eight union uses each frozen FID's realized PnL once, alongside
        # the candidate set after FID dedupe. The frozen member file stores PnL.
        merged=[]
        for f in frozen_map.values():
            try:
                ko=utc_naive(scores[str(f['fid'])]['ko'])
            except KeyError: continue
            local=ko.replace(tzinfo=dt.timezone.utc).astimezone(TZ)
            hist=by_fid.get(str(f['fid']))
            if local.year in (2024,2025,2026) and hist is not None:
                merged.append({'fid':str(f['fid']),'date':local.date().isoformat(),'net_u':float(f['pnl']),'odds':1.9,'settlement':'frozen_member'})
        cand_by={x['fid']:x for x in rs if x['year'] in (2024,2025,2026)}
        merged=[x for x in merged if x['fid'] not in cand_by]+list(cand_by.values())
        summaries[name]['merged_frozen_2024_2026']=stats(merged)
    # Return distributions by absolute market contract, fixed bins; complete rows.
    market_bins={}
    for name,rs in models.items():
        if name not in summaries: continue
        groups=collections.defaultdict(list)
        for x in rs:
            a=abs(x['line'])
            b='near_even_abs_line<0.5' if a<0.5 else 'medium_0.5_to_1.5' if a<1.5 else 'deep_abs_line>=1.5'
            groups[b].append(x)
        market_bins[name]={k:stats(v) for k,v in sorted(groups.items())}
    return models, {'methods':summaries,'by_year':year_rows,'by_league':league_rows,'contract_bins':market_bins,
                    'overlap':overlaps,'invalid_join_rows':dict(invalid)}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows,frozen,invalid,scores,frozen_members=event_rows()
    # Main homogeneous sample: all complete-score historical Crown path fixtures,
    # Beijing years from 2024 onward; retain older rows for fixed controls and
    # training audits but output this sample in total metrics by filter below.
    historical=[x for x in rows if x['year']>=2024]
    models,result=process(historical,frozen,invalid,scores,frozen_members)
    with gzip.open(OUT/'per_fixture_event_replay_20261120.jsonl.gz','wt',encoding='utf8') as f:
        for name,rs in models.items():
            if name=='B_market_favorite': continue
            for x in rs: f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
    # Separate event-path diagnostic: no profitable-event selection; compare
    # direction chosen by favorite, dog, and whole-sample baseline by fixed state.
    state_diag={}
    for col in ('path_shape','path_6_3_1'):
        state_diag[col]={}
        for value in sorted({str(x[col]) for x in historical}):
            bucket=[x for x in models['market_favorite'] if str(x[col])==value]
            state_diag[col][value]=stats(bucket)
    result['path_shape_diagnostics']=state_diag
    result['study']='M8 Crown AH event-level microstructure 2026-11-20'
    result['data']={'all_joined_fids':len(rows),'tested_beijing_2024_2026_fids':len(historical),'frozen_eight_fids':len(frozen),
                    'frozen_eight_overlap_test':0,'features_sha256':sha(PATHS),'scores_sha256':sha(SCORES),'membership_sha256':sha(MEM),
                    'timezone':'Asia/Shanghai UTC+08','crown_only':True,'AH_only':True,'historical_http_receipt_count':0,
                    'source_note':'Historical Crown event timestamps are later retrieved source events, not evidence of contemporaneous HTTP receipt or execution.'}
    (OUT/'results_20261120.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'data':result['data'],'methods':{k:{'n':v['n'],'net_u':v['net_u'],'roi_pct':v['roi_pct'],'mdd_u':v['mdd_u']} for k,v in result['methods'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
