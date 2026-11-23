#!/usr/bin/env python3
"""Independent quarter-line realized cash/identity audit for R4:
- 9,908 same-fixture later-club cases: seven independent models x AH/OU
- 2,018 early-club cases: two cross-season models x AH/OU
- compare same xG3 & cross ratio against earlier R3 same market ledger
- early prices compare against original Crown historical source payout columns.
This validator does not call research settlement, EV or Poisson helpers.
"""
import json,math,hashlib
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
LATE=HERE/"r4_season_scope_CrownT12_20261123.jsonl"
EARLY=HERE/"r4_earlyseason_club_CrownT12_20261123.jsonl"
R3=HERE/"attack_defense_CrownT12_20261123.jsonl"
PRICES=HERE.parent/"m8_early_joint_market_inventory_20261115.jsonl"
OUT=HERE/"r4_independent_cash_identity_audit_20261123.json"

def independent_pnl(market,line,odds,side,score):
    hg,ag=map(int,score.split("-"))
    n=round(line*4)
    assert abs(line-n/4)<1e-9,(line,n)
    legs=[(line,1.)] if n%2==0 else [
        (math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]
    ret=0.
    for part,weight in legs:
        x=hg-ag+part if side=="home" else ag-hg-part if side=="away" else hg+ag-part if side=="over" else part-hg-ag
        ret+=weight*((odds-1) if x>1e-9 else -1. if x< -1e-9 else 0.)
    return ret

prior={(r["fid"],r["market"]):r for r in map(json.loads,R3.open())}
rawsource={}
for s in PRICES.open():
    r=json.loads(s)
    if r.get("T")==12:rawsource[r["fid"]]=r
errors=Counter();checks=Counter();seenlate=set();seenearly=set()
for s in LATE.open():
    r=json.loads(s);key=(r["fid"],r["market"])
    if key in seenlate:errors["late_duplicate_key"]+=1
    seenlate.add(key);old=prior.get(key)
    if old is None:errors["late_missing_prior_R3"]+=1
    else:
        if r["score"]!=old["score"] or r["league"]!=old["league"]:
            errors["R3_identity"]+=1
    for name,obj in r["models"].items():
        checks["late_cash"]+=1
        net=independent_pnl(r["market"],r["quote_line"],r["odds"][obj["side"]],obj["side"],r["score"])
        if abs(net-obj["realized_U"])>1e-9:errors["late_cash"]+=1
        if old:
            oldname="xg3" if name=="xg3_same_season" else "attack_defense_dynamic365" if name=="ratio_decay_cross_season" else None
            if oldname:
                prior_obj=old["models"][oldname]
                checks["late_R3_reconciliation"]+=1
                if abs(prior_obj["net_U"]-obj["realized_U"])>1e-9 or old["market"]!=r["market"]:
                    errors["late_R3_cash"]+=1
                if abs(obj["lambda_home"]-prior_obj["lambda_home"])>1e-9 or abs(obj["lambda_away"]-prior_obj["lambda_away"])>1e-9:
                    errors["late_R3_lambda"]+=1
for s in EARLY.open():
    r=json.loads(s);fid=r["fid"]
    if fid in seenearly:errors["early_duplicate_fid"]+=1
    seenearly.add(fid)
    if not r["early"]:errors["not_early"]+=1
    if fid in {k[0] for k in seenlate}:errors["early_overlap_late"]+=1
    p=rawsource.get(fid)
    if p is None:errors["early_missing_Crown_original"]+=1;continue
    if p["date"]!=r["date"] or f"{p['hg']}-{p['ag']}"!=r["score"]:errors["early_identity"]+=1
    for key,obj in r["models"].items():
        market=key.split("_")[-1]
        side=obj["side"]
        oldodds=(p["ah"] if side=="home" else p["aa"]) if market=="AH" else (p["oo"] if side=="over" else p["ou"])
        oldline=p["al"] if market=="AH" else p["ol"]
        if abs(obj["quote_line"]-oldline)>1e-9 or abs(obj["odds"][side]-oldodds)>1e-9:
            errors["early_Crown_quote"]+=1
        cash=independent_pnl(market,oldline,oldodds,side,r["score"])
        checks["early_cash"]+=1
        if abs(cash-obj["net_U"])>1e-9:errors["early_cash"]+=1
        stored_key={"home":"home_U","away":"away_U","over":"over_U","under":"under_U"}[side]
        checks["early_saved_raw_Crown_cash"]+=1
        if abs(cash-p[stored_key])>1e-8:errors["early_Crown_saved_cash"]+=1
result={"status":"PASS" if not errors and len(seenlate)==19816 and len(seenearly)==2018 else "FAIL",
    "late_market_rows":len(seenlate),"early_unique_games":len(seenearly),
    "checks":dict(checks),"errors":dict(errors),
    "source_sha256":{"late":hashlib.sha256(LATE.read_bytes()).hexdigest(),
        "early":hashlib.sha256(EARLY.read_bytes()).hexdigest(),
        "Crown":hashlib.sha256(PRICES.read_bytes()).hexdigest()},
    "scope":"Five domestic club leagues; historical Crown source event; research only"}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="source_sha256"},ensure_ascii=False))
assert result["status"]=="PASS"
