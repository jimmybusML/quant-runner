#!/usr/bin/env python3
"""Exploratory structure discovery, 2019-23 discovery and 2024/25/26 frozen forward.
Historical Crown event time is not real historical receipt time. Research only.
"""
import collections,json,datetime as dt
from pathlib import Path
from research.m3.probabilities import settle_score
ROOT=Path(__file__).resolve().parent
SOURCE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
FAMILIES=[("line",),("price",),("momentum",),("age",),("line","price"),("line","momentum"),("price","momentum"),("line","age"),("momentum","age"),("line","price","momentum")]
def b(v,edges):return sum(v>=e for e in edges)
def features(r):
 return dict(line=b(abs(r["line"]),[.25,.75,1.25,2.25]),
 price=b(r["home"],[1.8,1.9,2.,2.1]),
 momentum=b(r["delta"],[-.5,-.125,.125,.5]),
 age=b(r["age"],[.5,2,6,12]))
def stats(v):
 return dict(n=len(v),net_U=round(sum(v),3),roi_pct=round(100*sum(v)/len(v),4) if v else None)
groups=collections.defaultdict(lambda:collections.defaultdict(list))
cohorts=collections.Counter()
invalid=0
with SOURCE.open() as f:
 for line in f:
  a=json.loads(line)
  if a.get("market")!="AH":continue
  try:
   year=str(a["year"]);h=int(a["entry_horizon_hours"])
   if year not in map(str,range(2019,2027)):continue
   home,away=float(a["odds"]["home"]),float(a["odds"]["away"])
   hg,ag=map(int,a["score"].split("-"))
   r=dict(line=float(a["line"]),home=home,away=away,delta=float(a.get("line_delta_since_first_quote") or 0),age=float(a["actual_hours_before_kickoff"])-h)
   pnl={"home":settle_score("AH",r["line"],"home",hg,ag,home)[1],"away":settle_score("AH",r["line"],"away",hg,ag,away)[1]}
   fav="home" if r["line"]<0 else "away" if r["line"]>0 else "home" if home<away else "away"
   pnl["favorite"]=pnl[fav];pnl["underdog"]=pnl["away" if fav=="home" else "home"]
   fs=features(r)
   for family in FAMILIES:
    name=";".join(f"{k}={fs[k]}" for k in family)
    for side,value in pnl.items():
     groups[(h,",".join(family),name,side)][year].append(value)
   cohorts[(h,year)]+=1
  except (ValueError,TypeError,KeyError,AssertionError,ZeroDivisionError):invalid+=1
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 source=str(SOURCE),provenance="Crown historical quote event times retrospectively collected in 2026; not true pregame HTTP receipt",
 methodology="Enumerate all 10 feature families and 4 sides, 2019-23 discover, 2024-26 fixed forward. No min sample, EV, ROI filter or production gate. All candidates retained.",
 cohort_counts={f"T{h}_{y}":v for (h,y),v in sorted(cohorts.items())},
 candidate_families=[list(f) for f in FAMILIES],invalid_rows=invalid,by_horizon={})
for (h,family,name,side),years in groups.items():
 train=sum((years.get(str(y),[]) for y in range(2019,2024)),[])
 if not train:continue
 z=dict(family=family,structure=name,direction=side,discovery=stats(train),
        years={str(y):stats(years.get(str(y),[])) for y in range(2019,2027)})
 out["by_horizon"].setdefault(str(h),[]).append(z)
for h,arr in out["by_horizon"].items():
 arr.sort(key=lambda x:(x["discovery"]["roi_pct"],x["discovery"]["n"]),reverse=True)
 print("T",h,"candidates",len(arr),"discovery",sum(cohorts.get((int(h),str(y)),0) for y in range(2019,2024)),"forward",[(y,cohorts.get((int(h),y),0)) for y in ("2024","2025","2026")])
 for z in arr[:3]:
  print("TOP",z["family"],z["structure"],z["direction"],z["discovery"],[(y,z["years"][y]) for y in ("2024","2025","2026")])
(ROOT/"structure_discovery_r1_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("DONE",sum(len(x) for x in out["by_horizon"].values()),"INVALID",invalid)
