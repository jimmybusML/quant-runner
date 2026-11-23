#!/usr/bin/env python3
"""R58 all available R57 eligible fixtures: goal-difference calibration diagnostic."""
import os,json,math,datetime as dt,collections
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
H=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
P=Path(__file__).resolve().parent
SHARD=os.environ.get("R58_SHARD","0")
OUT=P/("M9_GOAL_DIFFERENCE_R58_SHARD"+SHARD+".json")
R57=json.loads((P/"M9_MULTILEAGUE_RESIDUAL_R57.json").read_text())
targets={(x["league"],x["year"]) for x in R57["results"]}
# Bins preserve quarter AH settlement-relevant margins: 0, +/-1, +/-2, >=3
BINS=("away3plus","away2","away1","draw","home1","home2","home3plus")
def bin_index(diff):
 return 0 if diff<=-3 else 1 if diff==-2 else 2 if diff==-1 else 3 if diff==0 else 4 if diff==1 else 5 if diff==2 else 6
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
def bin_probs(g):
 ii,jj=np.indices(g.shape);ix=ii-jj
 return np.array([g[(ix<=-3)].sum(),g[ix==-2].sum(),g[ix==-1].sum(),g[ix==0].sum(),g[ix==1].sum(),g[ix==2].sum(),g[ix>=3].sum()])
def accum():
 return {"n":0,"observed":[0]*7,"expected_original":[0.]*7,"expected_corrected":[0.]*7,
 "brier_original_sum":0.,"brier_corrected_sum":0.,"margin_ll_original_sum":0.,"margin_ll_corrected_sum":0.}
def add(a,p,q,idx):
 a["n"]+=1;a["observed"][idx]+=1
 for k in range(7):a["expected_original"][k]+=float(p[k]);a["expected_corrected"][k]+=float(q[k])
 truth=np.eye(7)[idx]
 a["brier_original_sum"]+=float(np.sum((p-truth)**2));a["brier_corrected_sum"]+=float(np.sum((q-truth)**2))
 a["margin_ll_original_sum"]-=math.log(max(float(p[idx]),1e-12))
 a["margin_ll_corrected_sum"]-=math.log(max(float(q[idx]),1e-12))
out=json.loads(OUT.read_text()) if OUT.exists() else {"method":"Annual-frozen R57 original and prior-model OOS residual-corrected bivariate score grid; 7 actual margin categories, 2024-26, all eligible league-year fixtures; latest snapshot pre-kickoff filtered, not as-of historical archive.","results":[],"errors":[]}
done={(x["league"],x["year"]) for x in out["results"]+out["errors"]}
for path in sorted(H.glob("*.json"),key=lambda x:int(x.stem)):
 lid=path.stem
 if int(lid)%4!=int(SHARD):continue
 rows=read(path)
 for year in (2024,2025,2026):
  if (lid,year) not in targets or (lid,year) in done:continue
  cal=dt.datetime(year-1,1,1);cut=dt.datetime(year,1,1)
  earlier=[r for r in rows if r[0]<cal]
  previous=[r for r in rows if cal<=r[0]<cut]
  training=[r for r in rows if r[0]<cut]
  known_train={r[1] for r in training}|{r[2] for r in training}
  test=[r for r in rows if cut<=r[0]<dt.datetime(year+1,1,1) and r[1] in known_train and r[2] in known_train]
  try:
   old=fit(earlier);known_old={r[1] for r in earlier}|{r[2] for r in earlier}
   acc=collections.defaultdict(lambda:[0.,0])
   for t,h,a,gh,ga in previous:
    if h not in known_old or a not in known_old:continue
    g=np.asarray(old.predict(h,a).grid,dtype=float)
    ii,jj=np.indices(g.shape);eh=float(g[ii>jj].sum()+.5*g[ii==jj].sum())
    actual=1 if gh>ga else .5 if gh==ga else 0
    for team,d in ((h,actual-eh),(a,eh-actual)):
     acc[team][0]+=d;acc[team][1]+=1
   res={k:v[0]/v[1] for k,v in acc.items()}
   base=fit(training);agg=accum()
   for t,h,a,gh,ga in test:
    g=np.asarray(base.predict(h,a).grid,dtype=float)
    ii,jj=np.indices(g.shape);delta=.1*(res.get(h,0)-res.get(a,0))
    q=g*np.exp(np.clip(delta*(ii-jj),-30,30));q/=q.sum()
    add(agg,bin_probs(g),bin_probs(q),bin_index(gh-ga))
   out["results"].append({"league":lid,"year":year,**agg})
   print("OK",lid,year,agg["n"],flush=True)
  except Exception as e:
   out["errors"].append({"league":lid,"year":year,"error":repr(e)})
   print("ERROR",lid,year,repr(e),flush=True)
  OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("DONE",len(out["results"]),"errors",len(out["errors"]),flush=True)
