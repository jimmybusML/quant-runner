#!/usr/bin/env python3
"""R10 independent full book / data provenance / predictive checks.
All 9908 historical same-match Crown AH/OU cash and Brier reproduced via
new quarter-line payoff logic; prior two-year xG and goal dispersion
checks; immutable R5-R9 273-file SHA256. No official strategy changes.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,csv,math
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
SOURCE=ROOT/'frozen_research_snapshots'
R5=SOURCE/'R5_BAYES_BIVAR_FROZEN_20261123'
R6=SOURCE/'R6_BAYES_BIVAR_COMPLEMENT_20261123'
R7=SOURCE/'R7_CROWN_MARKET_PRICING_20261123'
R8=SOURCE/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123'
R9=SOURCE/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123'
XG=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
CROWN=R5/'research/r5_bayes_bivar_CrownT12_20261123.jsonl'
FEAT=R5/'research/r5_bayes_bivar_asof_features_20261123.jsonl'
R7MARKET=R7/'r7_market_implied_2market_20261123.jsonl'
SHAPE=HERE/'r10_prior_two_season_xg_Gamma_shape.json'
GAMMA=HERE/'r10_Gamma_xG_posterior_predictive_20261123.jsonl'
KALMAN=HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_20261123.jsonl'
NB=HERE/'r10_prev_two_season_asof_negative_binomial_CrownT12_20261123.jsonl'
BLEND=HERE/'r10_vs_Crown_market_incremental_1X2_20261123.jsonl'
SUM_G=HERE/'r10_Gamma_xG_posterior_predictive_summary_20261123.json'
SUM_D=HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_summary_20261123.json'
SUM_N=HERE/'r10_prev_two_season_asof_negative_binomial_summary_20261123.json'
SUM_B=HERE/'r10_vs_Crown_market_incremental_probabilities.json'
OUT=HERE/'r10_independent_math_source_frozen_validation.json'
checks=Counter();fail=Counter()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as fd:
  for b in iter(lambda:fd.read(1024*1024),b''):
   h.update(b)
 return h.hexdigest()
def payoff(side,market,line,odd,sc):
 h,a=map(int,sc.split('-'))
 q=round(float(line)*4)
 assert abs(float(line)-q/4)<1e-8
 parts=[(float(line),1)] if q%2==0 else [(math.floor(float(line)*2)/2,.5),(math.ceil(float(line)*2)/2,.5)]
 total=0.
 for part,w in parts:
  if market=='AH':v=(h-a+part) if side=='home' else (a-h-part)
  else:v=(h+a-part) if side=='over' else (part-h-a)
  total+=w*((odd-1) if v>1e-10 else -1 if v<-1e-10 else 0)
 return total
def proper(prob,sc):
 h,a=map(int,sc.split('-'))
 t=0 if h>a else (1 if h==a else 2)
 return sum((q-float(i==t))**2 for i,q in enumerate(prob)), -math.log(max(prob[t],1e-15))
prices=defaultdict(dict)
for r in map(json.loads,CROWN.open()):
 prices[(r['league'],r['fixture_id'])][r['market']]=r
assert len(prices)==9908
feat=defaultdict(dict)
for r in map(json.loads,FEAT.open()):
 feat[(r['league'],r['season'])][r['fixture_id']]=r
gamma={(r['league'],r['fixture_id']):r for r in map(json.loads,GAMMA.open())}
dynamic={(r['league'],r['fixture_id']):r for r in map(json.loads,KALMAN.open())}
nb={(r['league'],r['fixture_id']):r for r in map(json.loads,NB.open())}
blend={(r['league'],r['fixture_id']):r for r in map(json.loads,BLEND.open())}
market={r['fid']:r for r in map(json.loads,R7MARKET.open()) if r['cohort']=='historical_Crown_T12'}
if any(set(v)!=set(prices) for v in (gamma,dynamic,nb,blend)):fail['cohort_keys_differ']+=1
sums=defaultdict(float)
n=0
for key,price in prices.items():
 n+=1
 f=feat[(key[0],price['AH']['season'])][key[1]]
 gg=gamma[key];dy=dynamic[key];nn=nb[key];bl=blend[key];sc=f['score']
 if any(r['score']!=sc for r in (gg,dy,nn,bl)):fail['score_cohort_mismatch']+=1
 methods={**{'Gamma_k1':gg['methods']['gamma_obs_k1'],
             'Gamma_k2':gg['methods']['gamma_obs_k2']},
          'Dynamic':dy,
          'NB':nn}
 for method,mod in methods.items():
  checks['model_score_checks']+=1
  p=(mod['prob_1X2'] if method.startswith('Gamma') else mod['p_1x2'])
  b,ll=proper(p,sc)
  if max(abs(b-mod['Brier']),abs(ll-mod['logloss']),abs(sum(p)-1))>1e-9:
   fail['Brier_prob_invalid']+=1
  slot='price' if method.startswith('Gamma') else 'markets' if method=='Dynamic' else 'market'
  for mk in ('AH','OU'):
   checks['quarter_cash_checks']+=1
   x=mod[slot][mk]
   side=x['side']
   odd=price[mk]['odds'][side]
   observed=payoff(side,mk,price[mk]['line'],odd,sc)
   actual=x['actual_U'] if method!='NB' else x['net_U']
   if abs(actual-observed)>1e-9:fail['quarter_cash']+=1
   if method=='Gamma_k1' or method=='Gamma_k2':
    k=method[-1]
    old=price[mk]['models']['bayes_prior_'+k+'_independent']
    if abs(x['old_R5_mean_U']-old['net_U'])>1e-9:
     fail['Gamma_R5_cash_baseline']+=1
   elif method=='NB' or method=='Dynamic':
    old=price[mk]['models']['bayes_prior_2_independent']
    ref=x['R5_Bayes_k2_net_U'] if method=='NB' else x['R5_Bayes_k2_U']
    if abs(ref-old['net_U'])>1e-9:fail['nonGamma_R5_baseline']+=1
   sums[(method,mk)]+=observed
  sums[(method,'Brier')]+=b
  if method.startswith('Gamma'):
   mu,var=mod['posterior_lambda_total_mean'],mod['posterior_lambda_total_variance']
   if max(abs(mod['posterior_pred_total_variance']-(mu+var)),
          abs(mod['actual_total_sq_error']-
              (sum(map(int,sc.split('-')))-mu)**2))>1e-9:
    fail['posterior_goal_variance_wrong']+=1
 # Incremental Brier from each fixed blend, independent of source script.
 scores=bl['methods']
 m=market[price['AH']['fid']]['models']['market_implied_Poisson']
 marketprob=[m['1X2_p_home'],m['1X2_p_draw'],m['1X2_p_away']]
 others={'Gamma_xG_k1':methods['Gamma_k1']['prob_1X2'],
   'Gamma_xG_k2':methods['Gamma_k2']['prob_1X2'],
   'dynamic_Kalman':dy['p_1x2'],
   'goal_total_NB_k2':nn['p_1x2']}
 for name,prob in {'Crown_AH_OU_market':marketprob,**others}.items():
  b,ll=proper(prob,sc)
  if max(abs(b-scores[name]['brier']),abs(ll-scores[name]['logloss']))>1e-9:
   fail['fixed_market_aggregate_Brier']+=1
 for name,prob in others.items():
  for w,tag in ((.75,'market75_'),(.5,'market50_')):
   mixed=[w*a+(1-w)*b for a,b in zip(marketprob,prob)]
   label=tag+name+('25' if w==.75 else '50')
   b,ll=proper(mixed,sc)
   checks['market_fixed_blend_checks']+=1
   if max(abs(b-scores[label]['brier']),abs(ll-scores[label]['logloss']))>1e-9:
    fail['fixed_market_blend']+=1
 assert set(price)=={'AH','OU'}
checks['fixture_keys_full_sample']=n
assert checks['fixture_keys_full_sample']==9908
# Full source dispersion equations independently from prior two years
shape=json.loads(SHAPE.read_text())['by_league_season']
nbnoise=json.loads(SUM_N.read_text())['target_league_season_noise']
kalnoise=json.loads(SUM_D.read_text())['train_hyperparameters_by_league_season']
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
 for season in range(2019,2026):
  old=list(feat[(lg,season-2)].values())+list(feat[(lg,season-1)].values())
  den=sum(sum(r['candidate_lambda']['bayes_prior_2'])**2 for r in old)
  num=sum((sum(map(int,r['score'].split('-')))-sum(r['candidate_lambda']['bayes_prior_2']))**2-
      sum(r['candidate_lambda']['bayes_prior_2']) for r in old)
  q=num/den
  ref=nbnoise[lg][str(season)]
  if abs(ref['raw_delta_variance_over_mu_sq']-q)>1e-9:
   fail['previous_two_season_NB_moment']+=1
  if abs(ref['mathematically_valid_delta']-max(0.,q))>1e-9:
   fail['previous_two_season_NB_positive_support']+=1
  if ref['training_match_n']!=len(old):fail['previous_two_season_NB_count']+=1
  checks['prior_year_goal_dispersion_train_reconstruct']+=1
  # shape and Kalman hyperparameter estimates are exclusively prior two years;
  # audit source data support and count of prior xG fixtures.
  total_prior=0
  valid_xg_prior=0
  for y in (season-2,season-1):
   path=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'/lg/str(y)/'fixtures.csv'
   with path.open(encoding='utf-8-sig') as fd:
    for row in csv.DictReader(fd):
     total_prior+=1
     if row['totals_unreliable'].lower()=='true' or not row['home_published_xg'] or not row['away_published_xg']:
      continue
     valid_xg_prior+=1
  if valid_xg_prior!=shape[lg][str(season)]['trained_match_count']:
   fail['previous_two_seasons_shape_valid_xG_count']+=1
  if total_prior!=kalnoise[lg][str(season)]['train_games']:
   fail['previous_two_seasons_Kalman_raw_count']+=1
  checks['xg_train_two_prior_year_count']+=1
# Compare all model net, Brier and same market cohort across known summaries.
for method,summary in [('Gamma_k1',json.loads(SUM_G.read_text())['overall']['gamma_obs_k1']),
                       ('Gamma_k2',json.loads(SUM_G.read_text())['overall']['gamma_obs_k2']),
                       ('Dynamic',json.loads(SUM_D.read_text())['overall']),
                       ('NB',json.loads(SUM_N.read_text())['overall'])]:
 old_brier=summary['mean_Brier'] if method.startswith('Gamma') else summary['Brier']
 if abs(sums[(method,'Brier')]/n-old_brier)>1e-6:
  fail['summary_average_Brier_differ']+=1
 for mk in ('AH','OU'):
  if abs(sums[(method,mk)]-summary[mk]['net_U'])>1e-7:
   fail['summary_market_netU_differ']+=1
  checks['summary_model_market_cash']+=1
# Check exact R5-R9 immutability via 273 SHA digests
for directory,manifest in ((R5,'FROZEN_SHA256_MANIFEST.json'),
                           (R6,'R6_FREEZE_MANIFEST.json'),
                           (R7,'R7_FROZEN_SHA256_MANIFEST.json'),
                           (R8,'R8_FROZEN_SHA256_MANIFEST.json'),
                           (R9,'R9_FROZEN_SHA256_MANIFEST.json')):
 meta=json.loads((directory/manifest).read_text())
 for row in meta['files']:
  p=directory/(row.get('file') or row.get('relative_path'))
  checks['R5_to_R9_sha256_file_checks']+=1
  if not p.is_file() or sha(p)!=row['sha256']:
   fail['frozen_source_modified_or_missing']+=1
assert checks['R5_to_R9_sha256_file_checks']==273,checks
report={'status':'PASS' if not fail else 'FAIL',
 'checks':dict(checks),'errors':dict(fail),
 'R10_source_sha256':{p.name:sha(p) for p in (SHAPE,GAMMA,KALMAN,NB,BLEND)},
 'prior_frozen_R5_to_R9_manifest_SHA256':{directory.name:sha(directory/manifest) for directory,manifest in
 ((R5,'FROZEN_SHA256_MANIFEST.json'),(R6,'R6_FREEZE_MANIFEST.json'),
  (R7,'R7_FROZEN_SHA256_MANIFEST.json'),(R8,'R8_FROZEN_SHA256_MANIFEST.json'),
  (R9,'R9_FROZEN_SHA256_MANIFEST.json'))},
 'scope':'Full 9,908 same old Crown source-event fixtures, no actual trading; independent score/quarter payouts and previous-season dispersion, freeze integrity.'}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks':report['checks'],'errors':report['errors']},ensure_ascii=False))
assert report['status']=='PASS',report['errors']
