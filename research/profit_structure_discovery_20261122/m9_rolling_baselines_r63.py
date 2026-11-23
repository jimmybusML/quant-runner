#!/usr/bin/env python3
"""R63: monthly refitted BP/DC challengers with kickoff+3h available-result proxy.

This makes the BP/DC comparison less biased by their earlier annual freeze
against R62's online filter. Monthly schedule is a RESEARCH CHOICE, not a
user-approved workflow rule or proof of true receipt-time availability.
"""
import os,json,math,datetime as dt,collections,traceback
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import poisson
from penaltyblog.models import BivariatePoissonGoalModel,DixonColesGoalModel

P=Path(__file__).resolve().parent
CACHE=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
TARGETS={(x["league"],x["year"]):x for x in json.loads((P/"M9_MULTILEAGUE_RESIDUAL_R57.json").read_text())["results"]}
SHARD=int(os.environ.get("R63_SHARD","0"))
INCLUDE={x for x in os.environ.get("R63_INCLUDE","").split(",") if x}
LABEL=os.environ.get("R63_LABEL","")
OUT=P/(f"M9_ROLLING_BASELINES_R63_SHARD{SHARD}"+(f"_{LABEL}" if LABEL else "")+".json")
LINES=[-1.5,-1.25,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.25,1.5]
DIFF=np.indices((15,15))[0]-np.indices((15,15))[1]
MASK7=np.select([DIFF<=-3,DIFF==-2,DIFF==-1,DIFF==0,DIFF==1,DIFF==2],[0,1,2,3,4,5],default=6)
FIELDS=["one_ll","rps","exact_ll","margin_ll","margin_brier"]
def state(d,line):
    if round(line*4)%2:a=math.floor(line*2)/2;b=math.ceil(line*2)/2
    else:a=b=line
    pnl=.5*((d+a>0)-(d+a<0))+.5*((d+b>0)-(d+b<0))
    return {-1.:0,-.5:1,0.:2,.5:3,1.:4}[float(pnl)]
MASK5={str(l):np.vectorize(lambda d:state(int(d),l),otypes=[int])(DIFF) for l in LINES}
def read(path):
    data={}
    for r in json.loads(path.read_text()).get("rows",[]):
        if r.get("status")!="full":continue
        try:
            t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
            h,a=str(r["h_id"]),str(r["a_id"]);gh,ga=int(r["hg"]),int(r["ag"])
            if min(gh,ga)<0 or h==a:continue
            data[str(r["id"])]=(t,h,a,gh,ga)
        except (KeyError,ValueError,TypeError):continue
    return sorted(data.values())
def fit(cls,rows):
    f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
    m=cls(f.home_goals,f.away_goals,f.home_team,f.away_team);m.fit();return m
def dc_safe(m,h,a):
    hi,ai=m.team_to_idx[h],m.team_to_idx[a]
    p=m._params;n=m.n_teams
    lh=math.exp(p[hi]+p[ai+n]+p[-2]);la=math.exp(p[ai]+p[hi+n])
    rho=float(p[-1]);used=min(max(rho,max(-1/lh,-1/la)),min(1.,1/(lh*la)))
    g=np.outer(poisson.pmf(np.arange(15),lh),poisson.pmf(np.arange(15),la))
    g[0,0]*=1-lh*la*used;g[0,1]*=1+lh*used;g[1,0]*=1+la*used;g[1,1]*=1-used
    g/=g.sum()
    return g,abs(used-rho)>1e-12
