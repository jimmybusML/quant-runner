#!/usr/bin/env python3
"""R10-E: incremental probability information beyond R7 same-game Crown AH+OU
market-implied Poisson forecast. All 9908 identical fixtures and target scores.
No optimization: fixed market-only, xG-only, 75/25 and 50/50 blends.
Proper Brier and logloss ONLY; NO market prices turned into fake betting ROI.
"""
from pathlib import Path
from collections import defaultdict
import json,hashlib,math
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
G=HERE/'r10_Gamma_xG_posterior_predictive_20261123.jsonl'
D=HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_20261123.jsonl'
NB=HERE/'r10_prev_two_season_asof_negative_binomial_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
CROWN=R5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
OUT=HERE/'r10_vs_Crown_market_incremental_probabilities.json'
LEDGER=HERE/'r10_vs_Crown_market_incremental_1X2_20261123.jsonl'
g={(r['league'],r['fixture_id']):r for r in map(json.loads,G.open())}
d={(r['league'],r['fixture_id']):r for r in map(json.loads,D.open())}
n={(r['league'],r['fixture_id']):r for r in map(json.loads,NB.open())}
market={r['fid']:r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
crown={}
for r in map(json.loads,CROWN.open()):
    if r['market']=='AH':crown[(r['league'],r['fixture_id'])]=r['fid']
assert len(g)==len(d)==len(n)==len(crown)==len(market)==9908
variants=['Gamma_xG_k1','Gamma_xG_k2','dynamic_Kalman','goal_total_NB_k2']
def brier(prob,score):
    h,a=map(int,score.split('-'))
    target=0 if h>a else 1 if h==a else 2
    return {'brier':sum((p-float(i==target))**2 for i,p in enumerate(prob)),
        'logloss':-math.log(max(prob[target],1e-15))}
def weight(a,b,market_weight):
    return [market_weight*x+(1-market_weight)*y for x,y in zip(a,b)]
rows=[]
for key in sorted(crown):
    r=g[key];q=d[key];p=n[key];m=market[crown[key]]
    sc=r['score']
    if sc!=q['score'] or sc!=p['score'] or sc!=m['score']:
        raise RuntimeError(('different outcomes',key))
    market_probs=[m['models']['market_implied_Poisson'][x] for x in
                  ('1X2_p_home','1X2_p_draw','1X2_p_away')]
    forecast={
      'Crown_AH_OU_market':market_probs,
      'Gamma_xG_k1':r['methods']['gamma_obs_k1']['prob_1X2'],
      'Gamma_xG_k2':r['methods']['gamma_obs_k2']['prob_1X2'],
      'dynamic_Kalman':q['p_1x2'],
      'goal_total_NB_k2':p['p_1x2']}
    for var in variants:
        forecast['market75_'+var+'25']=weight(market_probs,forecast[var],.75)
        forecast['market50_'+var+'50']=weight(market_probs,forecast[var],.5)
    report={'league':r['league'],'fixture_id':r['fixture_id'],
        'season':r['season'],'score':sc,
        'methods':{label:brier(vals,sc) for label,vals in forecast.items()}}
    if any(abs(sum(vals)-1)>1e-8 for vals in forecast.values()):
        raise RuntimeError(('invalid probability sum',key))
    rows.append(report)
def summary(sub):
    x={'n':len(sub)}
    if not sub:return x
    labels=rows[0]['methods'].keys()
    for method in labels:
        x[method]={'Brier':round(sum(r['methods'][method]['brier'] for r in sub)/len(sub),7),
                   'logloss':round(sum(r['methods'][method]['logloss'] for r in sub)/len(sub),7)}
    x['best_single_model_by_Brier_is_descriptive_NOT_a_trading_selection_rule']=min(variants,key=lambda label:x[label]['Brier'])
    return x
stats={'study':'R10_ASOF_MODELS_INCREMENTAL_PROBABILITY_VS_CROWN_MARKET_PREGAME_HISTORICAL',
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (G,D,NB,MARKET,CROWN)},
 'scope':'Five domestic club leagues, exactly same 9908 historical source-event Crown paired fixtures, no national teams.',
 'methods':'The Crown market distribution is inferred from its same-event AH+OU prices. Compare each new model and 75% market /25% model or 50/50 fixed probability mixtures. None of the fixed weights was selected to maximize historic ROI or Brier; no order eligibility Gate.',
 'overall':summary(rows),
 'by_year':{str(year):summary([r for r in rows if r['season']==year]) for year in range(2019,2026)},
 'by_league':{league:summary([r for r in rows if r['league']==league]) for league in sorted({r['league'] for r in rows})},
 'limitations':['Brier does NOT imply bet profitability; benchmark Crown uses SAME odds and no independent market executable price.',
 'Historic Crown T12 source event retrieved after target game; not actually received historical quote.',
 'All R5-R10 model versions repeatedly explored same games, so exploratory comparisons are not fresh blind performance.',
 'No target-year goals or returns trained the Gamma xG shape or dynamic Q/R; prior-year goals train NB dispersion as method.',
 'No national teams, no new production rules or Telegram sends.']}
with LEDGER.open('w') as f:
    for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
OUT.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'n':len(rows),
    'comparisons':{name:stats['overall'][name] for name in
       ('Crown_AH_OU_market','Gamma_xG_k1','Gamma_xG_k2','dynamic_Kalman','goal_total_NB_k2',
        'market75_Gamma_xG_k1'+'25','market50_Gamma_xG_k1'+'50',
        'market75_Gamma_xG_k2'+'25','market50_Gamma_xG_k2'+'50')}},ensure_ascii=False))
