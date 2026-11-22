#!/usr/bin/env python3
"""R21: structural correlation and de-duplication sensitivity; research only."""
import collections,json,runpy,math
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"weight_conflict_r20.py"))
groups=r["groups"];catalog=r["catalog"]
# Group by match/horizon, and identify identical signal footprints, avoiding treating aliases as independent.
footprints=collections.defaultdict(set)
for k,sides in groups.items():
 for side,vals in sides.items():
  for candidate,pnl in vals:footprints[candidate].add((k,side))
byfp=collections.defaultdict(list)
for candidate,foot in footprints.items():byfp[frozenset(foot)].append(candidate)
clusters=list(byfp.values())
sizes=sorted((len(x) for x in clusters),reverse=True)
duplicate_candidates=sum(len(c)-1 for c in clusters)
# Score with all votes, identical-footprint cluster 1 vote, and family/batch capped 1 vote per side.
fixture_horizons=collections.defaultdict(list)
for k in groups:fixture_horizons[k[:2]].append(k)
policies=("skip_conflict","net")
weights=("raw","identical_cluster","batch_cap")
records=[]
cluster_id={candidate:i for i,cl in enumerate(clusters) for candidate in cl}
for timing in ("earliest","latest"):
 selected={max(ks,key=lambda k:k[2]) if timing=="earliest" else min(ks,key=lambda k:k[2]) for ks in fixture_horizons.values()}
 for wt in weights:
  for policy in policies:
   orders=[];both=0;multis=0
   for k in selected:
    sides=groups[k]
    if sides["home"] and sides["away"]:both+=1
    if sum(map(len,sides.values()))>1:multis+=1
    counts={}
    for side,vals in sides.items():
     if wt=="raw":counts[side]=len(vals)
     elif wt=="identical_cluster":counts[side]=len({cluster_id[c] for c,p in vals})
     else:counts[side]=len({catalog[c]["batch"] for c,p in vals})
    if policy=="skip_conflict" and counts["home"] and counts["away"]:continue
    if policy=="net" and counts["home"]==counts["away"]:continue
    side="home" if counts["home"]>counts["away"] else "away"
    if not counts[side]:continue
    orders.append((k[0],k[1],k[2],side,sides[side][0][1]))
   n=len(orders);net=sum(x[4] for x in orders)
   eq=peak=mdd=0
   for x in sorted(orders):
    eq+=x[4];peak=max(peak,eq);mdd=max(mdd,peak-eq)
   annual={str(y):{"n":sum(x[0][:4]==str(y) for x in orders),"net_U":round(sum(x[4] for x in orders if x[0][:4]==str(y)),3)} for y in range(2019,2024)}
   records.append(dict(timing=timing,weight=wt,conflict=policy,n=n,net_U=round(net,3),roi_pct=round(100*net/n,4),mdd_U=round(mdd,3),annual=annual,opposite_side_groups=both,multisignal_groups=multis))
out=dict(candidate_definitions=len(catalog),unique_signal_footprints=len(clusters),exact_duplicate_candidate_definitions=duplicate_candidates,
 cluster_size_top=sizes[:20],candidate_footprint_sizes=dict((c,len(f)) for c,f in footprints.items()),
 comparisons=records,limitations="All candidates selected with 2019-2023 outcomes; results in-sample. Exact footprint groups do not capture partial correlation. Batch-cap 1 vote per research round is a diagnostic, not a production rule. One fixture/one order is only a simulation comparison.")
(P/"CORRELATION_CONFLICT_R21_2019_2023.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print("R21",json.dumps({k:v for k,v in out.items() if k not in ("candidate_footprint_sizes","comparisons")},ensure_ascii=False),flush=True)
for z in records:print("COMPARE",z,flush=True)
