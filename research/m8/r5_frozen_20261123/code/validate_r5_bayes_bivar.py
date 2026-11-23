#!/usr/bin/env python3
"""Independent R5 audit. No import from forecasting, settlement, or
Bayesian scripts. Recalculate quarter handicap payouts from stored
ledger and original R4 Crown prices; quote SHA for received 2026 cohort.
"""
import json,math,hashlib,datetime
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
HIST=HERE/"r5_bayes_bivar_CrownT12_20261123.jsonl"
HIST_SRC=HERE/"r4_season_scope_CrownT12_20261123.jsonl"
RECEIPTS=HERE/"r5_bayes_bivar_actual_receipt_20261123.jsonl"
RECEIPTS_SRC=HERE/"attack_defense_2026_actual_receipt_20261123.jsonl"
OUT=HERE/"r5_independent_cash_cross_source_validation_20261123.json"

def cash(market,line,decimal_odds,side,final_score):
    h,a=map(int,final_score.split("-"))
    nearest=int(round(4*line))
    if abs(line-nearest/4)>1e-9:raise ValueError(line)
    if nearest%2==0:legs=[(line,1.0)]
    else:legs=[(math.floor(2*line)/2.,.5),(math.ceil(2*line)/2.,.5)]
    total=0.
    for leg,weight in legs:
        if market=="AH":
            d=h-a+leg if side=="home" else a-h-leg
        else:
            d=h+a-leg if side=="over" else leg-h-a
        unit=(decimal_odds-1) if d>1e-9 else (-1.0 if d<-1e-9 else 0.0)
        total+=weight*unit
    return total
err=Counter();checks=Counter()
historical={(r["fid"],r["market"]):r for r in map(json.loads,HIST_SRC.open())}
for r in map(json.loads,HIST.open()):
    k=(r["fid"],r["market"]);old=historical.get(k)
    if old is None:err["historical_missing_source"]+=1;continue
    if old["score"]!=r["score"] or old["quote_line"]!=r["line"] or old["odds"]!=r["odds"]:
        err["historical_source_quote_mismatch"]+=1
    oldbase=old["models"]["ratio_decay_same_season"]
    for name,m in r["models"].items():
        recash=cash(r["market"],r["line"],r["odds"][m["side"]],m["side"],r["score"])
        checks["historical_cash"]+=1
        if abs(recash-m["net_U"])>1e-9:err["historical_cash"]+=1
        if m["common_shock_c"] < 0 or m["common_shock_c"]-min(m["lambda_home"],m["lambda_away"])>1e-10:
            err["invalid_shared_component"]+=1
        if name=="independent_poisson":
            checks["historical_base_R4_cash"]+=1
            if abs(m["net_U"]-oldbase["realized_U"])>1e-9 or m["side"]!=oldbase["side"]:
                err["historical_base_cash_side"]+=1
            if abs(m["lambda_home"]-oldbase["lambda_home"])>1e-9 or abs(m["lambda_away"]-oldbase["lambda_away"])>1e-9:
                err["historical_base_lambda"]+=1

old_receipt={(r["fid"],r["market"]):r for r in map(json.loads,RECEIPTS_SRC.open())}
actual_ids=set()
for r in map(json.loads,RECEIPTS.open()):
    key=(r["fid"],r["market"])
    if key in actual_ids:err["receipt_duplicate"]+=1
    actual_ids.add(key)
    src=old_receipt.get(key)
    if src is None:err["receipt_missing_source"]+=1;continue
    if (r["source_Crown_raw_sha256"]!=src["raw_sha256"] or r["line"]!=src["line"] or
        r["odds"]!=src["odds"] or r["score"]!=src["score"]):
        err["receipt_quote_source_mismatch"]+=1
    t=lambda x:datetime.datetime.fromisoformat(x.replace("Z","+00:00"))
    if not (t(r["source_xG_maturity_latest_utc"])<t(r["Crown_quote_received_utc"])<t(r["kickoff_utc"])):
        err["receipt_feature_time_leakage"]+=1
    for name,m in r["models"].items():
        recash=cash(r["market"],r["line"],r["odds"][m["side"]],m["side"],r["score"])
        checks["receipt_cash"]+=1
        if abs(recash-m["net_U"])>1e-9:err["receipt_cash"]+=1
        if m["c"]<0 or m["c"]-min(m["lambda_home"],m["lambda_away"])>1e-10:
            err["receipt_common_component"]+=1
        if name=="old_arithmetic3_independent":
            checks["receipt_R3_old_baseline"]+=1
            old=src["models"]["attack_defense_arithmetic3"]
            if abs(old["realized_U"]-m["net_U"])>1e-9 or old["side"]!=m["side"]:
                err["receipt_baseline_mismatch"]+=1

expected_counts={"historical_cash":19816*8,"historical_base_R4_cash":19816,
                 "receipt_cash":276*9,"receipt_R3_old_baseline":276}
for k,v in expected_counts.items():
    if checks[k]!=v:err["wrong_"+k+"_count"]+=1
report={"status":"PASS" if not err else "FAIL",
        "research":"R5_CROWN_HISTORICAL_AND_ACTUAL_RECEIPT_INDEPENDENT_SETTLEMENT_AUDIT",
        "checks":dict(checks),"errors":dict(err),
        "receipt_unique_fixture_market_count":len(actual_ids),
        "receipt_unique_fixture_count":len({k[0] for k in actual_ids}),
        "sha256":{"historical":hashlib.sha256(HIST.read_bytes()).hexdigest(),
                  "received_2026":hashlib.sha256(RECEIPTS.read_bytes()).hexdigest()},
        "scope":"Domestic club leagues only; actual historical received quotes not formal TG trades"}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="sha256"},ensure_ascii=False))
assert report["status"]=="PASS"
