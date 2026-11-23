#!/usr/bin/env python3
"""R6 equal probability-score mixtures on the exact old R5 2026/27 actual
received (but posthoc evaluated) Crown HTTP cohort. No production change.
"""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
import json,hashlib,math
import numpy as np
R=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=R/'r6_bayes_bivar_20261123'
SRC=R/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research/r5_bayes_bivar_actual_receipt_20261123.jsonl'
LEDGER=HERE/'r6_actual_receipt_equal_weight_blends.jsonl'
SUMMARY=HERE/'r6_actual_receipt_equal_weight_blends.json'
M=20
K=np.arange(M+1,dtype=float)
H=K[:,None];A=K[None,:]
def poisson(x):
    z=np.zeros(M+1);z[0]=math.exp(-x)
    for i in range(1,M+1):z[i]=z[i-1]*x/i
    return z/z.sum()
def joint(h,a,c):
    if c==0:return np.outer(poisson(h),poisson(a))
    x=poisson(h-c);y=poisson(a-c);w=poisson(c)
    z=np.zeros((M+1,M+1))
    for k,pk in enumerate(w):
        if pk<1e-16:continue
        n=M+1-k
        z[k:,k:]+=pk*np.outer(x[:n],y[:n])
    return z/z.sum()
def legs(line):
    q=round(line*4)
    assert abs(q/4-line)<1e-9
    return [(line,1.)] if q%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
def cash(market,line,odds,side,score):
    hg,ag=map(int,score.split('-'))
    out=0.
    for leg,w in legs(line):
        if side=='home':d=hg-ag+leg
        elif side=='away':d=ag-hg-leg
        elif side=='over':d=hg+ag-leg
        else:d=leg-hg-ag
        out+=w*((odds-1.) if d>1e-9 else -1. if d<-1e-9 else 0.)
    return out
def expval(market,line,odds,side,p):
    v=0.
    for leg,w in legs(line):
        if side=='home':d=H-A+leg
        elif side=='away':d=A-H-leg
        elif side=='over':d=H+A-leg
        else:d=leg-H-A
        v+=w*float((p*np.where(d>1e-9,odds-1.,np.where(d< -1e-9,-1.,0.))).sum())
    return v
r5=[json.loads(x) for x in SRC.open()]
assert len(r5)==276
out=[];checks=Counter()
lastfid=None;P={}
for r in r5:
    if r['fid']!=lastfid:
        lastfid=r['fid'];P={}
        for name in ('same_season_ratio_independent','bayes_1_independent','bayes_2_independent','bayes_5_independent'):
            m=r['models'][name]
            P[name]=joint(m['lambda_home'],m['lambda_away'],m['c'])
        P['equal_blend_independent_and_bayes1']=(P['same_season_ratio_independent']+P['bayes_1_independent'])/2.
        P['equal_blend_bayes1_and_bayes2']=(P['bayes_1_independent']+P['bayes_2_independent'])/2.
    row={'fid':r['fid'],'market':r['market'],'league_id':r['league_id'],
      'score':r['score'],'line':r['line'],'odds':r['odds'],'original_Crown_SHA256':r['source_Crown_raw_sha256'],
      'quote_received_utc':r['Crown_quote_received_utc'],
      'model':{}}
    for name,p in P.items():
        ex={s:expval(r['market'],r['line'],r['odds'][s],s,p) for s in r['odds']}
        side=max(ex,key=lambda s:ex[s])
        actual=cash(r['market'],r['line'],r['odds'][side],side,r['score'])
        row['model'][name]={'side':side,'U':actual,'estimatedEV':ex[side]}
        if name in r['models']:
            old=r['models'][name]
            if old['side']!=side:checks['old_R5_side_mismatch']+=1
            if abs(old['net_U']-actual)>1e-9:checks['old_R5_payout_mismatch']+=1
            if abs(old['expected_U']-ex[side])>1e-7:checks['old_R5_EV_mismatch']+=1
    out.append(row)
assert not checks,checks
def summary(rs):
    n=len(rs);z={'n':n}
    for name in out[0]['model']:
        vals=[r['model'][name] for r in rs]
        u=sum(x['U'] for x in vals)
        z[name]={'net_U':round(u,5),'ROI_pct':round(100*u/n,5) if n else None,
                 'direction_change_vs_base':sum(r['model'][name]['side']!=r['model']['same_season_ratio_independent']['side'] for r in rs)}
    return z
result={'study':'R6_EQUAL_WEIGHT_SCORE_MIXTURE_ON_OLD_ACTUALLY_RECEIVED_CROWN_2026_27',
  'source_R5_frozen_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
  'checks':dict(checks),'same_received_fixtures':len({r['fid'] for r in out}),
  'overall':{market:summary([r for r in out if r['market']==market]) for market in ('AH','OU')},
  'by_league':{lg:{m:summary([r for r in out if r['league_id']==lg and r['market']==m]) for m in ('AH','OU')}
    for lg in sorted({r['league_id'] for r in out})},
  'limitations':['Original Crown HTTP receipt before match, but evaluated after known outcomes; NOT formal TG betting',
    'Football-Data 2026/27 differs from Understat historical archive',
    'Actual xG publication timestamp unknown, earlier study used +72h as-if maturity',
    'All research variants retain same 138 fixtures and both AH/OU prices, no EV gate',
    'Equal weight is an exploratory model comparison, not user-approved formal strategy',
    'No national teams; source data reads frozen R5 without mutation']}
with LEDGER.open('w') as f:
    for row in out:f.write(json.dumps(row,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':result['overall'],'checks':dict(checks)},ensure_ascii=False))
