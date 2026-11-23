#!/usr/bin/env python3
"""R54 full bivariate score grid with genuinely prior-model forecast residual; research only."""
import json,math,collections,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
H=Path("/Users/mac/QuantAsiaDesk/repos/m1/data/m1_history_cache")
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

from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
LEAGUES=("1","10","12","61");YEARS=(2024,2025,2026)
def model(rows):
 f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
 m=BivariatePoissonGoalModel(f.home_goals,f.away_goals,f.home_team,f.away_team);m.fit();return m
def masses(g):
 return float(np.tril(g,-1).sum()),float(np.trace(g)),float(np.triu(g,1).sum())
def tilt(g,d):
 i,j=np.indices(g.shape);a=g*np.exp(np.clip(d*(i-j),-30,30));return a/a.sum()
def stats(g,gh,ga):
 ph,pdraw,pa=masses(g);actual=0 if gh>ga else 1 if gh==ga else 2
 exact=-math.log(max(float(g[gh,ga]) if gh<g.shape[0] and ga<g.shape[1] else 0,1e-12))
 ll=-math.log(max((ph,pdraw,pa)[actual],1e-12))
 # Synthetic Asian handicap at line 0, 2.0 odds; not Crown.
 choice="home" if ph>=pa else "away"
 _,profit=settle_score("AH",0,choice,gh,ga,2.0)
 return exact,ll,profit
out={"scope":"Four-league annual-freeze actual M9 bivariate model-class score-grid research, NOT exact per-run production replay",
"method":"For test year Y, fit a calibration model on matches before Jan1(Y-1). Forecast fixtures in Y-1 for known teams; actual-minus-forecast expected points per team creates genuine prior-model forecast residual. Independently fit baseline M9 bivariate model on ALL matches before Jan1(Y); tilt its full score grid with exp(0.1*(home residual-away residual)*(home_goals-away_goals)), renormalize. Both baseline and corrected grids forecast same test fixtures Y. All calibration predictions use models trained strictly before their target matches. 0.1 is an exploratory grid-tilt parameter, not a user rule. Unseen teams get zero correction.",
"results":[],"errors":[]}
for lid in LEAGUES:
 rows=read(lid)
 for year in YEARS:
  cal_start=dt.datetime(year-1,1,1);test_start=dt.datetime(year,1,1)
  earlier=[r for r in rows if r[0]<cal_start]
  prev=[r for r in rows if cal_start<=r[0]<test_start]
  train=[r for r in rows if r[0]<test_start]
  known_earlier={r[1] for r in earlier}|{r[2] for r in earlier}
  known_train={r[1] for r in train}|{r[2] for r in train}
  test=[r for r in rows if test_start<=r[0]<dt.datetime(year+1,1,1) and r[1] in known_train and r[2] in known_train]
  if not earlier or not test:continue
  try:
   old=model(earlier);acc=collections.defaultdict(lambda:[0.,0])
   ncal=0
   for t,h,a,gh,ga in prev:
    if h not in known_earlier or a not in known_earlier:continue
    g=np.asarray(old.predict(h,a).grid,dtype=float);ph,pdraw,pa=masses(g)
    eh=ph+.5*pdraw;actual=1 if gh>ga else .5 if gh==ga else 0
    for team,delta in ((h,actual-eh),(a,eh-actual)):
     acc[team][0]+=delta;acc[team][1]+=1
    ncal+=1
   res={k:v[0]/v[1] for k,v in acc.items()}
   baseline=model(train);data={"original":[],"corrected":[]}
   for t,h,a,gh,ga in test:
    g=np.asarray(baseline.predict(h,a).grid,dtype=float)
    delta=res.get(h,0)-res.get(a,0)
    data["original"].append(stats(g,gh,ga))
    data["corrected"].append(stats(tilt(g,.1*delta),gh,ga))
   metrics={k:{"n":len(v),"exact_ll":float(np.mean([x[0] for x in v])),"1x2_ll":float(np.mean([x[1] for x in v])),"synthetic_AH0_unit":float(np.mean([x[2] for x in v]))} for k,v in data.items()}
   out["results"].append({"league":lid,"year":year,"calibration_train_n":len(earlier),"calibration_oos_n":ncal,"train_n":len(train),"test_n":len(test),"metrics":metrics})
   print(lid,year,"test",len(test),"cal",ncal,"LL",round(metrics["original"]["1x2_ll"],5),round(metrics["corrected"]["1x2_ll"],5),flush=True)
  except Exception as e:
   out["errors"].append({"league":lid,"year":year,"error":str(e)});print("ERROR",lid,year,str(e),flush=True)
  (P/"M9_TRUE_GRID_RESIDUAL_R54.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
out["caveats"]=["Calibration uses a prior-year OOS model forecast residual, not raw goal difference; model class is same as M9.","Calibration model is annual frozen, not per-match updated; previous-year OOS forecasts can be less recent than production.","Historical cache is latest snapshot and does not establish as-of historical receipt for each match.","0.1 score-grid tilt is exploratory, not fitted or authorized production setting.","Synthetic neutral AH0 2.0 is NOT Crown, no Crown ROI or tradable orders.","No formal M9, Telegram or ledger changes."]
(P/"M9_TRUE_GRID_RESIDUAL_R54.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
