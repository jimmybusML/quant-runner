import json,datetime,collections,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_transfer_activity_signal_20261117.py').read_text()
exec(s[:s.index('for market,sa,sb in')])
# M8 R51: AH-only. The historical OU experimental group's membership
# MUST NOT determine which AH fixtures are included in AH results.
ha=vec(H,'home_U');aa=vec(H,'away_U')
ra=vec(R,'home_U');rminus=vec(R,'away_U')
ind=(HY>=2024)&(HY<=2026)&hv
masks={
 'all_AH_eligible':ind,
 'outside_frozen_eight':ind&foundation,
 'R50_comparable_outside_ou_research':ind&foundation&other,
}
model_features={
 'market_path':lambda pairs,f:np.array([feature(a,b,'path') for a,b in pairs]),
 'market_90d_net':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[0,1,12,13]] @ np.array([[1,0],[ -1,0],[0,1],[0,-1]]))),
 'market_365d_net':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[6,7,18,19]] @ np.array([[1,0],[-1,0],[0,1],[0,-1]]))),
 'market_90_365d_net':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[0,1,12,13]] @ np.array([[1,0],[-1,0],[0,1],[0,-1]]),f[:,[6,7,18,19]] @ np.array([[1,0],[-1,0],[0,1],[0,-1]]))),
 'market_8_count':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[0,1,6,7,12,13,18,19]])),
 'market_4_diff':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[0,1,6,7]])),
 'market_8_count_ridge300':lambda pairs,f:np.column_stack((np.array([feature(a,b,'path') for a,b in pairs]),f[:,[0,1,6,7,12,13,18,19]]))
}
def pnl_stats(p,mask):
 if not mask.any():return {'n':0}
 v=p[mask];n=len(v)
 return {'n':n,'units':round(float(v.sum()),3),'ROI':round(100*float(v.mean()),3),
  'win':int((v>1e-10).sum()),'loss':int((v<-1e-10).sum()),'push':int((abs(v)<=1e-10).sum()),
  'stderr_roi_pp':round(100*float(v.std(ddof=1))/np.sqrt(n),3) if n>1 else None}
out={'research_id':'M8_R51_AH_ONLY','method':'AH-only study independent of OU profitability, original8 frozen. Previously same AH model used both frozen8 and unrelated OU experimental candidate exclusions for retrospective increment. Here compute all AH eligible and AH outside original8 separately without excluding OU research fixtures, and reproduce R50 narrower as a comparator. Train 2024/25/26 target strictly preceding-year, exclude all prospective receipt targets from fit; fixed Crown T12 AH exact-line payouts; all observed fixtures direction selected, no results/ROI filters or EV threshold; compare market alone, transfer in/out 90-day/365-day net and counts. New feature sets and ridge300 are research alternatives, not rules, optima, gates or production specs. Transfer info derives from backfilled TM effective dates through 2026-07-06, no proved contemporaneous ingestion; 2026 Oct/Nov receipt 0 valid, no real-time deployment, original8 unaffected.','coverage':{'all_eligible':int(masks['all_AH_eligible'].sum()),'outside_eight':int(masks['outside_frozen_eight'].sum()),'r50_comparable':int(masks['R50_comparable_outside_ou_research'].sum()),'receipt_valid':int(rv.sum()),'per_year_all':{str(y):int((ind&(HY==y)).sum()) for y in (2024,2025,2026)}},'hypotheses':{}}
for mode,generate in model_features.items():
 X=generate(hist,HF);Z=generate(pairs,RF)
 pred=np.zeros(len(H));rp=np.zeros(len(R));fit={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv;re=(RY==yr)&rv
  mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  xx=(X[tr]-mu)/sd
  ridge=300 if mode.endswith('ridge300') else 100
  penalty=np.eye(X.shape[1])*ridge;penalty[0,0]=0
  beta=np.linalg.solve(xx.T@xx+penalty,xx.T@(ha[tr]-aa[tr]))
  pred[te]=((X[te]-mu)/sd)@beta
  if re.any():rp[re]=((Z[re]-mu)/sd)@beta
  fit[str(yr)]={'n_train':int(tr.sum()),'n_features':int(X.shape[1]),'ridge':ridge,'coefficients':beta.tolist()}
 p=np.where(pred>=0,ha,aa)
 ret={}
 for label,m in masks.items():
  ret[label]={'total':score(H,p,m),'annual':{str(y):score(H,p,m&(HY==y)) for y in (2024,2025,2026)},'win_loss':pnl_stats(p,m),
    'daily':{k:{'n':int(sum(i for j,i in []))} for k in []}}
  # Source date month descriptive only, not a profitability-based rule.
  months=collections.defaultdict(list);leagues=collections.defaultdict(list)
  for i in np.flatnonzero(m):
   months[H[i]['date'][:7]].append(i)
   leagues[str(H[i]['league'])].append(i)
  ret[label]['by_month']={k:pnl_stats(p,np.isin(np.arange(len(H)),v)) for k,v in sorted(months.items())}
  ret[label]['by_league']={k:pnl_stats(p,np.isin(np.arange(len(H)),v)) for k,v in sorted(leagues.items())}
  ret[label]['unchanged_quote_price']={label:score(H,p,m&np.array([int(float(a['al'])==float(b['al'])) for a,b in hist],bool)) for label in ('identical_ah_line',)} if False else {}
 # Exactly no same underlying game included twice per cohort
 assert len({H[i]['fid'] for i in np.flatnonzero(masks['all_AH_eligible'])})==masks['all_AH_eligible'].sum()
 out['hypotheses'][mode]={'cohorts':ret,'training':fit}
 print('RESULT',mode,[(k,v['total']['n'],v['total']['U'],v['total']['ROI'],{y:z['ROI'] for y,z in v['annual'].items()}) for k,v in ret.items()],flush=True)
# Pairwise outcome differences (same fixture!) as stronger evidence than
# comparing separately filtered headline ROI. Values are not model EV.
base=out['hypotheses']['market_path']
for mode in out['hypotheses']:
 if mode=='market_path':continue
 v=out['hypotheses'][mode]['cohorts']
 out['hypotheses'][mode]['paired_improvement']={c:{
   'delta_units':round(v[c]['total']['U']-base['cohorts'][c]['total']['U'],3),
   'delta_roi_pp':round(v[c]['total']['ROI']-base['cohorts'][c]['total']['ROI'],3),
   'delta_roi_pp_by_year':{y:round(v[c]['annual'][y]['ROI']-base['cohorts'][c]['annual'][y]['ROI'],3) for y in ('2024','2025','2026')}
 } for c in masks}
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_ah_transfer_independent_deepdive_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
