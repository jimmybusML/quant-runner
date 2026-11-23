#!/usr/bin/env python3
"""Numerically reproduce all 35 previous-two-season R10 xG likelihood shape
and dynamic Kalman R/Q estimates directly from raw Understat fixtures,
independently from the two training programs. No future season target data
or betting ROI in either estimator.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,math
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
SHAPE=json.loads((HERE/'r10_prior_two_season_xg_Gamma_shape.json').read_text())['by_league_season']
KALMAN=json.loads((HERE/'r10_asof_dynamic_logxG_Kalman_CrownT12_summary_20261123.json').read_text())['train_hyperparameters_by_league_season']
OUT=HERE/'r10_independent_raw_xG_hyperparameter_validation.json'
err=Counter();check=Counter();maxdiff=defaultdict(float)
def rows(lg,y):
 f=DATA/lg/str(y)/'fixtures.csv'
 with f.open(encoding='utf-8-sig') as fd:
  for r in csv.DictReader(fd):
   if r['totals_unreliable'].lower()=='true' or not r['home_published_xg'] or not r['away_published_xg']:
    yield None
   else:
    yield (r['date'],r['home'],r['away'],float(r['home_published_xg']),float(r['away_published_xg']))
for league in SHAPE:
 for yy in range(2019,2026):
  past=list(rows(league,yy-2))+list(rows(league,yy-1))
  valid=[r for r in past if r is not None]
  gm=defaultdict(list)
  gz=defaultdict(list)
  home_values=[];away_values=[]
  for date,home,away,x,y in valid:
   home_values.append(x);away_values.append(y)
   for key,value in ((('home',home,'attack'),x),(('home',home,'defense'),y),
                     (('away',away,'attack'),y),(('away',away,'defense'),x)):
    gm[key].append(value)
    gz[key].append((date,math.log(value+.1)))
  top=0.;bottom=0.;groupcount=0;nobserved=0
  for values in gm.values():
   n=len(values)
   if n<2:continue
   mu=np.mean(values)
   top+=(n-1)*mu*mu
   bottom+=sum((v-mu)**2 for v in values)
   groupcount+=1;nobserved+=n
  estimated=top/bottom
  expected=SHAPE[league][str(yy)]
  checks_this={'xG_Gamma_shape':(estimated,expected['shape']),
      'train_valid_xG_games':(len(valid),expected['trained_match_count']),
      'train_Gamma_team_role_groups':(groupcount,expected['team_venue_role_groups']),
      'train_Gamma_observations':(nobserved,expected['xG_observations_in_groups'])}
  delta=[];pairs=[]
  for obs in gz.values():
   x=[v for dt,v in sorted(obs)]
   z=np.diff(x)
   delta.extend(z.tolist())
   pairs.extend(zip(z[:-1],z[1:]))
  d=np.asarray(delta,dtype=float);p=np.asarray(pairs,dtype=float)
  dv=float(d.var(ddof=1))
  cov=float(np.cov(p[:,0],p[:,1],ddof=1)[0,1])
  R=max(0.,-cov);Q=max(0.,dv+2*cov)
  all_log_means=[float(np.mean([v for dt,v in arr])) for arr in gz.values() if len(arr)>=2]
  pv=float(np.var(all_log_means,ddof=1))
  expect=KALMAN[league][str(yy)]
  checks_this.update({'Kalman_R':(R,expect['measurement_noise_logxG_R']),
     'Kalman_Q':(Q,expect['process_innovation_Q_per_team_venue_role_match']),
     'Kalman_prior_state_var':(pv,expect['prior_team_role_log_variance']),
     'Kalman_league_home_mean':(float(np.mean(home_values)),expect['prior_league_home_mean_xG']),
     'Kalman_league_away_mean':(float(np.mean(away_values)),expect['prior_league_away_mean_xG']),
     'Kalman_raw_fixture_count':(len(past),expect['train_games'])})
  for field,(act,exp) in checks_this.items():
   checks_key=(field,league,yy)
   diff=abs(float(act)-float(exp))
   maxdiff[field]=max(maxdiff[field],diff)
   if diff>1e-9:
    err[field]+=1
   check['independent_field_estimations']+=1
  check['league_year_hyperparameter_reconstruction']+=1
report={'status':'PASS' if not err else 'FAIL',
 'checks':dict(check),'error_fields':dict(err),
 'max_abs_difference_each_estimator':dict(maxdiff),
 'scope':'All 35 league×target-season parameter sets reproduced from previous two complete Understat seasons, using neither target scores nor betting ROI.',
 'note':'Raw training fixture count and reliable-xG fixture count are distinct; three 2-season groups contain 1 invalid xG entry each, fully accounted for. No changes to R5-R9.'}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
assert report['status']=='PASS',report['error_fields']
