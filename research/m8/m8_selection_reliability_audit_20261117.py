import json,datetime,collections,hashlib
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
j=json.loads((P/'m8_opportunity_selection_method_shift_20261117.json').read_text())
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
assert j['coverage']['source_snapshot_hashes']=={'membership':True,'inputs':True,'scripts':True}
assert dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256']
recs=[json.loads(s) for s in (P/'m8_new_receipt_frozen_eight_FT_20261115.jsonl').open()]
selected=[x for x in recs if x.get('cohort')]
assert len(recs)==306 and len(selected)==50
assert len({r['fid'] for r in selected})==50 and all(isinstance(r['pnl'],(int,float)) for r in selected)
assert abs(sum(r['pnl'] for r in selected)-3.64)<.001
rng=np.random.default_rng(55)
def bootstrap(vals,group=None,repeats=10000):
 a=np.asarray(vals,float)
 n=len(a)
 # Group whole dates when multiple matches same day can share exposures.
 if group:
  c=collections.defaultdict(list)
  for x,g in zip(a,group):c[g].append(x)
  totals=np.array([sum(r) for r in c.values()])
  length=np.array([len(r) for r in c.values()])
  k=len(totals)
  draws=rng.integers(0,k,size=(repeats,k))
  z=100*totals[draws].sum(1)/length[draws].sum(1)
 else:
  draws=rng.integers(0,n,size=(repeats,n))
  z=100*a[draws].mean(1)
 return {'n':n,'U':round(float(a.sum()),3),'ROI':round(100*float(a.mean()),3),'bootstrap95_roi_pp':[round(float(v),3) for v in np.quantile(z,[.025,.975])],
  'bootstrap_unit':'day' if group else 'match','resamples':repeats}
recent=bootstrap([r['pnl'] for r in selected],group=[r['kickoff_utc'][:10] for r in selected])
base=[r for r in selected if r['cohort']=='base']
other=[r for r in selected if r['cohort']!='base']
base_st=bootstrap([r['pnl'] for r in base],group=[r['kickoff_utc'][:10] for r in base])
other_st=bootstrap([r['pnl'] for r in other],group=[r['kickoff_utc'][:10] for r in other])
hist=[json.loads(s) for s in (P/'m8_foundation_20261115/historical_membership.jsonl').open()]
f26=[r for r in hist if r['year']==2026]
assert len(f26)==2218 and abs(sum(r['pnl'] for r in f26)-99.82)<.001
full26=bootstrap([r['pnl'] for r in f26],group=[r['date'] for r in f26],repeats=5000)
out={'analysis':'R55 supplementary credibility check. Source confirmed 306 actual received Crown T1 archive and 50 retrospectively recognized frozen8 signals; their outcomes are not a locked forward R55 strategy nor official TG orders. Original8 historical 2026 ROI confidence interval via UTC-day block bootstrap. Resampling intervals quantify historical variation, not repeated model-search selection bias. Model-neighbor predicted return optimism is an approximate analog score, not calibrated probability or actual executable EV. No production rules changed.','source':{'received_rows':len(recs),'selected_frozen':len(selected),'frozen':j['coverage']['source_snapshot_hashes']},'receipt_frozen':{'all':recent,'base':base_st,'others':other_st},'historical_2026_frozen_eight':full26,
 'model_neighbor_2026':{name:{'predicted_mean_roi_pp':round(z['years']['2026']['predicted_selected_profit_mean']*100,3),'observed_roi_pp':z['years']['2026']['selected']['ROI'],
  'optimism_gap_pp':round(z['years']['2026']['predicted_selected_profit_mean']*100-z['years']['2026']['selected']['ROI'],3),
  'selected_n':z['years']['2026']['selected']['n']} for name,z in j['models'].items()}}
(P/'m8_selection_reliability_audit_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
