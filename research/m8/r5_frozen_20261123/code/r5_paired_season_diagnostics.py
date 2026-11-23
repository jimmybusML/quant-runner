#!/usr/bin/env python3
"""Descriptive R5 paired return-difference uncertainty; no acceptance gates.
Resample existing target SEASONS as whole blocks, not independent bets. This
cannot remove repeated-historical-hypothesis-search or historical-price bias.
"""
import json,hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
HERE=Path(__file__).resolve().parent
SOURCE=HERE/"r5_bayes_bivar_CrownT12_20261123.jsonl"
OUT=HERE/"r5_bayes_bivar_season_block_diagnostics_20261123.json"
PAIRS=(
    ("bayes_prior_1_independent","independent_poisson"),
    ("bayes_prior_2_independent","independent_poisson"),
    ("bivar_empirical_c","independent_poisson"),
    ("bivar_fixed_c010","independent_poisson"),
    ("bayes_prior_2_bivar_empirical_c","bayes_prior_2_independent"),
    ("bayes_prior_2_bivar_fixed_c010","bayes_prior_2_independent"),
)
rows=[json.loads(line) for line in SOURCE.open()]
rng=np.random.default_rng(20261123)
report={"source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "scope":"Post-hoc description on seven previously explored seasons; confidence interval is not new model approval Gate; no adjustment for research multiplicity, historical quote bias or xG provider asof",
    "market":{}}
for market in ("AH","OU"):
    sub=[r for r in rows if r["market"]==market]
    season_ids=sorted({r["season"] for r in sub})
    market_result={}
    for a,b in PAIRS:
        blocks=[]
        for year in season_ids:
            s=[r for r in sub if r["season"]==year]
            delta=sum(r["models"][a]["net_U"]-r["models"][b]["net_U"] for r in s)
            blocks.append((year,len(s),delta))
        n=sum(z[1] for z in blocks)
        total_delta=sum(z[2] for z in blocks)
        boot=[]
        for _ in range(5000):
            sample=rng.integers(0,len(blocks),len(blocks))
            den=sum(blocks[k][1] for k in sample)
            v=sum(blocks[k][2] for k in sample)
            boot.append(100*v/den)
        market_result[f"{a} MINUS {b}"]={
            "total_paired_U_improvement":round(total_delta,5),
            "paired_ROI_pp_improvement":round(100*total_delta/n,5),
            "season_positive_count":sum(delta>0 for yr,matches,delta in blocks),
            "season_count":len(blocks),
            "block_bootstrap_resample_seasons_95pct_ROI_pp_interval":
                [round(float(v),5) for v in np.quantile(boot,[.025,.975])],
            "by_season":[{"year":yr,"n":matches,"delta_U":round(delta,5)} for yr,matches,delta in blocks]}
    report["market"][market]=market_result
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({market:{k:{kk:v for kk,v in x.items() if kk!="by_season"} for k,x in dat.items()} for market,dat in report["market"].items()},ensure_ascii=False))
