#!/usr/bin/env python3
"""R62: real online dynamic Poisson attack-defence EKF challenger, annual R57 fixtures.

Uses historical kickoff as known and a *hypothetical* +3h result visibility delay.
It is NOT a certified point-in-time replay of actual received event timestamps.
Research only; no actual bookmaker odds, orders, or Telegram actions.
"""
import os,json,math,heapq,datetime as dt,traceback
from pathlib import Path
import numpy as np
from dynamic_poisson_ekf_r62 import DynamicPoissonEKF

P=Path(__file__).resolve().parent
CACHE=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
TARGETS={(x["league"],x["year"]):x for x in json.loads((P/"M9_MULTILEAGUE_RESIDUAL_R57.json").read_text())["results"]}
SHARD=int(os.environ.get("R62_SHARD","0"))
OUT=P/f"M9_DYNAMIC_MODEL_R62_SHARD{SHARD}.json"
LINES=[-1.5,-1.25,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.25,1.5]
DIFF=np.indices((15,15))[0]-np.indices((15,15))[1]
MASK7=np.select([DIFF<=-3,DIFF==-2,DIFF==-1,DIFF==0,DIFF==1,DIFF==2],[0,1,2,3,4,5],default=6)
FIELDS=["one_ll","rps","exact_ll","margin_ll","margin_brier"]
def state(d,line):
    if round(line*4)%2:
        a=math.floor(line*2)/2;b=math.ceil(line*2)/2
    else:a=b=line
    pnl=.5*((d+a>0)-(d+a<0))+.5*((d+b>0)-(d+b<0))
    return {-1.:0,-.5:1,0.:2,.5:3,1.:4}[float(pnl)]
MASK5={str(l):np.vectorize(lambda d:state(int(d),l),otypes=[int])(DIFF) for l in LINES}
def read(path):
    data={}
    for r in json.loads(path.read_text()).get("rows",[]):
        if r.get("status")!="full":continue
        try:
            time=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
            home,away=str(r["h_id"]),str(r["a_id"])
            gh,ga=int(r["hg"]),int(r["ag"])
            if min(gh,ga)<0 or home==away:continue
            data[str(r["id"])]=(time,home,away,gh,ga)
        except (KeyError,ValueError,TypeError):continue
    return sorted(data.values())
def metric(grid,gh,ga):
    g=np.asarray(grid,dtype=float)
    assert g.shape==(15,15) and np.isfinite(g).all() and g.sum()>0 and g.min()>=0
    v=np.array([g[DIFF>0].sum(),g[DIFF==0].sum(),g[DIFF<0].sum()])
    k=0 if gh>ga else 1 if gh==ga else 2
    margin=np.bincount(MASK7.ravel(),weights=g.ravel(),minlength=7)
    d=gh-ga;b=0 if d<=-3 else 1 if d==-2 else 2 if d==-1 else 3 if d==0 else 4 if d==1 else 5 if d==2 else 6
    ah={}
    for line in LINES:
        key=str(line);probs=np.bincount(MASK5[key].ravel(),weights=g.ravel(),minlength=5)
        ka=state(d,line)
        ah[key]={"brier":float(((probs-np.eye(5)[ka])**2).sum()),
                 "ll":-math.log(max(float(probs[ka]),1e-12))}
    return {"one_ll":-math.log(max(float(v[k]),1e-12)),
            "rps":float(((np.cumsum(v)[:2]-np.cumsum(np.eye(3)[k])[:2])**2).sum()/2),
            "exact_ll":-math.log(max(float(g[gh,ga]) if gh<15 and ga<15 else 0.,1e-12)),
            "margin_ll":-math.log(max(float(margin[b]),1e-12)),
            "margin_brier":float(((margin-np.eye(7)[b])**2).sum()),"ah":ah}
def empty(lid,year):
    return {"league":lid,"year":year,"n":0,"summary":{f:0. for f in FIELDS},
           "ah":{str(l):{"brier":0.,"ll":0.} for l in LINES},
           "fixture_metrics":[]}
out=json.loads(OUT.read_text()) if OUT.exists() else {
    "method":"R62 full sequential diagonal-covariance assumed-density Poisson Extended Kalman state space; attack/defense per team and home/away league rate, random walk by elapsed days. Hypothetical result visibility kickoff+3h. All parameter values exploratory, no Crown ROI.","results":[],"errors":[]}
done={x["league"] for x in out["results"]+out["errors"] if "league" in x}
for path in sorted(CACHE.glob("*.json"),key=lambda p:int(p.stem)):
    lid=path.stem
    if int(lid)%4!=SHARD or lid in done or not any(k[0]==lid for k in TARGETS):continue
    try:
        rows=read(path)
        years=[y for (l,y) in TARGETS if l==lid]
        min_year=min(years);prior=[r for r in rows if r[0].year<min_year]
        # Prior baseline from only pre-first-test season histories, then full
        # sequential state filtering of all games up to and during test years.
        home_rate=sum(x[3] for x in prior)/len(prior)
        away_rate=sum(x[4] for x in prior)/len(prior)
        engine=DynamicPoissonEKF(home_goal_rate=home_rate,away_goal_rate=away_rate)
        known_by_year={y:{team for r in rows if r[0].year<y for team in (r[1],r[2])} for y in years}
        agg={y:empty(lid,y) for y in years};pending=[]
        for index,(time,h,a,gh,ga) in enumerate(rows):
            while pending and pending[0][0]<=time:
                available,_,rh,ra,rgh,rga=heapq.heappop(pending)
                engine.update(rh,ra,rgh,rga,available)
            grid,_=engine.predict(h,a,time)
            year=time.year
            if year in agg and h in known_by_year[year] and a in known_by_year[year]:
                result=agg[year];m=metric(grid,gh,ga)
                result["n"]+=1
                for key in FIELDS:result["summary"][key]+=m[key]
                for line in LINES:
                    sk=str(line)
                    for key in ("ll","brier"):result["ah"][sk][key]+=m["ah"][sk][key]
                result["fixture_metrics"].append([round(m[k],8) for k in FIELDS])
            heapq.heappush(pending,(time+dt.timedelta(hours=3),index,h,a,gh,ga))
        for year,result in agg.items():
            assert result["n"]>=TARGETS[(lid,year)]["n"],"Historical cache lost prior held-out fixtures"
            result["new_completed_since_r57"]=result["n"]-TARGETS[(lid,year)]["n"]
            result["training_before_first_test"]=len(prior)
            result["state_at_latest_fixture"]=engine.snapshot()
            out["results"].append(result)
            print("OK",lid,year,result["n"],"1x2",round(result["summary"]["one_ll"]/result["n"],5),flush=True)
    except Exception as e:
        out["errors"].append({"league":lid,"error":repr(e),"trace":traceback.format_exc()[-1400:]})
        print("ERROR",lid,repr(e),flush=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False)+"\n")
print("DONE",len(out["results"]),"errors",len(out["errors"]),flush=True)
