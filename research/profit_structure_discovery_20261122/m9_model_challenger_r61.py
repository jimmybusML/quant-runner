#!/usr/bin/env python3
"""R61: genuine Dixon-Coles vs existing M9-class bivariate annual-frozen replay.

Research-only: no market quotes, no live deployment. Identical held-out fixtures.
Run: R61_SHARD=0..3 python m9_model_challenger_r61.py
"""
import os,json,math,datetime as dt,traceback
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import poisson
from penaltyblog.models import BivariatePoissonGoalModel,DixonColesGoalModel

P=Path(__file__).resolve().parent
CACHE=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
SHARD=int(os.getenv("R61_SHARD","0"))
OUT=P/f"M9_MODEL_CHALLENGER_R61_SHARD{SHARD}.json"
R57=json.loads((P/"M9_MULTILEAGUE_RESIDUAL_R57.json").read_text())
TARGETS={(x["league"],x["year"]):x for x in R57["results"]}
LINES=[-1.5,-1.25,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.25,1.5]
DIFF=np.indices((15,15))[0]-np.indices((15,15))[1]
def read(path):
    data={}
    for r in json.loads(path.read_text()).get("rows",[]):
        if r.get("status")!="full":continue
        try:
            t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
            h,a=str(r["h_id"]),str(r["a_id"])
            hg,ag=int(r["hg"]),int(r["ag"])
            if min(hg,ag)<0 or h==a:continue
            data[str(r["id"])]=(t,h,a,hg,ag)
        except (KeyError,ValueError,TypeError):continue
    return sorted(data.values())
def fit(model,rows):
    f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
    m=model(f.home_goals,f.away_goals,f.home_team,f.away_team)
    m.fit();return m
def margin_idx(d):
    return 0 if d<=-3 else 1 if d==-2 else 2 if d==-1 else 3 if d==0 else 4 if d==1 else 5 if d==2 else 6
def state(diff,line):
    v1=math.floor(line*2)/2 if round(line*4)%2 else line
    v2=math.ceil(line*2)/2 if round(line*4)%2 else line
    pnl=.5*((diff+v1>0)-(diff+v1<0))+.5*((diff+v2>0)-(diff+v2<0))
    return {-1.:0,-.5:1,0.:2,.5:3,1.:4}[float(pnl)]
MASK7=np.select([DIFF<=-3,DIFF==-2,DIFF==-1,DIFF==0,DIFF==1,DIFF==2],[0,1,2,3,4,5],default=6)
MASK5={str(l):np.vectorize(lambda diff:state(int(diff),l),otypes=[int])(DIFF) for l in LINES}
def safe_dc_predict(model,h,a):
    """Fitted DC with mathematically valid per-fixture rho projection if necessary."""
    hi,ai=model.team_to_idx[h],model.team_to_idx[a]
    p=model._params;n=model.n_teams
    lh=math.exp(p[hi]+p[ai+n]+p[-2])
    la=math.exp(p[ai]+p[hi+n])
    rho=float(p[-1]);lower=max(-1/lh,-1/la);upper=min(1.,1/(lh*la))
    used=min(max(rho,lower),upper)
    grid=np.outer(poisson.pmf(np.arange(15),lh),poisson.pmf(np.arange(15),la))
    grid[0,0]*=1-lh*la*used
    grid[0,1]*=1+lh*used
    grid[1,0]*=1+la*used
    grid[1,1]*=1-used
    grid/=grid.sum()
    return grid,abs(used-rho)>1e-12

def metrics(grid,hg,ag):
    g=np.asarray(grid,dtype=float);g/=g.sum()
    assert g.shape==(15,15) and np.all(np.isfinite(g)) and g.min()>=0
    d=hg-ag
    one_x_two=np.array([g[DIFF>0].sum(),g[DIFF==0].sum(),g[DIFF<0].sum()])
    k=0 if d>0 else 1 if d==0 else 2
    m7=np.bincount(MASK7.ravel(),weights=g.ravel(),minlength=7);kb=margin_idx(d)
    observed=np.eye(7)[kb]
    ah={}
    for line in LINES:
        key=str(line);v=np.bincount(MASK5[key].ravel(),weights=g.ravel(),minlength=5)
        ka=state(d,line);t=np.eye(5)[ka]
        ah[key]={"brier":float(np.sum((v-t)**2)),"ll":-math.log(max(float(v[ka]),1e-12))}
    cumsum=np.cumsum(one_x_two)
    truth_cumsum=np.cumsum(np.eye(3)[k])
    return {"one_ll":-math.log(max(float(one_x_two[k]),1e-12)),
       "rps":float(np.sum((cumsum[:2]-truth_cumsum[:2])**2)/2),
       "exact_ll":-math.log(max(float(g[hg,ag]) if hg<15 and ag<15 else 0.,1e-12)),
       "margin_ll":-math.log(max(float(m7[kb]),1e-12)),
       "margin_brier":float(np.sum((m7-observed)**2)),
       "ah":ah,
       "one":one_x_two.tolist(),"margin":m7.tolist()}
