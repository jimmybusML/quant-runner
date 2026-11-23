#!/usr/bin/env python3
"""Independent reconstructed Crown receipt, timing, cash, and baseline comparison
for 2026/27 football-data xG attack/defense receipt research. Research only.
"""
import json,math,hashlib
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE.parent/"m7/m7_actual_receipt_1596_xg_profit_replay_20261116.jsonl"
OLD=HERE/"independent_xg_3venue_receipt_20261123.jsonl"
NEW=HERE/"attack_defense_2026_actual_receipt_20261123.jsonl"
OUT=HERE/"attack_defense_2026_actual_receipt_validation_20261123.json"
def parse(s):
    from datetime import datetime
    return datetime.fromisoformat(s.replace("Z","+00:00"))
def profit(market,line,odds,side,score):
    home,away=map(int,score.split("-"))
    q=round(line*4)
    if abs(line-q/4)>1e-8:raise RuntimeError(line)
    split=[(line,1.)] if q%2==0 else [(math.floor(line*2)/2,.5),(math.ceil(line*2)/2,.5)]
    value=0.
    for h,w in split:
        d=home-away+h if side=="home" else away-home-h if side=="away" else home+away-h if side=="over" else h-home-away
        value+=w*((odds-1.) if d>1e-9 else (-1. if d<-1e-9 else 0.))
    return value

src={(r["fixture_id"],r["market"]):r for r in map(json.loads,SRC.open())}
old={(r["fixture_id"],r["market"]):r for r in map(json.loads,OLD.open())}
errors=Counter();counts=Counter();fidset=set()
for r in map(json.loads,NEW.open()):
    key=(r["fid"],r["market"])
    if key in fidset:errors["duplicate"]+=1
    fidset.add(key)
    base=src.get(key)
    if not base:errors["missing_old_source"]+=1;continue
    m=old.get(key)
    if not m:errors["missing_old_independent"]+=1;continue
    if base["raw_sha256"]!=r["raw_sha256"]:errors["receipt_sha"]+=1
    if base["line"]!=r["line"] or base["odds"]!=r["odds"]:errors["receipt_quote"]+=1
    if base["score"]!=r["score"]:errors["result_mismatch"]+=1
    if base["quote_received_utc"]!=r["receipt_utc"]:errors["receipt_time"]+=1
    if parse(r["receipt_utc"])>=parse(r["kickoff_utc"]):errors["late_receipt"]+=1
    if parse(r["latest_history_maturity_utc"])>=parse(r["receipt_utc"]):errors["leaked_source_event"]+=1
    for name in ("independent_xg3","attack_defense_arithmetic3"):
        model=r["models"][name]
        cash=profit(r["market"],r["line"],r["odds"][model["side"]],model["side"],r["score"])
        counts["independent_cash_checks"]+=1
        if abs(cash-model["realized_U"])>1e-9:errors["bad_cash"]+=1
    indep=r["models"]["independent_xg3"]
    if indep["side"]!=m["independent_xg3_direction"]:errors["independent_baseline_side"]+=1
    if abs(indep["realized_U"]-m["independent_xg3_realized_U"])>1e-9:errors["independent_baseline_pnl"]+=1
    counts[r["market"]]+=1
result={"status":"PASS" if not errors and counts["AH"]==138 and counts["OU"]==138 else "FAIL",
    "unique_fixture_markets":len(fidset),
    "distinct_fixtures":len({k[0] for k in fidset}),
    "checks":dict(counts),"errors":dict(errors),
    "source_receipt_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
    "source_independent_baseline_sha256":hashlib.sha256(OLD.read_bytes()).hexdigest(),
    "research_only":True}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(result,ensure_ascii=False))
assert result["status"]=="PASS"
