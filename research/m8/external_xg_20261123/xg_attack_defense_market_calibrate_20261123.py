#!/usr/bin/env python3
"""Chronological AH/OU event-survival isotonic calibration.
Three independent xG attack/defense lines; raw/global/league by prior TWO seasons.
No ROI tuning, no EV gating, every fixture-market receives a direction.
Market prices are historical Crown T12 source events, not live receipts.
"""
import json,math,hashlib,sys
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson,settle,split_line
SOURCE=HERE/"attack_defense_CrownT12_20261123.jsonl"
SUMMARY=HERE/"attack_defense_rolling_contract_calibration_20261123.json"
LEDGER=HERE/"attack_defense_rolling_contract_calibration_20261123.jsonl"
FOCUS=("xg3","attack_defense_arithmetic3","attack_defense_dynamic365")
CAL=("raw","global_two_season","league_two_season")
src=[json.loads(s) for s in SOURCE.open() if s.strip()]
assert len(src)==19816
def surv(lh,la,market,ts):
    ph=poisson(lh);pa=poisson(la)
    dist=defaultdict(float)
    for i,p in enumerate(ph):
        for j,q in enumerate(pa):
            d=i-j if market=="AH" else i+j
            dist[d]+=p*q
    return {t:sum(mass for x,mass in dist.items() if x>t) for t in ts}

def pts(market,line):
    s=set()
    for leg,w in split_line(line):
        t=math.floor(-leg) if market=="AH" else math.floor(leg)
        s.add(t)
        if abs(leg-round(leg))<1e-10:s.add(t-1)
    return sorted(s)

def ev(market,line,odds,P):
    sides=("home","away") if market=="AH" else ("over","under")
    result={}
    for side in sides:
        val=0.
        for leg,w in split_line(line):
            t=math.floor(-leg) if market=="AH" else math.floor(leg)
            pos=P[t]
            neg=1.-(P[t-1] if abs(leg-round(leg))<1e-10 else pos)
            # P(diff>t) is HOME winning event; P(total>t) is OVER winning event.
            wp,lp=(pos,neg) if side in ("home","over") else (neg,pos)
            val+=w*(wp*(odds[side]-1)-lp)
        result[side]=val
    return result

def pav(pairs):
    pairs.sort()
    groups=[]
    for x,y in pairs:
        groups.append([x,x,1,float(y)])
        while len(groups)>1 and groups[-2][3]/groups[-2][2]>groups[-1][3]/groups[-1][2]:
            b=groups.pop();a=groups[-1]
            a[1]=b[1];a[2]+=b[2];a[3]+=b[3]
    return [(z[1],z[3]/z[2]) for z in groups] if groups else None

def apply(model,p):
    if model is None:return p
    lo,hi=0,len(model)
    while lo<hi:
        k=(lo+hi)//2
        if model[k][0]<p:lo=k+1
        else:hi=k
    return model[min(lo,len(model)-1)][1]

bygroup=defaultdict(list)
checks=Counter()
for r in src:
    market=r["market"]
    line=r["quote_line"]
    thresholds=pts(market,line)
    obsval=(lambda hg,ag: hg-ag if market=="AH" else hg+ag)(*map(int,r["score"].split("-")))
    for name in FOCUS:
        feature=r["models"][name]
        P=surv(feature["lambda_home"],feature["lambda_away"],market,thresholds)
        raw=ev(market,line,r["odds"],P)
        sides=("home","away") if market=="AH" else ("over","under")
        raw_side=max(sides,key=lambda x:raw[x])
        if raw_side!=feature["side"] and abs(raw[sides[0]]-raw[sides[1]])>1e-7:
            checks["raw_direction_mismatch"]+=1
        bygroup[(name,market,r["season"])].append((r,P,thresholds,obsval))
print("Input prepared",len(src),"keys",len(bygroup),"checks",dict(checks),flush=True)

def fit(rows,league=None):
    pairs=[]
    for r,P,t,obs in rows:
        if league is not None and r["league"]!=league:continue
        pairs.extend((P[i],obs>i) for i in t)
    return pav(pairs),len(pairs)

