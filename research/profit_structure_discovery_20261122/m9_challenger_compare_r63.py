#!/usr/bin/env python3
"""Aggregate R61-R63 five-model matched retrospective scores and bootstrap."""
import json,gzip,os
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
def load(prefix,indices):
    if os.getenv("M9_COMPARE_EVIDENCE_ONLY"):
        with gzip.open(P/f"{prefix}_EVIDENCE.json.gz","rt") as f:
            z=json.load(f)
        assert not z["errors"]
        return z["results"]
    data=[json.loads((P/f"{prefix}_SHARD{i}.json").read_text()) for i in indices]
    assert all(not z["errors"] for z in data), "Unresolved experiment error"
    return [r for z in data for r in z["results"]]
R61=load("M9_MODEL_CHALLENGER_R61",(0,1,2,3))
R62=load("M9_DYNAMIC_MODEL_R62",(0,1,2,3))
files=[P/f"M9_ROLLING_BASELINES_R63_SHARD{i}.json" for i in (0,1,3)]
files += [P/f"M9_ROLLING_BASELINES_R63_SHARD2_{lab}.json" for lab in ("extraA","extraB","extraC")]
files += [P/"M9_ROLLING_BASELINES_R63_SHARD2.json"]
rolling={}
if os.getenv("M9_COMPARE_EVIDENCE_ONLY"):
    with gzip.open(P/"M9_ROLLING_BASELINES_R63_EVIDENCE.json.gz","rt") as f:
        zlist=[json.load(f)]
else:
    zlist=[json.loads(f.read_text()) for f in files]
for z in zlist:
    assert not z["errors"], z["errors"]
    for r in z["results"]:
        lid=r["league"]
        if lid in rolling:
            assert {y:x["n"] for y,x in rolling[lid]["years"].items()}=={y:x["n"] for y,x in r["years"].items()}
        else:rolling[lid]=r
r61={(x["league"],x["year"]):x for x in R61}
r62={(x["league"],x["year"]):x for x in R62}
assert len(r61)==len(r62)==121 and len(rolling)==43
models=["m9_annual","dc_annual","dynamic","bp_monthly","dc_monthly"]
metrics=["one_ll","rps","exact_ll","margin_ll","margin_brier"]
lines=[-1.5,-1.25,-1.,-.75,-.5,-.25,0.,.25,.5,.75,1.,1.25,1.5]
groups=[]
for (lid,year),x in sorted(r61.items(),key=lambda pair:(int(pair[0][0]),pair[0][1])):
    dy=r62[(lid,year)];roll=rolling[lid]["years"][str(year)]
    assert x["n"]==dy["n"]==roll["n"],(lid,year)
    assert roll["unpredicted"]==0,(lid,year,roll["unpredicted"])
    groups.append({"league":lid,"year":year,"n":x["n"],
      "scores":{"m9_annual":x["summary"]["m9"],"dc_annual":x["summary"]["dc"],
                "dynamic":dy["summary"],"bp_monthly":roll["summary"]["bp"],
                "dc_monthly":roll["summary"]["dc"]},
      "ah":{"m9_annual":x["ah"]["m9"],"dc_annual":x["ah"]["dc"],
            "dynamic":dy["ah"],"bp_monthly":roll["ah"]["bp"],
            "dc_monthly":roll["ah"]["dc"]},
      "monthly_fits":roll["monthly_fits"]})
def score(gg):
    n=sum(x["n"] for x in gg)
    return {"n":n,"metrics":{m:{f:sum(x["scores"][m][f] for x in gg)/n for f in metrics} for m in models}}
overall=score(groups)
years={str(y):score([x for x in groups if x["year"]==y]) for y in (2024,2025,2026)}
handicap={m:{str(l):{t:sum(x["ah"][m][str(l)][t] for x in groups)/overall["n"]
                           for t in ("ll","brier")} for l in lines} for m in models}
league_ids=sorted({x["league"] for x in groups},key=int)
def bootstrap(base,new):
    numerator=[];denominator=[]
    for league in league_ids:
        g=[x for x in groups if x["league"]==league]
        numerator.append(sum(x["scores"][base]["one_ll"]-x["scores"][new]["one_ll"] for x in g))
        denominator.append(sum(x["n"] for x in g))
    numerator=np.array(numerator);denominator=np.array(denominator)
    rng=np.random.default_rng(20261123)
    draws=rng.integers(0,len(league_ids),size=(5000,len(league_ids)))
    samples=numerator[draws].sum(axis=1)/denominator[draws].sum(axis=1)
    return {"gain":float(numerator.sum()/denominator.sum()),
            "improved_leagues":int((numerator>0).sum()),
            "bootstrap_95":[float(v) for v in np.percentile(samples,[2.5,97.5])]}
boot={"annual_dc_vs_annual_bp":bootstrap("m9_annual","dc_annual"),
      "dynamic_vs_annual_bp":bootstrap("m9_annual","dynamic"),
      "dynamic_vs_annual_dc":bootstrap("dc_annual","dynamic"),
      "dynamic_vs_monthly_bp":bootstrap("bp_monthly","dynamic"),
      "dynamic_vs_monthly_dc":bootstrap("dc_monthly","dynamic")}
coverage={"fixtures":overall["n"],"leagues":len(league_ids),"league_years":len(groups),
          "new_final_since_r57":sum(x["new_completed_since_r57"] for x in R61),
          "annual_rho_projection_n":sum(x["dc_rho_projection_n"] for x in R61),
          "monthly_rho_projection_n":sum(x["projections"] for x in rolling.values()),
          "monthly_fit_periods":sum(x["monthly_fits"] for x in groups)}
