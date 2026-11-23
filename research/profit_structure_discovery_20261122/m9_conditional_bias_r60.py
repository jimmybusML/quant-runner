#!/usr/bin/env python3
"""R60: cross-year persistence of league-specific goal-difference calibration error.
No new model training; uses previously saved held-out R58 aggregate evidence."""
import json,math,collections
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
src=json.loads((P/"M9_GOAL_DIFFERENCE_R58.json").read_text())
rows=src["results"];bins=src["bins"]
by=collections.defaultdict(dict)
for x in rows:by[x["league"]][x["year"]]=x
pairs=[]
for league,yrs in by.items():
 for year in (2025,2026):
  if year-1 not in yrs or year not in yrs:continue
  a,b=yrs[year-1],yrs[year]
  for i,category in enumerate(bins):
   e1=(a["observed"][i]-a["expected_original"][i])/a["n"]
   e2=(b["observed"][i]-b["expected_original"][i])/b["n"]
   pairs.append({"league":league,"year":year,"bin":category,"n_prior":a["n"],"n_test":b["n"],"prior_bias":e1,"test_bias":e2})
def stats(v):
 if not v:return {"pairs":0}
 a=np.array([x["prior_bias"] for x in v]);b=np.array([x["test_bias"] for x in v]);w=np.array([x["n_test"] for x in v],float)
 same=float(np.average(np.sign(a)==np.sign(b),weights=w))
 corr=float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else None
 # Candidate fixed correction = previous-year residual; predict next-year residual
 baseline=float(np.average(b*b,weights=w))
 direct=float(np.average((b-a)**2,weights=w))
 # oracle shrink coefficient for diagnosis only, not used in any prediction
 oracle=float(np.sum(w*a*b)/np.sum(w*a*a)) if np.sum(w*a*a)>0 else None
 return {"pairs":len(v),"test_n_weighted":int(w.sum()),"same_sign_weighted":same,"pearson":corr,"baseline_error_mse":baseline,"prior_correction_error_mse":direct,"prior_correction_relative_mse":direct/baseline if baseline else None,"oracle_shrink_diagnostic":oracle}
out={"method":"R60 test persistence of prior-year league-specific model minus actual 7-bin goal-margin frequency residual using R58 held-out per-year aggregates. Uses previous test-year aggregate only to explain following-year aggregate; no future leakage in pairing, but no per-match conditional model or real Crown ROI.","overall":stats(pairs),"by_bin":{k:stats([x for x in pairs if x["bin"]==k]) for k in bins},"by_target_year":{str(y):stats([x for x in pairs if x["year"]==y]) for y in (2025,2026)},"pairs":pairs}
(P/"M9_CONDITIONAL_BIAS_R60.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in out.items() if k!="pairs"},indent=2))
