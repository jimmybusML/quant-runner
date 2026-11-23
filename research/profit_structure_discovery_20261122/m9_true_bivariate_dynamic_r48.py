#!/usr/bin/env python3
"""R48 same-fixture actual M9 class BivariatePoissonGoalModel: equal history vs time-decay weighted history.
Research-only sampled league pilot; no Crown or Telegram."""
import json,math,collections,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
ROOT=Path(__file__).resolve().parents[2]
P=Path(__file__).resolve().parent
H=Path("/Users/mac/QuantAsiaDesk/repos/m1/data/m1_history_cache")
LEAGUES=("1","10","12","61") # Research pilot selection, not production scope filter.
YEARS=(2024,2025,2026)
def read(lid):
 data=json.loads((H/(lid+".json")).read_text());rows={}
 for r in data["rows"]:
  if r.get("status")!="full":continue
  try:
   t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
   h,a=str(r["h_id"]),str(r["a_id"]);gh,ga=int(r["hg"]),int(r["ag"])
   if min(gh,ga)<0 or h==a:continue
   rows[str(r["id"])]=(t,h,a,gh,ga)
  except (KeyError,TypeError,ValueError):continue
 return sorted(rows.values())
def predict(model,h,a):
 grid=np.asarray(model.predict(h,a).grid,dtype=float)
 return grid
def scores(rows,grids):
 s=collections.defaultdict(list)
 for r,g in zip(rows,grids):
  t,h,a,gh,ga=r
  p=max(float(g[gh,ga]) if gh<g.shape[0] and ga<g.shape[1] else 0,1e-12)
  s["exact_ll"].append(-math.log(p))
  ph=float(np.tril(g,-1).sum());pd_=float(np.trace(g));pa=float(np.triu(g,1).sum())
  outcome=0 if gh>ga else 1 if gh==ga else 2
  q=(ph,pd_,pa)
  s["1x2_ll"].append(-math.log(max(q[outcome],1e-12)))
  s["1x2_brier"].append(sum((x-(i==outcome))**2 for i,x in enumerate(q)))
  # At a hypothetical AH 0 and 2.0 neutral odds: choose side with larger win mass; push if draw.
  pick=0 if ph>=pa else 2
  s["neutral_AH0_unit"].append(0 if outcome==1 else 1 if outcome==pick else -1)
 return {k:sum(v)/len(v) for k,v in s.items()}|{"n":len(rows)}
out={"source":str(H),"models":{},"years":list(YEARS),"leagues":list(LEAGUES),
"method":"For each league and calendar test year, fit the exact production M9 BivariatePoissonGoalModel class on all matches before January 1. Baseline uses equal weights, challenger uses exp(-age_days/365) recency weights. Forecast all fixtures of test year for which both teams appear in the frozen training history. This is a research-only annual-freeze comparison, not M9's per-run refit.",
"results":[],"errors":[]}
for lid in LEAGUES:
 all_rows=read(lid)
 for year in YEARS:
  cutoff=dt.datetime(year,1,1)
  train=[r for r in all_rows if r[0]<cutoff]
  known={r[1] for r in train}|{r[2] for r in train}
  test=[r for r in all_rows if cutoff<=r[0]<dt.datetime(year+1,1,1) and r[1] in known and r[2] in known]
  if not train or not test:continue
  frame=pd.DataFrame(train,columns=["t","home_team","away_team","home_goals","away_goals"])
  age=np.array([(cutoff-r[0]).total_seconds()/86400 for r in train])
  results={}
  for variant in ("original","recent_weighted"):
   try:
    weights=None if variant=="original" else np.exp(-age/365)
    m=BivariatePoissonGoalModel(frame.home_goals,frame.away_goals,frame.home_team,frame.away_team,weights=weights)
    m.fit()
    grids=[predict(m,r[1],r[2]) for r in test]
    results[variant]=scores(test,grids)
   except Exception as e:
    out["errors"].append({"league":lid,"year":year,"variant":variant,"error":str(e)})
  out["results"].append({"league":lid,"year":year,"train_n":len(train),"test_n":len(test),"models":results})
  print(lid,year,len(train),len(test),{k:{z:round(v[z],5) for z in ("exact_ll","1x2_ll","neutral_AH0_unit")} for k,v in results.items()},flush=True)
  (P/"M9_TRUE_BIVARIATE_DYNAMIC_R48.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
out["caveats"]=["Pilot subset leagues and calendar-year frozen training, not exact M9 per-run training time or full M9 scope.","365-day exponential half-life parameter is an exploratory comparison, not a user-approved production setting.","Neutral AH0 @2.0 is a synthetic directional diagnostic; NOT Crown quote/ROI or real M9 AH line.","M1 cached historical rows are latest snapshots; historical availability and corrections at the old forecast date are not proven.","No model rule, gate, Telegram or official ledger changed."]
(P/"M9_TRUE_BIVARIATE_DYNAMIC_R48.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