def metric(g,gh,ga):
    g=np.asarray(g,dtype=float);assert g.shape==(15,15) and np.isfinite(g).all() and g.min()>=0
    p=np.array([g[DIFF>0].sum(),g[DIFF==0].sum(),g[DIFF<0].sum()])
    k=0 if gh>ga else 1 if gh==ga else 2;d=gh-ga
    margin=np.bincount(MASK7.ravel(),weights=g.ravel(),minlength=7)
    b=0 if d<=-3 else 1 if d==-2 else 2 if d==-1 else 3 if d==0 else 4 if d==1 else 5 if d==2 else 6
    ah={}
    for line in LINES:
        key=str(line);q=np.bincount(MASK5[key].ravel(),weights=g.ravel(),minlength=5);kk=state(d,line)
        ah[key]={"brier":float(((q-np.eye(5)[kk])**2).sum()),"ll":-math.log(max(float(q[kk]),1e-12))}
    return {"one_ll":-math.log(max(float(p[k]),1e-12)),
            "rps":float(((np.cumsum(p)[:2]-np.cumsum(np.eye(3)[k])[:2])**2).sum()/2),
            "exact_ll":-math.log(max(float(g[gh,ga]) if gh<15 and ga<15 else 0.,1e-12)),
            "margin_ll":-math.log(max(float(margin[b]),1e-12)),
            "margin_brier":float(((margin-np.eye(7)[b])**2).sum()),"ah":ah}
out=json.loads(OUT.read_text()) if OUT.exists() else {"method":"R63 monthly re-fit BP/DC on matches whose proxy result-availability was earlier than month start (kickoff+3h); matched R57 eligible fixture scope, no actual Crown ROI.","results":[],"errors":[]}
done={x["league"] for x in out["results"]+out["errors"]}
for path in sorted(CACHE.glob("*.json"),key=lambda p:int(p.stem)):
    lid=path.stem
    if int(lid)%4!=SHARD or lid in done or (INCLUDE and lid not in INCLUDE) or not any(k[0]==lid for k in TARGETS):continue
    try:
        rows=read(path)
        relevant_years={y for (l,y) in TARGETS if l==lid}
        known_by_year={y:{t for r in rows if r[0].year<y for t in (r[1],r[2])} for y in relevant_years}
        tests={y:[r for r in rows if r[0].year==y and r[1] in known_by_year[y] and r[2] in known_by_year[y]] for y in relevant_years}
        output={"league":lid,"years":{},"projections":0,"errors":[]}
        for year in sorted(relevant_years):
            test=tests[year]
            result={"n":len(test),"summary":{t:{f:0. for f in FIELDS} for t in ("bp","dc")},
                 "ah":{t:{str(l):{"brier":0.,"ll":0.} for l in LINES} for t in ("bp","dc")},
                 "unpredicted":0,"fixture_metrics":{"bp":[],"dc":[]},"monthly_fits":0}
            groups=collections.defaultdict(list)
            for r in test:groups[(r[0].year,r[0].month)].append(r)
            for (year_,month),fixtures in sorted(groups.items()):
                start=dt.datetime(year_,month,1)
                training=[r for r in rows if r[0]+dt.timedelta(hours=3)<=start]
                base=fit(BivariatePoissonGoalModel,training)
                dc=fit(DixonColesGoalModel,training)
                result["monthly_fits"]+=1
                for t,h,a,gh,ga in fixtures:
                    if h not in base.teams or a not in base.teams or h not in dc.teams or a not in dc.teams:
                        result["unpredicted"]+=1
                        for tag in ("bp","dc"):result["fixture_metrics"][tag].append(None)
                        continue
                    pred={"bp":base.predict(h,a,max_goals=15).grid}
                    pred["dc"],projected=dc_safe(dc,h,a);output["projections"]+=int(projected)
                    for tag in ("bp","dc"):
                        m=metric(pred[tag],gh,ga)
                        for f in FIELDS:result["summary"][tag][f]+=m[f]
                        for line in LINES:
                            key=str(line)
                            for f in ("ll","brier"):result["ah"][tag][key][f]+=m["ah"][key][f]
                        result["fixture_metrics"][tag].append([round(m[f],8) for f in FIELDS])
            assert result["n"]>=TARGETS[(lid,year)]["n"],"History missing old R57 fixture(s)"
            assert len(result["fixture_metrics"]["bp"])==len(test)
            output["years"][str(year)]=result
            print("OK",lid,year,len(test),"unpred",result["unpredicted"],"fits",result["monthly_fits"],flush=True)
        out["results"].append(output)
    except Exception as e:
        out["errors"].append({"league":lid,"error":repr(e),"trace":traceback.format_exc()[-1700:]})
        print("ERROR",lid,repr(e),flush=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False)+"\n")
print("DONE",len(out["results"]),"errors",len(out["errors"]),flush=True)
