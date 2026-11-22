#!/usr/bin/env python3
"""R33 R7 per-year portfolio stability using R32 historical-only ordering."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
# R32 script recomputes original frozen candidates, retains exact historical-only ranking.
r=runpy.run_path(str(P/"r7_marginal_coverage_r32.py"))
train=r["train"];test=r["test"];r7=r["r7"];order=[x["added"] for x in r["greedy"]]
def portfolio(groups,ids):
 fi=collections.defaultdict(list)
 for k,sides in groups.items():
  h=[(c,p) for c,p in sides["home"] if c in ids]
  a=[(c,p) for c,p in sides["away"] if c in ids]
  if h or a:fi[k[:2]].append((k,h,a))
 out=collections.defaultdict(list);overlap=collections.defaultdict(lambda:collections.Counter())
 for fixture,ks in fi.items():
  k,h,a=max(ks,key=lambda x:x[0][2]);year=k[0][:4]
  overlap[year]["fixtures_with_signal"]+=1
  overlap[year]["multi_structure"]+=len(h)+len(a)>1
  overlap[year]["opposing"]+=bool(h and a)
  if len(h)==len(a):
   overlap[year]["tied"]+=1;continue
  p=(h if len(h)>len(a) else a)[0][1]
  out[year].append(p)
 return {y:dict(n=len(v),net_U=round(sum(v),3),roi_pct=round(100*sum(v)/len(v),4)) for y,v in sorted(out.items())},dict(overlap)
prefix=[]
for n in range(1,len(order)+1):
 ids=set(order[:n]);yrs,ov=portfolio(train,ids);t,ot=portfolio(test,ids)
 prefix.append(dict(step=n,added=order[n-1],historical_years=yrs,year2024=t.get("2024"),historical_overlap=ov,year2024_overlap=ot.get("2024",{})))
 print("PREFIX",n,"2019-23",[(y,round(v["roi_pct"],2)) for y,v in yrs.items()],"2024",t.get("2024"),flush=True)
base,base_ov=portfolio(train,r7);testbase,testov=portfolio(test,r7)
leave=[]
for c in sorted(r7):
 yrs,_=portfolio(train,r7-{c});ty,_=portfolio(test,r7-{c})
 leave.append(dict(candidate=c,annual_net_U_contribution={y:round(base[y]["net_U"]-yrs.get(y,{}).get("net_U",0),3) for y in base},
  annual_order_contribution={y:base[y]["n"]-yrs.get(y,{}).get("n",0) for y in base},
  year2024_net_U_contribution=round(testbase["2024"]["net_U"]-ty.get("2024",{}).get("net_U",0),3),
  historical_positive_contribution_years=sum(base[y]["net_U"]-yrs.get(y,{}).get("net_U",0)>0 for y in base)))
out=dict(scope="R7 historical per-year marginal portfolio and coverage stability",baseline_years=base,baseline_2024=testbase,
 historical_only_order=order,prefixes=prefix,leave_one_out=leave,
 caveats=["2019-2023 years are in-sample for original R7 structure selection, not independent rolling validation.",
 "R32 historical-only order fixed without using 2024; prefix selection after inspecting 2024 remains post-hoc.",
 "Annual leave-one-out differences are portfolio changes, including vote, horizon and tie changes; not standalone candidate profit.",
 "No new strategy rules, selection gates, or 2025-2026 use. Crown quotes retrospective, not proven real-time executable."])
(P/"R7_YEAR_STABILITY_R33.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
