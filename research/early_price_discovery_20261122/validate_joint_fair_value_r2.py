#!/usr/bin/env python3
"""Independent R2 validation: Poisson Asian quarter-line exact outcomes, row reconciliation, and weekly uncertainty."""
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import random
from pathlib import Path
import sys

import numpy as np

from research.m3.probabilities import settle_score
from research.early_price_discovery_20261122.joint_fair_value_r2 import ah_components, ou_components

HERE=Path(__file__).resolve().parent
S=HERE/"joint_fair_value_r2_results.json"
R=HERE/"joint_fair_value_r2_research_rows.jsonl.gz"
OUT=HERE/"joint_fair_value_r2_validation.json"
SOURCE=Path("/Users/mac/QuantAsiaDesk/research-work/m8_early_joint_market_inventory_20261115.jsonl")
CLOSE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl")
data=json.load(open(S))
rows=[json.loads(line) for line in gzip.open(R,"rt")]
idx={r["fid"]:r for r in rows}
assert len(idx)==len(rows)
audit=collections.Counter()

# Independently verify the Asian contract win/lose stake integration against explicit scores.
for market in ("AH","OU"):
    for line in [-2.75,-1.25,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1,1.5,2,2.25,2.75,3.25,3.5]:
        mu_h,mu_a=1.42,1.11
        if market=="OU" and line<0:continue
        h=np.array([math.exp(-mu_h)*mu_h**k/math.factorial(k) for k in range(28)])
        a=np.array([math.exp(-mu_a)*mu_a**k/math.factorial(k) for k in range(28)])
        W=L=0.0
        for hg,ph in enumerate(h):
            for ag,pa in enumerate(a):
                pnl=settle_score(market,line,"home" if market=="AH" else "over",hg,ag,2.0)[1]
                W+=ph*pa*max(pnl,0)
                L+=ph*pa*max(-pnl,0)
        if market=="AH":
            wc,lc=ah_components(np.array([mu_h+mu_a]),np.array([mu_h/(mu_h+mu_a)]),np.array([line]))
        else:
            wc,lc=ou_components(np.array([mu_h+mu_a]),np.array([line]))
        assert abs(W-wc[0])<1e-7 and abs(L-lc[0])<1e-7, (market,line,W,L,wc,lc)
        audit["quarter_line_distribution_exact_cases"]+=1

early={}
for line in SOURCE.open():
    r=json.loads(line)
    if r["T"]==12 and r["fid"] in idx:
        early[r["fid"]]=r
assert len(early)==len(rows)
close={}
for line in CLOSE.open():
    r=json.loads(line)
    if str(r["fixture_id"]) in idx:
        close[str(r["fixture_id"])]=r
SUP=HERE/"m5_2026_close_supplement.local.jsonl"
for line in SUP.open():
    r=json.loads(line)
    if str(r["fixture_id"]) in idx:
        close[str(r["fixture_id"])]=r
assert len(close)==len(rows)

for r in rows:
    e=early[r["fid"]];c=close[r["fid"]]
    assert str(e["fid"])==str(r["fid"])
    assert e["year"]==r["year"]
    assert r["kickoff_utc"]==c["kickoff_utc"]
    assert e["al"]==r["line_early"]
    assert c["markets"]["AH"]["line"]==r["line_close"]
    h,a=e["hg"],e["ag"]
    for side in ("home","away"):
        price=e["ah"] if side=="home" else e["aa"]
        pnl=settle_score("AH",e["al"],side,h,a,price)[1]
        assert abs(r["pnl_"+side]-pnl)<1e-9
    chosen=r["predicted_residual_side"]
    assert abs(r["pnl_residual"]-r["pnl_"+chosen])<1e-9
    assert abs(r["clv_residual"]-r["close_CLV_ev_"+chosen])<1e-6
    audit["row_pnl_and_price_audited"]+=1

for k,g in data["groups"].items():
    if k in ("2025","2026","all"):
        z=[r for r in rows if k=="all" or str(r["year"])==k]
        assert len(z)==g["residual_side"]["n"]
        assert abs(round(sum(r["pnl_residual"] for r in z),3)-g["residual_side"]["net_U"])<1e-8
        assert abs(round(sum(r["pnl_opposite"] for r in z),3)-g["opposite_side"]["net_U"])<1e-8
        audit["reconciled_summary_"+k]=len(z)

# Descriptive weekly block bootstrap to avoid treating correlated same-week fixtures as IID.
rng=random.Random(20261122)
def group_ci(z,iterations=2500):
    byweek=collections.defaultdict(list)
    for r in z:
        d=dt.date.fromisoformat(r["kickoff_utc"][:10]).isocalendar()
        byweek[(d.year,d.week)].append(r["pnl_residual"])
    units=list(byweek.values());k=len(units)
    values=[]
    if not k:return None
    for _ in range(iterations):
        selected=[units[rng.randrange(k)] for _ in range(k)]
        values.append(100*sum(sum(x) for x in selected)/sum(len(x) for x in selected))
    values.sort()
    return dict(weeks=k,roi_pct=round(100*sum(r["pnl_residual"] for r in z)/len(z),4),
                block_bootstrap_95pct=[round(values[int(.025*iterations)],4),
                                        round(values[int(.975*iterations)],4)])
groups={}
for year in (2025,2026):
    yr=[r for r in rows if r["year"]==year]
    groups[str(year)]=group_ci(yr)
    z=[r for r in yr if r["age_1x2_h"]<=6]
    groups[str(year)+"_1x2_age_le_6h"]=group_ci(z)
    month=collections.defaultdict(list)
    for r in yr:month[r["kickoff_utc"][:7]].append(r)
    groups[str(year)+"_by_month"]={
        m:dict(n=len(v),ROI_pct=round(100*sum(r["pnl_residual"] for r in v)/len(v),4))
        for m,v in sorted(month.items())
    }

source_sha={}
# Verify sample of actual raw HTTP response hashes from close inventory as separate chain of evidence.
for fid,c in list(close.items())[:30]:
    path=Path(c.get("source_file") or "")
    if path.is_file():
        source_sha[fid]=(hashlib.sha256(path.read_bytes()).hexdigest()==c["raw_sha256"])
assert all(source_sha.values())
audit["raw_sha_checked"]=len(source_sha)

res=dict(pass_=True,generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
         audit=dict(audit),groups=groups,
         note="This validates calculations and raw-file sample checks, NOT time-of-receipt execution, real CLV truth or selection rules.")
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(res,ensure_ascii=False,indent=2))
