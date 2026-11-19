#!/usr/bin/env python3
"""Research-only Crown AH odds-margin decomposition on frozen-eight excluded matches.

Counterfactual 0-overround payout is *NOT* an executable bet.
No new signal, no selection gate, no model modification.
"""
import collections, datetime as dt, hashlib,json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
FEAT=WORK/'m8_late_full_path_water_features_20261114.jsonl'
FROZEN=WORK/'m8_foundation_20261115/historical_membership.jsonl'
RUN=ROOT/'research/m8/m8_large_sample_regime_walkforward_20261119/per_fixture_predictions.jsonl'
OUT=ROOT/'research/m8/m8_crown_dutching_feasibility_20261119'
def val(x):return float(x)
def gain(u,price,margin):
    return max(0.,float(u))/(float(price)-1.)*float(price)*margin
def stat(a):
    n=len(a);v=sum(x[1] for x in a);cf=sum(x[2] for x in a)
    return {'n':n,'actual_U':round(v,4),'actual_roi_pct':round(v/n*100,4) if n else None,
            'zero_vig_counterfactual_U':round(cf,4),
            'zero_vig_roi_pct':round(cf/n*100,4) if n else None,
            'vig_uplift':round(cf-v,4)}
def main():
    frozen={str(json.loads(l)['fid']) for l in FROZEN.open() if l.strip()}
    data={}; yrs=collections.defaultdict(list); leagues=collections.defaultdict(lambda:collections.defaultdict(list))
    for l in FEAT.open():
        r=json.loads(l);fid=str(r['fid'])
        if fid in frozen or int(r['year']) not in (2024,2025,2026):continue
        h=float(r['home_price']);a=float(r['away_price']);m=1/h+1/a-1
        if m<0:raise AssertionError('not matched underround')
        data[fid]={'year':int(r['year']),'league':str(r.get('league')),'date':r['date'],'margin':m,
                   'home':(float(r['end_home_U']),h),'away':(float(r['end_away_U']),a)}
        yrs[int(r['year'])].append(m);leagues[str(r.get('league'))][int(r['year'])].append(m)
    methods=collections.defaultdict(list); yearly=collections.defaultdict(lambda:collections.defaultdict(list))
    for l in RUN.open():
        r=json.loads(l);fid=r['fid'];year=int(r['year'])
        if year not in (2024,2025,2026):continue
        x=data[fid]
        assert x['year']==year
        u,odds=x[r['side']]
        assert abs(u-float(r['pnl_u']))<1e-8
        cf=u+gain(u,odds,x['margin'])
        methods[r['family']].append((fid,u,cf))
        yearly[r['family']][year].append((fid,u,cf))
    result={
      'meaning':'No-vig payouts multiply each outcome odds by its same-quote reciprocal sum. This is an accounting upper-price counterfactual, not available executable odds.',
      'used_source':'Crown T1 post-retrieved AH same match home/away; frozen-eight FIDs excluded',
      'frozen_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
      'input_sha256':hashlib.sha256(FEAT.read_bytes()).hexdigest(),
      'actual_quotes_count':len(data),
      'source_years':{str(y):{'n':len(v),'mean_quote_overround_pct':round(sum(v)/len(v)*100,5),
        'min_overround_pct':round(min(v)*100,5),
        'max_overround_pct':round(max(v)*100,5)} for y,v in sorted(yrs.items())},
      'selected_methods':{},
    }
    both=[l for l in leagues.values() if 2024 in l and 2026 in l]
    result['overlapping_leagues_2024_2026']={
      'common_league_ids':len(both),
      'higher_overround_2026':sum(sum(v[2026])/len(v[2026]) > sum(v[2024])/len(v[2024]) for v in both),
      'lower_overround_2026':sum(sum(v[2026])/len(v[2026]) < sum(v[2024])/len(v[2024]) for v in both)}
    for family,rows in methods.items():
        assert len(rows)==len({r[0] for r in rows})
        result['selected_methods'][family]={
            '2024_2026':stat(rows),
            'by_year':{str(y):stat(v) for y,v in sorted(yearly[family].items())}}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'margin_decomposition.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('QUOTE_YEARS',json.dumps(result['source_years'],ensure_ascii=False))
    print('LEAGUES',json.dumps(result['overlapping_leagues_2024_2026'],ensure_ascii=False))
    for k,v in result['selected_methods'].items():
        x=v['2024_2026']
        print('METHOD',k,x['n'],x['actual_U'],x['zero_vig_counterfactual_U'],x['vig_uplift'])
if __name__=='__main__':main()
