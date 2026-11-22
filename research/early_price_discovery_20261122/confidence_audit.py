#!/usr/bin/env python3
"""Descriptive ranking of heldout predictions; quintiles are NOT production thresholds."""
import collections
import datetime as dt
import gzip
import json
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PRED=HERE/"holdout_research_predictions.jsonl.gz"
OUT=HERE/"confidence_audit.json"

buckets=collections.defaultdict(list)
with gzip.open(PRED,"rt") as f:
    for line in f:
        r=json.loads(line)
        buckets[(r["market"],r["year"])].append(r)

def summarise(v):
    n=len(v)
    out={"n":n,"net_U":round(sum(r["pnl_at_early_quote"] for r in v),4),
         "roi_pct":round(100*sum(r["pnl_at_early_quote"] for r in v)/n,4) if n else None,
         "market_dir_moving":sum(r["close_direction"]!=0 for r in v),
         "market_dir_hits":sum(((r["close_direction"]>0)==(r["predicted_side"] in ("home","over"))) for r in v if r["close_direction"]!=0)}
    out["market_direction_accuracy"]=round(out["market_dir_hits"]/out["market_dir_moving"],4) if out["market_dir_moving"] else None
    same=[r for r in v if r["same_line"]]
    improve=[r["entry_side_odds"]/r["close_side_odds"]-1 for r in same]
    out["same_line_n"]=len(same)
    out["same_line_improved_fraction"]=round(sum(q>1e-12 for q in improve)/len(improve),4) if improve else None
    out["same_line_mean_entry_to_close_price_ratio_minus_one_pct"]=round(100*sum(improve)/len(improve),4) if improve else None
    out["same_line_late_odds_drop_at_least_0_2_decimal"]=sum(r["entry_side_odds"]-r["close_side_odds"]>=0.2 for r in same)
    out["same_line_entry_about_1_9_to_close_1_6_or_below"]=sum(1.88<=r["entry_side_odds"]<=1.92 and r["close_side_odds"]<=1.6 for r in same)
    return out

report={"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "method":"Within each market+holdout-year, rank ALL model predictions by abs(prob_side1_up - 0.5), descriptive equal-count quintiles; all orders remain in the audit.",
        "caution":"This is an ex-post breakdown of out-of-year predictions, not a prevalidated trading gate or deployable portfolio.",
        "groups":{}}
for (market,year),rr in sorted(buckets.items()):
    s=sorted(rr,key=lambda r:abs(r["prob_side1_up"]-0.5))
    out={"all":summarise(s),"quintiles":{}}
    for i in range(5):
        selected=s[int(len(s)*i/5):int(len(s)*(i+1)/5)]
        out["quintiles"][str(i+1)]={
            "confidence_min":round(float(min(abs(r["prob_side1_up"]-0.5) for r in selected)),5),
            "confidence_max":round(float(max(abs(r["prob_side1_up"]-0.5) for r in selected)),5),
            **summarise(selected)}
    report["groups"][market+"_"+str(year)]=out
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False,indent=2))