output=[];train_info={}
for name in FOCUS:
    for market in ("AH","OU"):
        for season in range(2021,2026):
            training=bygroup.get((name,market,season-2),[])+bygroup.get((name,market,season-1),[])
            global_fit,global_size=fit(training)
            league_fit={lg:fit(training,lg) for lg in {r["league"] for r,P,t,obs in training}}
            train_info[f"{name}:{market}:{season}"]={"train_years":[season-2,season-1],
                    "trained_event_observations":global_size,
                    "league_counts":{lg:q for lg,(_,q) in league_fit.items()}}
            for r,P,ts,obs in bygroup.get((name,market,season),[]):
                venue_fit=league_fit.get(r["league"],(None,0))[0]
                data={"fid":r["fid"],"market":market,"league":r["league"],
                      "season":season,"model_name":name,"quote_line":r["quote_line"],
                      "odds":r["odds"],"score":r["score"],"methods":{}}
                sides=("home","away") if market=="AH" else ("over","under")
                for cal,model in (("raw",None),("global_two_season",global_fit),
                                  ("league_two_season",venue_fit)):
                    q={t:apply(model,P[t]) for t in ts}
                    assert all(q[i]>=q[j]-1e-10 for i,j in zip(ts,ts[1:])),(name,season,r["fid"],q)
                    expect=ev(market,r["quote_line"],r["odds"],q)
                    side=max(sides,key=lambda x:expect[x])
                    profit=settle(market,r["quote_line"],r["odds"][side],side,r["score"])
                    if cal=="raw":
                        if side!=r["models"][name]["side"] and abs(expect[sides[0]]-expect[sides[1]])>1e-7:
                            checks["raw_pnl_direction_mismatch"]+=1
                        if abs(profit-r["models"][name]["net_U"])>1e-8:
                            checks["raw_settlement_mismatch"]+=1
                    data["methods"][cal]={"side":side,"realized_U":profit,"expected_U":expect[side],
                       "binary_brier":sum((q[t]-float(obs>t))**2 for t in ts)/len(ts),
                       "survival_prob_by_threshold":{str(t):q[t] for t in ts}}
                output.append(data)
        print("Completed",name,market,len([r for r in output if r["model_name"]==name and r["market"]==market]),flush=True)

def agg(rows):
    n=len(rows);a={"n":n}
    for cal in CAL:
        pnl=sum(r["methods"][cal]["realized_U"] for r in rows)
        a[cal]={"U":round(pnl,5),"ROI_pct":round(100*pnl/n,5) if n else None,
                "Brier":round(sum(r["methods"][cal]["binary_brier"] for r in rows)/n,7) if n else None,
                "direction_change_vs_raw":sum(r["methods"][cal]["side"]!=r["methods"]["raw"]["side"] for r in rows)}
    return a

report={"research":"AH_AND_OU_ROLLING_CALIBRATION_OF_ATTACK_DEFENSE_XG",
    "input_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "methods":list(FOCUS),"calibration_methods":list(CAL),
    "train_lead":"strictly previous 2 full seasons from historical source-event archive, same market, no ROI target",
    "checks":dict(checks),"train_info":train_info,
    "results":{name:{
        m:{"total":agg([r for r in output if r["model_name"]==name and r["market"]==m]),
            "by_season":{str(yr):agg([r for r in output if r["model_name"]==name and r["market"]==m and r["season"]==yr]) for yr in range(2021,2026)},
            "by_league":{lg:agg([r for r in output if r["model_name"]==name and r["market"]==m and r["league"]==lg])
                         for lg in sorted({r["league"] for r in output})}}
                for m in ("AH","OU")} for name in FOCUS},
    "limitations":["Crown T12 historic quote source events are not actual pregame HTTP receipts",
        "The target source cohort has been previously studied and is not independent blind forward deployment",
        "No calibrated probability based gate/pass or stake rule introduced",
        "Historic team ID crosswalk had retrospective score anchored identity mappings",
        "Historical xG original publication timestamp unavailable; all underlying football xG features from previous game dates only",
        "Data remains independent of formal Telegram order/settlement records"]}
with LEDGER.open("w") as f:
    for r in output:f.write(json.dumps(r,ensure_ascii=False)+"\n")
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(output),"checks":dict(checks),
    "totals":{k:{m:v["total"] for m,v in result.items()} for k,result in report["results"].items()}},ensure_ascii=False))
