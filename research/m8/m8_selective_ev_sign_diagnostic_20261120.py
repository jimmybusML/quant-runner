#!/usr/bin/env python3
"""Descriptive sign diagnostics for frozen E/I/market_response q80 receipt subsets."""
import collections,gzip,json,datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
D=ROOT/'research/m8/selective_research_20261119'
OUT=ROOT/'research/m8/selective_decomposition_20261120'
res=json.load(open(D/'M8_SELECTIVE_PROFITABILITY_RESULTS_20261119.json'))
methods=['E_discrete_AH_contract_calibration','I_line_style','market_response']
rows=[]
with gzip.open(D/'m8_selective_scores_20261119.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line)
  if r['method'] in methods and r.get('actual_home_u') is not None: rows.append(r)
out={}
for m in methods:
 threshold=float(res['actual_receipt_transfer_calibrations'][m]['top20_prior_confidence']['threshold'])
 entry={'threshold':threshold,'years':{},'actual_receipt_selected_outside_frozen_eight':{}}
 for year in ('2024','2025','2026'):
  z=[r for r in rows if r['method']==m and r['source_type']=='historical_event_replay' and not r.get('foundation_overlap') and r['date'][:4]==year and abs(float(r.get('confidence_abs') or 0))>=threshold]
  groups=collections.defaultdict(list)
  for r in z:
   best=max(float(r['predicted_home_return']),float(r['predicted_away_return']))
   groups['positive_best_EV' if best>0 else 'nonpositive_best_EV'].append(r)
  entry['years'][year]={k:{'n':len(v),'net_U':round(sum(float(r['pnl_u']) for r in v),6),'ROI_pct':round(100*sum(float(r['pnl_u']) for r in v)/len(v),6) if v else None} for k,v in groups.items()}
 z=[r for r in rows if r['method']==m and r['source_type']=='actual_http_receipt' and r.get('receipt_horizon') and not r.get('foundation_overlap') and abs(float(r.get('confidence_abs') or 0))>=threshold]
 groups=collections.defaultdict(list)
 for r in z:
  best=max(float(r['predicted_home_return']),float(r['predicted_away_return']))
  groups['positive_best_EV' if best>0 else 'nonpositive_best_EV'].append(r)
 entry['actual_receipt_selected_outside_frozen_eight']={k:{'n':len(v),'net_U':round(sum(float(r['pnl_u']) for r in v),6),'ROI_pct':round(100*sum(float(r['pnl_u']) for r in v)/len(v),6) if v else None} for k,v in groups.items()}
 out[m]=entry
(OUT/'M8_SELECTIVE_EV_SIGN_DIAGNOSTIC_20261120.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
for m,x in out.items():print(m,json.dumps(x['actual_receipt_selected_outside_frozen_eight'],ensure_ascii=False))
