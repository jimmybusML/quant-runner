#!/usr/bin/env python3
"""AH five-state settlement via rolling 2-year monotone survival calibration.
Research only: no EV eligibility restriction, one direction every fixture,
Crown historical price only, no user strategy or production changes.
"""
import json, math, sys, hashlib
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson, settle, split_line
SRC=HERE/"xg3_historical_CrownT12_five_league_20261123.jsonl"
rows=[json.loads(s) for s in SRC.open() if s.strip()]
rows=[r for r in rows if r["market"]=="AH"]
assert len(rows)==len({r["fid"] for r in rows})

def cdf(lh,la):
    ph=poisson(lh);pa=poisson(la)
    diff=defaultdict(float)
    for a,p in enumerate(ph):
        for b,q in enumerate(pa):diff[a-b]+=p*q
    return {t:sum(p for x,p in diff.items() if x>t) for t in range(-23,24)}

def line_thresholds(line):
    thresholds=set()
    for h,w in split_line(line):
        t=math.floor(-h)
        thresholds.add(t)
        if abs(h-round(h))<1e-10:thresholds.add(t-1)
    return sorted(thresholds)

def contract_ev(line,odds,P):
    ans={}
    for side in ("home","away"):
        val=0.0
        for leg,w in split_line(line):
            t=math.floor(-leg)
            home_win=P[t]
            home_loss=1.0-(P[t-1] if abs(leg-round(leg))<1e-10 else home_win)
            win,loss=(home_win,home_loss) if side=="home" else (home_loss,home_win)
            val+=w*(win*(odds[side]-1)-loss)
        ans[side]=val
    return ans

def fit(train,league=None):
    pairs=[]
    for r,P,ts in train:
        if league is not None and r["league"]!=league:continue
        score=list(map(int,r["score"].split("-")))
        dif=score[0]-score[1]
        pairs.extend((P[t],float(dif>t)) for t in ts)
    if not pairs:return None,0
    pairs.sort()
    blocks=[]
    for p,y in pairs:
        blocks.append([p,p,1,y])
        while len(blocks)>1 and blocks[-2][3]/blocks[-2][2]>blocks[-1][3]/blocks[-1][2]:
            b=blocks.pop();a=blocks[-1];a[1]=b[1];a[2]+=b[2];a[3]+=b[3]
    return [(b[1],b[3]/b[2]) for b in blocks],len(pairs)

def calibrate(model,p):
    if model is None:return p
    lo,hi=0,len(model)
    while lo<hi:
        m=(lo+hi)//2
        if model[m][0]<p:lo=m+1
        else:hi=m
    return model[min(lo,len(model)-1)][1]

by_year=defaultdict(list)
for r in rows:
    P=cdf(r["method"]["xG3"]["lambda_home"],r["method"]["xG3"]["lambda_away"])
    by_year[r["year"]].append((r,P,line_thresholds(r["quote_line"])))

ledger=[]
fit_info={}
for year in sorted(by_year):
    if year<2021:continue
    train=by_year.get(year-2,[])+by_year.get(year-1,[])
    global_fit,n=fit(train)
    league_fit={lg:fit(train,lg) for lg in {r["league"] for r,P,ts in train}}
    fit_info[str(year)]={"training":[year-2,year-1],"global_events":n,
                          "league_events":{lg:x[1] for lg,x in league_fit.items()}}
    for r,P,ts in by_year[year]:
        diff=int(r["score"].split("-")[0])-int(r["score"].split("-")[1])
        obs={t:float(diff>t) for t in ts}
        entry={"fid":r["fid"],"date":r["date"],"year":year,
               "league":r["league"],"line":r["quote_line"],"odds":r["odds"],
               "score":r["score"],"model":{}}
        for label,m in (("raw",None),("global_two_year",global_fit),
                        ("league_two_year",league_fit.get(r["league"],(None,0))[0])):
            q={t:calibrate(m,P[t]) for t in ts}
            assert all(q[a]>=q[b]-1e-10 for a,b in zip(ts,ts[1:])),(r["fid"],q)
            odds_ev=contract_ev(r["quote_line"],r["odds"],q)
            side=max(("home","away"),key=lambda s:odds_ev[s])
            u=settle("AH",r["quote_line"],r["odds"][side],side,r["score"])
            entry["model"][label]={"side":side,"realized_U":u,
                 "expected_U":odds_ev[side],"brier":sum((q[t]-obs[t])**2 for t in ts)/len(ts),
                 "survival_probs":{str(t):q[t] for t in ts},
                 "five_state_winning_leg_ev":odds_ev}
        if abs(entry["model"]["raw"]["realized_U"]-r["method"]["xG3"]["net_U"])>1e-8:
            ev=contract_ev(r["quote_line"],r["odds"],P)
            if abs(ev["home"]-ev["away"])>1e-7:
                raise RuntimeError(("raw reconstruction mismatch",r["fid"],ev))
        ledger.append(entry)

def agg(items):
    out={"n":len(items)}
    for name in ("raw","global_two_year","league_two_year"):
        n=len(items);u=sum(r["model"][name]["realized_U"] for r in items)
        out[name]={"net_U":round(u,5),"ROI_pct":round(100*u/n,5) if n else None,
             "brier":round(sum(r["model"][name]["brier"] for r in items)/n,7) if n else None,
             "changed_direction_vs_raw":sum(r["model"][name]["side"]!=r["model"]["raw"]["side"] for r in items)}
    return out

report={"study":"AH five-state CDF calibration using xG3 and prior 2 seasons",
  "base_source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
  "method":"calibrate elementary P(home goal difference > line-relevant integer) with isotonic PAV; apply same monotone function to both legs, preserve pushes and impossible states",
  "price_source":"Crown historical T12 source-event quotes retrieved post-match; NOT actually received tradable quotes",
  "calibration_training":fit_info,
  "overall":agg(ledger),
  "by_year":{str(y):agg([r for r in ledger if r["year"]==y]) for y in sorted({r["year"] for r in ledger})},
  "by_league":{lg:agg([r for r in ledger if r["league"]==lg]) for lg in sorted({r["league"] for r in ledger})},
  "limitations":["All known historical outcomes; historical experiment not a new blinded future test",
    "No positive-EV or minimum-count eligibility, every same fixture has a direction",
    "Historic crosswalk uses retrospective score for entity mapping, not prospective identity",
    "Isotonic PAV state calibration is a study hypothesis not a user-approved rule",
    "No live orders or formal Telegram orders or production ledger changes"]}
L=HERE/"xg3_ah_cdf_calibration_20261123.jsonl"
R=HERE/"xg3_ah_cdf_calibration_20261123.json"
with L.open("w") as f:
    for x in ledger:f.write(json.dumps(x,ensure_ascii=False)+"\n")
R.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"count":len(ledger),"overall":report["overall"],
  "by_year":report["by_year"],"by_league":report["by_league"]},ensure_ascii=False))
