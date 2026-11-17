import json, hashlib, collections, datetime, math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_early_leading_price_mechanism_20261117.py').read_text()
exec(src[:src.index('def regression(')])
# Original frozen-eight membership is used ONLY as an outcome label at T1,
# never as a T12 model feature nor as a T12-time opportunity filter.
fr={r['fid']:r for r in map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open())}
assert len(fr)==10294
def labels(pack):
 mem=np.zeros(len(pack),float)
 # label direction -1 unknown, 0 away, 1 home (no frozen hit also unknown).
 direction=np.full(len(pack),-1,int)
 original_pnl=np.zeros(len(pack))
 ambiguous=collections.Counter()
 for i,z in enumerate(pack):
  a,b,c,d=z
  r=fr.get(b['fid'])
  if not r:continue
  mem[i]=1
  original_pnl[i]=float(r['pnl'])
  home=abs(float(d['home_U'])-float(r['pnl']))<1e-8
  away=abs(float(d['away_U'])-float(r['pnl']))<1e-8
  assert home or away
  if home and away:ambiguous[r['cohort']]+=1
  else:direction[i]=1 if home else 0
 return mem,direction,original_pnl,dict(ambiguous)
membership,side,t1pnl,amb=labels(h6)
h12=len(h6)
assert h12==38846
years=np.array([z[1]['year'] for z in h6])
dates=np.array([z[1]['date'] for z in h6])
fids=np.array([z[1]['fid'] for z in h6])
excluded_receipts=np.array([z not in receiptids for z in fids])
Q=np.array([features(a,b,'T12') for a,b,c,d in h6])
# Two feature arms: A uses early T12 AH market snapshot, B adds already
# observed T24->T12 repricing events (not T12->future repricing!).
def enhance(a,b):
 line24=float(a['al']);line12=float(b['al'])
 hp24=float(a['ah']);ap24=float(a['aa'])
 hp12=float(b['ah']);ap12=float(b['aa'])
 p24=ap24/(hp24+ap24);p12=ap12/(hp12+ap12)
 line_move=line12-line24
 phmove=hp12-hp24;pmove=ap12-ap24
 odds_event=(abs(phmove)>1e-10 or abs(pmove)>1e-10)
 ln_event=abs(line_move)>1e-10
 return [float(ln_event),float((not ln_event) and odds_event),
  float((not ln_event) and (not odds_event)),
  float(p12>p24+1e-10),float(p12<p24-1e-10),
  float(phmove>1e-10),float(phmove<-1e-10),
  float(pmove>1e-10),float(pmove<-1e-10),
  (p12-p24)*np.sign(line12),line_move*line12,
  abs(phmove)+abs(pmove),
  float((phmove*pmove)<-1e-10),
  float((phmove*pmove)>1e-10)]
extra=np.array([enhance(a,b) for a,b,c,d in h6])
X={
 'T12_AH_snapshot':Q[:,[0,2,3,4,5,7,13,15,16,17,18,19]],
 'T24_T12_AH_path':Q,
 'AH_path_plus_early_repricing_events':np.column_stack((Q,extra)),
}
assert all(np.isfinite(v).all() for v in X.values())
H=np.array([z[1]['home_U'] for z in h6],float)
A=np.array([z[1]['away_U'] for z in h6],float)
valid_side=(side>=0)
def fit(A0,y,training,at,reg=100):
 mean=A0[training].mean(0);sd=A0[training].std(0)
 mean[0]=0;sd[0]=1;sd=np.where(sd<1e-9,1,sd)
 xt=np.clip((A0[training]-mean)/sd,-8,8)
 yy=np.asarray(y)[training]
 pen=np.eye(A0.shape[1])*reg;pen[0,0]=0
 beta=np.linalg.solve(xt.T@xt+pen,xt.T@yy)
 def pred(s):return ((np.clip((s-mean)/sd,-8,8))@beta)
 return pred(A0[at]),pred(A0[training]),(mean,sd,beta)
def calc(pay,selected,year=None):
 if year is not None:selected=selected&(years==year)
 v=pay[selected]
 return {'n':int(len(v)),'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if len(v) else None,
  'wins':int((v>1e-9).sum()),'losses':int((v<-1e-9).sum()),'push':int((abs(v)<=1e-9).sum())}
def yearly(pay,selected):
 return {str(y):calc(pay,selected,y) for y in (2024,2025,2026)}
# Actual 1230 real Crown receipts from previously raw+SHA verified R22/R57.
R=[b for a,b in pairs]
actual_X={}
for key in X:
 a=np.array([features(a,b,'T12') for a,b in pairs])
 if key=='T12_AH_snapshot':a=a[:,[0,2,3,4,5,7,13,15,16,17,18,19]]
 if key=='AH_path_plus_early_repricing_events':
  a=np.column_stack((a,np.array([enhance(a,b) for a,b in pairs])))
 actual_X[key]=a
 assert a.shape[1]==X[key].shape[1]
