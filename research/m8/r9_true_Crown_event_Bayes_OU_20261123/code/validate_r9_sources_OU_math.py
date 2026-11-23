#!/usr/bin/env python3
"""Independent R9 time-event, OU price probability, settlement, calibration
and frozen research integrity audit. Does not import any R9 modeling script.
"""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
import json,hashlib,math
import numpy as np
from scipy.stats import poisson,nbinom
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
R8=ROOT/'frozen_research_snapshots/R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123'
R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123'
R6=ROOT/'frozen_research_snapshots/R6_BAYES_BIVAR_COMPLEMENT_20261123'
R7=ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123'
TIME=HERE/'r9_crown_true_source_event_transition_ledger.jsonl'
BAYES=HERE/'r9_Bayes_OU_Over_to_Under_mechanism.jsonl'
SUMMARY_A=HERE/'r9_crown_true_source_event_transition_summary.json'
SUMMARY_B=HERE/'r9_Bayes_OU_Over_to_Under_summary.json'
SUMMARY_C=HERE/'r9_Bayes_OU_distribution_shape_sensitivity.json'
SUMMARY_D=HERE/'r9_Bayes_OU_variance_calibration_by_year.json'
SOURCE=R8/'r8_11club_Crown_actual_receipt_market_timing.jsonl'
FEATURE=R5/'research/r5_bayes_bivar_asof_features_20261123.jsonl'
CROWN=R5/'research/r5_bayes_bivar_CrownT12_20261123.jsonl'
POST=R8/'r8_full_posterior_predictive_club_20261123.jsonl'
OUT=HERE/'r9_independent_validation.json'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
 return h.hexdigest()
