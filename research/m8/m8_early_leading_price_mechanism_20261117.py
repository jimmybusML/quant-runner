import json,datetime,hashlib,collections,math
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Source functions have already independently verified Crown T24/T12:
# H/R are the target-time quote, hist/pairs the (T24,T12) pairs.
inv=collections.defaultdict(dict)
for line in (P/'m8_early_joint_market_inventory_20261115.jsonl').open():
 a=json.loads(line);t=a['T']
 if t in (6,12,24):
  assert t not in inv[a['fid']]
  inv[a['fid']][t]=a
t1={}
for file in ('m8_late_full_path_water_features_20261114.jsonl',
  'm8_extra_inventory_frozen_eight_20261115.jsonl',
  'm8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 for line in (P/file).open():
  a=json.loads(line);fid=a['fid']
  assert fid not in t1;t1[fid]=a
assert len(t1)==44956
def receipt_compatible(a,b):
 return all(a[k]==b[k] for k in ('fid','date','year','league','home_id','away_id','hg','ag'))
h12=[];errors=collections.Counter()
for a,b in hist:
 f=b['fid'];future=inv[f].get(6)
 if future is None:errors['12_missing_T6']+=1;continue
 if not receipt_compatible(b,future):errors['12_identity_score_mismatch']+=1;continue
 h12.append((a,b,future))
assert len(h12)==38846,(len(h12),errors)
h6=[]
for a,b,c in h12:
 q=t1.get(b['fid'])
 if q is None:errors['6_missing_T1']+=1;continue
 if any(str(c[k])!=str(q[k]) for k in ('fid','date','year','league')):
  errors['6_T1_identity_mismatch']+=1;continue
 try:
  hl=float(q['end_line']);ho=float(q['home_price']);ao=float(q['away_price'])
  hg=int(c['hg']);ag=int(c['ag'])
  ph=settle_score('AH',hl,'home',hg,ag,ho)[1]
  pa=settle_score('AH',hl,'away',hg,ag,ao)[1]
  assert abs(ph-float(q['end_home_U']))<1e-7 and abs(pa-float(q['end_away_U']))<1e-7
  # Same fixture FT score now tested against the T1 stored outcome and price.
  future={'fid':c['fid'],'year':c['year'],'date':c['date'],'league':c['league'],
   'al':hl,'ah':ho,'aa':ao,'home_U':ph,'away_U':pa,
   'hg':hg,'ag':ag,'home_id':c['home_id'],'away_id':c['away_id']}
  h6.append((a,b,c,future))
 except Exception as ex:errors['6_T1_invalid_'+type(ex).__name__]+=1
print('MATCH',len(h12),len(h6),'t1total',len(t1),'errors',dict(errors),'actual_receipt',len(R),flush=True)
def features(prev,now,horizon):
 a=prev;b=now
 line0=float(a['al']);line1=float(b['al'])
 h0=float(a['ah']);v0=float(a['aa']);h1=float(b['ah']);v1=float(b['aa'])
 p0=v0/(h0+v0);p1=v1/(h1+v1)
 phase=round(abs(line1)*4)%4
 delta=line1-line0
 return np.array([1.,line0,line1,abs(line1),np.sign(line1),float(line1==0),
  p0-.5,p1-.5,p1-p0,h0-h1,v0-v1,abs(delta),delta,
  1/h1+1/v1-1.,np.log1p(float(a['age_ah'])),
  np.log1p(float(b['age_ah'])),
  float(phase==0),float(phase==1),float(phase==2),float(phase==3),
  (h0-h1)*np.sign(line1),(v0-v1)*np.sign(line1)],float)
def target(now,future):
 # Exact same contract only. On change of AH handicap line target is 0
 # for the research label "demonstrable SAME CONTRACT odds shortening".
 # It is NOT an estimate of the comparable value of a different handicap.
 if float(now['al'])!=float(future['al']):return np.array([0.,0.])
 return np.array([float(now['ah'])-float(future['ah']),float(now['aa'])-float(future['aa'])])
def stats(p,mask=None):
 if mask is not None:p=np.asarray(p)[mask]
 n=len(p)
 return {'n':n,'U':round(float(sum(p)),3),'ROI':round(100*float(np.mean(p)),3) if n else None,
  'win':int((np.asarray(p)>1e-8).sum()),'loss':int((np.asarray(p)<-1e-8).sum()),'push':int((abs(np.asarray(p))<=1e-8).sum())}
def stage_data(pack,stage):
 if stage=='T12':
  previous=[z[0] for z in pack];now=[z[1] for z in pack];future=[z[2] for z in pack]
 else:
  previous=[z[1] for z in pack];now=[z[2] for z in pack];future=[z[3] for z in pack]
 X=np.array([features(a,b,stage) for a,b in zip(previous,now)])
 y=np.array([target(b,c) for b,c in zip(now,future)])
 year=np.array([z['year'] for z in now])
 fid=np.array([z['fid'] for z in now])
 frozen=np.array([z not in ids for z in fid])
 disjoint=np.array([z not in receiptids for z in fid])
 ph=np.array([z['home_U'] for z in now],float)
 pa=np.array([z['away_U'] for z in now],float)
 same=np.array([z['al']==c['al'] for z,c in zip(now,future)])
 return {'previous':previous,'now':now,'future':future,'X':X,'y':y,'year':year,'fid':fid,'outside_eight':frozen,
  'disjoint':disjoint,'home_pay':ph,'away_pay':pa,'same_line':same}
D={'T12':stage_data(h12,'T12'),'T6':stage_data(h6,'T6')}
def regression(A,Y,test,penalty=100):
 mu=A.mean(0);sd=A.std(0)
 mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 xt=np.clip((A-mu)/sd,-8,8)
 bet=np.eye(A.shape[1])*penalty;bet[0,0]=0
 coef=np.linalg.solve(xt.T@xt+bet,xt.T@Y)
 return np.clip((test-mu)/sd,-8,8)@coef,coef
def evaluate_stage(stage,d):
 years=d['year'];x=d['X'];targets=d['y'];out=d['outside_eight'];ind=d['disjoint']
 full=years>=2024
 test=out&full
 model_preds=np.zeros((len(years),2))
 fit={}
 for year in (2024,2025,2026):
  tr=(years<year)&ind;te=years==year
  assert np.max(years[tr])<year
  model_preds[te],coef=regression(x[tr],targets[tr],x[te])
  fit[str(year)]={'train_n':int(tr.sum()),'feature_n':int(x.shape[1]),'coef':coef.tolist()}
 # Predict SAME-contract shortening with no future price or final score in X.
 # Model selection is always a side, optional abstention is RESEARCH ONLY.
 buy_home=model_preds[:,0]>=model_preds[:,1]
 selected_clv=np.where(buy_home,targets[:,0],targets[:,1])
 expected_clv=np.max(model_preds,axis=1)
 p=np.where(buy_home,d['home_pay'],d['away_pay'])
 measures={}
 for mode,choices,pays in [
  ('price_forecast_always',np.ones(len(years),bool),p),
  ('price_forecast_opportunity_only',expected_clv>0,p),
  ('previous_drift_momentum',np.ones(len(years),bool),np.where(x[:,9]>=x[:,10],d['home_pay'],d['away_pay'])),
  ('previous_drift_reversal',np.ones(len(years),bool),np.where(x[:,9]<x[:,10],d['home_pay'],d['away_pay'])),
 ]:
  sample=test&choices
  summary={'total':stats(pays[sample]),'by_year':{str(y):stats(pays[sample&(years==y)]) for y in (2024,2025,2026)},
   'matched_quote_target':{'n':int(sample.sum()),'same_line_n':int((sample&d['same_line']).sum()),
    'selected_same_contract_shortening_mean_price_units':round(float(selected_clv[sample].mean()),6) if sample.any() and mode.startswith('price_forecast') else None,
    'predicted_same_contract_shortening_mean_price_units':round(float(expected_clv[sample].mean()),6) if sample.any() and mode.startswith('price_forecast') else None},
    'not_selected_n':int((test&~choices).sum()),
    'not_selected_if_forced':stats(pays[test&~choices])}
  if stage=='T12' and mode.startswith('price_forecast'):
   # Fit separately for actual verified receipts with 2026 prior years.
   XX=np.array([features(a,b,'T12') for a,b in pairs])
   target_pred,_=regression(x[(years<2026)&ind],targets[(years<2026)&ind],XX)
   rp=np.where(target_pred[:,0]>=target_pred[:,1],vec(R,'home_U'),vec(R,'away_U'))
   actual_choose=(target_pred.max(1)>0) if mode.endswith('only') else np.ones(len(R),bool)
   receipt_mask=rf&actual_choose
   summary['verified_actual_receipt_outside_eight']={
    'result':stats(rp[receipt_mask]),'all_eligible_receipts':int(rf.sum()),
    'abstained':int((rf&~actual_choose).sum()),
    'predicted_price_shortening_mean':round(float(target_pred.max(1)[receipt_mask].mean()),6) if receipt_mask.any() else None,
    'realized_future_clv':'unavailable: no receipt-verified T6 quote paired to these T12 receipts'}
  # Unrestricted target cohorts are the only cohorts not conditioned on
  # future T1 membership. Out-of-eight is retrospective attribution only.
  all_eligible=full&choices
  summary['all_eligible_at_time']={'total':stats(pays[all_eligible]),
     'by_year':{str(y):stats(pays[all_eligible&(years==y)]) for y in (2024,2025,2026)},
     'same_line_future_quote_n':int((all_eligible&d['same_line']).sum())}
  if stage=='T12' and mode.startswith('price_forecast'):
   summary['verified_actual_receipt_all_quotes']={
    'result':stats(rp[actual_choose]), 'received_pairs':len(R),
    'abstained':int((~actual_choose).sum())}
  measures[mode]=summary
  print('RESULT',stage,mode,'H',summary['total'],'2026',summary['by_year']['2026'],
   'ACTUAL',summary.get('verified_actual_receipt_outside_eight',{}),flush=True)
 return {'coverage':{'n_all_years':len(years),'n_test_outside_eight':int(test.sum()),
  'n_years':{str(y):int((test&(years==y)).sum()) for y in (2024,2025,2026)},
  'same_line_price_target_pct':round(float(d['same_line'][test].mean()*100),3)},
  'models':measures,'fit':fit}
out={'method':'R56 AH-only PRICE-MECHANISM research, not direct match winner modeling. Stage T12 uses exact pre-T12 Crown T24,T12 quote to forecast T12->T6 SAME CONTRACT selected-side odds shortening, and evaluates the AH stake AT T12 (not at future T6); Stage T6 uses exact T12,T6 historical quote to forecast T6->T1 SAME CONTRACT selected-side odds shortening, evaluates AH stake at T6. Price movement target for line-changed contracts is zero as a sentinel for not being comparable, never reports it as positive CLV. Model ridge 100 fit previous calendar years only, target results excluded from fit; exclude all separately verified receipt target fixture IDs in training. Benchmarks always pick side, momentum and reversal; research-only option choose to abstain when modeled price gain nonpositive. No trading new gate or default rule. Receipt dataset verifies Crown raw snapshot, identity, FT and actual receipt times for T24/T12; there is no same-receipt independently verified T6 or T1 later quote so later realized CLV on actual receipts is unavailable, not filled from retrospectively fetched quote. Historical quote timestamps do not imply actual pregame retrieval/executability, no TG orders. Original8 membership exclusion strictly retrospective contribution accounting, not executable filter. Same cohorts and negative results retained; no OU performance or candidates used. Features use only AH, no OU.','source':{'historical_T24_T12_T6_pairs':len(h12),'historical_T24_T12_T6_T1_pairs':len(h6),
  'actual_verified_T24_T12_receipts':len(R),'actual_receipts_outside_original_eight':int(rf.sum()),
  'quality':dict(errors)},'stages':{},'foundation':{}}
for stage,rows in D.items():out['stages'][stage]=evaluate_stage(stage,rows)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_early_leading_price_mechanism_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('SAVED',flush=True)
