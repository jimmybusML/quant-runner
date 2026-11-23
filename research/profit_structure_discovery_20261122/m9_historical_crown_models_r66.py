#!/usr/bin/env python3
"""R66 large historical 2023-26 Crown open/close replay, three probability engines.

Inputs are genuine but retrospectively received historical Crown quotes, verified
by R65. This is NOT an actually tradeable 2023-25 live receipt, and never writes
to formal Telegram or settled ledgers. No EV gating: one simulated home/away
choice per valid fixture per historical opening/closing price.
"""
import os,json,math,datetime as dt,collections,traceback
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np,pandas as pd
from scipy.stats import poisson
from penaltyblog.models import BivariatePoissonGoalModel,DixonColesGoalModel
from research.m3.probabilities import settle_score
from dynamic_poisson_ekf_r62 import DynamicPoissonEKF

HOME=Path.home()/"QuantAsiaDesk"
P=Path(__file__).resolve().parent
SHARD=int(os.environ.get("R66_SHARD","0"))
TAG=os.environ.get("R66_TAG","")
SUFFIX="_"+TAG if TAG else ""
OUT=P/f"M9_HISTORICAL_CROWN_R66_SHARD{SHARD}{SUFFIX}.json"
PRIVATE=HOME/f"state/m9_r66_replay_shard{SHARD}{SUFFIX}_private.json"
INPUT=Path(os.environ.get("R66_INPUT",str(HOME/"state/m9_r65_historical_crown_private.json")))
RAW=json.loads(INPUT.read_text())["rows"]
H=HOME/"repos/m1/data/m1_history_cache"
TZ=ZoneInfo("Asia/Shanghai")
DELAY=dt.timedelta(hours=3)
MODELS=("annual_bp","annual_dc","dynamic_ekf")
DIFF=np.indices((15,15))[0]-np.indices((15,15))[1]
STATE_KEYS=("FULL_WIN","HALF_WIN","PUSH","HALF_LOSS","FULL_LOSS")
CACHED={}
def utc(x):return dt.datetime.fromisoformat(str(x).replace("Z","+00:00"))
def fixture_time(x):return dt.datetime.strptime(x[:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ).astimezone(dt.timezone.utc)
def read(lid):
    data={}
    for r in json.loads((H/(lid+".json")).read_text())["rows"]:
        if r.get("status")!="full":continue
        try:
            t=fixture_time(str(r["start"]));h,a=str(r["h_id"]),str(r["a_id"]);hg,ga=int(r["hg"]),int(r["ag"])
            if min(hg,ga)<0 or h==a:continue
            data[str(r["id"])]=(t,h,a,hg,ga)
        except (KeyError,ValueError,TypeError):continue
    return sorted(data.values(),key=lambda r:r[0]+DELAY)
def fit(model,rows):
    data=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
    obj=model(data.home_goals,data.away_goals,data.home_team,data.away_team)
    try:obj.fit()
    except ValueError as exc:
        if "Iteration limit reached" not in str(exc):raise
        obj.fit(minimizer_options={"maxiter":3000})
    return obj
def dcgrid(m,h,a):
    hi,ai=m.team_to_idx[h],m.team_to_idx[a];p=m._params;n=m.n_teams
    lh=math.exp(p[hi]+p[ai+n]+p[-2]);la=math.exp(p[ai]+p[hi+n])
    rho=float(p[-1]);lo=max(-1/lh,-1/la);hi_bound=min(1.,1/(lh*la))
    adjusted=min(max(rho,lo),hi_bound)
    g=np.outer(poisson.pmf(np.arange(15),lh),poisson.pmf(np.arange(15),la))
    g[0,0]*=1-lh*la*adjusted;g[0,1]*=1+lh*adjusted;g[1,0]*=1+la*adjusted;g[1,1]*=1-adjusted
    return g/g.sum(),abs(adjusted-rho)>1e-12
def masks(line):
    if line not in CACHED:
        a={}
        for side in ("home","away"):
            d=DIFF if side=="home" else -DIFF
            l=line if side=="home" else -line
            if round(l*4)%2:l1=math.floor(l*2)/2;l2=math.ceil(l*2)/2
            else:l1=l2=l
            pnl=.5*(np.sign(d+l1)+np.sign(d+l2))
            a[side]=np.array([pnl==v for v in (1.,.5,0.,-.5,-1.)])
        CACHED[line]=a
    return CACHED[line]
def score_model(grid,quote,gh,ga):
    assert np.isfinite(grid).all() and grid.min()>=0 and abs(grid.sum()-1)<1e-7
    line=float(quote["line"]);ms=masks(line);scores={}
    for side in ("home","away"):
        odd=float(quote[side+"_decimal"])
        state=np.array([float(grid[mask].sum()) for mask in ms[side]])
        ev=float((state[0]+.5*state[1])*(odd-1)-state[3]*.5-state[4])
        neutral=float((state[0]+.5*state[1])-state[3]*.5-state[4])
        real_state,pnl=settle_score("AH",line,side,int(gh),int(ga),odd)
        scores[side]={"ev":ev,"neutral":neutral,"pnl_u":pnl,"state":real_state,"probabilities":state.tolist()}
    ev_side=max(scores,key=lambda v:(scores[v]["ev"],v=="home"))
    neutral_side=max(scores,key=lambda v:(scores[v]["neutral"],v=="home"))
    d=gh-ga;prob=np.array([grid[DIFF>0].sum(),grid[DIFF==0].sum(),grid[DIFF<0].sum()])
    obs=0 if d>0 else 1 if d==0 else 2
    return {"ev_side":ev_side,"neutral_side":neutral_side,
       "ev_choice":scores[ev_side],"neutral_choice":scores[neutral_side],
       "one_ll":-math.log(max(float(prob[obs]),1e-12))}

allrows=collections.defaultdict(list)
for q in RAW:
    if int(q["league_id"])%4==SHARD:allrows[q["league_id"]].append(q)
out=json.loads(OUT.read_text()) if OUT.exists() else {"method":"2023-26 genuinely SHA-verified historic Crown open/close prices, retrospective event-time models (no actual then-received quote), Poisson BP annual, Dixon-Coles annual and online Poisson EKF (hypothetical kickoff+3h result visibility), one research simulated side per event with no EV threshold, not placed orders.","leagues":[],"errors":[]}
done={r["league"] for r in out["leagues"]+out["errors"]}
private=[]
for lid,quotes in sorted(allrows.items(),key=lambda kv:int(kv[0])):
    if lid in done:continue
    try:
        history=read(lid)
        prices=sorted((q for q in quotes if q.get("raw_verification")=="ok"),key=lambda q:(q["quote_source_utc"],q["fid"],q["kind"]))
        if not prices:continue
        init=[r for r in history if r[0].year<2023 and r[0]+DELAY<utc(prices[0]["quote_source_utc"])]
        if not init:
            init=[r for r in history if r[0]+DELAY<utc(prices[0]["quote_source_utc"])]
        home_init=sum(r[3] for r in init)/len(init) if init else 0.0
        away_init=sum(r[4] for r in init)/len(init) if init else 0.0
        if home_init>0 and away_init>0:
            engine=DynamicPoissonEKF(home_goal_rate=home_init,away_goal_rate=away_init)
        else:
            # Explicit research-only generic prior, no future scores used.
            engine=DynamicPoissonEKF()
        annual={}
        byyear=collections.defaultdict(lambda:collections.Counter())
        valid=[];skip=collections.Counter();counter=0;projection=0
        for q in prices:
            time=utc(q["quote_source_utc"])
            while counter<len(history) and history[counter][0]+DELAY<=time:
                game=history[counter];engine.update(game[1],game[2],game[3],game[4],game[0]+DELAY)
                counter+=1
            year=int(q["year"])
            # Opening prices may precede the fixture calendar year; never fit on scores
            # that were not even hypothetically visible by the quote source time.
            fit_year=min(year,time.year)
            if fit_year not in annual:
                cut=dt.datetime(fit_year,1,1,tzinfo=dt.timezone.utc)
                training=[r for r in history if r[0]+DELAY<=cut]
                if not training:
                    annual[fit_year]=(None,None)
                    skip["no_past_year_training"]+=1
                else:
                    try:
                        annual[fit_year]=(fit(BivariatePoissonGoalModel,training),fit(DixonColesGoalModel,training))
                    except Exception as exc:
                        annual[fit_year]=(None,None)
                        skip["annual_fit_failed_"+type(exc).__name__]+=1
            h,a=q["home_id"],q["away_id"]
            m_bp,m_dc=annual[fit_year]
            if not m_bp or not m_dc:
                skip["no_annual_fit"]+=1;continue
            if h not in m_bp.teams or a not in m_bp.teams or h not in m_dc.teams or a not in m_dc.teams:
                skip["unseen_annual_team"]+=1;continue
            gh,ga=int(q["home_goals"]),int(q["away_goals"])
            gridbp=np.asarray(m_bp.predict(h,a).grid,dtype=float)
            griddc,proj=dcgrid(m_dc,h,a)
            projection+=int(proj)
            griddyn,_=engine.predict(h,a,time)
            grids={"annual_bp":gridbp,"annual_dc":griddc,"dynamic_ekf":griddyn}
            results={}
            for model,g in grids.items():
                results[model]=score_model(g,q,gh,ga)
            valid.append({"year":q["year"],"kind":q["kind"],"results":results,
                          "lead_minutes":(utc(q["kickoff_utc"])-time).total_seconds()/60,
                          "capture_mode":q["capture_mode"],"prospective":q["prospective"],
                          "quote_received_utc":q["response_received_utc"],
                          "league":lid,"fid":q["fid"],"source_at":q["quote_source_utc"]})
            byyear[q["year"]][q["kind"]]+=1
        out["leagues"].append({"league":lid,"selected":len(prices),"valid":len(valid),"skipped":dict(skip),
                              "rho_projected":projection,"by_year":{y:dict(v) for y,v in byyear.items()}})
        private+=valid
        print("DONE",lid,"quotes",len(prices),"valid",len(valid),"skipped",dict(skip),flush=True)
    except Exception as e:
        out["errors"].append({"league":lid,"error":repr(e),"trace":traceback.format_exc()[-1000:]})
        print("ERROR",lid,repr(e),flush=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False)+"\n")
# save privacy scoped matched results separately without modifying production.
PRIVATE.write_text(json.dumps({"rows":private},ensure_ascii=False)+"\n")
print("COMPLETE leagues",len(out["leagues"]),"errors",len(out["errors"]),"rows",len(private),flush=True)
