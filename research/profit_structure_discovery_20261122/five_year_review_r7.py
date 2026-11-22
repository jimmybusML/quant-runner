#!/usr/bin/env python3
"""2019-23 only. Full-year positive R1 candidates; monthly and peak-to-trough audits.
Research review only. No future years, production edits or acceptance policy.
"""
import collections,datetime as dt,json,csv
from pathlib import Path
from research.m3.probabilities import settle_score
ROOT=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
r1=json.load(open(ROOT/"structure_discovery_r1_results.json"))
candidates={}
for h,items in r1["by_horizon"].items():
 for a in items:
  if all(a["years"][str(y)]["n"]>0 and a["years"][str(y)]["net_U"]>0 for y in range(2019,2024)):
   k=(int(h),a["family"],a["structure"],a["direction"]);candidates[k]=a
assert len(candidates)==27,len(candidates)
ledger=collections.defaultdict(list);cohorts=collections.Counter();fid_year=collections.defaultdict(set)
def b(v,edges):return sum(v>=e for e in edges)
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
 h=int(a["entry_horizon_hours"]);y=str(a["year"]);fid=str(a["fixture_id"]);cohorts[(y,h)]+=1
 fid_year[y].add(fid)
 x=dict(line=float(a["line"]),home=float(a["odds"]["home"]),away=float(a["odds"]["away"]),delta=float(a.get("line_delta_since_first_quote") or 0),age=float(a["actual_hours_before_kickoff"])-h)
 features=dict(line=b(abs(x["line"]),[.25,.75,1.25,2.25]),price=b(x["home"],[1.8,1.9,2,2.1]),momentum=b(x["delta"],[-.5,-.125,.125,.5]),age=b(x["age"],[.5,2,6,12]))
 hg,ag=map(int,a["score"].split("-"))
 fav="home" if x["line"]<0 else "away" if x["line"]>0 else "home" if x["home"]<x["away"] else "away"
 directions=dict(home="home",away="away",favorite=fav,underdog="away" if fav=="home" else "home")
 for k in candidates:
  hh,family,structure,direction=k
  if hh!=h or structure!=";".join(f"{f}={features[f]}" for f in family.split(",")):continue
  side=directions[direction]
  pnl=settle_score("AH",x["line"],side,hg,ag,x["home"] if side=="home" else x["away"])[1]
  ledger[k].append((a["kickoff_utc"],fid,side,pnl))
def stats(v):
 n=len(v);s=sum(v)
 return dict(n=n,net_U=round(s,3),roi_pct=round(100*s/n,4) if n else None)
out=dict(scope="2019-2023 only, 2024-2026 not consulted in selection or stats",source=str(SRC),created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),year_unique_fixtures={y:len(s) for y,s in fid_year.items()},year_window_rows={y:{str(h):cohorts[(y,h)] for h in (24,12,6,2)} for y in fid_year},candidates=[])
for k,a in candidates.items():
 rows=sorted(ledger[k],key=lambda r:(r[0],r[1]))
 byyear={y:stats([v for date,fid,side,v in rows if date[:4]==y]) for y in map(str,range(2019,2024))}
 monthly={f"{y}-{m:02}":stats([v for date,fid,side,v in rows if date[:7]==f"{y}-{m:02}"]) for y in range(2019,2024) for m in range(1,13)}
 equity=0;peak=0;dd=0;dd_start=None;dd_end=None;peak_at="initial";worst_run=0;current_run=0
 for date,fid,side,pnl in rows:
  equity+=pnl
  if equity>peak:peak=equity;peak_at=date
  if peak-equity>dd:dd=peak-equity;dd_start=peak_at;dd_end=date
  if pnl<0:current_run+=1;worst_run=max(worst_run,current_run)
  else:current_run=0
 z=dict(id=f"T{k[0]}|{k[1]}|{k[2]}|{k[3]}",horizon_hours=k[0],family=k[1],structure=k[2],direction=k[3],
        overall=stats([r[3] for r in rows]),years=byyear,months=monthly,
        max_drawdown_U=round(dd,3),drawdown_from=dd_start,drawdown_to=dd_end,max_consecutive_loss_orders=worst_run,
        unique_fids=len({r[1] for r in rows}))
 assert z["overall"]["n"]==a["discovery"]["n"],(k,z["overall"],a["discovery"])
 assert abs(z["overall"]["net_U"]-a["discovery"]["net_U"])<.0001,(k,z["overall"],a["discovery"])
 for y in byyear:
  assert byyear[y]["n"]==a["years"][y]["n"],(k,y)
  assert abs(byyear[y]["net_U"]-a["years"][y]["net_U"])<.0001,(k,y)
 assert sum(x["n"] for x in monthly.values())==z["overall"]["n"]
 out["candidates"].append(z)
out["candidates"].sort(key=lambda z:z["overall"]["net_U"],reverse=True)
out["audit"]=dict(candidate_count=len(out["candidates"]),all_candidate_years_reconciled_to_R1=True,monthly_counts_reconciled=True,
                   unique_all_fids=len(set.union(*fid_year.values())))
(ROOT/"five_year_review_r7_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (ROOT/"five_year_review_r7_monthly.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["candidate","year_month","n","net_U","roi_pct"])
 for z in out["candidates"]:
  for month,v in z["months"].items():w.writerow([z["id"],month,v["n"],v["net_U"],v["roi_pct"]])
print("AUDIT",out["audit"],"FIXTURES",out["year_unique_fixtures"])
for z in out["candidates"]:
 print(z["id"],"ALL",z["overall"],"YEARS",[(y,z["years"][y]) for y in map(str,range(2019,2024))],"MDD",z["max_drawdown_U"],"LOSS_STREAK",z["max_consecutive_loss_orders"])
