#!/usr/bin/env python3
"""R57 all available historical league caches, year-forward true residual score-grid.
Research only. No bookmaker ROI. Incremental resumable JSON checkpoint."""
import json,math,collections,datetime as dt,sys,traceback,os
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
from research.m3.probabilities import settle_score
H=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
P=Path(__file__).resolve().parent;OUT=P/"M9_MULTILEAGUE_RESIDUAL_R57.json"
YEARS=(2024,2025,2026)
SHARD=os.environ.get("R57_SHARD")
if SHARD is not None: OUT=P/("M9_MULTILEAGUE_RESIDUAL_R57_SHARD"+SHARD+".json")
def read(path):
 z=json.loads(path.read_text());data={}
 for r in z.get("rows",[]):
  if r.get("status")!="full":continue
  try:
   t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
   h,a=str(r["h_id"]),str(r["a_id"]);gh,ga=int(r["hg"]),int(r["ag"])
   if gh<0 or ga<0 or h==a:continue
   data[str(r["id"])]=(t,h,a,gh,ga)
  except (KeyError,TypeError,ValueError):continue
 return sorted(data.values())
def fit(rows):
 f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
 m=BivariatePoissonGoalModel(f.home_goals,f.away_goals,f.home_team,f.away_team);m.fit();return m
def evaluate(g,gh,ga):
 ph=float(np.tril(g,-1).sum());pdraw=float(np.trace(g));pa=float(np.triu(g,1).sum())
 truth=0 if gh>ga else 1 if gh==ga else 2
 ll=-math.log(max((ph,pdraw,pa)[truth],1e-12))
 exact=-math.log(max(float(g[gh,ga]) if gh<g.shape[0] and ga<g.shape[1] else 0,1e-12))
 side="home" if ph>=pa else "away"
 return ll,exact,side
def summarize(v):
 n=len(v)
 return {"n":n,"original_1x2_ll":sum(x[0] for x in v)/n,"corrected_1x2_ll":sum(x[1] for x in v)/n,
 "original_exact_ll":sum(x[2] for x in v)/n,"corrected_exact_ll":sum(x[3] for x in v)/n,
 "changed_AH0_side":sum(x[4]!=x[5] for x in v)}
result=json.loads(OUT.read_text()) if OUT.exists() else {"method":"Annual frozen M9 BivariatePoissonGoalModel class, previous-year OOS team points residual from model trained before that previous year, full-grid exp(0.1*(home-away residual)*(home goals-away goals)) tilt. All available league caches, years 2024-26. No bookmaker prices, no Crown ROI.","results":[],"errors":[],"skipped":[]}
done={(x["league"],x["year"]) for k in ("results","errors","skipped") for x in result[k]}
for path in sorted(H.glob("*.json"),key=lambda p:int(p.stem) if p.stem.isdigit() else 999999):
 lid=path.stem
 if SHARD is not None and int(lid)%4!=int(SHARD):continue
 rows=read(path)
 for year in YEARS:
  if (lid,year) in done:continue
  cal=dt.datetime(year-1,1,1);cut=dt.datetime(year,1,1)
  earlier=[r for r in rows if r[0]<cal]
  previous=[r for r in rows if cal<=r[0]<cut]
  training=[r for r in rows if r[0]<cut]
  test=[r for r in rows if cut<=r[0]<dt.datetime(year+1,1,1)]
  known={r[1] for r in training}|{r[2] for r in training}
  test=[r for r in test if r[1] in known and r[2] in known]
  if len(earlier)<25 or len(training)<40 or len(test)==0:
   result["skipped"].append({"league":lid,"year":year,"earlier":len(earlier),"training":len(training),"test":len(test)})
  else:
   try:
    old=fit(earlier);known_old={r[1] for r in earlier}|{r[2] for r in earlier}
    acc=collections.defaultdict(lambda:[0.,0]);ncal=0
    for t,h,a,gh,ga in previous:
     if h not in known_old or a not in known_old:continue
     g=np.asarray(old.predict(h,a).grid,dtype=float)
     expected=float(np.tril(g,-1).sum())+.5*float(np.trace(g))
     actual=1 if gh>ga else .5 if gh==ga else 0
     for team,d in ((h,actual-expected),(a,expected-actual)):
      acc[team][0]+=d;acc[team][1]+=1
     ncal+=1
    residual={k:v[0]/v[1] for k,v in acc.items()}
    base=fit(training);metrics=[]
    for t,h,a,gh,ga in test:
     g=np.asarray(base.predict(h,a).grid,dtype=float)
     delta=.1*(residual.get(h,0)-residual.get(a,0))
     ii,jj=np.indices(g.shape);q=g*np.exp(np.clip(delta*(ii-jj),-30,30));q/=q.sum()
     x=evaluate(g,gh,ga);y=evaluate(q,gh,ga)
     metrics.append((x[0],y[0],x[1],y[1],x[2],y[2]))
    result["results"].append({"league":lid,"year":year,"calibration_n":ncal,"training_n":len(training),**summarize(metrics)})
    print("OK",lid,year,len(test),round(result["results"][-1]["original_1x2_ll"]-result["results"][-1]["corrected_1x2_ll"],5),flush=True)
   except Exception as e:
    result["errors"].append({"league":lid,"year":year,"error":repr(e)})
    print("ERROR",lid,year,repr(e),flush=True)
  OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print("DONE",len(result["results"]),"skipped",len(result["skipped"]),"errors",len(result["errors"]),flush=True)
