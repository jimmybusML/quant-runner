#!/usr/bin/env python3
"""R70: historical Crown 2023-26 AH EV and five-state probability calibration.
Uses ONLY Codex R66-R68 historic archived quote inputs; never formal M9 sends.
Source quote timestamps are retrospectively recovered; not live executed bets.
No EV filter or new production rule.
"""
import json,datetime as dt,collections
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path.home()/"QuantAsiaDesk"
P=Path(__file__).resolve().parent
MODELS=("annual_bp","annual_dc","dynamic_ekf")
LEADS=("lead6h","lead12h")
YEARS=(2023,2024,2025,2026)
STATES=("FULL_WIN","HALF_WIN","PUSH","HALF_LOSS","FULL_LOSS")
PKEYS=("p_fw","p_hw","p_push","p_hl","p_fl")
WIDTH=.025  # descriptive EV bin, NOT trading threshold
OUT=P/"M9_CROWN_EV_CALIBRATION_R70.json"
quotes=json.loads((ROOT/"state/m9_r68_lead_crown_private.json").read_text())["rows"]
Q={(str(x["fid"]),x["kind"]):x for x in quotes}
assert len(Q)==len(quotes)
source=json.loads((P/"M9_HISTORICAL_CROWN_R68_R69.json").read_text())
data=[]
checks=collections.Counter()
for shard in range(4):
    matches=json.loads((ROOT/f"state/m9_r66_replay_shard{shard}_lead_private.json").read_text())["rows"]
    for rec in matches:
        key=(str(rec["fid"]),rec["kind"])
        assert key in Q,key
        q=Q[key]
        assert q["raw_verification"]=="ok" and rec["year"]==q["year"]
        assert rec["league"]==q["league_id"]
        for model in MODELS:
            r=rec["results"][model]
            side=r["ev_side"];x=r["ev_choice"]
            odd=float(q["home_decimal"] if side=="home" else q["away_decimal"])
            p=np.asarray(x["probabilities"],dtype=float)
            assert p.shape==(5,) and np.isfinite(p).all() and p.min()>=0 and abs(p.sum()-1)<1e-8
            ev=float((p[0]+p[1]/2)*(odd-1)-p[3]/2-p[4])
            assert abs(ev-x["ev"])<1e-8,(key,model)
            idx=STATES.index(x["state"])
            pnl=(odd-1,(odd-1)/2,0.,-.5,-1.)[idx]
            assert abs(pnl-x["pnl_u"])<1e-8,(key,model)
            line=float(q["line"])
            row={"year":int(rec["year"]),"lead":rec["kind"],"model":model,
                 "league":rec["league"],"fixture_id":str(rec["fid"]),
                 "ev":ev,"pnl":pnl,"odds":odd,"state_idx":idx,"side":side,
                 "line":line,"line_type":("integer","quarter","half","three-quarter")[abs(round(line*4))%4],
                 "home_handicap_direction":"home_gives" if line<0 else ("home_gets" if line>0 else "level"),
                 "two_way_inverse_odds_excess":1/float(q["home_decimal"])+1/float(q["away_decimal"])-1}
            row.update({k:float(v) for k,v in zip(PKEYS,p)})
            data.append(row)
            checks["recalculated_ev_and_pnl"]+=1
df=pd.DataFrame(data)
assert len(df)==3*sum(source["by_kind"][lead]["n"] for lead in LEADS)
for lead in LEADS:
    for model in MODELS:
        group=df[(df.lead==lead)&(df.model==model)]
        assert len(group)==source["by_kind"][lead]["n"]
        assert group.fixture_id.nunique()==len(group)
prob=df[list(PKEYS)].to_numpy()
idx=df.state_idx.to_numpy(dtype=int)
df["brier5"]=((prob-np.eye(5)[idx])**2).sum(axis=1)
df["logloss5"]=-np.log(np.maximum(prob[np.arange(len(df)),idx],1e-12))
df["gap"]=df.ev-df.pnl
df["ev_bucket"]=np.floor(df.ev/WIDTH).astype(int)
df["odds_bucket"]=np.floor((df.odds-1)/.1).astype(int)

