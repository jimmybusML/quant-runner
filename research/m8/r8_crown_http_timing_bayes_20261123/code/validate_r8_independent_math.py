#!/usr/bin/env python3
"""R8 independent data & calculations audit. No R8 forecast module import.
Checks actual HTTP time, scores, original frozen R5/R6/R7 integrity, R7 market
result reproduction, R5 point comparator and all R8 posterior realized payouts;
independently reconstructs 24 posterior-predictive fixtures via separate score
matrix, >40-goal tail to corroborate pseudo-QMC AH/OU expected cash.
"""
from pathlib import Path
from collections import defaultdict,Counter
import math,json,hashlib,datetime
import numpy as np
from scipy.stats import qmc,invgamma
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123'
R6=ROOT/'frozen_research_snapshots/R6_BAYES_BIVAR_COMPLEMENT_20261123'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
ARR=HERE/'r8_11club_Crown_actual_receipt_market_timing.jsonl'
POST=HERE/'r8_full_posterior_predictive_club_20261123.jsonl'
ARCH=ROOT/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'
FT=ROOT/'m7/m7_full_scope_8_axis_combo_pending_FT_recovered_20261110.jsonl'
SOURCE=R5/'research/r5_bayes_bivar_CrownT12_20261123.jsonl'
FEATURE=R5/'research/r5_bayes_bivar_asof_features_20261123.jsonl'
R5RECEIPT=R5/'research/r5_bayes_bivar_actual_receipt_20261123.jsonl'
R7MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
OUT=HERE/'r8_independent_source_and_cash_validation.json'
checks=Counter();err=Counter()
def hashfile(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for z in iter(lambda:f.read(1024*1024),b''):h.update(z)
 return h.hexdigest()
def dt(t):return datetime.datetime.fromisoformat(t.replace('Z','+00:00'))
def legs(line):
 n=round(float(line)*4)
 assert abs(float(line)-n/4)<1e-10
 return [(float(line),1.)] if n%2==0 else [(math.floor(float(line)*2)/2.,.5),(math.ceil(float(line)*2)/2.,.5)]
def unit(mkt,line,odd,side,hg,ag):
 u=0.
 for leg,w in legs(line):
  v=hg-ag+leg if side=='home' else ag-hg-leg if side=='away' else hg+ag-leg if side=='over' else leg-hg-ag
  u+=w*((odd-1.) if v>1e-10 else -1. if v<-1e-10 else 0.)
 return u
def brier(prob,score):
 hg,ag=map(int,score.split('-'))
 y=0 if hg>ag else 1 if hg==ag else 2
 return sum((x-float(i==y))**2 for i,x in enumerate(prob))
ft={r['fixture_id']:r for r in map(json.loads,FT.open())}
r5old=defaultdict(dict)
for r in map(json.loads,R5RECEIPT.open()):
 r5old[r['fid']][r['market']]=r
r7m={r['fid']:r for r in map(json.loads,R7MARKET.open()) if r['cohort']=='actual_HTTP_2026_receipt'}
stats=[]
for rec in map(json.loads,ARR.open()):
 checks['timing_fixtures']+=1
 fid=rec['fid']
 if rec['score']!=ft[fid]['verified_FT_score']:err['FT_mismatch']+=1
 prev=None
 for snap in rec['snapshots']:
  checks['timing_receipts']+=1
  if dt(snap['HTTP_received_utc'])>=dt(snap['kickoff_utc']):err['receipt_not_pregame']+=1
  if max(dt(snap['AH_quote_source_event_utc']),dt(snap['OU_quote_source_event_utc']))>dt(snap['HTTP_received_utc']):
   err['event_after_receipt']+=1
  if prev is not None and dt(snap['HTTP_received_utc'])<dt(prev['HTTP_received_utc']):
   err['time_order_error']+=1
  prev=snap
  lh=snap['market']['lambda_home'];la=snap['market']['lambda_away']
  if abs(lh+la-snap['market']['lambda_total'])>1e-9:err['market_lambda_sum']+=1
  n=18
  H=np.empty(n+1);A=np.empty(n+1)
  H[0]=math.exp(-lh);A[0]=math.exp(-la)
  for g in range(1,n+1):H[g]=H[g-1]*lh/g;A[g]=A[g-1]*la/g
  m=np.outer(H/H.sum(),A/A.sum())
  ii=np.arange(n+1);D=ii[:,None]-ii[None,:]
  p=[float(m[D>0].sum()),float(m[D==0].sum()),float(m[D<0].sum())]
  if abs(brier(p,snap['score'])-snap['1X2_Brier'])>1e-9:err['timing_Brier']+=1
 if rec['R5_old_2026_sample']:
  if not rec.get('R5_exact_original_snapshot_matched'):err['R5_receipt_Sha_time_missing']+=1
  if abs(rec['last_Brier']-r7m[fid]['models']['market_implied_Poisson']['1X2_brier'])>1e-8:
   err['R7_last_Brier_baseline']+=1
  checks['R5_old_2026_same_exact_snapshot']+=1
assert checks['timing_fixtures']==468 and checks['timing_receipts']==3999,checks
assert checks['R5_old_2026_same_exact_snapshot']==138,checks
srcidx=defaultdict(dict)
for r in map(json.loads,SOURCE.open()):
 srcidx[(r['league'],r['fixture_id'])][r['market']]=r
features={(r['league'],r['fixture_id']):r for r in map(json.loads,FEATURE.open())}
assert len(features)==13312 and len(srcidx)==9908
postrows=[]
for r in map(json.loads,POST.open()):
 checks['posterior_fixture_rows']+=1
 key=(r['league'],r['fixture_id'])
 if key not in features:err['feature_missing']+=1
 if r['score']!=features[key]['score']:err['feature_score_mismatch']+=1
 for k in (1,2):
  z=r['models']['posterior_predictive_k'+str(k)]
  checks['posterior_predictive_score_checks']+=1
  if abs(sum(z['prob'])-1)>1e-9 or min(z['prob'])<0:err['posterior_prob_mass']+=1
  if abs(z['Brier']-brier(z['prob'],r['score']))>1e-10:err['posterior_brier_wrong']+=1
  if r['Crown_matched']:
   orig=srcidx[key]
   for mkt in ('AH','OU'):
    checks['posterior_crown_cash_checks']+=1
    out=z[mkt];base=orig[mkt]
    old=base['models']['bayes_prior_'+str(k)+'_independent']
    hh,aa=map(int,r['score'].split('-'))
    if out['R5_mean_model_side']!=old['side'] or abs(out['R5_mean_model_U']-old['net_U'])>1e-9:
     err['R5_original_model_baseline_mismatch']+=1
    if abs(out['realized_U']-unit(mkt,base['line'],base['odds'][out['side']],out['side'],hh,aa))>1e-9:
     err['posterior_payout_wrong']+=1
  if k==1 and r['Crown_matched']:
   ref=srcidx[key]['AH']['fid']
   if ref!=r['market_Crown_fid']:err['Crown_quote_join_error']+=1
 postrows.append(r)
assert checks['posterior_fixture_rows']==13312 and checks['posterior_crown_cash_checks']==39632,checks
# Independent posterior conditional score-grid expectation on representative
# Crown-paired fixtures across all seasons/leagues, including AH integer,half,quarter.
sobol=qmc.Sobol(d=4,scramble=True,seed=20261123).random_base2(8)
picked=[]
seen=set()
for r in postrows:
 if not r['Crown_matched']:continue
 key=(r['league'],r['season'])
 if key in seen:continue
 picked.append(r);seen.add(key)
 if len(picked)>=24:break
def direct_eval(f,r,k,mkt,quote):
 n=64
 idx=np.arange(n+1,dtype=float)
 hh=idx[:,None];aa=idx[None,:]
 prior=f['posterior_means']['bayes_prior_'+str(k)]
 eff=f['effective_venue_history']
 mu=[prior[t] for t in ('home_attack','away_defense','away_attack','home_defense')]
 count=[eff['home'],eff['away'],eff['away'],eff['home']]
 samples=[]
 for dim in range(4):
  a=k+1+count[dim];b=mu[dim]*(k+count[dim])
  samples.append(invgamma.ppf(sobol[:,dim],a=a,scale=b))
 lh=samples[0]*samples[1]/f['league_mean_home_xg']
 la=samples[2]*samples[3]/f['league_mean_away_xg']
 prob=np.zeros((n+1,n+1))
 for x,y in zip(lh,la):
  ph=np.empty(n+1);pa=np.empty(n+1)
  ph[0]=math.exp(-x);pa[0]=math.exp(-y)
  for i in range(1,n+1):
   ph[i]=ph[i-1]*x/i
   pa[i]=pa[i-1]*y/i
  prob+=np.outer(ph,pa)/len(lh)
 ph=float(prob[hh>aa].sum());pd=float(prob[hh==aa].sum());pa=float(prob[hh<aa].sum())
 z=r['models']['posterior_predictive_k'+str(k)]
 # <=1e-5 tolerance is independent scoring quality. Most tails negligible.
 if max(abs(ph-z['prob'][0]),abs(pd-z['prob'][1]),abs(pa-z['prob'][2]))>1e-5:
  err['independent_posterior_grid_1X2']+=1
 opts=['home','away'] if mkt=='AH' else ['over','under']
 best={}
 for side in opts:
  p=np.zeros_like(prob)
  for part,w in legs(quote['line']):
   if side=='home':v=hh-aa+part
   elif side=='away':v=aa-hh-part
   elif side=='over':v=hh+aa-part
   else:v=part-hh-aa
   p+=w*np.where(v>1e-10,quote['odds'][side]-1.,np.where(v< -1e-10,-1.,0.))
  best[side]=float((prob*p).sum())
 original_ev=z[mkt]['expected_U'];selected=z[mkt]['side']
 if abs(original_ev-best[selected])>1e-5:err['independent_posterior_grid_expected_EV']+=1
 checks['full_posterior_grid_cash_expectation_spots']+=1
for r in picked:
 key=(r['league'],r['fixture_id'])
 f=features[key]
 for k in (1,2):
  for mk in ('AH','OU'):
   direct_eval(f,r,k,mk,srcidx[key][mk])
# Frozen integrity: all three existing research snapshots.
for location,manifestname in [
 (R5,'FROZEN_SHA256_MANIFEST.json'),
 (R6,'R6_FREEZE_MANIFEST.json'),
 (R7,'R7_FROZEN_SHA256_MANIFEST.json')]:
 manifest=json.loads((location/manifestname).read_text())
 files=manifest['files']
 for m in files:
  path=location/(m.get('file') or m.get('relative_path'))
  checks['old_frozen_sha256_files']+=1
  if not path.exists() or hashfile(path)!=m['sha256']:err['prior_frozen_modified']+=1
result={'status':'PASS' if not err else 'FAIL','checks':dict(checks),'errors':dict(err),
  'R5_R6_R7_old_snapshot_SHA256':{x.name:hashfile(x/y) for x,y in ((R5,'FROZEN_SHA256_MANIFEST.json'),(R6,'R6_FREEZE_MANIFEST.json'),(R7,'R7_FROZEN_SHA256_MANIFEST.json'))},
  'R8_outputs_SHA256':{p.name:hashfile(p) for p in (ARR,POST)},
  'scope':'11 domestic club league pregame HTTP receipt time study + five-league historic posterior predictive; R5/R6/R7 unchanged.'}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':result['checks'],'errors':result['errors']},ensure_ascii=False))
assert result['status']=='PASS'