#!/usr/bin/env python3
"""R7 A: market-implied independent-Poisson benchmark fit from same-source
Crown AH + OU prices. This is a NEW market-fit hypothesis, NOT a reproduction
of Hegarty/Whelan's empirical-refund method. Club leagues only.
No model ROI fitted, no EV Gate, no betting instruction.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,hashlib
import numpy as np
from scipy.optimize import brentq
from scipy.stats import poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r7_market_pricing_20261123'
F=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
SRC=F/'r5_bayes_bivar_CrownT12_20261123.jsonl'
R=F/'r5_bayes_bivar_actual_receipt_20261123.jsonl'
OUT=HERE/'r7_market_implied_2market_20261123.jsonl'
REP=HERE/'r7_market_implied_2market_summary_20261123.json'
MAXGOAL=18
AR=np.arange(MAXGOAL+1,dtype=float)
H=AR[:,None];A=AR[None,:]
D=H-A;S=H+A
def legs(x):
    n=round(x*4)
    assert abs(n/4-x)<1e-8
    if n%2==0:return [(x,1.)]
    return [(math.floor(x*2)/2.,.5),(math.ceil(x*2)/2.,.5)]
def pmf(lam):
    p=np.zeros(MAXGOAL+1);p[0]=math.exp(-lam)
    for i in range(1,MAXGOAL+1):p[i]=p[i-1]*lam/i
    return p/p.sum()
def joint(lh,la):
    return np.outer(pmf(lh),pmf(la))
def winloss(p,market,line):
    grid=D if market=='AH' else S
    wins=loss=0.
    for leg,w in legs(line):
        boundary=-leg if market=='AH' else leg
        wins+=w*float(p[grid>boundary+1e-10].sum())
        loss+=w*float(p[grid<boundary-1e-10].sum())
    return wins,loss
def imbalance(p,market,line,odds):
    o0=odds['home'] if market=='AH' else odds['over']
    o1=odds['away'] if market=='AH' else odds['under']
    a,b=winloss(p,market,line)
    return o0*a-o1*b
def solve(ah,ou):
    count=Counter()
    # O/U only identifies the model's assumed sum of Poisson intensities.
    overline=ou['line'];overodds=ou['odds']
    def OUfunc(total):
        p=poisson.pmf(np.arange(0,MAXGOAL*2+1),total)
        # O/U total of two Poissons; negligible grid tail at chosen finite n
        # For fit only: direct scalar, avoid 2D matrix.
        norm=p.sum()
        p=p/norm
        w=l=0.
        for leg,frac in legs(overline):
            k=np.arange(len(p))
            w+=frac*float(p[k>leg+1e-10].sum())
            l+=frac*float(p[k<leg-1e-10].sum())
        return overodds['over']*w-overodds['under']*l
    low=.05;high=12.
    flo=OUfunc(low);fhi=OUfunc(high)
    if flo*fhi>=0:
        count['ou_root_outside_bracket']+=1
        return None,count
    total=brentq(OUfunc,low,high,xtol=1e-8)
    line=ah['line'];odds=ah['odds']
    def AHfunc(share):
        lh=total*share
        la=total*(1-share)
        return imbalance(joint(lh,la),'AH',line,odds)
    low=.003;high=.997
    a=AHfunc(low);b=AHfunc(high)
    if a*b>=0:
        count['ah_root_outside_bracket']+=1
        return None,count
    share=brentq(AHfunc,low,high,xtol=1e-8)
    lh=total*share;la=total*(1-share)
    p=joint(lh,la)
    resAH=imbalance(p,'AH',ah['line'],ah['odds'])
    resOU=imbalance(p,'OU',ou['line'],ou['odds'])
    return {'lambda_home':lh,'lambda_away':la,'lambda_total':total,
      'share_home':share,'fit_AH_equal_return_residual':resAH,
      'fit_OU_equal_return_residual':resOU},count
def eval_score(lh,la,score):
    h,a=map(int,score.split('-'))
    p=joint(lh,la)
    w=float(p[D>0].sum());d=float(p[D==0].sum());l=float(p[D<0].sum())
    probs=[w,d,l];y=0 if h>a else (1 if h==a else 2)
    return {'1X2_brier':sum((p-float(i==y))**2 for i,p in enumerate(probs)),
      '1X2_logloss':-math.log(max(probs[y],1e-16)),
      '1X2_p_home':w,'1X2_p_draw':d,'1X2_p_away':l,
      'goal_total_pred':lh+la,'goal_diff_pred':lh-la,
      'goal_total_absolute_error':abs(lh+la-(h+a)),
      'goal_diff_absolute_error':abs(lh-la-(h-a))}
def load_records(path,historical):
    groups=defaultdict(dict)
    for line in path.open():
        r=json.loads(line)
        fid=r['fid']
        assert r['market'] not in groups[fid]
        groups[fid][r['market']]=r
    assert all(set(z)=={'AH','OU'} for z in groups.values())
    return groups
checks=Counter();result=[]
for cohort,path in (('historical_Crown_T12',SRC),('actual_HTTP_2026_receipt',R)):
    pairs=load_records(path,cohort=='historical_Crown_T12')
    for fid,pair in pairs.items():
        ah,ou=pair['AH'],pair['OU']
        if ah['score']!=ou['score']:
            checks['same_fixture_score_mismatch']+=1;continue
        if cohort=='historical_Crown_T12':
            score=ah['score'];league=ah['league'];year=ah['season']
            cand=('independent_poisson','bayes_prior_1_independent','bayes_prior_2_independent')
            mlambda=lambda r,m:(r['models'][m]['lambda_home'],r['models'][m]['lambda_away'])
        else:
            score=ah['score'];league=ah['league_id'];year=2026
            cand=('same_season_ratio_independent','bayes_1_independent','bayes_2_independent')
            mlambda=lambda r,m:(r['models'][m]['lambda_home'],r['models'][m]['lambda_away'])
        # Normalize AH and OU fields to original Crown contract names.
        def fix(r):
            return {'line':r['line'],'odds':r['odds']}
        solved,diag=solve(fix(ah),fix(ou))
        checks.update(diag)
        row={'fid':fid,'cohort':cohort,'league':league,'season':year,
             'score':score,'market_AH':fix(ah),'market_OU':fix(ou),
             'market_fit_identifiability':'Poisson independent-score assumption + AH and OU fair equal-return equations',
             'models':{}}
        if solved:
            row['market_model_lambda']=solved
            row['models']['market_implied_Poisson']=eval_score(solved['lambda_home'],solved['lambda_away'],score)
            checks[cohort+'_market_fit_success']+=1
        else:
            row['market_model_lambda']=None
            checks[cohort+'_market_fit_failed']+=1
        for m in cand:
            lh,la=mlambda(ah,m)
            row['models'][m]=eval_score(lh,la,score)
        result.append(row)
def agg(rows):
    o={'n':len(rows),'market_fit_n':sum('market_implied_Poisson' in r['models'] for r in rows)}
    for model in sorted({m for r in rows for m in r['models']}):
        z=[r['models'][model] for r in rows if model in r['models']]
        n=len(z)
        o[model]={'n':n,'Brier':round(sum(r['1X2_brier'] for r in z)/n,7) if n else None,
          'logloss':round(sum(r['1X2_logloss'] for r in z)/n,7) if n else None,
          'goal_total_MAE':round(sum(r['goal_total_absolute_error'] for r in z)/n,6) if n else None,
          'goal_diff_MAE':round(sum(r['goal_diff_absolute_error'] for r in z)/n,6) if n else None}
    return o
historical=[r for r in result if r['cohort']=='historical_Crown_T12']
receipt=[r for r in result if r['cohort']=='actual_HTTP_2026_receipt']
summary={'research':'R7_CROWN_AH_OU_IMPLIED_POISSON_MARKET_FORECAST_CLUB_ONLY',
 'historical_source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
 'actual_received_source_sha256':hashlib.sha256(R.read_bytes()).hexdigest(),
 'main':{'historical_Crown_T12':agg(historical),'actual_HTTP_2026_receipt':agg(receipt)},
 'by_season':{str(y):agg([r for r in historical if r['season']==y]) for y in sorted({r['season'] for r in historical})},
 'by_league':{lg:agg([r for r in historical if r['league']==lg]) for lg in sorted({r['league'] for r in historical})},
 'checks':dict(checks),
 'methodology':['This is a new market-implied independent-Poisson experiment, not Hegarty-Whelan empirical-refund method.',
 'Two equations: at the current AH, home expected cash return equals away expected cash return; at the current OU, over equals under. A common match score Poisson distribution then uniquely identifies lambda if within brackets.',
 'Matches with no valid positive AH/OU root are logged as unavailable; these are failed numerical/market identification, not a strategy selection gate.',
 'The same AH/OU market prices were used for fitting market probabilities; score evaluation is a market benchmark, NOT an independent xG forecast and must NOT be treated as trading profit.',
 'All historical Crown quotes source event timestamps before kickoff but downloaded after; not true pregame receipts.',
 'Actual HTTP price sample previously studied, not new blinded future test; xG publication timestamps unverified.',
 'No national team events or formal orders.'],
 'R7_parameter_status':'Experimental inverse pricing only; no new official trading rule or stake limit'}
with OUT.open('w') as fd:
    for r in result:fd.write(json.dumps(r,ensure_ascii=False)+'\n')
REP.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'main':summary['main'],'checks':dict(checks),'by_season_market':{y:(x['market_implied_Poisson']['Brier'] if 'market_implied_Poisson' in x else None) for y,x in summary['by_season'].items()}},ensure_ascii=False))