import json, math, collections, hashlib, datetime
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
P=Path('/Users/mac/QuantAsiaDesk/research-work')
root=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
digest=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
foundation={'membership':digest(root['historical_membership']['local_file'])==root['historical_membership']['sha256'],
 'inputs':all(digest(k)==v for k,v in root['input_sha256'].items()),
 'scripts':all(digest(k)==v for k,v in root['script_sha256'].items())}
assert all(foundation.values())
load=lambda k:[json.loads(s) for s in (P/k).open()]
member=load(root['historical_membership']['local_file']);ids={r['fid'] for r in member}
assert len(member)==len(ids)==10294
base=load('m8_late_full_path_water_features_20261114.jsonl')
extra=load('m8_extra_inventory_frozen_eight_20261115.jsonl')
raw=load('m8_raw_capture_unindexed_frozen_replay_20261115.jsonl')
same={r['fid']:r for r in load('m8_same_line_probability_path_20261114.jsonl')}
rows=[{**r,**same.get(r['fid'],{})} for r in base]+extra+raw
assert len(rows)==44956 and len({r['fid'] for r in rows})==44956
rows=sorted(rows,key=lambda r:(r['date'],r['fid']))
fids=[r['fid'] for r in rows]
years=np.array([r['year'] for r in rows]);dates=np.array([r['date'] for r in rows])
H=np.array([float(r['end_home_U']) for r in rows]);A=np.array([float(r['end_away_U']) for r in rows])
inside=np.array([r['fid'] in ids for r in rows])
assert int(inside.sum())==10294
# Exact snapshot member payout reconciliation, no hidden backfilled selections.
frozen={r['fid']:r for r in member}
for r,h,a in zip(rows,H,A):
 if r['fid'] in frozen:
  pnl=float(frozen[r['fid']]['pnl'])
  assert min(abs(pnl-h),abs(pnl-a))<=1e-7,(r['fid'],pnl,h,a)
# Only fields recorded by historical T1 snapshot. Never use score, cohort,
# membership or payoff itself as a feature. Zero-match flags separate.
def nz(v):
 try:return float(v) if v is not None and np.isfinite(float(v)) else 0.
 except:return 0.
shapes=['never_changed','one_way','reverted','oscillating']
def vector(r,rich):
 p=r['path_shape'];line=nz(r['end_line'])
 endh=nz(r['home_price']);enda=nz(r['away_price'])
 x=[line,nz(r['start_line']),abs(line),endh,enda,
  endh-enda,nz(r['home_price_vs_timeavg']),nz(r['away_price_vs_timeavg']),
  nz(r['line_range']),np.log1p(nz(r['n_line_changes'])),
  np.log1p(nz(r['n_events'])),np.log1p(max(0,nz(r['late_event_age_min']))),
  float(line==0.),float(r['had_anchor']),float(r['had_step']),
  *[float(p==v) for v in shapes]]
 if rich:
  x += [nz(r.get('p0')),nz(r.get('p3')),nz(r.get('p1')),
   nz(r.get('pstd')),nz(r.get('pmax'))-nz(r.get('pmin')),
   nz(r.get('home_price'))-nz(r.get('start_home_price')),
   nz(r.get('away_price'))-nz(r.get('start_away_price')),
   nz(r.get('n_price_moves')),nz(r.get('variation')),
   nz(r.get('final_line_minutes'))/60.,
   nz(r.get('last_line_change_age_min'))/60.,
   *[float(r.get('path_6_3_1')==v) for v in (
    'same_same','same_weaken','same_deepen','weaken_same',
    'deepen_same','weaken_deepen','deepen_weaken',
    'weaken_weaken','deepen_deepen')]]
 return x
X0=np.array([vector(r,False) for r in rows])
X1=np.array([vector(r,True) for r in rows])
# Avoid structural imbalance: payoffs and membership are NEVER used to scale,
# center or select nearest neighbors. Yearly scalers rely only prior years.
def transform(x,train,eval_ids):
 a=x[train];b=x[eval_ids]
 scale=a.std(0);center=a.mean(0)
 # Prespecified numeric research transform, not a trading gate.
 scale=np.where(scale<.05,1.,scale)
 return np.clip((a-center)/scale,-8,8),np.clip((b-center)/scale,-8,8)
def perf(indices,prices):
 v=np.asarray(prices,float)
 n=len(v)
 return {'n':n,'U':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3) if n else None,
  'wins':int((v>1e-10).sum()),'losses':int((v<-1e-10).sum()),'push':int((abs(v)<=1e-10).sum())}
# Estimate *return on each AH side*, not merely winner or which side would
# have returned more. Null action is part of opportunity research only.
# The previously tried always-bet models cannot express abstention.
models=[('structural_k128',X0,128),('structural_k512',X0,512),
        ('richer_k128',X1,128),('richer_k512',X1,512)]
