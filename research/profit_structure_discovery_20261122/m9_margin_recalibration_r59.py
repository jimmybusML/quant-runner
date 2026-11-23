#!/usr/bin/env python3
"""R59 previous-year-only OOS seven-margin multiplicative calibration, read-only."""
import os,json,math,datetime as dt
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
H=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
P=Path(__file__).resolve().parent
SHARD=int(os.environ.get("R59_SHARD","0"))
OUT=P/f"M9_MARGIN_RECALIBRATION_R59_SHARD{SHARD}.json"
targets={(x["league"],x["year"]) for x in json.loads((P/"M9_MULTILEAGUE_RESIDUAL_R57.json").read_text())["results"]}
LINES=(-1.5,-1.25,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.25,1.5)
def read(path):
 data={}
 for r in json.loads(path.read_text()).get("rows",[]):
  if r.get("status")!="full":continue
  try:
   t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S");h,a=str(r["h_id"]),str(r["a_id"]);gh,ga=int(r["hg"]),int(r["ag"])
   if min(gh,ga)<0 or h==a:continue
   data[str(r["id"])]=(t,h,a,gh,ga)
  except (KeyError,TypeError,ValueError):continue
 return sorted(data.values())
def fit(rows):
 f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
 m=BivariatePoissonGoalModel(f.home_goals,f.away_goals,f.home_team,f.away_team);m.fit();return m
def index(diff):
 return 0 if diff<=-3 else 1 if diff==-2 else 2 if diff==-1 else 3 if diff==0 else 4 if diff==1 else 5 if diff==2 else 6
def arrays(g):
 ii,jj=np.indices(g.shape);return ii-jj,np.asarray([g[(ii-jj<=-3)].sum(),g[(ii-jj==-2)].sum(),g[(ii-jj==-1)].sum(),g[(ii-jj==0)].sum(),g[(ii-jj==1)].sum(),g[(ii-jj==2)].sum(),g[(ii-jj>=3)].sum()])
def adjust(g,factors):
 diff,_=arrays(g);weights=np.take(factors,np.select([diff<=-3,diff==-2,diff==-1,diff==0,diff==1,diff==2],[0,1,2,3,4,5],default=6))
 q=g*weights;return q/q.sum()
def state(diff,line):
 # home handicap outcome unit returns at 2.0, quarter splits
 quarter=round(line*4)
 if quarter%2:
  l1=math.floor(line*2)/2;l2=math.ceil(line*2)/2
  pnl=.5*((diff+l1>0)-(diff+l1<0))+.5*((diff+l2>0)-(diff+l2<0))
 else:pnl=(diff+line>0)-(diff+line<0)
 return {-1.:0,-.5:1,0.:2,.5:3,1.:4}[float(pnl)]
def init():
 return {"n":0,"cal_n":0,"margin_ll_base":0.,"margin_ll_corrected":0.,"margin_brier_base":0.,"margin_brier_corrected":0.,
 "observed":[0]*7,"expected_base":[0.]*7,"expected_corrected":[0.]*7,
 "ah_state_brier_base":{str(x):0. for x in LINES},"ah_state_brier_corrected":{str(x):0. for x in LINES},
 "ah_state_ll_base":{str(x):0. for x in LINES},"ah_state_ll_corrected":{str(x):0. for x in LINES},
 "ah0_side_changed":0}
out=json.loads(OUT.read_text()) if OUT.exists() else {"method":"R59 annual frozen model-class prior-year OOS margin recalibration, 7 categories, multiplicative (observed+1)/(expected+1) exploratory pseudocount; tested only next year. AH five-state synthetic handicap-line probability scoring at neutral odds 2.0, NOT Crown ROI.","results":[],"errors":[]}
done={(x["league"],x["year"]) for x in out["results"]+out["errors"]}
for path in sorted(H.glob("*.json"),key=lambda p:int(p.stem)):
 lid=path.stem
 if int(lid)%4!=SHARD:continue
 rows=read(path)
 for year in (2024,2025,2026):
  if (lid,year) not in targets or (lid,year) in done:continue
  cal=dt.datetime(year-1,1,1);cut=dt.datetime(year,1,1)
  earlier=[r for r in rows if r[0]<cal];previous=[r for r in rows if cal<=r[0]<cut];training=[r for r in rows if r[0]<cut]
  known_old={r[1] for r in earlier}|{r[2] for r in earlier};known={r[1] for r in training}|{r[2] for r in training}
  test=[r for r in rows if cut<=r[0]<dt.datetime(year+1,1,1) and r[1] in known and r[2] in known]
  try:
   old=fit(earlier);obs=np.zeros(7);exp=np.zeros(7);cal_n=0
   for t,h,a,gh,ga in previous:
    if h not in known_old or a not in known_old:continue
    g=np.asarray(old.predict(h,a).grid,dtype=float);_,pr=arrays(g)
    obs[index(gh-ga)]+=1;exp+=pr;cal_n+=1
   factors=(obs+1)/(exp+1)
   base=fit(training);agg=init();agg["cal_n"]=cal_n
   for t,h,a,gh,ga in test:
    g=np.asarray(base.predict(h,a).grid,dtype=float);q=adjust(g,factors)
    dif,p=arrays(g);_,pq=arrays(q);k=index(gh-ga);truth=np.eye(7)[k]
    agg["n"]+=1;agg["observed"][k]+=1
    for i in range(7):agg["expected_base"][i]+=float(p[i]);agg["expected_corrected"][i]+=float(pq[i])
    agg["margin_ll_base"]-=math.log(max(float(p[k]),1e-12));agg["margin_ll_corrected"]-=math.log(max(float(pq[k]),1e-12))
    agg["margin_brier_base"]+=float(((p-truth)**2).sum());agg["margin_brier_corrected"]+=float(((pq-truth)**2).sum())
    if (p[4]+p[5]+p[6]>=p[0]+p[1]+p[2])!=(pq[4]+pq[5]+pq[6]>=pq[0]+pq[1]+pq[2]):agg["ah0_side_changed"]+=1
    for line in LINES:
     key=str(line);v=np.zeros(5);w=np.zeros(5)
     for d in np.unique(dif):
      idx=state(int(d),line);v[idx]+=g[dif==d].sum();w[idx]+=q[dif==d].sum()
     actual=state(gh-ga,line);one=np.eye(5)[actual]
     agg["ah_state_brier_base"][key]+=float(((v-one)**2).sum())
     agg["ah_state_brier_corrected"][key]+=float(((w-one)**2).sum())
     agg["ah_state_ll_base"][key]-=math.log(max(v[actual],1e-12))
     agg["ah_state_ll_corrected"][key]-=math.log(max(w[actual],1e-12))
   out["results"].append({"league":lid,"year":year,**agg})
   print("OK",lid,year,agg["n"],"cal",cal_n,flush=True)
  except Exception as e:
   out["errors"].append({"league":lid,"year":year,"error":repr(e)});print("ERROR",lid,year,repr(e),flush=True)
  OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("DONE",len(out["results"]),"errors",len(out["errors"]),flush=True)
