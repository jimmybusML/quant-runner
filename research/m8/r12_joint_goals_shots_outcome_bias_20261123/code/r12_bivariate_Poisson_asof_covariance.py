#!/usr/bin/env python3
"""R12-A bivariate Poisson dependence, learned only from last two COMPLETE
seasons goal residual covariance per league, no betting profit training.
Keep R5 k2 expected home/away goals and match/market identically fixed.
Shared latent count >=0; when fitted covariance <=0 independent Poisson is
natural boundary, not an entry filter. For feasibility shared count cannot
exceed either team's expected goals; per-fixture cap is probability identity.
All 9908 Crown historical source-event matches each AH+OU, no EV eligibility.
"""
import json,math,hashlib
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from scipy.stats import poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
F=R5/'r5_bayes_bivar_asof_features_20261123.jsonl'
C=R5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
M=R7/'r7_market_implied_2market_20261123.jsonl'
L=HERE/'r12_bivariate_shared_count_CrownT12_20261123.jsonl'
S=HERE/'r12_bivariate_shared_count_summary_20261123.json'
f={(r['league'],r['fixture_id']):r for r in map(json.loads,F.open())}
pri=defaultdict(list)
for r in f.values():pri[(r['league'],r['season'])].append(r)
q=defaultdict(dict)
for r in map(json.loads,C.open()):q[(r['league'],r['fixture_id'])][r['market']]=r
mk={r['fid']:r for r in map(json.loads,M.open()) if r['cohort']=='historical_Crown_T12'}
assert len(q)==len(mk)==9908
N=25; V=np.arange(N+1,dtype=float);D=V[:,None]-V[None,:];T=V[:,None]+V[None,:]
def asof_cov(lg,yr):
 rows=pri[(lg,yr-2)]+pri[(lg,yr-1)]
 a=[];b=[]
 for r in rows:
  h,away=r['candidate_lambda']['bayes_prior_2']
  fh,fa=map(int,r['score'].split('-'))
  a.append(fh-h);b.append(fa-away)
 if len(a)<100:raise RuntimeError((lg,yr,len(a)))
 cov=float(np.cov(np.array([a,b]),ddof=1)[0,1])
 return {'train_seasons':[yr-2,yr-1],'train_match_n':len(a),
   'residual_covariance_raw':cov,
   'shared_poisson_covariance_nonnegative':max(0.,cov),
   'residual_corr':float(np.corrcoef(a,b)[0,1]),
   'train_home_residual_mean':float(np.mean(a)),
   'train_away_residual_mean':float(np.mean(b))}
est={lg:{str(y):asof_cov(lg,y) for y in range(2019,2026)} for lg in
 ('epl','bundesliga','serie-a','la-liga','ligue-1')}
def joint(lh,la,c):
 p=np.zeros((N+1,N+1))
 c=min(c,lh,la)
 # Xh=U+Z, Xa=V+Z. For fixed k evaluate all H>=k, A>=k.
 # Loss due to max H/A>N must be negligible; normalize truncated tails.
 ph=poisson.pmf(V,lh-c);pa=poisson.pmf(V,la-c)
 if c==0:return np.outer(ph,pa)/ph.sum()/pa.sum()
 z=poisson.pmf(V,c)
 for k in range(N+1):
  if z[k]<1e-16:continue
  p[k:,k:]+=z[k]*np.outer(ph[:N+1-k],pa[:N+1-k])
 return p/p.sum()
def quarter(line):
 a=round(line*4)
 if abs(a/4-line)>1e-9:raise ValueError(line)
 return [(line,1.)] if a%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
def eval_markets(probs,kind,quote):
 grid=D if kind=='AH' else T
 w=l=0.
 for part,rate in quarter(float(quote['line'])):
  delta=grid+part if kind=='AH' else grid-part
  w+=rate*float(probs[delta>1e-9].sum())
  l+=rate*float(probs[delta< -1e-9].sum())
 odds=quote['odds']
 if kind=='AH':values={'home':(odds['home']-1)*w-l,'away':(odds['away']-1)*l-w}
 else:values={'over':(odds['over']-1)*w-l,'under':(odds['under']-1)*l-w}
 return max(values,key=values.get),values
def cash(score,kind,quote,side):
 h,a=map(int,score.split('-'))
 result=0.
 for part,w in quarter(float(quote['line'])):
  d=h-a+part if side=='home' else a-h-part if side=='away' else h+a-part if side=='over' else part-h-a
  result+=w*((quote['odds'][side]-1) if d>1e-9 else -1 if d<-1e-9 else 0)
 return result
