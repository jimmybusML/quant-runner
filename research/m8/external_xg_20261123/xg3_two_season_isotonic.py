#!/usr/bin/env python3
"""Two-prior-season outcome-wise isotonic calibration (research-only)
of venue-specific xG3 Skellam forecasts. Paper-inspired, NOT exact paper ROI.
Implements PAV blocks in pure Python and clipping + class normalization.
"""
import json,math
from pathlib import Path
from collections import defaultdict
HERE=Path(__file__).resolve().parent
INPUT=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
OUT=HERE/"xg3_isotonic_2season_20261123.json"
LEDGER=HERE/"xg3_isotonic_2season_20261123.jsonl"
rows=[json.loads(x) for x in INPUT.open()]
byleague=defaultdict(list)
for r in rows:byleague[r["league"]].append(r)

def fit(xs,labels):
    data=sorted(zip(xs,labels),key=lambda x:x[0])
    groups=[]
    for x,y in data:
        if groups and groups[-1]["hi"]==x and groups[-1]["n"]==1:
            pass
        groups.append({"lo":x,"hi":x,"n":1,"sum":float(y)})
        while len(groups)>=2 and groups[-2]["sum"]/groups[-2]["n"]>groups[-1]["sum"]/groups[-1]["n"]:
            b=groups.pop();a=groups[-1]
            a["hi"]=b["hi"];a["n"]+=b["n"];a["sum"]+=b["sum"]
    return groups

def apply(groups,x):
    if not groups:return x
    for b in groups:
        if x<=b["hi"]:
            return b["sum"]/b["n"]
    return groups[-1]["sum"]/groups[-1]["n"]

predictions=[]
fit_audit={}
for league,allrows in sorted(byleague.items()):
    for year in range(2019,2026):
        calib=[r for r in allrows if year-2<=r["season"]<year]
        targets=[r for r in allrows if r["season"]==year]
        if not calib or not targets:continue
        models=[]
        for outcome,pkey in enumerate(["p_H","p_D","p_A"]):
            xs=[r["xG3"][pkey] for r in calib]
            ys=[int(r["outcome"]==outcome) for r in calib]
            models.append(fit(xs,ys))
        fit_audit[f"{league}/{year}"]={"train_seasons":[year-2,year-1],"train_rows":len(calib),"test_rows":len(targets),"pav_blocks":[len(m) for m in models]}
        for r in targets:
            p=[r["xG3"][k] for k in ("p_H","p_D","p_A")]
            q=[max(.05,min(.95,apply(m,x))) for m,x in zip(models,p)]
            q=[x/sum(q) for x in q]
            y=r["outcome"]
            loss=-math.log(max(q[y],1e-15))
            brier=sum((q[i]-int(i==y))**2 for i in range(3))
            predictions.append({"league":league,"season":year,"fid":r["fixture_id"],
                "outcome":y,"raw":p,"calibrated":q,
                "raw_log_loss":r["xG3"]["log_loss"],
                "calibrated_log_loss":loss,
                "raw_brier":r["xG3"]["brier"],
                "calibrated_brier":brier})

def agg(xs):
    n=len(xs)
    return {"n":n,
        "raw_Brier":round(sum(x["raw_brier"] for x in xs)/n,6) if n else None,
        "cal_Brier":round(sum(x["calibrated_brier"] for x in xs)/n,6) if n else None,
        "raw_logloss":round(sum(x["raw_log_loss"] for x in xs)/n,6) if n else None,
        "cal_logloss":round(sum(x["calibrated_log_loss"] for x in xs)/n,6) if n else None,
        "raw_accuracy_pct":round(100*sum(max(range(3),key=lambda i:x["raw"][i])==x["outcome"] for x in xs)/n,4) if n else None,
        "cal_accuracy_pct":round(100*sum(max(range(3),key=lambda i:x["calibrated"][i])==x["outcome"] for x in xs)/n,4) if n else None}
report={"method":"TWO_PRIOR_SEASON_PAV_ISOTONIC_CLASSWISE_RESEARCH_APPROXIMATION",
    "matching_paper":"Per-league 2 prior seasons, H/D/A separate monotonic calibration, clip .05-.95, renormalize. Uses PAV piecewise-constant rather than original paper's linearly interpolated/extrapolated mapping.",
    "isotonic_train_record_restriction":"strictly previous years only",
    "all":agg(predictions),
    "by_league":{league:agg([r for r in predictions if r["league"]==league]) for league in sorted(byleague)},
    "by_season":{str(y):agg([r for r in predictions if r["season"]==y]) for y in range(2019,2026)},
    "fit_audit":fit_audit,
    "limitations":["Prediction quality only: no bookmaker prices or Crown AH/O/U profits",
      "Same data archive reconstructed after matches; old xG availability timestamps not established",
      "Pure Python PAV step mapping is approximation of paper's piecewise-linear calibration",
      "The paper calibrates on one league and evaluates 1X2 betting thresholds; this test is five leagues 1X2 forecasts"]}
with LEDGER.open("w") as f:
    for r in predictions:f.write(json.dumps(r,ensure_ascii=False)+"\n")
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"all":report["all"],"by_league":report["by_league"],"by_season":report["by_season"]},ensure_ascii=False))
