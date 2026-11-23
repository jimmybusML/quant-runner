#!/usr/bin/env python3
"""R10-D: exact common-scale Poisson-Gamma / Negative Binomial goal total
model with market payoffs on SAME R5 k=2 expected goals.
Estimate total-goal overdispersion q from two PRIOR seasons' scored games only.
For each target match, T~NB(mean=mu_total, variance=mu+q mu^2);
H|T~Binomial(T, lambdaH/mu). q<=0 => mathematically Poisson limit,
not betting Gate; all 9908 fixtures included, no ROI-driven tuning.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from scipy.stats import nbinom,binom,poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
FEAT=R5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=R5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
LEDGER=HERE/'r10_prev_two_season_asof_negative_binomial_CrownT12_20261123.jsonl'
OUT=HERE/'r10_prev_two_season_asof_negative_binomial_summary_20261123.json'
feature=defaultdict(dict)
for r in map(json.loads,FEAT.open()):
    feature[(r['league'],r['season'])][r['fixture_id']]=r
crown=defaultdict(dict)
for r in map(json.loads,CROWN.open()):
    crown[(r['league'],r['fixture_id'])][r['market']]=r
market={(r['league'],r['fid']):r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
assert len(crown)==len(market)==9908
T=42
I=np.arange(T+1,dtype=int)
H=I[:,None];A=I[None,:]
TOTAL=H+A
D=H-A
audit=Counter()
def train_q(rows):
    n=len(rows)
    sum_over=0.
    denom=0.
    for r in rows:
        mu=sum(r['candidate_lambda']['bayes_prior_2'])
        y=sum(map(int,r['score'].split('-')))
        sum_over+=(y-mu)**2-mu
        denom+=mu*mu
    if n==0 or denom<=0:raise RuntimeError('missing previous two season prediction sample')
    raw=sum_over/denom
    return {'raw_delta_variance_over_mu_sq':raw,
      'mathematically_valid_delta':max(0.,raw),
      'effective_negative_binomial_shape':float(1/max(0.,raw)) if raw>0 else None,
      'training_match_n':n,
      'training_includes_goals_but_NO_betting_results_or_target_season':True}
noise={}
for league in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
    noise[league]={}
    for season in range(2019,2026):
        prev=list(feature[(league,season-2)].values())+list(feature[(league,season-1)].values())
        v=train_q(prev)
        v['train_seasons']=[season-2,season-1]
        noise[league][str(season)]=v
        if v['mathematically_valid_delta']==0:audit['league_target_season_nb_equals_poisson']+=1
def joint(lh,la,q):
    mu=lh+la
    if q==0:
        ph=poisson.pmf(I,lh);pa=poisson.pmf(I,la)
        m=np.outer(ph,pa)
    else:
        shape=1/q
        success=shape/(shape+mu)
        m=nbinom.pmf(TOTAL,shape,success)*binom.pmf(H,TOTAL,lh/mu)
    m=m/m.sum()
    return m
def legs(v):
    k=round(v*4)
    assert abs(k/4-v)<1e-9
    return [(v,1.)] if k%2==0 else [(math.floor(v*2)/2.,.5),(math.ceil(v*2)/2.,.5)]
def candidates(mkt,line,odds,p):
    g=D if mkt=='AH' else TOTAL
    w=l=0.
    for part,weight in legs(line):
        gap=g+part if mkt=='AH' else g-part
        w+=weight*float(p[gap>1e-9].sum())
        l+=weight*float(p[gap< -1e-9].sum())
    if mkt=='AH':
        return {'home':(odds['home']-1)*w-l,'away':(odds['away']-1)*l-w}
    return {'over':(odds['over']-1)*w-l,'under':(odds['under']-1)*l-w}
def payout(mkt,line,odds,side,sc):
    hg,ag=map(int,sc.split('-'))
    z=0.
    for part,weight in legs(line):
        v=hg-ag+part if side=='home' else ag-hg-part if side=='away' else hg+ag-part if side=='over' else part-hg-ag
        z+=weight*((odds-1) if v>1e-9 else -1 if v<-1e-9 else 0.)
    return z
rows=[]
for key,quotes in sorted(crown.items()):
    lg,fid=key;f=None
    # Season is stored in actual Crown quote, independent of future target score.
    season=int(quotes['AH']['season'])
    f=feature[(lg,season)][fid]
    q=noise[lg][str(season)]['mathematically_valid_delta']
    lh,la=f['candidate_lambda']['bayes_prior_2']
    m=joint(lh,la,q)
    pp=[float(m[D>0].sum()),float(m[D==0].sum()),float(m[D<0].sum())]
    hg,ag=map(int,f['score'].split('-'));label=0 if hg>ag else 1 if hg==ag else 2
    row={'fixture_id':fid,'league':lg,'season':season,'score':f['score'],
         'train_delta_raw':noise[lg][str(season)]['raw_delta_variance_over_mu_sq'],
         'train_delta_used':q,'xG_mean_home':lh,'xG_mean_away':la,
         'Brier':sum((x-float(i==label))**2 for i,x in enumerate(pp)),
         'logloss':-math.log(max(pp[label],1e-15)),
         'p_1x2':pp,'model_total_variance':lh+la+q*(lh+la)**2,
         'actual_total_squared_error':(hg+ag-lh-la)**2,
         'R7_Crown_market_Brier':market[(lg,quotes['AH']['fid'])]['models']['market_implied_Poisson']['1X2_brier'],
         'market':{}}
    for kind,price in quotes.items():
        E=candidates(kind,float(price['line']),price['odds'],m)
        side=max(E,key=E.get)
        realized=payout(kind,float(price['line']),price['odds'][side],side,f['score'])
        old=price['models']['bayes_prior_2_independent']
        row['market'][kind]={'side':side,'net_U':realized,'expected_U':E[side],
           'R5_Bayes_k2_side':old['side'],'R5_Bayes_k2_net_U':old['net_U']}
        audit['market_cash_checked']+=1
        if q==0 and (side!=old['side'] or abs(realized-old['net_U'])>1e-9):
            audit['NB_zero_variance_not_same_as_R5_poisson']+=1
    rows.append(row)
assert len(rows)==9908
def aggregate(rr):
    n=len(rr)
    if n==0:return {'n':0}
    out={'n':n,'Brier':round(sum(r['Brier'] for r in rr)/n,7),
      'logloss':round(sum(r['logloss'] for r in rr)/n,7),
      'market_Brier':round(sum(r['R7_Crown_market_Brier'] for r in rr)/n,7),
      'mean_pred_total_variance':round(sum(r['model_total_variance'] for r in rr)/n,6),
      'mean_actual_total_sq_error':round(sum(r['actual_total_squared_error'] for r in rr)/n,6),
      'NB_greater_dispersion_fixture_n':sum(r['train_delta_used']>0 for r in rr)}
    for marketname in ('AH','OU'):
        z=[r['market'][marketname] for r in rr]
        U=sum(p['net_U'] for p in z)
        out[marketname]={'n':n,'net_U':round(U,5),'ROI_pct':round(100*U/n,5),
         'R5_k2_poisson_U':round(sum(p['R5_Bayes_k2_net_U'] for p in z),5),
         'paired_delta_vs_R5_k2_U':round(sum(p['net_U']-p['R5_Bayes_k2_net_U'] for p in z),5),
         'switch_from_R5_k2':sum(p['side']!=p['R5_Bayes_k2_side'] for p in z)}
    return out
assert audit['NB_zero_variance_not_same_as_R5_poisson']==0,audit
report={'study':'R10_PREV_TWO_SEASON_TOTAL_GOALS_NEGATIVE_BINOMIAL_PREMATCH_PREDICTIVE',
    'source_SHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (FEAT,CROWN,MARKET)},
    'method':'Same R5 Bayesian k2 per-fixture means. Estimate overdispersion delta=(sum((T-mu)^2-mu))/sum(mu^2) on previous TWO completed seasons same league. For delta>0 use common Gamma match-rate mixer and total NB goals with H|T binomial share. For delta<=0 NB overdispersion cannot represent negative variance, Poisson limit exact. Scores from prior years allowed for goal dispersion; NO ROI or target-year scores fitted.',
    'target_league_season_noise':noise,
    'overall':aggregate(rows),
    'by_year':{str(year):aggregate([r for r in rows if r['season']==year]) for year in range(2019,2026)},
    'by_league':{lg:aggregate([r for r in rows if r['league']==lg]) for lg in sorted({r['league'] for r in rows})},
    'audit':dict(audit),
    'limitations':['NB only represents nonnegative excess variance; negative method-of-moments estimate maps to Poisson distribution as an intrinsic probability-family boundary, not a trading Gate.',
      'R5 mean xG provider actual publication time unverified; previous fixture-date source is not proof of historic provider access.',
      'Crown T12 historical source event returned post-game, not truly executed or actually pregame HTTP price.',
      'All fixtures and AH/OU outcomes included, including negative ROI, no formal Telegram or new release logic; national teams excluded.']}
with LEDGER.open('w') as f:
    for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],
                   'NB_positive_league_years':35-audit['league_target_season_nb_equals_poisson'],
                   'audit':dict(audit)},ensure_ascii=False))
