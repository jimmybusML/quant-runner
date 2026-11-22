#!/usr/bin/env python3
"""Read-only research: early Crown price discovery, forward-year direction, and realized Asian settlement.

One T-12h snapshot per fixture-market; historical source events were received in 2026.
The market-direction label uses *future* close and must never be used as an input.
There are no research-derived production order thresholds, filters or gates.
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
from research.m3.probabilities import settle_score

SRC = Path("/Users/mac/QuantAsiaDesk/research-work/m7")
ENTRY = SRC / "m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl"
CLOSE = SRC / "m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl"
OUT = HERE / "early_price_discovery_results.json"
PRED = HERE / "holdout_research_predictions.jsonl.gz"


def utc(value):
    d = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if not d.tzinfo:
        raise ValueError("timezone missing")
    return d.astimezone(dt.timezone.utc)


def numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def fair1(o1, o2):
    a, b = 1 / float(o1), 1 / float(o2)
    return a / (a + b)


def get_stats(rows, market, pick):
    pp = [float(r["pnl"][pick(r)]) for r in rows]
    n = len(pp)
    w = sum(x > 1e-9 for x in pp)
    l = sum(x < -1e-9 for x in pp)
    push = n - w - l
    return dict(n=n, win=w, loss=l, push=push, net_U=round(sum(pp), 5),
                roi_pct=round(100 * sum(pp)/n, 4) if n else None)


def sigmoid(a):
    return 1/(1+np.exp(-np.clip(a, -40, 40)))


def fit(X, Y):
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Z = np.column_stack((np.ones(len(X)), (X-mu)/sd))
    # Estimator regularization; not a signal or portfolio gate.
    reg = 0.001
    def fg(b):
        z = Z @ b
        p = sigmoid(z)
        loss = float(np.mean(np.logaddexp(0, z) - Y*z)
                     + reg*np.sum(b[1:]**2))
        grad = Z.T @ (p-Y)/len(Y)
        grad[1:] += 2*reg*b[1:]
        return loss, grad
    opt = minimize(fg, np.zeros(Z.shape[1]), method="L-BFGS-B", jac=True,
                   options={"maxiter":150})
    return (opt.x, mu, sd, bool(opt.success))


def score(b, mu, sd, x):
    return sigmoid(np.column_stack((np.ones(len(x)), (x-mu)/sd)) @ b)


def features(e, market, kickoff, entry_t, p):
    line = float(e["line"])
    hist_line = e.get("line_delta_since_first_quote")
    hist_line = float(hist_line) if numeric(hist_line) else 0
    # A more negative HOME handicap strengthens HOME; higher OU strengthens OVER.
    hist_s1 = (-hist_line if market == "AH" else hist_line)
    dp = e.get("same_line_no_vig_probability_delta_side1")
    dp = float(dp) if numeric(dp) else 0
    lead = (kickoff-entry_t).total_seconds()/3600
    first = e.get("first_available_quote") or {}
    try:
        observed = (entry_t-utc(first.get("time"))).total_seconds()/3600
    except Exception:
        observed = 0
    n_ticks = e.get("window_ticks_available")
    n_ticks = int(n_ticks) if numeric(n_ticks) and n_ticks >= 0 else 0
    month = kickoff.month
    return [10*(p-0.5), line if market == "AH" else line-2.5,
            hist_s1, 10*dp, math.log1p(n_ticks),
            math.log1p(max(0,lead)), math.log1p(max(0,observed)),
            math.sin(2*math.pi*month/12), math.cos(2*math.pi*month/12)]


def main():
    audit = collections.Counter()
    index = {}
    with CLOSE.open() as f:
        for line in f:
            r=json.loads(line)
            if r.get("capture_mode")!="historical" or r.get("prospective_observation") is not False:
                audit["other_capture_class"]+=1
                continue
            index[str(r["fixture_id"])] = r
    audit["close_index_fixtures"] = len(index)
    rows = {"AH":[], "OU":[]}
    example_hashes = []
    with ENTRY.open() as f:
        for line in f:
            e=json.loads(line)
            if e.get("entry_horizon_hours") != 12:
                continue
            market=e["market"]
            if market not in rows:
                audit["other_market"]+=1
                continue
            audit["entry_12h_"+market]+=1
            fid=str(e["fixture_id"])
            c=index.get(fid)
            if not c:
                audit["missing_close_fixture_"+market]+=1
                continue
            if market not in (c.get("markets") or {}):
                audit["missing_close_market_"+market]+=1
                continue
            try:
                kickoff=utc(e["kickoff_utc"])
                quote=utc(e["quote_time_utc"])
                close_m=c["markets"][market]
                close_time=utc(close_m["quote_source_at_utc"])
                if kickoff!=utc(c["kickoff_utc"]):
                    audit["kickoff_mismatch"]+=1; continue
                if not (quote <= kickoff-dt.timedelta(hours=12) and quote < close_time < kickoff):
                    audit["invalid_time_order_"+market]+=1; continue
                line_e=float(e["line"])
                line_c=float(close_m["line"])
                eod=e["odds"]
                cod=close_m["odds"]
                s1,s2=("home","away") if market=="AH" else ("over","under")
                o1,o2=float(eod[s1]),float(eod[s2])
                z1,z2=float(cod[s1]),float(cod[s2])
                if not all(numeric(v) for v in (line_e,line_c,o1,o2,z1,z2)):
                    audit["invalid_numeric"]+=1;continue
                if min(o1,o2,z1,z2)<=1.0:
                    audit["invalid_odds"]+=1;continue
                if (abs(line_e*4-round(line_e*4))>1e-6 or
                    abs(line_c*4-round(line_c*4))>1e-6):
                    audit["invalid_quarter_line"]+=1; continue
                hg,ag=map(int,e["score"].split("-"))
                if e["score"] != c["score"]:
                    audit["score_mismatch"]+=1;continue
                p=fair1(o1,o2)
                pc=fair1(z1,z2)
                delta_line=line_c-line_e
                same_line=abs(delta_line)<1e-8
                if not same_line:
                    signal = -delta_line if market=="AH" else delta_line
                else:
                    signal=pc-p
                direction=1 if signal>1e-9 else (-1 if signal< -1e-9 else 0)
                pnl={s1:settle_score(market,line_e,s1,hg,ag,o1)[1],
                     s2:settle_score(market,line_e,s2,hg,ag,o2)[1]}
                fs=features(e,market,kickoff,quote,p)
                r=dict(fid=fid, market=market, year=kickoff.year,
                       kickoff=kickoff.isoformat(), entry_time=quote.isoformat(),
                       close_time=close_time.isoformat(), lead_h=round((kickoff-quote).total_seconds()/3600,3),
                       line=line_e, close_line=line_c, same_line=same_line, direction=direction,
                       entry_odds={s1:o1,s2:o2}, close_odds={s1:z1,s2:z2},
                       pnl=pnl, features=fs, s1=s1,s2=s2, pretrend=(-float(e["line_delta_since_first_quote"]) if market=="AH" else float(e["line_delta_since_first_quote"])) if numeric(e.get("line_delta_since_first_quote")) else 0,
                       price_prelag=float(e["same_line_no_vig_probability_delta_side1"]) if numeric(e.get("same_line_no_vig_probability_delta_side1")) else 0)
                rows[market].append(r)
                audit["paired_"+market]+=1
                if not same_line: audit["changed_line_"+market]+=1
                if direction==0:audit["neutral_close_direction_"+market]+=1
                # Check a small deterministic sample of source file fingerprints against the index.
                if len(example_hashes)<12 and c.get("source_file") and c.get("raw_sha256"):
                    z=Path(c["source_file"])
                    if z.is_file():
                        example_hashes.append(dict(fid=fid,
                            matches=(hashlib.sha256(z.read_bytes()).hexdigest()==c["raw_sha256"])))
            except Exception as err:
                audit["row_exception_"+type(err).__name__]+=1
                if audit["row_exception_"+type(err).__name__]<4:
                    print("EXCEPTION",fid,market,repr(err),flush=True)
    result={
      "protocol":"EARLY_PRICE_DISCOVERY_T12H_ALL_FIXTURE_MARKET_YEAR_FORWARD_V1",
      "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "provenance":"Crown historical movement events, source received after matches in 2026; NOT tradable timestamp receipts",
      "quote_comparison":"T-12h asof last quote versus prematch close; when line changes, ordinal market direction, NOT same-contract CLV",
      "audit":dict(audit),
      "sha_sample":example_hashes,
      "outputs":{},
      "source_paths":[str(ENTRY),str(CLOSE)],
    }
    with gzip.open(PRED,"wt") as out:
      for market in ("AH","OU"):
        group=rows[market]
        metrics={}
        for test_year in (2025,2026):
            train=[r for r in group if r["year"]<test_year and r["direction"]!=0]
            test=[r for r in group if r["year"]==test_year]
            if not train or not test:
                metrics[str(test_year)]={"status":"unavailable","train":len(train),"test":len(test)}
                continue
            X=np.array([r["features"] for r in train],dtype=float)
            Y=np.array([int(r["direction"]==1) for r in train],dtype=float)
            xx=np.array([r["features"] for r in test],dtype=float)
            b,mu,sd,success=fit(X,Y)
            probs=score(b,mu,sd,xx)
            ytrainmean=float(Y.mean())
            for r,pred in zip(test,probs):
                r["prob_side1_up"]=float(pred)
                r["pred_side"]=r["s1"] if pred>=0.5 else r["s2"]
                r["momentum_side"]=r["s1"] if (r["pretrend"] or r["price_prelag"])>0 else r["s2"]
                r["majority_side"]=r["s1"] if ytrainmean>=0.5 else r["s2"]
                # no hidden threshold: all fixture-markets get a direction
                out.write(json.dumps(dict(fid=r["fid"],market=market,year=test_year,
                    kickoff=r["kickoff"],entry_time=r["entry_time"],lead_hours=r["lead_h"],
                    entry_line=r["line"],close_line=r["close_line"],
                    same_line=r["same_line"],close_direction=r["direction"],
                    predicted_side=r["pred_side"],prob_side1_up=round(float(pred),6),
                    pnl_at_early_quote=r["pnl"][r["pred_side"]],
                    entry_side_odds=r["entry_odds"][r["pred_side"]],
                    close_side_odds=r["close_odds"][r["pred_side"]]),ensure_ascii=False)+"\n")
            valid=[r for r in test if r["direction"]!=0]
            def pred_success(r,pick):
                true=r["s1"] if r["direction"]==1 else r["s2"]
                return pick(r)==true
            pred_accuracy=sum(pred_success(r,lambda x:x["pred_side"]) for r in valid)/len(valid) if valid else None
            majority_accuracy=sum(pred_success(r,lambda x:x["majority_side"]) for r in valid)/len(valid) if valid else None
            momentum_accuracy=sum(pred_success(r,lambda x:x["momentum_side"]) for r in valid)/len(valid) if valid else None
            same=[r for r in test if r["same_line"]]
            contraction=[]
            for r in same:
                s=r["pred_side"]
                contraction.append(r["entry_odds"][s]/r["close_odds"][s]-1)
            bylead={}
            for name,filterf in (
                ("12_20h",lambda r:12<=r["lead_h"]<=20),
                ("over20h",lambda r:r["lead_h"]>20)):
                z=[r for r in test if filterf(r)]
                bylead[name]=get_stats(z,market,lambda r:r["pred_side"])
                bylead[name]["direction_accuracy_on_moved"]=round(sum(pred_success(r,lambda x:x["pred_side"]) for r in z if r["direction"]!=0)/sum(r["direction"]!=0 for r in z),4) if sum(r["direction"]!=0 for r in z) else None
            metrics[str(test_year)]={
                "training_n":len(train),"training_years":sorted({r["year"] for r in train}),
                "training_side1_strengthening_frequency":round(ytrainmean,4),
                "optimizer_converged":success,
                "holdout_market_pairs":len(test),"holdout_unique_fixtures":len({r["fid"] for r in test}),
                "market_direction_moving":len(valid),"market_direction_flat":len(test)-len(valid),
                "line_changed_n":len(test)-len(same),"same_line_n":len(same),
                "actual_lead_hours_median":round(float(np.median([r["lead_h"] for r in test])),3),
                "prediction_side1_pct":round(100*sum(r["pred_side"]==r["s1"] for r in test)/len(test),3),
                "direction_accuracy":round(pred_accuracy,4) if pred_accuracy is not None else None,
                "majority_baseline_direction_accuracy":round(majority_accuracy,4) if majority_accuracy is not None else None,
                "momentum_baseline_direction_accuracy":round(momentum_accuracy,4) if momentum_accuracy is not None else None,
                "always_side1":get_stats(test,market,lambda r:r["s1"]),
                "always_side2":get_stats(test,market,lambda r:r["s2"]),
                "historical_majority_baseline":get_stats(test,market,lambda r:r["majority_side"]),
                "preentry_momentum_baseline":get_stats(test,market,lambda r:r["momentum_side"]),
                "year_forward_price_direction_model":get_stats(test,market,lambda r:r["pred_side"]),
                "same_line_contract_price_improvement":{
                    "n":len(contraction),
                    "mean_entry_over_close_minus_one_pct":round(float(np.mean(contraction))*100,4) if contraction else None,
                    "median_entry_over_close_minus_one_pct":round(float(np.median(contraction))*100,4) if contraction else None,
                    "fraction_entry_odds_better_than_close":round(sum(x>1e-10 for x in contraction)/len(contraction),4) if contraction else None
                },
                "by_entry_lead":bylead,
            }
        result["outputs"][market]=metrics
    result["predictions_file"]=str(PRED)
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("RESULT_PATH",OUT)
    print(json.dumps(result,ensure_ascii=False,indent=2)[:23000])

if __name__=="__main__":
    main()
