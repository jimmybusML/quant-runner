#!/usr/bin/env python3
"""R22 compare conflict strength and quote horizon without new production rules."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"weight_conflict_r20.py"))
groups=r["groups"];catalog=r["catalog"]
fids=collections.defaultdict(list)
for k in groups:fids[k[:2]].append(k)
# First and last signal-bearing horizons; fixed-horizon T24/T12/T6/T2;
# vote-margin differences; original votes vs batch-unique votes.
strategies=[]
for timing in ("earliest","latest","T24","T12","T6","T2"):
 for vote in ("raw","batch"):
  for conflict in ("skip","net","stronger_by_2","stronger_by_3","stronger_by_5"):
   orders=[];conflicts=0;abstentions=0
   for f,ks in fids.items():
    if timing=="earliest":k=max(ks,key=lambda x:x[2])
    elif timing=="latest":k=min(ks,key=lambda x:x[2])
    else:
     matches=[x for x in ks if x[2]==int(timing[1:])]
     if not matches:continue
     k=matches[0]
    sides=groups[k]
    counts={s:(len(v) if vote=="raw" else len({catalog[c]["batch"] for c,p in v})) for s,v in sides.items()}
    if counts["home"] and counts["away"]:conflicts+=1
    if conflict=="skip" and counts["home"] and counts["away"]:abstentions+=1;continue
    if counts["home"]==counts["away"]:abstentions+=1;continue
    diff=abs(counts["home"]-counts["away"])
    if conflict.startswith("stronger_by_") and diff<int(conflict.split("_")[-1]):abstentions+=1;continue
    side=max(counts,key=counts.get)
    orders.append((k[0],k[1],k[2],side,sides[side][0][1],counts["home"],counts["away"]))
   n=len(orders);net=sum(x[4] for x in orders)
   eq=peak=mdd=0.
   for x in sorted(orders):
    eq+=x[4];peak=max(peak,eq);mdd=max(mdd,peak-eq)
   years={str(y):dict(n=sum(x[0][:4]==str(y) for x in orders),net_U=round(sum(x[4] for x in orders if x[0][:4]==str(y)),3)) for y in range(2019,2024)}
   strategies.append(dict(timing=timing,vote=vote,conflict=conflict,n=n,net_U=round(net,3),roi_pct=round(100*net/n,4) if n else None,mdd_U=round(mdd,3),conflict_groups=conflicts,abstentions=abstentions,years=years))
out=dict(scope="2019-2023 Crown AH, 494 R7-R15 preselected candidates",strategies=strategies,limitations="All candidate structures selected on 2019-2023 outcomes; selection leakage. Vote-margin minimums are exploratory diagnostics, not user-approved gates. Earliest/latest use signal-bearing horizons. 1U per fixture, no bankroll optimization. No R17/R18 candidates, no 2024-2026.")
(P/"CONFLICT_TIMING_R22_2019_2023.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("TOTAL",len(strategies),flush=True)
for z in strategies:
 if z["timing"] in ("earliest","latest") and z["vote"]=="raw" or z["timing"].startswith("T") and z["vote"]=="raw" and z["conflict"] in ("skip","net"):
  print("ROW",z,flush=True)