true_R_membership=np.array([b['fid'] in fr for b in R])
actual_H=np.array([b['home_U'] for b in R],float)
actual_A=np.array([b['away_U'] for b in R],float)
source_evt=collections.Counter()
for a,b,c,d in h6:
 state='line_changed' if a['al']!=b['al'] else 'same_line_odds_changed' if a['ah']!=b['ah'] or a['aa']!=b['aa'] else 'no_price_change'
 source_evt[state]+=1
res={'study':'M8_R59_T12_PREDICT_FROZEN_T1_PRECURSORS_WITH_EARLY_REPRICING',
'method':'Historical target at future T1: frozen original-eight membership and its side (only if T1 exact settlement uniquely identifies side). Input strictly Crown AH T24/T12 prices already existing at T12 and early T24->T12 repricing event. No T6/T3/T1 future info in features, no score or membership used as feature. Fit previous calendar years only, explicitly exclude R22 actual receipt target FIDs from training. Evaluate independent held-out year 2024/25/26 and actual pregame HTTP receipts separately (retrospective model research, not locked forward). 100 ridge regularization and train-score 75th/90th percentile propensity are PREDEFINED research sensitivity alternatives, not approved EV gate, volume cap or production requirement. Rank on T1-frozen membership score, side predicted separately only on unambiguous known historical frozen side labels. Later T1 strategy signals available as targets, not as live T12 predicates. Causal ORIGINALLY FROZEN 8 + early model replaces any original fixture chosen earlier and retains original T1 otherwise; no duplicate match count; it is a hypothetical historical order transition and NOT deployed. All true positives, true negatives, early failed signals and negative returns are retained. Frozen original-eight historical strategy may itself have been selected using all these same years and cannot be held-out independent actual performance. Historical Crown market-event time pre-kickoff is retrospective, not proof of actual receipt; raw received quotes evaluated but prediction model invented after receipt. No OU candidate exclusions, all AH cohort, no Crown API calls or production changes.',
 'sources':{'historical_T24_T12_T6_T1':len(h6),
  'verified_received_T24_T12':len(R),
  'frozen_all_membership':len(fr),'historical_labeled_membership_in_same_archive':int(membership.sum()),
  'ambiguous_label_side_count':int(sum(amb.values())),'ambiguous_per_cohort':amb,
  'early_market_events':dict(source_evt),
  'actual_receipt_future_T1_member_RETROSPECTIVE':int(true_R_membership.sum())},
 'by_market_event':{},'models':{},'foundation':{}}
# Pure early-event groups are diagnostics, not filters/rules.
for label in ('line_changed','same_line_odds_changed','no_price_change'):
 mask=np.array([('line_changed' if a['al']!=b['al'] else 'same_line_odds_changed' if a['ah']!=b['ah'] or a['aa']!=b['aa'] else 'no_price_change')==label for a,b,c,d in h6])
 res['by_market_event'][label]={'historical_all':{'n':int(mask.sum()),'future_T1_frozen_n':int((mask&(membership>0)).sum()),
  'frozen_rate_pct':round(100*float(membership[mask].mean()),3)},
  'annual':{str(y):{'n':int((mask&(years==y)).sum()),
   'future_T1_frozen_n':int((mask&(years==y)&(membership>0)).sum())} for y in (2024,2025,2026)}}
