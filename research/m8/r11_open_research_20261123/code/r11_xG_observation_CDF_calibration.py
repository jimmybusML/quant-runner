#!/usr/bin/env python3
"""R11-C: genuine target-season OUTCOME diagnostic for xG observations.
R5 per-fixture prior-match-date team attack posterior mean is the forecast
of target game's OWN xGF, NOT Crown-adjusted goals. Predict a low-xG (<=0.25,
<=0.5) and high-xG (>=2, >=3) observation with:
  - Exponential shape=1 (R5 underlying observation assumption);
  - Previous TWO season measured Gamma shape (R10).
Use only pre-target historical shape and R5 asof team means. Actual target
xG is held for evaluation and has no influence on shape/mean. All 9908
target Crown-matched fixtures, 19816 team xG observations, no selection.
The thresholds are scoring-distribution diagnostic CDF points, NOT trade Gates.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,hashlib,math
import numpy as np
from scipy.stats import gamma as gd
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r11_open_method_research_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
F5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/research'
F10=ROOT/'frozen_research_snapshots/R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123'
FEAT=F5/'r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=F5/'r5_bayes_bivar_CrownT12_20261123.jsonl'
PARAM=F10/'r10_prior_two_season_xg_Gamma_shape.json'
OUT=HERE/'r11_xG_observation_calibration_2019_2025.jsonl'
SUMMARY=HERE/'r11_xG_observation_calibration_summary.json'
features={(r['league'],r['fixture_id']):r for r in map(json.loads,FEAT.open())}
cohort={(r['league'],r['fixture_id']) for r in map(json.loads,CROWN.open()) if r['market']=='AH'}
shape=json.loads(PARAM.read_text())['by_league_season']
fixtures={}
for lg in ('epl','bundesliga','serie-a','la-liga','ligue-1'):
 for yr in range(2019,2026):
  file=DATA/lg/str(yr)/'fixtures.csv'
  with file.open(encoding='utf-8-sig') as fd:
   for r in csv.DictReader(fd):
    key=(lg,r['fixture_id'])
    if key in cohort:fixtures[key]=r
assert len(cohort)==len(fixtures)==9908
thresholds={'lte_025':.25,'lte_050':.50,'gte_200':2.,'gte_300':3.}
rows=[];audit=Counter()
for key in sorted(cohort):
 f=features[key];raw=fixtures[key];lg=f['league'];yr=str(f['season'])
 assert raw['score']==f['score']
 if raw['totals_unreliable'].lower()=='true' or not raw['home_published_xg'] or not raw['away_published_xg']:
  audit['unreliable_target_xG']+=1;continue
 sh=shape[lg][yr]['shape']
 for venue in ('home','away'):
  observed=float(raw[venue+'_published_xg'])
  mean=f['posterior_means']['bayes_prior_2'][venue+'_attack']
  if mean<=0:raise ValueError((key,mean))
  data={'league':lg,'season':int(yr),'fixture_id':f['fixture_id'],'venue':venue,
   'observed_xGF':observed,'prior_asof_R5_attack_mean':mean,
   'prior_two_season_Gamma_shape':sh,'calibration':{}}
  for model,v in [('exp_shape1',1.),('asof_Gamma',sh)]:
   z={'observed_sq_error':(observed-mean)**2,
      'pred_variance':mean**2/v,
      'shape':v}
   for name,threshold in thresholds.items():
    p=gd.cdf(threshold,a=v,scale=mean/v)
    # For continuous model, P(xG >= threshold) complement CDF
    if name.startswith('gte_'):p=1-p
    y=int((observed<=threshold) if name.startswith('lte_') else (observed>=threshold))
    z[name+'_observed']=y
    z[name+'_prob']=p
    z[name+'_Brier']=(p-y)**2
   data['calibration'][model]=z
  rows.append(data)
  audit['target_team_observations']+=1
  if observed==0:audit['exact_zero_observed']+=1
assert len(rows)==2*(len(cohort)-audit['unreliable_target_xG']),(len(rows),audit)
audit['source_Crown_fixtures_unscored_for_xG_CDF_due_to_missing_outcome']=audit['unreliable_target_xG']
def agg(ss):
 n=len(ss)
 if n==0:return {'n':0}
 res={'n':n,'observed_zero':sum(z['observed_xGF']==0 for z in ss),
     'mean_observed_xG':round(sum(z['observed_xGF'] for z in ss)/n,7)}
 for model in ('exp_shape1','asof_Gamma'):
  s=[r['calibration'][model] for r in ss]
  res[model]={'n':n,
    'MSE_mean_xG':round(sum(q['observed_sq_error'] for q in s)/n,7),
    'avg_assumed_observation_var':round(sum(q['pred_variance'] for q in s)/n,7),
    'MSE_to_var_ratio':round(sum(q['observed_sq_error'] for q in s)/sum(q['pred_variance'] for q in s),7)}
  for name in thresholds:
   res[model][name]={'observed_rate':round(sum(q[name+'_observed'] for q in s)/n,6),
     'predicted_rate':round(sum(q[name+'_prob'] for q in s)/n,6),
     'Brier':round(sum(q[name+'_Brier'] for q in s)/n,7)}
 return res
result={'study':'R11_HISTORICAL_ASOF_XG_OBSERVATION_LIKELIHOOD_CALIBRATION',
 'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (FEAT,CROWN,PARAM)},
 'model':'Compare as-of pregame venue team attack means (R5 k2) against eventual actual match xG observation, under R5 exponential shape1 versus prior two completed season learned Gamma shape r≈3.3. No target-year goals or xG used to estimate shape or means.',
 'thresholds_only_probabilistic_CDF_scoring_points_not_trade_Gates':thresholds,
 'overall':agg(rows),
 'by_season':{str(y):agg([r for r in rows if r['season']==y]) for y in range(2019,2026)},
 'by_league':{lg:agg([r for r in rows if r['league']==lg]) for lg in sorted({r['league'] for r in rows})},
 'audit':dict(audit),
 'limitations':['Pre-game R5 attack means are estimates of venue-specific team expected xGF, but not equal to true latent strength; errors include injuries/opponents/drift.',
  'Original historical xG provider publication UTC not verified, only past match dates.',
  'Zero xG observations are point masses for rounded xG data; both continuous Gamma/Exponential assign zero exact point probability. Scores use cumulative thresholds, not exact-zero log likelihood.',
  'Data is previously explored matched Crown cohort, no new prospective sample; no betting gate or result-based selection, no national teams.']}
with OUT.open('w') as file:
 for r in rows:file.write(json.dumps(r,ensure_ascii=False)+'\n')
SUMMARY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'overall':result['overall'],'audit':result['audit']},ensure_ascii=False))
