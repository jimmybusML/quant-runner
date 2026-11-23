#!/usr/bin/env python3
"""R7 C: Does a fixed independent xG probability mixture improve beyond
MARKET AH+OU implied 1X2? No ROI selection, no Gate, only proper scores.
Test historical and old actually-received pregame price samples separately.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r7_market_pricing_20261123'
SOURCE=HERE/'r7_market_implied_2market_20261123.jsonl'
OUT=HERE/'r7_market_vs_Bayes_fixed_blend_score.json'
LEDGER=HERE/'r7_market_vs_Bayes_fixed_blend_score.jsonl'
rows=[json.loads(x) for x in SOURCE.open()]
variants=('market_alone','Bayes_k1_alone','Bayes_k2_alone',
          'market_plus_Bayes_k1_50_50','market_plus_Bayes_k2_50_50',
          'market_plus_Bayes_k1_75_25')
results=[]
def proba(x):
    return [x['1X2_p_home'],x['1X2_p_draw'],x['1X2_p_away']]
def score(p,sc):
    hg,ag=map(int,sc.split('-'))
    y=0 if hg>ag else 1 if hg==ag else 2
    return {'Brier':sum((q-float(i==y))**2 for i,q in enumerate(p)),
            'logloss':-math.log(max(p[y],1e-15))}
for r in rows:
    market=r['models'].get('market_implied_Poisson')
    if not market:continue
    m=proba(market)
    label1='bayes_prior_1_independent' if r['cohort']=='historical_Crown_T12' else 'bayes_1_independent'
    label2='bayes_prior_2_independent' if r['cohort']=='historical_Crown_T12' else 'bayes_2_independent'
    a=proba(r['models'][label1]);b=proba(r['models'][label2])
    ps={'market_alone':m,'Bayes_k1_alone':a,'Bayes_k2_alone':b,
        'market_plus_Bayes_k1_50_50':[(u+v)/2 for u,v in zip(m,a)],
        'market_plus_Bayes_k2_50_50':[(u+v)/2 for u,v in zip(m,b)],
        'market_plus_Bayes_k1_75_25':[.75*u+.25*v for u,v in zip(m,a)]}
    result={'fid':r['fid'],'cohort':r['cohort'],'season':r['season'],
      'league':r['league'],'score':r['score'],
      'forecast':{k:{**score(p,r['score']),'p_home':p[0],'p_draw':p[1],'p_away':p[2]} for k,p in ps.items()}}
    results.append(result)
def agg(rs):
    o={'n':len(rs)}
    for k in variants:
        vals=[r['forecast'][k] for r in rs]
        o[k]={'Brier':round(sum(x['Brier'] for x in vals)/len(vals),7) if vals else None,
           'logloss':round(sum(x['logloss'] for x in vals)/len(vals),7) if vals else None}
    o['Bayes_k2_plus_market_vs_market_Brier_delta']=round(o['market_plus_Bayes_k2_50_50']['Brier']-o['market_alone']['Brier'],7) if rs else None
    return o
historical=[r for r in results if r['cohort']=='historical_Crown_T12']
receipt=[r for r in results if r['cohort']=='actual_HTTP_2026_receipt']
assert len(historical)==9908 and len(receipt)==138
out={'study':'R7_MARKET_VS_XG_INDEPENDENT_INCREMENTAL_1X2_SCORE',
  'data_source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
  'fixed_weights_only':'50/50 and market .75 + Bayes k1 .25 are research sensitivities; weights not fitted to ROI or validation outcomes',
  'overall':{'historical_Crown_T12':agg(historical),'actual_HTTP_2026_receipt':agg(receipt)},
  'by_season':{str(y):agg([r for r in historical if r['season']==y]) for y in sorted({r['season'] for r in historical})},
  'by_league':{lg:agg([r for r in historical if r['league']==lg]) for lg in sorted({r['league'] for r in historical})},
  'limitations':['Market model fits to SAME pre-match AH/OU odds; no independent bookmaker price info',
    'xG models source time may be post-match published; old receipt has +72h proxy only',
    'Market-fitted score probabilities cannot be called profitable or tradable by themselves',
    'Historical Crown T12 source events retrieved AFTER match; actual HTTP receipts are prior-researched posthoc replay',
    'No national team events, no Gate or formal strategy modification.']}
with LEDGER.open('w') as f:
 for row in results:f.write(json.dumps(row,ensure_ascii=False)+'\n')
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':out['overall'],'years':{y:{k:x[k]['Brier'] for k in ('market_alone','Bayes_k2_alone','market_plus_Bayes_k2_50_50')} for y,x in out['by_season'].items()}},ensure_ascii=False))