out={"method":"R61 annual BP/DC, R62 online diagonal Gaussian assumed-density Poisson EKF, R63 month-start expanding refit BP/DC. Historical as-of simulated by kickoff+3h and not actual received-time evidence. All 5 models same latest-cache 2024-26 fixture counts. No Crown ROI, no production change.",
     "coverage":coverage,"overall":overall,"by_year":years,"ah_five_state":handicap,
     "league_cluster_bootstrap":boot,"groups":groups}
(P/"M9_MODEL_CHALLENGERS_R61_R63.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
def markdown_table(header,rows):
    return ["| "+" | ".join(header)+" |","|"+"|".join(["---"]*len(header))+"|"]+["| "+" | ".join(map(str,r))+" |" for r in rows]
labels={"m9_annual":"M9-class annual BP","dc_annual":"Annual Dixon-Coles","dynamic":"Online Poisson EKF",
        "bp_monthly":"Monthly BP refit","dc_monthly":"Monthly Dixon-Coles refit"}
s=["# R61-R63 | Matched real model challenger research","","## Implementations",
   "- Real fitted original M9-class bivariate Poisson and Dixon-Coles, annual frozen baseline.",
   "- An independent, reusable Poisson attack/defence diagonal-covariance assumed-density EKF with per-team attack/defense, league scoring rates, process variance, and post-result online updating.",
   "- BP and Dixon-Coles expanding monthly re-fits with available-result proxy, a cadence-control research comparison. It cannot isolate all advantages from differing update cadence.",
   "- Dixon-Coles rho projected only when mathematically necessary for nonnegative low-score probabilities; count reported.",
   "- Research forecast CLI permits explicit as-of date, fixture and synthetic home handicap; state checkpoint serialization tested.",
   "",
   "## Historical coverage",
   f"{coverage['fixtures']:,} 2024-26 fixtures, {coverage['leagues']} leagues, {coverage['league_years']} league-year pairs. {coverage['new_final_since_r57']} newly finalized fixtures since R57. Annual DC projection {coverage['annual_rho_projection_n']} and rolling DC projection {coverage['monthly_rho_projection_n']} predictions. Monthly fit periods {coverage['monthly_fit_periods']}. No missing predictions.",
   "",
   "## Probability metrics (lower is better)"]
s+=markdown_table(["Model","1X2 LL","RPS","Exact-score LL","7-bin margin LL","7-bin margin Brier"],
  [[labels[m]]+[f"{overall['metrics'][m][key]:.6f}" for key in metrics] for m in models])
s+=["","## 1X2 Log Loss by year"]
s+=markdown_table(["Year","N"]+[labels[m] for m in models],
  [[y,years[y]["n"]]+[f"{years[y]['metrics'][m]['one_ll']:.6f}" for m in models] for y in ("2024","2025","2026")])
s+=["","## Descriptive league-cluster bootstrap of 1X2 LL gain",
    "Positive gain means the challenger reduces loss. 5,000 seeded resamples of 43 league clusters; ignores higher-order dependence and repeated research selection. Not a production promotion test."]
s+=markdown_table(["Comparison","Gain","Improved leagues","Bootstrap 95%"],
  [[name,f"{v['gain']:+.6f}",f"{v['improved_leagues']}/43",
    f"[{v['bootstrap_95'][0]:+.6f}, {v['bootstrap_95'][1]:+.6f}]"] for name,v in boot.items()])
s+=["","## Synthetic home Asian handicap five-state Brier",
    "Score states full-win, half-win, push, half-loss, full-loss. These are neutral synthetic lines, not actual Crown quotes."]
s+=markdown_table(["Home AH"]+[labels[m] for m in models],
  [[f"{l:+g}"]+[f"{handicap[m][str(l)]['brier']:.6f}" for m in models] for l in lines])
s+=["","## Interpretation and limitations",
    "- Training and scoring are code-based using latest historical cache; there is no archived truly point-in-time as-of fixture fact source.",
    "- The R62 EKF result becomes eligible for state update only after assumed kickoff+3h, not a verified final-score receipt. This assumed lag is research code, NOT a user-approved rule.",
    "- Annual model versus online model is update cadence confounded; rolling-month models improve comparability but still do not update after each match.",
    "- All EKF variances, process noise, fit cadence, and DC safe-rho projection are exploratory research choices, not formal M9 changes.",
    "- Some individual metrics/years may worsen. The model is a candidate, not yet proven with Crown-market EV or profit.",
    "- 2026 is partial. League-cluster bootstrap is descriptive, not conclusive under complex calendar, within-team, and selection dependencies.",
    "- No official model, TG orders, Crown evidence, formal ledger, or settlement changed.",
    "",
    "## Files",
    "Model: dynamic_poisson_ekf_r62.py",
    "Predict CLI: m9_dynamic_forecast_r62.py",
    "Annual model experiment: m9_model_challenger_r61.py",
    "Online model experiment: m9_dynamic_model_r62.py",
    "Rolling control experiment: m9_rolling_baselines_r63.py",
    "Compare/report: m9_challenger_compare_r63.py",
    "",
    "## Optional next investigation",
    "Replay actual recorded result-receipt timestamps and paired pre-kickoff Crown quotes for both candidate grids. Then examine AH five-state EV, placed-side differences and settlement ROI as research shadow. No new production gates are assumed.",
    ""]
(P/"M9_MODEL_CHALLENGERS_R61_R63.md").write_text("\n".join(s))
print(json.dumps({"coverage":coverage,"overall":overall,"by_year":years,"boot":boot},indent=2))
