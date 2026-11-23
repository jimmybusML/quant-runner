#!/usr/bin/env python3
"""Independently audit all AH/OU raw payouts and rolling calibrated
probability mass and chosen-side EV for the independent attack/defense study.
Does not import original model / payout helper.
"""
import json,math
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
RAW=HERE/"attack_defense_CrownT12_20261123.jsonl"
CAL=HERE/"attack_defense_rolling_contract_calibration_20261123.jsonl"
OUT=HERE/"attack_defense_independent_settlement_audit_20261123.json"
errors=Counter()
def legs(v):
    n=round(v*4)
    if abs(n/4-v)>1e-9:raise ValueError(v)
    return [(v,1.)] if n%2==0 else [(math.floor(v*2)/2,.5),(math.ceil(v*2)/2,.5)]
def cash(market,hg,ag,line,odds,side):
    profit=0.
    for leg,weight in legs(line):
        if market=="AH":d=hg-ag+leg if side=="home" else ag-hg-leg
        else:d=hg+ag-leg if side=="over" else leg-hg-ag
        profit+=weight*((odds-1) if d>1e-9 else (-1. if d<-1e-9 else 0.))
    return profit

raw_count=0
for line in RAW.open():
    r=json.loads(line);raw_count+=1
    hg,ag=map(int,r["score"].split("-"))
    for name,data in r["models"].items():
        side=data["side"]
        pnl=cash(r["market"],hg,ag,r["quote_line"],r["odds"][side],side)
        if abs(pnl-data["net_U"])>1e-9:errors["raw_pnl"]+=1
cal_count=0
max_ev_error=0.
prob_min=1.
for line in CAL.open():
    r=json.loads(line);cal_count+=1
    hg,ag=map(int,r["score"].split("-"))
    market=r["market"]
    for name,data in r["methods"].items():
        side=data["side"];odds=r["odds"][side]
        pnl=cash(market,hg,ag,r["quote_line"],odds,side)
        if abs(pnl-data["realized_U"])>1e-9:errors["cal_pnl"]+=1
        sur={int(k):v for k,v in data["survival_prob_by_threshold"].items()}
        t=sorted(sur)
        pieces=[(t[0]-2 if market=="AH" else max(0,t[0]),1-sur[t[0]])]
        pieces.extend((t[i]+1,sur[t[i]]-sur[t[i+1]]) for i in range(len(t)-1))
        pieces.append((t[-1]+2,sur[t[-1]]))
        if any(z<-1e-10 for _,z in pieces):errors["negative_mass"]+=1
        if abs(sum(z for _,z in pieces)-1)>1e-9:errors["mass_total"]+=1
        prob_min=min(prob_min,min(z for _,z in pieces))
        if market=="AH":
            expected=sum(z*cash(market,d,0,r["quote_line"],odds,side) for d,z in pieces)
        else:
            expected=sum(z*cash(market,d,0,r["quote_line"],odds,side) for d,z in pieces)
        err=abs(expected-data["expected_U"])
        max_ev_error=max(max_ev_error,err)
        if err>1e-7:errors["cal_expected"]+=1
report={"status":"PASS" if not errors and raw_count==19816 and cal_count==42438 else "FAIL",
    "raw_market_rows":raw_count,"raw_variant_payout_checks":raw_count*6,
    "rolling_calibration_rows":cal_count,"calibrated_payout_expected_checks":cal_count*3,
    "errors":dict(errors),
    "max_probability_expval_difference":max_ev_error,
    "minimum_probability_mass":prob_min,
    "scope":"research only, offline historical Crown source-event T12 quotation, not actual pregame receipt"}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
assert report["status"]=="PASS"