FIELDS=["one_ll","rps","exact_ll","margin_ll","margin_brier"]
out=json.loads(OUT.read_text()) if OUT.exists() else {"method":"R61 real fitted penaltyblog DixonColesGoalModel vs same M9-class BivariatePoissonGoalModel, annual-frozen historical-cache league/year pre-kickoff training, latest-cache matched held-out fixtures. DC rho projected only when mathematically necessary to prevent negative low-score probabilities; projection count reported. Synthetic AH probability, no Crown ROI.","results":[],"errors":[]}
done={(x["league"],x["year"]) for x in out["results"]+out["errors"]}
for path in sorted(CACHE.glob("*.json"),key=lambda p:int(p.stem)):
    lid=path.stem
    if int(lid)%4!=SHARD:continue
    rows=read(path)
    for year in (2024,2025,2026):
        if (lid,year) not in TARGETS or (lid,year) in done:continue
        cut=dt.datetime(year,1,1);nxt=dt.datetime(year+1,1,1)
        train=[r for r in rows if r[0]<cut]
        known={r[1] for r in train}|{r[2] for r in train}
        test=[r for r in rows if cut<=r[0]<nxt and r[1] in known and r[2] in known]
        try:
            base=fit(BivariatePoissonGoalModel,train)
            dc=fit(DixonColesGoalModel,train)
            total={"m9":{f:0. for f in FIELDS},"dc":{f:0. for f in FIELDS}}
            ah={tag:{str(x):{"brier":0.,"ll":0.} for x in LINES} for tag in ("m9","dc")}
            annual={"n":len(test),"n_training":len(train),"league":lid,"year":year,
                    "summary":total,"ah":ah,"fixture_differences":[],
                    "dc_rho_projection_n":0,"new_completed_since_r57":len(test)-TARGETS[(lid,year)]["n"]}
            for t,h,a,gh,ga in test:
                scores={}
                for tag,model in (("m9",base),("dc",dc)):
                    if tag=="dc":
                        dcgrid,projected=safe_dc_predict(model,h,a)
                        annual["dc_rho_projection_n"]+=int(projected)
                        scores[tag]=metrics(dcgrid,gh,ga)
                    else:
                        scores[tag]=metrics(model.predict(h,a,max_goals=15).grid,gh,ga)
                    for f in FIELDS:total[tag][f]+=scores[tag][f]
                    for line in LINES:
                        key=str(line)
                        for metric in ("brier","ll"):ah[tag][key][metric]+=scores[tag]["ah"][key][metric]
                annual["fixture_differences"].append([round(scores["m9"][f]-scores["dc"][f],8) for f in FIELDS])
            assert len(test)>=TARGETS[(lid,year)]["n"], "historical cache lost old heldout fixtures"
            if len(test)==TARGETS[(lid,year)]["n"]:
                assert abs(total["m9"]["one_ll"]/len(test)-TARGETS[(lid,year)]["original_1x2_ll"])<1e-8
            out["results"].append(annual)
            print("OK",lid,year,len(test),
                  "1x2 gain",round((total["m9"]["one_ll"]-total["dc"]["one_ll"])/len(test),6),flush=True)
        except Exception as e:
            out["errors"].append({"league":lid,"year":year,"error":repr(e),"trace":traceback.format_exc()[-1100:]})
            print("ERROR",lid,year,repr(e),flush=True)
        OUT.write_text(json.dumps(out,ensure_ascii=False)+"\n")
print("DONE",len(out["results"]),"errors",len(out["errors"]),flush=True)