ledger=[];audit=Counter()
for key,pair in sorted(q.items()):
 r=f[key];lg=r['league'];year=r['season']
 lh,la=r['candidate_lambda']['bayes_prior_2']
 raw=est[lg][str(year)]['shared_poisson_covariance_nonnegative']
 shared=min(raw,lh,la)
 p=joint(lh,la,shared)
 base=joint(lh,la,0.)
 if p.min()<-1e-11 or abs(p.sum()-1)>1e-10:audit['invalid_joint_mass']+=1
 ih,ia=map(int,r['score'].split('-'));lab=0 if ih>ia else 1 if ih==ia else 2
 probs=[float(p[D>0].sum()),float(p[D==0].sum()),float(p[D<0].sum())]
 pb=[float(base[D>0].sum()),float(base[D==0].sum()),float(base[D<0].sum())]
 brier=lambda values:sum((val-float(i==lab))**2 for i,val in enumerate(values))
 assert set(pair)=={'AH','OU'}
 z={'league':lg,'fixture_id':r['fixture_id'],'season':year,'score':r['score'],
     'estimated_shared_cov_prior_two_years':raw,'used_shared_cov_math_feasible':shared,
     '1X2_Brier_bivar':brier(probs),
     '1X2_Brier_indep_same_mean':brier(pb),
     '1X2_Crown_market_Brier':mk[pair['AH']['fid']]['models']['market_implied_Poisson']['1X2_brier'],
     'p_1x2':probs,'markets':{}}
 for kind,quote in pair.items():
  side,e=eval_markets(p,kind,quote)
  val=cash(r['score'],kind,quote,side)
  old=quote['models']['bayes_prior_2_independent']
  z['markets'][kind]={'side':side,'expected_U':e[side],'realized_U':val,
    'R5_point_side':old['side'],'R5_point_U':old['net_U']}
  audit['market_contracts']+=1
 ledger.append(z)
assert len(ledger)==9908
assert not {k:v for k,v in audit.items() if k!='market_contracts' and v},audit
def agg(a):
 n=len(a);z={'n':n}
 if not n:return z
 z.update({'bivariate_Brier':round(sum(r['1X2_Brier_bivar'] for r in a)/n,7),
  'independent_same_mean_Brier':round(sum(r['1X2_Brier_indep_same_mean'] for r in a)/n,7),
  'Crown_market_Brier':round(sum(r['1X2_Crown_market_Brier'] for r in a)/n,7),
  'mean_used_shared_component':round(sum(r['used_shared_cov_math_feasible'] for r in a)/n,7),
  'positive_shared_fixture_count':sum(r['used_shared_cov_math_feasible']>0 for r in a),
  'feasibility_cap_activated':sum(r['estimated_shared_cov_prior_two_years']>r['used_shared_cov_math_feasible']+1e-12 for r in a)})
 for kind in ('AH','OU'):
  xx=[r['markets'][kind] for r in a];u=sum(t['realized_U'] for t in xx)
  z[kind]={'n':n,'net_U':round(u,5),'ROI_pct':round(100*u/n,5),
    'R5_indep_U':round(sum(t['R5_point_U'] for t in xx),5),
    'delta_v_R5_U':round(sum(t['realized_U']-t['R5_point_U'] for t in xx),5),
    'switched_sides':sum(t['side']!=t['R5_point_side'] for t in xx)}
 return z
report={'study':'R12_BIVARIATE_POISSON_PRIOR_TWO_SEASON_RESIDUAL_SHARED_COMPONENT',
 'sources_SHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (F,C,M)},
 'method':'Use R5 k2 prematch expected goals, estimate covariance of actual-minus-predicted two team scores on previous two completed seasons same league, use positive part as shared Poisson count covariance; nonnegative component and <=min(lambdaH,lambdaA) required by probability definition; no gambling ROI used. All 9908 paired Crown historic fixtures AH/OU selected unconditionally by maximum estimated EV of both sides, no positive EV gate.',
 'trained_per_league_year':est,'overall':agg(ledger),
 'by_season':{str(y):agg([r for r in ledger if r['season']==y]) for y in range(2019,2026)},
 'by_league':{lg:agg([r for r in ledger if r['league']==lg]) for lg in sorted({r['league'] for r in ledger})},
 'audit':dict(audit),
 'limitations':['Bivariate Poisson only represents nonnegative correlation. If residual covariance is negative, model reduces to independent Poisson; cannot establish universal independent-goal correctness.',
    'Source R5 xG asof provider publishing time is unverified; historical Crown T12 source-event retrieved after games.',
    'Same long-studied 9908 fixtures. No blind new prices, no new trading rule, Gate or production order. National teams excluded.']}
with L.open('w') as output:
 for row in ledger:output.write(json.dumps(row,ensure_ascii=False)+'\n')
S.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':report['overall'],
  'positive_cov_groups':sum(x['shared_poisson_covariance_nonnegative']>0 for v in est.values() for x in v.values()),
  'by_year':{k:{'AH_delta':v['AH']['delta_v_R5_U'],'OU_delta':v['OU']['delta_v_R5_U']} for k,v in report['by_season'].items()},
  'audit':report['audit']},ensure_ascii=False))
