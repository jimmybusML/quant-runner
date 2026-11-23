#!/usr/bin/env python3
"""R49: original M9 bivariate score grids vs pre-cutoff team residual shrinkage, same fixtures.
Read-only research, pilot scope, synthetic neutral handicap only."""
import json,math,collections,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
P=Path(__file__).resolve().parent
H=Path("/Users/mac/QuantAsiaDesk/repos/m1/data/m1_history_cache")
LEAGUES=("1","10","12","61")
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
def fit_residuals(train,cutoff,window):
 # Team goal-difference residual versus M9 baseline expectation, using only pre-cutoff training matches.
 # Baseline in-sample residuals are an exploratory diagnostic, NOT OOS model calibration.
 res=collections.defaultdict(lambda:[0.,0])
 for t,h,a,gh,ga in train:
  if not (cutoff-dt.timedelta(days=window)<=t<cutoff):continue
  # League-neutral observed goal difference residual: demean by the entire historical home-advantage goal difference.
  res[h][0]+=gh-ga;res[h][1]+=1
  res[a][0]+=ga-gh;res[a][1]+=1
 return {k:v[0]/v[1] for k,v in res.items()}
def tilt(grid,delta,scale):
 # Symmetric score-difference exponential tilt; maintains nonnegative normalized full grid.
 i,j=np.indices(grid.shape)
 logits=np.clip(scale*delta*(i-j),-30,30)
 out=grid*np.exp(logits);return out/out.sum()
def score(grid,gh,ga):
 exact=-math.log(max(float(grid[gh,ga]) if gh<grid.shape[0] and ga<grid.shape[1] else 0,1e-12))
 ph=float(np.tril(grid,-1).sum());pd=float(np.trace(grid));pa=float(np.triu(grid,1).sum())
 truth=0 if gh>ga else 1 if gh==ga else 2
 probs=[ph,pd,pa]
 ll=-math.log(max(probs[truth],1e-12))
 brier=sum((v-(k==truth))**2 for k,v in enumerate(probs))
 # Synthetic neutral AH0 direction, no bookmaker quotes.
 pick=0 if ph>=pa else 2
 unit=0 if truth==1 else 1 if pick==truth else -1
 return exact,ll,brier,unit
variants=("original","recent_1y","smoothed_2y")
out={"scope":"M9 class same-fixture annual-frozen pilot; exploratory team goal-difference signal","source":str(H),"leagues":LEAGUES,"years":YEARS,"results":[],"errors":[],
"method":"Original bivariate grid vs symmetric score-difference exponential tilt. Team signal is each team's observed goal difference per match from previous one/two calendar years, calculated strictly before test year. Subtract home and away team signals. Exponential tilt strength is 0.1 (exploratory, NOT production). Note: raw goal difference is NOT a model forecast residual; the name of this file is historical, but method is goal-difference signal. Same fixtures, score grids, no Crown."}
for lid in LEAGUES:
 all_rows=read(lid)
 for year in YEARS:
  cutoff=dt.datetime(year,1,1)
  train=[r for r in all_rows if r[0]<cutoff]
  known={r[1] for r in train}|{r[2] for r in train}
  test=[r for r in all_rows if cutoff<=r[0]<dt.datetime(year+1,1,1) and r[1] in known and r[2] in known]
  if not train or not test:continue
  frame=pd.DataFrame(train,columns=["t","home_team","away_team","home_goals","away_goals"])
  try:
   m=BivariatePoissonGoalModel(frame.home_goals,frame.away_goals,frame.home_team,frame.away_team);m.fit()
   recent=fit_residuals(train,cutoff,365)
   smoothed=fit_residuals(train,cutoff,730)
   scores={v:[] for v in variants}
   for t,h,a,gh,ga in test:
    g=np.asarray(m.predict(h,a).grid,dtype=float)
    delta_recent=recent.get(h,0)-recent.get(a,0)
    delta_smooth=smoothed.get(h,0)-smoothed.get(a,0)
    for v,grid in (("original",g),("recent_1y",tilt(g,delta_recent,.1)),("smoothed_2y",tilt(g,delta_smooth,.1))):
     scores[v].append(score(grid,gh,ga))
   agg={v:{"n":len(q),"exact_ll":sum(x[0] for x in q)/len(q),"1x2_ll":sum(x[1] for x in q)/len(q),"brier":sum(x[2] for x in q)/len(q),"synthetic_AH0_unit":sum(x[3] for x in q)/len(q)} for v,q in scores.items()}
   out["results"].append({"league":lid,"year":year,"train_n":len(train),"test_n":len(test),"models":agg})
   print(lid,year,len(test),{v:round(a["1x2_ll"],6) for v,a in agg.items()},flush=True)
  except Exception as e:out["errors"].append({"league":lid,"year":year,"error":str(e)});print("ERROR",lid,year,e,flush=True)
  (P/"M9_SCOREGRID_STRENGTH_R49.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
out["caveats"]=["This is observed goal-difference signal, not forecast-error residual, and can double-count model strength. Results must not be described as R47 residual directly embedded.","0.1 tilt and 1y/2y windows are exploratory only, not approved production parameters.","Annual frozen model is not exact M9 per-run retraining.","Only four pilot league IDs; source is latest historical cache, not proven historically available at each cutoff.","Synthetic AH0 at 2.0 is not Crown AH or tradable ROI.","No production or Telegram changes."]
(P/"M9_SCOREGRID_STRENGTH_R49.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