def time(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
checks=Counter();errors=Counter()
origtime={r['fid']:r for r in map(json.loads,SOURCE.open())}
def quote(s,m):return (float(s[m]['line']),tuple(sorted(s[m]['odds'].items())))
for row in map(json.loads,TIME.open()):
 checks['timing_fixtures']+=1
 orig=origtime[row['fid']]
 arr=orig['snapshots'];tt=row['transitions']
 if len(tt)!=len(arr)-1:errors['missing_transitions']+=1
 accum=0.;changes=0
 for i,t in enumerate(tt):
  checks['timing_transition_checks']+=1
  a,b=arr[i:i+2]
  diff=b['1X2_Brier']-a['1X2_Brier']
  if abs(diff-t['Brier_delta_after_minus_before'])>1e-12:errors['transition_score_diff']+=1
  qchange=any(quote(a,m)!=quote(b,m) for m in ('AH','OU'))
  if bool(t['price_changed'])!=qchange:errors['quote_change_reconstruction']+=1
  for m in ('AH','OU'):
   advanced=time(b[m+'_quote_source_event_utc'])>time(a[m+'_quote_source_event_utc'])
   if bool(t['AH_and_OU'][m]['source_event_time_advanced'])!=advanced:
    errors['source_time_advance_wrong']+=1
  rawchanged=a['raw_SHA256']!=b['raw_SHA256']
  if t['raw_http_sha_changed']!=rawchanged:errors['raw_changed_wrong']+=1
  if not qchange and abs(diff)>1e-12:errors['unchanged_quotes_changed_Brier']+=1
  changes+=qchange;accum+=diff
 if abs(accum-(orig['last_Brier']-orig['first_Brier']))>1e-12:errors['fixture_Brier_telescoping']+=1
 if changes==0:errors['fixture_no_updates_missed']+=1
assert checks['timing_fixtures']==468 and checks['timing_transition_checks']==3531
a_summary=json.loads(SUMMARY_A.read_text())
t=a_summary['all']['all_11_domestic_club_leagues']
if t['quote_update_transition_count']!=2387:errors['quote_update_count']+=1
if sum(v['n'] for v in t['transitions_by_state'].values())!=3531:errors['transition_type_count']+=1
# R5 historic source and R8 selected outputs never changed; exact independent
# settlement based on quarter-line two-leg contract and the SOURCE actual score.
crown={(r['league'],r['fixture_id']):r for r in map(json.loads,CROWN.open()) if r['market']=='OU'}
post={(r['league'],r['fixture_id']):r for r in map(json.loads,POST.open()) if r['Crown_matched']}
def legs(v):
 q=round(v*4)
 assert abs(q/4-v)<1e-9
 return [(v,1.)] if q%2==0 else [(math.floor(v*2)/2.,.5),(math.ceil(v*2)/2.,.5)]
def realized(side,line,odds,score):
 h,a=map(int,score.split('-'))
 ret=0.
 for v,w in legs(line):
  diff=h+a-v if side=='over' else v-h-a
  ret+=w*((odds-1) if diff>1e-10 else -1 if diff<-1e-10 else 0.)
 return ret
sums=defaultdict(lambda:defaultdict(float));n=0
for row in map(json.loads,BAYES.open()):
 checks['Bayes_OU_fixture_checks']+=1
 key=(row['league'],row['fixture_id'])
 original=crown[key];r8=post[key]
 for k in (1,2):
  z=row['models']['k'+str(k)]
  old=original['models']['bayes_prior_'+str(k)+'_independent']
  new=r8['models']['posterior_predictive_k'+str(k)]['OU']
  checks['Bayes_OU_model_fixture_checks']+=1
  if z['baseline_side']!=old['side'] or z['mixture_side']!=new['side']:
   errors['R5_R8_direction_mismatch']+=1
  p=z['R5_point_price_prob'];q=z['R8_full_posterior_price_prob']
  for model in (p,q,z['R8_sampling_mean_point_price_prob']):
   win=model['over_win'];loss=model['over_loss'];push=model['middle_push_mass']
   if min(win,loss,push)<-1e-9 or abs(win+loss+push-1)>1e-8:
    errors['OU_win_loss_push_mass']+=1
   od=row
   ov=(od['OU_price_over']-1)*win-loss
   un=(od['OU_price_under']-1)*loss-win
   margin=ov-un
   if max(abs(model['over']-ov),abs(model['under']-un),abs(model['over_minus_under']-margin))>1e-9:
    errors['OU_net_cash_probability_identity']+=1
  if abs(z['over_minus_under_EV_margin_total_delta']-
         (z['mean_shift_component']+z['uncertainty_mixture_component']))>1e-10:
   errors['EV_margin_variance_decomposition']+=1
  if z['mixture_side']!=max(('over','under'),key=lambda x:q[x]):
   errors['OU_market_selection_diff']+=1
  if z['baseline_side']!=max(('over','under'),key=lambda x:p[x]):
   errors['OU_market_base_selection_diff']+=1
  payoffnew=realized(z['mixture_side'],row['OU_line'],row['OU_price_'+z['mixture_side']],row['score'])
  payoffold=realized(z['baseline_side'],row['OU_line'],row['OU_price_'+z['baseline_side']],row['score'])
  if max(abs(payoffnew-new['realized_U']),abs(payoffold-old['net_U']),
         abs(payoffnew-z['R8_mixture_OU_U']),abs(payoffold-z['R5_point_OU_U']))>1e-9:
   errors['OU_independent_quarter_cash']+=1
  if abs(q[z['mixture_side']]-new['expected_U'])>1e-7 or abs(p[z['baseline_side']]-old['expected_U'])>1e-7:
   errors['OU_expected_U_R5_R8_mismatch']+=1
  sums[str(k)]['new']+=payoffnew;sums[str(k)]['old']+=payoffold
assert checks['Bayes_OU_fixture_checks']==9908 and checks['Bayes_OU_model_fixture_checks']==19816
bs=json.loads(SUMMARY_B.read_text())
for k in (1,2):
 z=bs['overall']['k'+str(k)]
 if abs(sums[str(k)]['new']-z['R8_posterior_return_U'])>1e-8 or abs(sums[str(k)]['old']-z['R5_point_return_U'])>1e-8:
  errors['OU_summary_cash']+=1
# Sensitivity matching shape and total actual squared prediction errors:
cs=json.loads(SUMMARY_C.read_text());vs=json.loads(SUMMARY_D.read_text())
for k in (1,2):
 p=vs['overall']['k'+str(k)]
 s=cs['k'+str(k)]['summary']
 checks['shape_aggregate_comparisons']+=1
 if abs(p['actual_total_squared_error_vs_posterior_mc_mean']-s['sq_error'])>1e-6:
  errors['shape_variance_MSE_summary']+=1
 if abs(p['posterior_mixture_mean_pred_variance']-s['mixture_variance'])>1e-6:
  errors['shape_variance_predicted']+=1
 if p['variance_excess_mix_minus_actual']<0:
  errors['not_overdispersed']+=1
# Verify all four earlier frozen sources remain byte-identical.
for location,manifest in ((R5,'FROZEN_SHA256_MANIFEST.json'),
                          (R6,'R6_FREEZE_MANIFEST.json'),
                          (R7,'R7_FROZEN_SHA256_MANIFEST.json'),
                          (R8,'R8_FROZEN_SHA256_MANIFEST.json')):
 m=json.loads((location/manifest).read_text())
 for row in m['files']:
  p=location/(row.get('file') or row.get('relative_path'))
  checks['R5_to_R8_prior_frozen_sha256_checks']+=1
  if not p.is_file() or sha(p)!=row['sha256']:
   errors['frozen_file_different']+=1
report={'status':'PASS' if not errors else 'FAIL','checks':dict(checks),'errors':dict(errors),
 'source_SHA256':{p.name:sha(p) for p in (SOURCE,FEATURE,CROWN,POST)},
 'outputs_SHA256':{p.name:sha(p) for p in (TIME,BAYES,SUMMARY_A,SUMMARY_B,SUMMARY_C,SUMMARY_D)},
 'prior_frozen_manifest_SHA256':{loc.name:sha(loc/manifest) for loc,manifest in
 ((R5,'FROZEN_SHA256_MANIFEST.json'),(R6,'R6_FREEZE_MANIFEST.json'),
  (R7,'R7_FROZEN_SHA256_MANIFEST.json'),(R8,'R8_FROZEN_SHA256_MANIFEST.json'))},
 'scope':'Independent R9 source-event transitions, Asian-quarter outcomes, posterior mixture decomposition and four previous frozen research integrity checks.'}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks':report['checks'],'errors':report['errors']},ensure_ascii=False))
assert report['status']=='PASS',errors