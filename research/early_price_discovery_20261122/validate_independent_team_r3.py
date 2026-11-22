#!/usr/bin/env python3
"""Read-only independent reconciliation of R3 chosen sides, Asian FT, and model-CLV values."""
import collections
import datetime as dt
import gzip
import json
from pathlib import Path

import numpy as np
from research.m3.probabilities import settle_score

HERE=Path(__file__).resolve().parent
RESULTS=HERE/"independent_team_information_r3_results.json"
PRED=HERE/"independent_team_information_r3_predictions.local.jsonl.gz"
R2=HERE/"joint_fair_value_r2_research_rows.jsonl.gz"
EARLY=Path("/Users/mac/QuantAsiaDesk/research-work/m8_early_joint_market_inventory_20261115.jsonl")
OUT=HERE/"independent_team_information_r3_validation.json"
summary=json.load(open(RESULTS))
p=[json.loads(line) for line in gzip.open(PRED,"rt")]
ref={}
for line in gzip.open(R2,"rt"):
    z=json.loads(line)
    if z["year"]==2026:ref[z["fid"]]=z
e={}
for line in EARLY.open():
    z=json.loads(line)
    if z["T"]==12 and z["fid"] in ref:
        e[z["fid"]]=z
assert len(p)==len(ref)==len(e)==8860
assert len({r["fid"] for r in p})==len(p)
names=summary["baselines"]+summary["variants"]
count=collections.Counter()
miss=0
for r in p:
    f=r["fid"];original=ref[f];q=e[f]
    assert original["year"]==r["year"]==2026
    assert r["ko"]==original["kickoff_utc"]
    cutoff=dt.datetime.fromisoformat(r["T12"])
    if r["history_max_available"] is not None:
        assert dt.datetime.fromisoformat(r["history_max_available"]) <= cutoff
    h,a=q["hg"],q["ag"]
    home=settle_score("AH",q["al"],"home",h,a,q["ah"])[1]
    away=settle_score("AH",q["al"],"away",h,a,q["aa"])[1]
    assert abs(home-original["pnl_home"])<1e-8
    assert abs(away-original["pnl_away"])<1e-8
    assert abs(home-r["pnl_home"])<1e-8 and abs(away-r["pnl_away"])<1e-8
    assert abs(r["clv_home"]-original["clv_home"])<1e-8
    assert abs(r["clv_away"]-original["clv_away"])<1e-8
    assert len(r["feature"]["team"])==14
    assert len(r["feature"]["market"])==9
    assert len(r["feature"]["combined"])==23
    assert r["predict"]["R2_stale_1x2_residual"]==original["predicted_residual_side"]
    assert r["predict"]["early_favorite"]==(
        "home" if q["al"]<0 else "away" if q["al"]>0 else
        ("home" if q["ah"]<q["aa"] else "away"))
    for name in names:
        assert r["predict"][name] in ("home","away")
    count["verified_row"]+=1
    if r["team_missing_any"]:miss+=1
assert count["verified_row"]==8860

# Independent group recon to published summary; both payoff and across-line model close-value.
for name in names:
    s=[r["predict"][name] for r in p]
    pnl=np.array([r["pnl_"+side] for r,side in zip(p,s)],dtype=float)
    val=np.array([r["clv_"+side] for r,side in zip(p,s)],dtype=float)
    a=summary["summary_2026"][name]
    assert a["n"]==len(p)
    assert abs(a["net_U"]-round(float(pnl.sum()),4))<1e-7
    assert abs(a["roi_pct"]-round(100*float(pnl.mean()),4))<1e-7
    assert abs(a["crossline_close_implied_ev_pct"]-round(100*float(val.mean()),4))<1e-7
    count["validated_variant"]+=1

# Realized ex post high-value events, descriptive. Never used for direction selection.
breakdown={}
for t in (0,0.05,0.10,0.15,0.1875,0.25):
    candidates=[r for r in p if max(r["clv_home"],r["clv_away"])>t]
    capture={}
    for name in ("early_favorite","R2_stale_1x2_residual",
                 "market_clv_frozen_2025","team_clv_frozen_2025","combined_clv_frozen_2025",
                 "market_clv_expanding_monthly","team_clv_expanding_monthly","combined_clv_expanding_monthly"):
        capture[name]=sum(r["clv_"+r["predict"][name]]>t for r in candidates)
    breakdown[str(t)]=dict(total=len(candidates),fraction_all=round(len(candidates)/len(p),5),
                           chosen_side_captures=capture)

week=collections.defaultdict(list)
for r in p:
    z=dt.date.fromisoformat(r["ko"][:10]).isocalendar()
    week[(z.year,z.week)].append(r)

rng=np.random.default_rng(20261122)
comparisons={}
for a,b in [
    ("team_clv_frozen_2025","market_clv_frozen_2025"),
    ("combined_clv_frozen_2025","market_clv_frozen_2025"),
    ("team_clv_expanding_monthly","market_clv_expanding_monthly"),
    ("combined_clv_expanding_monthly","market_clv_expanding_monthly"),
    ("team_pnl_expanding_monthly","market_pnl_expanding_monthly"),
    ("combined_pnl_expanding_monthly","market_pnl_expanding_monthly")
]:
    def calc_delta(group,measure):
        return sum(r[measure+"_"+r["predict"][a]]-r[measure+"_"+r["predict"][b]] for r in group)
    weekly=[(calc_delta(g,"pnl"),calc_delta(g,"clv"),len(g)) for g in week.values()]
    values=np.array(weekly)
    selected=rng.integers(0,len(weekly),size=(3500,len(weekly)))
    sums=values[selected].sum(1)
    delta_roi=100*sums[:,0]/sums[:,2]
    delta_clv=100*sums[:,1]/sums[:,2]
    comparisons[a+"_vs_"+b]=dict(
      weeks=len(weekly),
      delta_roi_pctpoints=round(100*values[:,0].sum()/values[:,2].sum(),4),
      roi_week_bootstrap95=[round(float(z),4) for z in np.quantile(delta_roi,[.025,.975])],
      delta_close_model_ev_pctpoints=round(100*values[:,1].sum()/values[:,2].sum(),4),
      close_model_ev_week_bootstrap95=[round(float(z),4) for z in np.quantile(delta_clv,[.025,.975])])
r=dict(validated=True,generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    count=dict(count),rows_with_at_least_one_team_without_prior_match=int(miss),
    all_2026_holdout_rows=len(p),research_outcome_source="historical Crown FT and source-event prices",
    model_comparisons=comparisons,ex_post_large_price_value_events=breakdown,
    caveat="Strong positive close-implied-value cases are only identifiable using FUTURE closing odds. Do NOT use these ex post labels as prediction signals or trading thresholds.")
OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
print("VALIDATED",r["validated"],"rows",len(p),"missing",miss)
for k,v in comparisons.items():print(k,v)
for k,v in breakdown.items():print("EXPOST_VALUE",k,v)