# All target years and every elected early opportunity are included; only
# early predicted score ranking is used, not actual future membership.
for name,data in X.items():
 output={'feature_count':int(data.shape[1]),'years':{},'actual_received_quotes':{}}
 for year in (2024,2025,2026):
  train=np.flatnonzero((years<year)&excluded_receipts)
  te=np.flatnonzero(years==year)
  assert np.max(years[train])<year
  trside=np.flatnonzero((years<year)&excluded_receipts&valid_side)
  assert len(trside)>0
  pr,pr_train,mp=fit(data,membership,train,te)
  pside,ps_train,sp=fit(data,side,trside,te)
  decision=pside>=.5
  # Percentile from PRIOR YEARS' PREDICTIONS, not current-year
  # outcomes or current-year score rank, to avoid lookahead.
  thresholds={'every_fixture':-float('inf'),
   'research_training_p75':float(np.quantile(pr_train,.75)),
   'research_training_p90':float(np.quantile(pr_train,.90))}
  table={'n_train':len(train),'train_positive_members':int(membership[train].sum()),
   'side_training_n':len(trside),'year_test_n':len(te),'T1_member_n':int(membership[te].sum()),
   'model_membership_avg_score':round(float(pr.mean()),5),
   'side_accuracy_on_unique_T1_member':round(float((decision[valid_side[te]]==side[te][valid_side[te]]).mean()),5),
   'selected_by_experimental_score':{}}
  curpay=np.where(decision,H[te],A[te])
  idxmap={int(ix):j for j,ix in enumerate(te)}
  for mode,thr in thresholds.items():
   chosen=pr>thr
   early_ids=te[chosen]
   early=curpay[chosen]
   predicted_hit=np.asarray(membership[early_ids],bool)
   # Hypothetical unique-ID timing: early selection replaces any later T1
   # member order. There is no prior use of T1 membership in early decision.
   late_frozen=te[(membership[te]>0)&~np.isin(te,early_ids)]
   late_p=t1pnl[late_frozen]
   combined=np.r_[early,late_p]
   frozen_only=t1pnl[te[membership[te]>0]]
   keys=[fids[i] for i in early_ids]+[fids[i] for i in late_frozen]
   assert len(keys)==len(set(keys))
   normal=calc(curpay,chosen)
   cum={'n':len(combined),'U':round(float(combined.sum()),3),
        'ROI':round(float(100*combined.mean()),3) if len(combined) else None}
   item={'training_threshold':round(thr,7) if np.isfinite(thr) else None,
    'early_AH_simulation':normal,
    'future_T1_frozen_overlap_n_POSTHOC':int(predicted_hit.sum()),
    'future_T1_frozen_precision_POSTHOC':round(float(predicted_hit.mean()),4) if chosen.any() else None,
    'early_home_n':int(decision[chosen].sum()),
    'early_away_n':int((~decision[chosen]).sum()),
    'early_nonfrozen_retrospective_attribution':calc(curpay,chosen & ~(membership[te]>0)),
    'early_original8_replaced_n':int(predicted_hit.sum()),
    'late_original8_retained_n':len(late_frozen),
    'causal_combined_research':cum,
    'original8_frozen_baseline':{'n':len(frozen_only),'U':round(float(frozen_only.sum()),3),'ROI':round(100*float(frozen_only.mean()),3)},
    'causal_net_new_fixture_n':int(len(combined)-len(frozen_only)),
    'causal_delta_profit_U':round(float(combined.sum()-frozen_only.sum()),3)}
   table['selected_by_experimental_score'][mode]=item
  output['years'][str(year)]=table
  print('HIST',name,year,'ROC proxy T1rate',round(float(membership[te].mean()),4),'side_acc',table['side_accuracy_on_unique_T1_member'],
  [(k,v['early_AH_simulation']['n'],v['early_AH_simulation']['U'],v['early_AH_simulation']['ROI'],
    v['causal_net_new_fixture_n'],v['causal_delta_profit_U'],v['causal_combined_research']['ROI']) for k,v in table['selected_by_experimental_score'].items()],flush=True)
 # Actual R22 receipt data: fixed train <=2025, using only actually
 # received earlier Crown AH quotes for 2026; no future snapshot in model.
 train=np.flatnonzero((years<2026)&excluded_receipts)
 trside=np.flatnonzero((years<2026)&excluded_receipts&valid_side)
 actual=actual_X[name]
 _,_,mm=fit(data,membership,train,train)
 _,_,sm=fit(data,side,trside,trside)
 def predict(s,params):
  mean,sd,beta=params
  return np.clip((s-mean)/sd,-8,8)@beta
 pr=predict(actual,mm);dr=predict(actual,sm)>=.5
 pay=np.where(dr,actual_H,actual_A)
 prtr=predict(data[train],mm)
 for mode,thr in [('every_fixture',-float('inf')),('research_training_p75',float(np.quantile(prtr,.75))),
  ('research_training_p90',float(np.quantile(prtr,.90)))]:
  chosen=pr>thr
  vecp=pay[chosen]
  output['actual_received_quotes'][mode]={
    'price_received_AH_simulation':{'n':len(vecp),'U':round(float(vecp.sum()),3),
      'ROI':round(100*float(vecp.mean()),3) if len(vecp) else None},
    'future_T1_frozen_overlap_POSTHOC':int(true_R_membership[chosen].sum()),
    'price_received_outside_original8_POSTHOC':{
       'n':int((chosen&~true_R_membership).sum()),
       'U':round(float(pay[chosen&~true_R_membership].sum()),3),
       'ROI':round(100*float(pay[chosen&~true_R_membership].mean()),3) if (chosen&~true_R_membership).any() else None},
    'training_threshold':round(float(thr),7) if np.isfinite(thr) else None}
 print('RECEIPTS',name,output['actual_received_quotes'],flush=True)
 res['models'][name]=output
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
res['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],
 'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),
 'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(res['foundation'].values())
(P/'m8_r59_early_precursor_repricing_20261117.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
print('R59_SAVED',flush=True)
