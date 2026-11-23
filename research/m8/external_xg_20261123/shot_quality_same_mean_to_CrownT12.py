#!/usr/bin/env python3
"""AH/OU Crown historical T12 same-fixture shot-quality PB mixture vs xG3.
Read-only research, neither M8 approved set nor formal models changed.
"""
import json,math,hashlib,sys
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import settle,split_line,expected,poisson
CROWN=HERE/"xg3_historical_CrownT12_five_league_20261123.jsonl"
SHOT=HERE/"shot_quality_same_mean_20261123.jsonl"
OUT=HERE/"shot_quality_same_mean_CrownT12_20261123.json"
LEDGER=HERE/"shot_quality_same_mean_CrownT12_20261123.jsonl"
src={}
for line in SHOT.open():
    r=json.loads(line)
    src[(r["league"],r["fixture_id"])]=r
rows=[json.loads(s) for s in CROWN.open() if s.strip()]
missing=defaultdict(int);results=[]

def calculate(market,line,odds,ph,pa):
    total=defaultdict(float)
    for i,p in enumerate(ph):
        for j,q in enumerate(pa):
            key=(i-j) if market=="AH" else (i+j)
            total[key]+=p*q
    two={}
    for side,odd in odds.items():
        val=0.0
        for x,prob in total.items():
            u=0.0
            for part,weight in split_line(line):
                if market=="AH":
                    margin=(x+part) if side=="home" else (-x-part)
                else:
                    margin=(x-part) if side=="over" else (part-x)
                payoff=(odd-1.) if margin>1e-9 else (-1. if margin < -1e-9 else 0.)
                u+=weight*payoff
            val+=prob*u
        two[side]=val
    return two

for r in rows:
    shot=src.get((r["league"],r["understat_fixture_id"]))
    if shot is None:
        missing[r["market"]]+=1
        continue
    assert shot["score"]==r["score"] and shot["date"]==r["date"]
    market=r["market"];line=r["quote_line"];odds=r["odds"]
    p_h,p_a=shot["home_goal_pmf"],shot["away_goal_pmf"]
    vals=calculate(market,line,odds,p_h,p_a)
    side=max(odds,key=lambda s:vals[s])
    outcome=settle(market,line,odds[side],side,r["score"])
    orig=r["method"]["xG3"]
    new={"fid":r["fid"],"understat_fixture_id":r["understat_fixture_id"],
         "market":market,"year":r["year"],"league":r["league"],
         "date":r["date"],"line":line,"odds":odds,"score":r["score"],
         "status":"historical_Crown_event_source_not_actual_receipt",
         "model":{"shot_quality_mixture":{"side":side,"expected_U":vals[side],
                   "expected_both_sides":vals,"realized_U":outcome},
                  "xg3_poisson":orig,
                  "goals3_poisson":r["method"]["goals3"]},
         "source_shot_features":{"home_equal_mean":shot["mean_home_goals"],"away_equal_mean":shot["mean_away_goals"]}}
    assert abs(settle(market,line,odds[orig["direction"]],orig["direction"],r["score"])-orig["net_U"])<1e-8
    results.append(new)

def agg(sample):
    n=len(sample)
    outcome={"n":n}
    for name in ("shot_quality_mixture","xg3_poisson","goals3_poisson"):
        u=sum(r["model"][name]["realized_U"] if name=="shot_quality_mixture"
              else r["model"][name]["net_U"] for r in sample)
        outcome[name]={"net_U":round(u,5),"ROI_pct":round(100*u/n,5) if n else None}
    outcome["shot_minus_xg_U"]=round(outcome["shot_quality_mixture"]["net_U"]-outcome["xg3_poisson"]["net_U"],5)
    outcome["shot_vs_xg_direction_changes"]=sum(r["model"]["shot_quality_mixture"]["side"]!=r["model"]["xg3_poisson"]["direction"] for r in sample)
    return outcome

report={"research":"SHOT_LEVEL_BERNOULLI_MIXTURE_SAME_PUBLISHED_XG_MEAN_CROWN_T12",
 "date":"2026-11-23",
 "Crown_source_sha256":hashlib.sha256(CROWN.read_bytes()).hexdigest(),
 "shot_predictions_sha256":hashlib.sha256(SHOT.read_bytes()).hexdigest(),
 "missing":dict(missing),
 "overall":{market:agg([r for r in results if r["market"]==market]) for market in ("AH","OU")},
 "by_year":{str(y):{m:agg([r for r in results if r["year"]==y and r["market"]==m]) for m in ("AH","OU")} for y in sorted({r["year"] for r in results})},
 "by_league":{lg:{m:agg([r for r in results if r["league"]==lg and r["market"]==m]) for m in ("AH","OU")} for lg in sorted({r["league"] for r in results})},
 "limitations":["Crown T12 quote is historical source event retrieved after match, not live receipt or fill",
    "Crosswalk identity built using final score uniquely for team mapping, not standalone pre-game identity",
    "Shot provider historical publication dates unavailable; shape estimated strictly using prior match dates",
    "No EV positive requirement, volume gate, strategy addition or merged portfolio",
    "No new blind out-of-sample test; previously explored historical periods"]}
with LEDGER.open("w") as f:
    for r in results:f.write(json.dumps(r,ensure_ascii=False)+"\n")
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(results),"overall":report["overall"],
                   "by_year":report["by_year"],"missing":report["missing"]},ensure_ascii=False))