def brief(g):
    if g.empty:return {"n":0}
    return {"n":len(g),"pred_ev_pct":float(100*g.ev.mean()),
            "real_roi_pct":float(100*g.pnl.mean()),
            "gap_pp":float(100*g.gap.mean()),
            "pnl_u":float(g.pnl.sum())}
def overall(g):
    r=brief(g)
    r.update({"brier5":float(g.brier5.mean()),"logloss5":float(g.logloss5.mean()),
      "mean_odds":float(g.odds.mean()),
      "two_way_inverse_odds_excess_pct":float(100*g.two_way_inverse_odds_excess.mean()),
      "selected_home_pct":float(100*(g.side=="home").mean())})
    r["state_calibration"]={s:{"predicted_pct":float(100*g[pkey].mean()),
         "observed_pct":float(100*(g.state_idx==i).mean()),
         "gap_pp":float(100*(g[pkey]-(g.state_idx==i)).mean())}
         for i,(s,pkey) in enumerate(zip(STATES,PKEYS))}
    return r
def bins(g,col,formatkey):
    return [{formatkey:float(k) if col=="line" else int(k),**brief(x)}
            for k,x in g.groupby(col,sort=True)]
def ev20(g):
    g=g.sort_values("ev",kind="mergesort").reset_index(drop=True)
    bucket=(np.arange(len(g))*20)//len(g)
    return [{"quantile_1_to_20":int(k)+1,"min_ev_pct":float(x.ev.min()*100),
             "max_ev_pct":float(x.ev.max()*100),**brief(x)}
            for k,x in g.groupby(bucket,sort=True)]
def persistence(g):
    yearly={(int(y),float(line)):(float(x.gap.mean()),len(x))
            for (y,line),x in g.groupby(["year","line"])}
    pairs=[]
    for y in (2023,2024,2025):
        old={line:v for (t,line),v in yearly.items() if t==y}
        new={line:v for (t,line),v in yearly.items() if t==y+1}
        for line in sorted(set(old)&set(new)):
            e0,n0=old[line];e1,n1=new[line]
            pairs.append({"transition":f"{y}->{y+1}","home_handicap":line,
                "prior_gap_pp":100*e0,"next_gap_pp":100*e1,
                "n_prior":n0,"n_next":n1,"same_sign":bool((e0>=0)==(e1>=0))})
    return {"pairs":pairs,"pair_count":len(pairs),
      "next_year_weighted_same_sign_pct":float(
          100*sum(r["same_sign"]*r["n_next"] for r in pairs)/sum(r["n_next"] for r in pairs)) if pairs else None}
def cluster_boot(g):
    a=g.groupby("league").agg(n=("ev","size"),err=("gap","sum"))
    vals=a.err.to_numpy(float);n=a.n.to_numpy(float)
    rng=np.random.default_rng(20261123)
    draws=rng.integers(0,len(vals),size=(4000,len(vals)))
    samples=100*vals[draws].sum(axis=1)/n[draws].sum(axis=1)
    return {"leagues":len(a),"95pct":[float(x) for x in np.percentile(samples,[2.5,97.5])]}
def forward(g):
    scores=[]
    for testyear in (2024,2025,2026):
        train=g[g.year<testyear];test=g[g.year==testyear]
        if train.empty or test.empty:continue
        slope,intercept=np.polyfit(train.ev.to_numpy(),train.pnl.to_numpy(),1)
        meanbias=float(train.gap.mean())
        y=test.pnl.to_numpy();raw=test.ev.to_numpy()
        shifted=raw-meanbias;linear=intercept+slope*raw
        mse=lambda pred:float(np.mean((pred-y)**2))
        scores.append({"test_year":testyear,"train_n":len(train),"test_n":len(test),
            "train_gap_pp":100*meanbias,"linear_slope":float(slope),
            "linear_intercept":float(intercept),"realized_roi_pct":float(100*y.mean()),
            "raw_ev_pct":float(100*raw.mean()),
            "prior_bias_corrected_ev_pct":float(100*shifted.mean()),
            "prior_linear_corrected_ev_pct":float(100*linear.mean()),
            "raw_mse":mse(raw),"prior_bias_mse":mse(shifted),"prior_linear_mse":mse(linear)})
    n=sum(z["test_n"] for z in scores)
    return {"years":scores,"test_n":n,
      "pooled_raw_mse":sum(z["raw_mse"]*z["test_n"] for z in scores)/n,
      "pooled_prior_bias_mse":sum(z["prior_bias_mse"]*z["test_n"] for z in scores)/n,
      "pooled_prior_linear_mse":sum(z["prior_linear_mse"]*z["test_n"] for z in scores)/n}