out={'research_id':'R55_METHOD_SHIFT_OPPORTUNITY_VS_FORCED_BET',
 'method':'Entire original49 Crown T6/T3/T1 source-timestamp historical universe 44956 unique events, 10294 frozen original8. Contrast active selected path strategy and forced AH all-fixture model. Historical 2024/25/26 chronological holdout, all prior calendar years for k-nearest return analogues. Analyze home and away expected realized payout as independent targets then null action if BOTH historical neighbor means nonpositive; for positive max side simulate one unit, otherwise no simulated bet. 0 payoff cutoff, k=128/512 and fixed snapshot features are transparent offline research parameters, NOT newly approved EV trading gates or production rules. Negative predicted opportunities retained in abstained cohort for auditing. Simulated same-T1 choice without knowing future and no use of score, label, membership or payoff as predictors. Historical Crown sources were fetched retrospectively despite pregame source-event times; results are not real-time fillable or independent precommitted research. Existing frozen eight may have been historically optimized and is not necessarily pure out-of-sample. No OU outcomes, no original 8 modification. Date-cluster bootstrap is descriptive. Cannot merge study bets automatically or convert sample sizes to planned orders.',
 'coverage':{'unique_events':len(rows),'frozen_n':int(inside.sum()),
  'non_frozen_n':int((~inside).sum()),'years':{str(y):int((years==y).sum()) for y in sorted(set(years))},
  'source_snapshot_hashes':foundation},
 'original_eight':{},'unconditional':{},'models':{}}
for yr in (2024,2025,2026):
 m=(years==yr)
 frozen_ids=np.flatnonzero(m&inside)
 remainder_ids=np.flatnonzero(m&~inside)
 pay_frozen=np.array([frozen[fids[i]]['pnl'] for i in frozen_ids],float)
 out['original_eight'][str(yr)]=perf(frozen_ids,pay_frozen)
 out['unconditional'][str(yr)]={'non_frozen_home':perf(remainder_ids,H[remainder_ids]),
  'non_frozen_away':perf(remainder_ids,A[remainder_ids])}
 print('FROZEN',yr,out['original_eight'][str(yr)],
 'REST',out['unconditional'][str(yr)],flush=True)
for mode,X,k in models:
 results={'years':{},'diagnostic':{},'parameters':{'k':k,'features':X.shape[1],
   'profit_classifier':'nearest-neighbor empirical net Crown AH payout for both sides; simulate null when both <=0, a research-only null option'}}
 for yr in (2024,2025,2026):
  tr=np.flatnonzero(years<yr)
  te=np.flatnonzero((years==yr)&~inside)
  a,b=transform(X,tr,te)
  tree=cKDTree(a,leafsize=64)
  dd,neighbors=tree.query(b,k=min(k,len(tr)),workers=1)
  if neighbors.ndim==1:neighbors=neighbors[:,None]
  oh=H[tr][neighbors].mean(1);oa=A[tr][neighbors].mean(1)
  profit=np.maximum(oh,oa)
  is_trade=profit>0
  buy_home=oh>=oa
  trade=te[is_trade];pass_ids=te[~is_trade]
  p=np.where(buy_home[is_trade],H[trade],A[trade])
  forced_p=np.where(buy_home,H[te],A[te])
  # Same signal ranking to show high-confidence and low-confidence losses.
  result={'training_n':len(tr),'total_target_n':len(te),'selected':perf(trade,p),
   'abstained_n':len(pass_ids),
   'forced_all':perf(te,forced_p),
   'abstained_if_forced':perf(pass_ids,forced_p[~is_trade]),
   'selected_home_fraction':round(float(buy_home[is_trade].mean()),4) if len(trade) else None,
   'predicted_selected_profit_mean':round(float(profit[is_trade].mean()),5) if len(trade) else None,
   'predicted_abstained_profit_mean':round(float(profit[~is_trade].mean()),5) if len(pass_ids) else None,
   'actual_selected_per_month':{mon:int(sum(dates[trade]==mon)) for mon in sorted(set(dates[trade])) if mon[:4]==str(yr)}}
  results['years'][str(yr)]=result
  print('MODEL',mode,yr,'selected',result['selected'],'abstain',result['abstained_n'],
   'forced',result['forced_all'],'unselected_forced',result['abstained_if_forced'],flush=True)
 out['models'][mode]=results
# Distinguish actual received price cohort from the T1 late raw archive:
# previously 306 independently verified T1 snapshots and 50 frozen matches,
# but the full kNN features for all real receipts are not available as a
# matched timestamp-consistent table; NO fake actual receipt ROI for this model.
out['real_receipt_status']='No R55 model predictions made from real-time raw HTTP T1 snapshots; T1 historical replay only. Existing frozen 50 real-receipt-replay outcomes are not a forward precommitted new R55 model.'
(P/'m8_opportunity_selection_method_shift_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('SAVED',len(out['models']),flush=True)
