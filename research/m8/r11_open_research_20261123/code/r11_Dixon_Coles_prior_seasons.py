#!/usr/bin/env python3
"""R11-A learned Dixon-Coles low-score correction, strict prior TWO complete
seasons for each test season and league; fixed R5 k2 expected goals.
Train rho on GOAL scores of previous completed seasons ONLY, never target
results and never ROI. The valid rho domain is mathematically derived from
nonnegative score probabilities for observed prematch lambdas, not a betting
rule. Evaluate all 9908 historic Crown paired AH/OU events.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r11_open_method_research_20261123'
F5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
FEAT=F5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
OUT=HERE/'r11_Dixon_Coles_rolling_prior_2seasons_CrownT12.jsonl'
SUM=HERE/'r11_Dixon_Coles_rolling_prior_2seasons_summary.json'
f={(r['league'],r['fixture_id']):r for r in map(json.loads,FEAT.open())}
by_season=defaultdict(list)
for r in f.values():by_season[(r['league'],r['season'])].append(r)
quotes=defaultdict(dict)
for x in map(json.loads,CROWN.open()):quotes[(x['league'],x['fixture_id'])][x['market']]=x
market={x['fid']:x for x in map(json.loads,MARKET.open()) if x['cohort']=='historical_Crown_T12'}
assert len(quotes)==9908
N=28
G=np.arange(N+1,dtype=int)
H=G[:,None];A=G[None,:]
DIFF=H-A
TOTAL=H+A
def tau(hg,ag,lh,la,rho):
 if hg==0 and ag==0:return 1-lh*la*rho
 if hg==0 and ag==1:return 1+lh*rho
 if hg==1 and ag==0:return 1+la*rho
 if hg==1 and ag==1:return 1-rho
 return 1.
def coeff(r):
 h,a=map(int,r['score'].split('-'))
 lh,la=r['candidate_lambda']['bayes_prior_2']
 if h==0 and a==0:return -lh*la
 if h==0 and a==1:return lh
 if h==1 and a==0:return la
 if h==1 and a==1:return -1.
 return 0.
def choose_rho(lg,target):
 train=by_season[(lg,target-2)]+by_season[(lg,target-1)]
 evals=by_season[(lg,target)]
 lam=np.asarray([r['candidate_lambda']['bayes_prior_2'] for r in train],float)
 # The estimation support uses ONLY previous two completed seasons, even
 # for mathematical probability feasibility; never future target-year covariates.
 # Each test fixture's joint low-score probability is separately validated.
 hi=min(1.,float(np.min(1./(lam[:,0]*lam[:,1]))))
 lo=max(-float(np.min(1./lam[:,0])),-float(np.min(1./lam[:,1])))
 coeffs=np.asarray([coeff(z) for z in train],float)
 def objective(rho):
    vals=1+coeffs*rho
    if np.any(vals<=0):return np.inf
    return -float(np.log(vals).sum())
 # Endpoints analytically valid only as limits; numeric eps avoids ln(0).
 opt=minimize_scalar(objective,bounds=(lo+1e-9,hi-1e-9),
        method='bounded',options={'xatol':1e-12})
 if not opt.success:raise RuntimeError(('rho minimization failed',lg,target,opt.message))
 return {'rho':float(opt.x),'score_loglik_gain_train_over_independent':-opt.fun,
 'train_fixtures':len(train),'estimated_sample_support_low':lo,
 'estimated_sample_support_high':hi,
 'train_low_four_scores':int(sum(coeffs!=0)),
 'target_fixture_count':len(evals)}
def score(p,sc):
 h,a=map(int,sc.split('-'))
 y=0 if h>a else 1 if h==a else 2
 return sum((x-float(i==y))**2 for i,x in enumerate(p))
def quarter(line):
 q=round(float(line)*4)
 if abs(q/4-float(line))>1e-9:raise ValueError(line)
 return [(float(line),1.)] if q%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
def selection(p,mkt,quote):
 g=DIFF if mkt=='AH' else TOTAL
 w=l=0.
 for part,c in quarter(quote['line']):
  value=g+part if mkt=='AH' else g-part
  w+=c*float(p[value>1e-10].sum())
  l+=c*float(p[value<-1e-10].sum())
 odd=quote['odds']
 if mkt=='AH':
  scores={'home':(odd['home']-1)*w-l,'away':(odd['away']-1)*l-w}
 else:
  scores={'over':(odd['over']-1)*w-l,'under':(odd['under']-1)*l-w}
 side=max(scores,key=scores.get)
 return side,scores[side]
def settled(sc,mkt,line,odd,side):
 h,a=map(int,sc.split('-'))
 total=0.
 for part,c in quarter(line):
  v=h-a+part if side=='home' else a-h-part if side=='away' else h+a-part if side=='over' else part-h-a
  total+=c*((odd-1) if v>1e-9 else -1 if v<-1e-9 else 0)
 return total
learned={lg:{str(y):choose_rho(lg,y) for y in range(2019,2026)} for lg in
 ('epl','bundesliga','serie-a','la-liga','ligue-1')}
rows=[];audit=Counter()
for key,q in sorted(quotes.items()):
 feat=f[key];lg=feat['league'];yr=feat['season']
 lamh,lama=feat['candidate_lambda']['bayes_prior_2']
 rho=learned[lg][str(yr)]['rho']
 ph=poisson.pmf(G,lamh);pa=poisson.pmf(G,lama)
 pp=np.outer(ph,pa)
 base=pp.copy()
 pp[0,0]*=1-lamh*lama*rho
 pp[0,1]*=1+lamh*rho
 pp[1,0]*=1+lama*rho
 pp[1,1]*=1-rho
 if pp.min()<-1e-12:audit['negative_joint_cell']+=1
 if abs(pp.sum()-base.sum())>1e-10:audit['nonconserved_probability_mass']+=1
 pp/=pp.sum();base/=base.sum()
 p1x2=[float(pp[DIFF>0].sum()),float(pp[DIFF==0].sum()),float(pp[DIFF<0].sum())]
 pbase=[float(base[DIFF>0].sum()),float(base[DIFF==0].sum()),float(base[DIFF<0].sum())]
 row={'fixture_id':feat['fixture_id'],'league':lg,'season':yr,'score':feat['score'],
      'trained_rho_previous_two_seasons':rho,
      'Brier_DC':score(p1x2,feat['score']),
      'Brier_independent_Poisson_k2':score(pbase,feat['score']),
      'Brier_Crown_market':market[q['AH']['fid']]['models']['market_implied_Poisson']['1X2_brier'],
      'p_1x2_DC':p1x2,'market':{}}
 for mk,quote in q.items():
  side,ev=selection(pp,mk,quote)
  U=settled(feat['score'],mk,quote['line'],quote['odds'][side],side)
  old=quote['models']['bayes_prior_2_independent']
  row['market'][mk]={'side':side,'EV':ev,'net_U':U,'R5_poisson_side':old['side'],'R5_poisson_net_U':old['net_U']}
  audit['market_contracts_processed']+=1
 rows.append(row)
assert len(rows)==9908 and not {k:v for k,v in audit.items() if k != "market_contracts_processed" and v},audit
def agg(rs):
 n=len(rs)
 if not n:return {'n':0}
 z={'n':n,'DC_Brier':round(sum(r['Brier_DC'] for r in rs)/n,7),
 'independent_k2_Brier':round(sum(r['Brier_independent_Poisson_k2'] for r in rs)/n,7),
 'Crown_market_Brier':round(sum(r['Brier_Crown_market'] for r in rs)/n,7),
 'mean_trained_rho':round(sum(r['trained_rho_previous_two_seasons'] for r in rs)/n,7)}
 for mk in ('AH','OU'):
  a=[r['market'][mk] for r in rs]
  z[mk]={'n':n,'DC_net_U':round(sum(x['net_U'] for x in a),5),
  'DC_ROI_pct':round(sum(x['net_U'] for x in a)*100/n,5),
  'R5_k2_independent_net_U':round(sum(x['R5_poisson_net_U'] for x in a),5),
  'delta_net_U':round(sum(x['net_U']-x['R5_poisson_net_U'] for x in a),5),
  'changed_sides':sum(x['side']!=x['R5_poisson_side'] for x in a)}
 return z
result={'study':'R11_ROLLING_PRIOR_TWO_SEASON_DIXON_COLES_LOW_SCORE_CORRELATION',
 'sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (FEAT,CROWN,MARKET)},
 'learned_rho':learned,'overall':agg(rows),
 'by_season':{str(y):agg([r for r in rows if r['season']==y]) for y in range(2019,2026)},
 'by_league':{lg:agg([r for r in rows if r['league']==lg]) for lg in sorted({r['league'] for r in rows})},
 'audit':dict(audit),
 'research_method':'Dixon-Coles local score probability multiplier for 0-0,0-1,1-0,1-1; coefficient fitted by prior two seasons goals maximising low-score likelihood. Valid parameter interval derives from score-probability nonnegativity given observed prediction lambda (past+target prematch features). NO target result or ROI used for rho. All 9908 Crown quote fixtures included.',
 'limitations':['Historic Crown source-event price retrieved AFTER match, not actual received/executable quote.',
 'R5 mean features historical Understat publication time unknown. Study is NOT genuinely blinded.',
 'Dixon-Coles low-score correlation can affect AH/OU quarter payouts; no user-approved new strategy rule or filter.',
 'No national teams. Mathematical rho supports are not trading limits.']}
with OUT.open('w') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
SUM.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':result['overall'],
 'rho_by_year':{lg:{y:round(p['rho'],4) for y,p in x.items()} for lg,x in learned.items()},
 'audit':dict(audit)},ensure_ascii=False))
