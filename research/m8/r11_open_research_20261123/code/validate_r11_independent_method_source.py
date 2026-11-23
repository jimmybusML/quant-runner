#!/usr/bin/env python3
"""R11 standalone independent validation:
- 9908 historic Crown source-event D-C score Brier, AH/OU quarter payouts
- 35 prior-two-season D-C likelihood score gradients vs learned rho
- 7073 train/test year-ordered market residual forecast Brier/logloss and
  learned coefficients gradient against actual prior two seasons,
- 19812 xG diagnostic probs, real target Understat xG CDF,
- backup source index identity and timestamp, without changing provider order,
- all 294 frozen R5-R10 files SHA256 unchanged.
No new trading rule; never import R11 model modules.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from scipy.special import softmax
from scipy.stats import gamma as gammacdf, poisson
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r11_open_method_research_20261123'
SNAP=ROOT/'frozen_research_snapshots'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
R5=SNAP/'R5_BAYES_BIVAR_FROZEN_20261123'
R7=SNAP/'R7_CROWN_MARKET_PRICING_20261123'
R10=SNAP/'R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123'
FEAT=R5/'research/r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=R5/'research/r5_bayes_bivar_CrownT12_20261123.jsonl'
MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
GAMMA=R10/'r10_Gamma_xG_posterior_predictive_20261123.jsonl'
SHAPE=R10/'r10_prior_two_season_xg_Gamma_shape.json'
DCL=HERE/'r11_Dixon_Coles_rolling_prior_2seasons_CrownT12.jsonl'
DCJ=HERE/'r11_Dixon_Coles_rolling_prior_2seasons_summary.json'
WF=HERE/'r11_market_residual_walk_forward_2021_2025.jsonl'
WFJ=HERE/'r11_market_residual_walk_forward_summary.json'
XGLEDGER=HERE/'r11_xG_observation_calibration_2019_2025.jsonl'
XGJ=HERE/'r11_xG_observation_calibration_summary.json'
FALLBACK=HERE/'r11_independent_totalcorner_default_snapshot_coverage.json'
OUT=HERE/'r11_independent_full_validation.json'
chk=Counter();err=Counter()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as file:
  for data in iter(lambda:file.read(1024*1024),b''):
   h.update(data)
 return h.hexdigest()
def leg(v):
 q=round(v*4)
 assert abs(v-q/4)<1e-10
 return [(v,1.)] if q%2==0 else [(math.floor(v*2)/2.,.5),(math.ceil(v*2)/2.,.5)]
def settle(side,market,line,odds,sc):
 h,a=map(int,sc.split('-'))
 val=0.
 for part,w in leg(line):
  x=h-a+part if side=='home' else a-h-part if side=='away' else h+a-part if side=='over' else part-h-a
  val+=w*((odds-1) if x>1e-9 else -1 if x<-1e-9 else 0.)
 return val
def br(p,sc):
 h,a=map(int,sc.split('-'))
 t=0 if h>a else 1 if h==a else 2
 return float(sum((v-(t==i))**2 for i,v in enumerate(p))),float(-math.log(max(p[t],1e-15)))
feat={(r['league'],r['fixture_id']):r for r in map(json.loads,FEAT.open())}
quotes=defaultdict(dict)
for r in map(json.loads,CROWN.open()):
 quotes[(r['league'],r['fixture_id'])][r['market']]=r
market={r['fid']:r for r in map(json.loads,MARKET.open()) if r['cohort']=='historical_Crown_T12'}
shape=json.loads(SHAPE.read_text())['by_league_season']
dcl_summary=json.loads(DCJ.read_text())
dcl={ (r['league'],r['fixture_id']):r for r in map(json.loads,DCL.open())}
for key,r in dcl.items():
 chk['Dixon_Coles_fixture']+=1
 f=feat[key]
 if f['score']!=r['score']:err['Dixon_Coles_wrong_target']+=1
 rho=dcl_summary['learned_rho'][r['league']][str(r['season'])]['rho']
 if abs(rho-r['trained_rho_previous_two_seasons'])>1e-12:err['Dixon_Coles_rho_join']+=1
 h,a=f['candidate_lambda']['bayes_prior_2']
 grid=np.arange(29,dtype=float)
 x=np.outer(poisson.pmf(grid,h),poisson.pmf(grid,a))
 x[0,0]*=1-h*a*rho;x[0,1]*=1+h*rho;x[1,0]*=1+a*rho;x[1,1]*=1-rho
 if x.min()<-1e-12:err['DC_negative_probability']+=1
 x/=x.sum()
 D=grid[:,None]-grid[None,:]
 p=[float(x[D>0].sum()),float(x[D==0].sum()),float(x[D<0].sum())]
 if abs(br(p,f['score'])[0]-r['Brier_DC'])>1e-10:
  err['DC_independent_Brier']+=1
 for markettype in ('AH','OU'):
  chk['DC_quarter_payoff']+=1
  rec=r['market'][markettype];q=quotes[key][markettype]
  if abs(rec['net_U']-settle(rec['side'],markettype,q['line'],q['odds'][rec['side']],f['score']))>1e-10:
   err['DC_cashflow']+=1
  orig=q['models']['bayes_prior_2_independent']
  if abs(rec['R5_poisson_net_U']-orig['net_U'])>1e-10:
   err['DC_R5_source_model_mismatch']+=1
assert chk['Dixon_Coles_fixture']==9908
# training D-C rho derivative of proper train-time loglik, per league/year
by_s=defaultdict(list)
for r in feat.values():by_s[(r['league'],r['season'])].append(r)
for lg,byyear in dcl_summary['learned_rho'].items():
 for year,s in byyear.items():
  target=int(year)
  train=by_s[(lg,target-2)]+by_s[(lg,target-1)]
  assert len(train)==s['train_fixtures']
  c=[]
  for row in train:
   h,a=map(int,row['score'].split('-'))
   lh,la=row['candidate_lambda']['bayes_prior_2']
   if h==a==0:v=-lh*la
   elif h==0 and a==1:v=lh
   elif h==1 and a==0:v=la
   elif h==1 and a==1:v=-1.
   else:v=0.
   c.append(v)
  c=np.array(c)
  rho=s['rho']
  gradient=float((c/(1+c*rho)).sum())
  if abs(gradient)>1e-4:err['Dixon_Coles_prior_Likelihood_gradient']+=1
  chk['DC_prior_year_parameter_calibration']+=1
# R11 multivariate walkforward re-score probabilities independently
wf_summary=json.loads(WFJ.read_text())
wf={(r['key'][0],r['key'][1]):r for r in map(json.loads,WF.open())}
g={(r['league'],r['fixture_id']):r for r in map(json.loads,GAMMA.open())}
assert len(g)==len(dcl)==9908
counts=Counter(r['season'] for r in g.values())
for yy,params in wf_summary['learned_parameters_by_test_year'].items():
 yr=int(yy)
 expected=counts[yr-2]+counts[yr-1]
 for k in ('xGk1','xGk2'):
  for mode,cal in params[k].items():
   if cal['train_n']!=expected:err['walkforward_prior_year_n_mismatch']+=1
   if cal['train_gradient_max_abs']>1e-6:err['walkforward_optimizer_gradient_too_large']+=1
   chk['walkforward_prior_year_fit_parameters']+=1
for key,z in wf.items():
 chk['walkforward_fixtures']+=1
 yr=z['season']
 if yr not in (2021,2022,2023,2024,2025):
  err['walkforward_invalid_test_year']+=1
 sc=z['score']
 assert g[key]['score']==sc
 q=quotes[key]['AH'];m=market[q['fid']]
 pm=np.array([m['models']['market_implied_Poisson'][a] for a in ('1X2_p_home','1X2_p_draw','1X2_p_away')])
 if abs(br(pm,sc)[0]-z['models']['market_raw']['Brier'])>1e-10:
  err['walkforward_market_Brier']+=1
 for k in ('xGk1','xGk2'):
  px=np.array(g[key]['methods']['gamma_obs_k'+k[-1]]['prob_1X2'])
  if abs(br(px,sc)[0]-z['models'][k+'_alone']['Brier'])>1e-10:
   err['walkforward_xG_Brier']+=1
  train=wf_summary['learned_parameters_by_test_year'][str(yr)][k]
  for mode,pars in train.items():
   theta=pars['params']
   logm=np.log(pm);diff=np.log(px)-logm
   if mode=='market_temperature':logit=theta[0]*logm
   elif mode=='market_plus_xG':logit=logm+theta[0]*diff
   else:logit=theta[0]*logm+theta[1]*diff
   p=softmax(logit)
   b,l=br(p,sc)
   v=z['models'][k+'_'+mode]
   chk['walkforward_model_probability_rechecks']+=1
   if max(abs(b-v['Brier']),abs(l-v['logloss']))>1e-10:
    err['walkforward_independent_score']+=1
assert chk['walkforward_fixtures']==7073
# xG shape distribution CDF independent rechecks all target xG outcomes
xg={ (r['league'],r['fixture_id'],r['venue']):r for r in map(json.loads,XGLEDGER.open()) }
xg_sum=json.loads(XGJ.read_text())
for key,r in xg.items():
 chk['xG_observation_records']+=1
 z=r['prior_asof_R5_attack_mean'];act=r['observed_xGF']
 if abs(z-feat[(r['league'],r['fixture_id'])]['posterior_means']['bayes_prior_2'][r['venue']+'_attack'])>1e-12:
  err['xG_prior_mean_join']+=1
 if abs(r['prior_two_season_Gamma_shape']-shape[r['league']][str(r['season'])]['shape'])>1e-12:
  err['xG_Gamma_prior_training_shape_join']+=1
 for model,shape_value in (('exp_shape1',1.),('asof_Gamma',r['prior_two_season_Gamma_shape'])):
  x=r['calibration'][model]
  if abs(x['pred_variance']-z*z/shape_value)>1e-10:
   err['xG_model_variance_recalc']+=1
  for name,cut in (('lte_025',.25),('lte_050',.5),('gte_200',2.),('gte_300',3.)):
   pp=float(gammacdf.cdf(cut,a=shape_value,scale=z/shape_value))
   if name.startswith('gte'):pp=1-pp
   target=(act<=cut) if name.startswith('lte') else (act>=cut)
   chk['xG_CDF_prob_brier_checks']+=1
   if max(abs(pp-x[name+'_prob']),
          abs((pp-target)**2-x[name+'_Brier']))>1e-10:
    err['xG_CDF_recalculation']+=1
assert chk['xG_observation_records']==19812
# fallback separate provider source, use timestamped progress only
fb=json.loads(FALLBACK.read_text())
if fb['index_rows']!=1156 or fb['index_capture_last_utc'][:10]!='2026-11-06':
 err['fallback_stale_source_provenance_wrong']+=1
chk['fallback_source_provenance']+=1
# all R5-R10 freezes unchanged 294 files
prior=[(SNAP/'R5_BAYES_BIVAR_FROZEN_20261123','FROZEN_SHA256_MANIFEST.json'),
       (SNAP/'R6_BAYES_BIVAR_COMPLEMENT_20261123','R6_FREEZE_MANIFEST.json'),
       (SNAP/'R7_CROWN_MARKET_PRICING_20261123','R7_FROZEN_SHA256_MANIFEST.json'),
       (SNAP/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123','R8_FROZEN_SHA256_MANIFEST.json'),
       (SNAP/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123','R9_FROZEN_SHA256_MANIFEST.json'),
       (SNAP/'R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123','R10_FROZEN_SHA256_MANIFEST.json')]
for folder,manifest in prior:
 content=json.loads((folder/manifest).read_text())
 for z in content['files']:
  f=folder/(z.get('file') or z.get('relative_path'))
  chk['R5_R10_frozen_SHA256_file_checks']+=1
  if not f.exists() or sha(f)!=z['sha256']:
   err['old_frozen_mutated_or_missing']+=1
assert chk['R5_R10_frozen_SHA256_file_checks']==294,chk
res={'status':'PASS' if not err else 'FAIL',
 'checks':dict(chk),'errors':dict(err),
 'prior_snapshot_manifest_SHA256':{f.name:sha(f/m) for f,m in prior},
 'R11_source_SHA256':{p.name:sha(p) for p in (FEAT,CROWN,MARKET,GAMMA,SHAPE)},
 'R11_result_SHA256':{p.name:sha(p) for p in (DCL,DCJ,WF,WFJ,XGLEDGER,XGJ,FALLBACK)},
 'scope':'Prior two-season D-C and learned market+xG parameters, 9908 Crown source-event quarter cash, 7073 cross-year proper scores, 19812 target xG CDF events, 294 earlier SHA immutable.'}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':res['status'],'checks':res['checks'],'errors':res['errors']},ensure_ascii=False))
assert res['status']=='PASS',res['errors']