report={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
 "scope":"Retrospectively recovered 2023-26 Codex Crown AH history; source quote T-minus-6/12 hours; NO actual M9 formal orders. No EV gating, new trading rules, production modifications or Telegram.",
 "metrics":"One Crown side chosen per original R66 model by maximum modeled EV even when both negative. Predicted EV vs full/half/push settled 1-unit PnL. Five-state Brier/logloss and mean class calibration. EV/odds groups are diagnostics, not eligibility rules.",
 "limitations":["Provider quote source-time not verified as original system-received time: most historical records backfilled 2026.","Match score availability modeled as kickoff+3h, not actual archived first score receipt.","Annual bivariate Poisson/DC versus online EKF have different update cadence; full paired source universe covers only model-supported fixtures.","Two lead scenarios can refer to same fixture. No doubled orders.","Performance from historical source-quote prices is not executable market ROI."],
 "recomputed_records":len(df),"checks":dict(checks),"groups":{}}
for lead in LEADS:
    report["groups"][lead]={}
    for model in MODELS:
        g=df[(df.lead==lead)&(df.model==model)]
        report["groups"][lead][model]={
          "overall":overall(g),
          "by_year":{str(y):overall(g[g.year==y]) for y in YEARS},
          "by_handicap_fraction":{k:brief(x) for k,x in g.groupby("line_type")},
          "by_handicap_direction":{k:brief(x) for k,x in g.groupby("home_handicap_direction")},
          "by_selected_side":{k:brief(x) for k,x in g.groupby("side")},
          "by_exact_home_handicap":bins(g,"line","home_line"),
          "by_decimal_odds_0p1":bins(g,"odds_bucket","bin_0p1_from_1"),
          "by_ev_0p025":bins(g,"ev_bucket","ev_bin_index"),
          "ev_twenty_quantile_cells":ev20(g),
          "by_league":{k:brief(x) for k,x in g.groupby("league")},
          "by_year_and_fraction":{str(y):{k:brief(x) for k,x in g[g.year==y].groupby("line_type")} for y in YEARS},
          "by_year_and_ev_0p025":{str(y):bins(g[g.year==y],"ev_bucket","ev_bin_index") for y in YEARS},
          "year_line_bias_persistence":persistence(g),
          "ev_gap_bootstrap_league":cluster_boot(g),
          "forward_only_ev_correction":forward(g)}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print("RECORDS",len(df),"SOURCE_T6",source["by_kind"]["lead6h"]["n"],"SOURCE_T12",source["by_kind"]["lead12h"]["n"],flush=True)
for lead in LEADS:
    for model in MODELS:
        z=report["groups"][lead][model]
        print(lead,model,"OVERALL",json.dumps(z["overall"],ensure_ascii=False),flush=True)
        if model=="dynamic_ekf":
            print("YEAR",json.dumps({k:{"ev":v["pred_ev_pct"],"ROI":v["real_roi_pct"],"gap":v["gap_pp"]} for k,v in z["by_year"].items()}),flush=True)
            print("FORWARD",json.dumps(z["forward_only_ev_correction"]),flush=True)
            print("EV20",json.dumps(z["ev_twenty_quantile_cells"]),flush=True)
            print("LINE",json.dumps(z["by_handicap_fraction"]),flush=True)
            print("PERSIST",z["year_line_bias_persistence"]["next_year_weighted_same_sign_pct"],flush=True)
