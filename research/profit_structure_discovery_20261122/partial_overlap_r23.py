#!/usr/bin/env python3
"""R23 partial overlap Jaccard + annual/monthly stability, research-only."""
import collections,json,runpy,itertools
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"weight_conflict_r20.py"))
groups=r["groups"];catalog=r["catalog"]
foot=collections.defaultdict(set)
for k,sides in groups.items():
 for side,vals in sides.items():
  for candidate,pnl in vals:foot[candidate].add((k,side))
# Sparse inverted index for pairwise intersections, only shared signals.
inverted=collections.defaultdict(list)
for c,items in foot.items():
 for item in items:inverted[item].append(c)
inter=collections.Counter()
for candidates in inverted.values():
 for pair in itertools.combinations(sorted(set(candidates)),2):inter[pair]+=1
thresholds=(.5,.7,.8,.9,.95,1.0)
pairs={str(t):0 for t in thresholds}
adj={t:collections.defaultdict(set) for t in thresholds}
top=[]
for (a,b),n in inter.items():
 j=n/(len(foot[a])+len(foot[b])-n)
 for t in thresholds:
  if j>=t:pairs[str(t)]+=1;adj[t][a].add(b);adj[t][b].add(a)
 if j>=.9:top.append((round(j,5),a,b,n))
# Connected components for diagnostic only (transitive chaining != mutual correlation).
components={}
for t in thresholds:
 seen=set();sizes=[]
 for c in catalog:
  if c in seen:continue
  stack=[c];seen.add(c);size=0
  while stack:
   q=stack.pop();size+=1
   for other in adj[t].get(q,()):
    if other not in seen:seen.add(other);stack.append(other)
  sizes.append(size)
 components[str(t)]=dict(components=len(sizes),largest=max(sizes),multi_components=sum(x>1 for x in sizes),members_in_multi=sum(x for x in sizes if x>1))
# Stable monthly and annual statistics for baseline policies; compare consistent matched order sets.
fids=collections.defaultdict(list)
for k in groups:fids[k[:2]].append(k)
baseline=[]
for timing in ("earliest","latest"):
 for policy in ("skip","net","margin2","margin3"):
  orders=[]
  for fid,ks in fids.items():
   k=max(ks,key=lambda x:x[2]) if timing=="earliest" else min(ks,key=lambda x:x[2])
   sides=groups[k];h=len(sides["home"]);a=len(sides["away"])
   if policy=="skip" and h and a:continue
   if h==a:continue
   if policy=="margin2" and abs(h-a)<2:continue
   if policy=="margin3" and abs(h-a)<3:continue
   side="home" if h>a else "away"
   orders.append((k[0],k[1],sides[side][0][1]))
  month=collections.defaultdict(list)
  for date,fid,pnl in orders:month[date[:7]].append(pnl)
  active={m:dict(n=len(p),net_U=round(sum(p),3),roi_pct=round(100*sum(p)/len(p),4)) for m,p in sorted(month.items())}
  years={str(y):dict(n=sum(x[0][:4]==str(y) for x in orders),net_U=round(sum(x[2] for x in orders if x[0][:4]==str(y)),3)) for y in range(2019,2024)}
  baseline.append(dict(timing=timing,policy=policy,n=len(orders),net_U=round(sum(x[2] for x in orders),3),
   positive_active_months=sum(z["net_U"]>0 for z in active.values()),
   negative_active_months=sum(z["net_U"]<0 for z in active.values()),
   zero_active_months=sum(z["net_U"]==0 for z in active.values()),
   active_months=len(active),worst_month=min(active.items(),key=lambda x:x[1]["net_U"]) if active else None,
   best_month=max(active.items(),key=lambda x:x[1]["net_U"]) if active else None,
   years=years,months=active))
out=dict(scope="2019-2023 historical Crown AH; R7-R15 preselected 494",candidate_definitions=len(catalog),
 candidate_pairs_total=len(catalog)*(len(catalog)-1)//2,shared_signal_pairs=len(inter),
 jaccard_pair_counts=pairs,connected_components=components,
 high_similarity_examples=sorted(top,reverse=True)[:30],baseline_stability=baseline,
 limitations="All 494 definitions were selected on 2019-2023 outcome data; these are descriptive, not out-of-sample. Jaccard counts shared identical fixture+horizon+physical side; graph connected components can chain dissimilar candidates. 1U per fixture is an experimental comparison, not a rule. No 2024-2026 data.")
(P/"PARTIAL_OVERLAP_R23_2019_2023.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
print("PAIRS",pairs,flush=True)
print("COMPONENTS",components,flush=True)
for z in baseline:print("STABILITY",{k:v for k,v in z.items() if k not in ("months","years")},flush=True)
