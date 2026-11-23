#!/usr/bin/env python3
"""R8 descriptive (no acceptance gates): paired fixture bootstrap of pregame
Crown market forecast Brier improvement / deterioration. Existing verified
older receipts, not new prospective evidence. Cluster resample fixtures.
"""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
SRC=HERE/'r8_11club_Crown_actual_receipt_market_timing.jsonl'
OUT=HERE/'r8_11club_market_timing_paired_bootstrap_20261123.json'
Z=[json.loads(s) for s in SRC.open()]
BIG={'1','12','14','16','25'}
rng=np.random.default_rng(20261123)
def calc(items,tag):
    n=len(items)
    dif=np.array([r['last_minus_first_Brier'] for r in items])
    # Positive diff => later quote worse
    ids=rng.integers(0,n,(10000,n)) if n else np.empty((0,0),dtype=int)
    boot=dif[ids].mean(axis=1) if n else np.array([])
    six=[r for r in items if r.get('T6plus_received_count',0)>=2]
    delta6=np.array([r['T6plus_latest']-r['T6plus_earliest'] for r in six])
    ids6=rng.integers(0,len(six),(10000,len(six))) if six else np.empty((0,0),dtype=int)
    boot6=delta6[ids6].mean(axis=1) if six else np.array([])
    def bounds(values):
        return [round(float(x),7) for x in np.quantile(values,[.025,.975])] if len(values) else None
    by_month={month:{'n':sum(r['month']==month for r in items),
        'delta_Brier':round(sum(r['last_minus_first_Brier'] for r in items if r['month']==month)/
          sum(r['month']==month for r in items),7)} for month in sorted(set(r['month'] for r in items))}
    return {'label':tag,'n':n,'mean_latest_minus_earliest_Brier':round(float(dif.mean()),7) if n else None,
       'paired_bootstrap_95pct_Brier_delta':bounds(boot),
       'T6plus_n':len(six),'T6plus_late_minus_early_Brier':round(float(delta6.mean()),7) if len(six) else None,
       'T6plus_bootstrap_95pct_Brier_delta':bounds(boot6),
       'by_month':by_month}
groups={'all_11_domestic_club_leagues':Z,
  'five_big_club_leagues':[r for r in Z if r['league_id'] in BIG],
  'R5_old_138_receipt':[r for r in Z if r['R5_old_2026_sample']],
  'R5_old_71_big5':[r for r in Z if r['R5_old_2026_sample'] and r['league_id'] in BIG]}
res={'method':'Paired fixture (not quote) bootstrap with 10,000 resamples, randomized seed 20261123. Descriptive uncertainty; no new model acceptance gate.',
  'source_SHA256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
  'groups':{name:calc(g,name) for name,g in groups.items()},
  'notes':['R7 old 138 actual receipts are 11 domestic club leagues; only 71 from the five major leagues. Historical 9908 matches remain five.',
           'No causal claim: early and late snapshots are a repeated known-outcome observation, quoted lines and implied margins may change.',
           'Intervals are observational uncertainty; repeat historical study and selection not accounted for; no blinded new live prices.']}
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(res['groups'],ensure_ascii=False))