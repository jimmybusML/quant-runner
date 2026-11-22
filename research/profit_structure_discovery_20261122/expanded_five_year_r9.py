#!/usr/bin/env python3
"""Expand candidate vocabulary beyond R1, 2019-2023 only; full candidate audit.
Feature bins are exploratory, not production conditions.
"""
import collections,csv,datetime as dt,json
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
old=json.load(open(P/"five_year_review_r7_results.json"))
oldids={z["id"] for z in old["candidates"]}
families=[("signed_line",),("side_price",),("prob_delta",),("side_price","signed_line"),
 ("side_price","momentum"),("side_price","prob_delta"),("signed_line","prob_delta"),
 ("line","prob_delta"),("momentum","prob_delta"),("age","prob_delta"),
 ("line","side_price","prob_delta"),("side_price","momentum","prob_delta")]
def b(v,edges):return sum(v>=e for e in edges)
def iterate():
 for raw in SRC.open():
  a=json.loads(raw)
  if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
  h=int(a["entry_horizon_hours"]);fid=str(a["fixture_id"]);year=str(a["year"])
  line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
  hg,ag=map(int,a["score"].split("-"))
  fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
  side_map={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
  base=dict(signed_line=b(line,[-2,-1,-.25,.25,1,2]),line=b(abs(line),[.25,.75,1.25,2.25]),
    momentum=b(float(a.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5]),
    age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]),
    prob_delta=b(float(a.get("same_line_no_vig_probability_delta_side1") or 0),[-.02,-.005,.005,.02]))
  for direction,side in side_map.items():
   fs=dict(base,side_price=b(home if side=="home" else away,[1.8,1.9,2.,2.1]))
   pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
   for family in families:
    key=f"T{h}|{','.join(family)}|{';'.join(f'{k}={fs[k]}' for k in family)}|{direction}"
    yield key,year,a["kickoff_utc"],fid,side,pnl
counts=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.]))
for key,year,date,fid,side,pnl in iterate():
 x=counts[key][year];x[0]+=1;x[1]+=pnl
survivors={key for key,v in counts.items() if all(v[str(y)][0]>0 and v[str(y)][1]>1e-9 for y in range(2019,2024))}
# Keep all survivors, including low-sample ones. No gate.
rows=collections.defaultdict(list)
for key,year,date,fid,side,pnl in iterate():
 if key in survivors:rows[key].append((date,fid,side,pnl))
def stat(v):
 return dict(n=len(v),net_U=round(sum(v),3),roi_pct=round(100*sum(v)/len(v),4) if v else None)
result=[]
for key,rr in rows.items():
 rr.sort(key=lambda x:(x[0],x[1]));yearly={str(y):stat([x[3] for x in rr if x[0][:4]==str(y)]) for y in range(2019,2024)}
 monthly={f"{y}-{m:02}":stat([x[3] for x in rr if x[0][:7]==f"{y}-{m:02}"]) for y in range(2019,2024) for m in range(1,13)}
 eq=peak=dd=0.;start="initial";ddstart=ddend=None
 for date,fid,side,pnl in rr:
  eq+=pnl
  if eq>peak:peak=eq;start=date
  if peak-eq>dd:dd=peak-eq;ddstart=start;ddend=date
 result.append(dict(id=key,overall=stat([x[3] for x in rr]),years=yearly,months=monthly,max_drawdown_U=round(dd,3),drawdown_from=ddstart,drawdown_to=ddend,unique_fids=len({x[1] for x in rr})))
result.sort(key=lambda x:x["overall"]["net_U"],reverse=True)
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),scope="2019-2023 only",
 source=str(SRC),families=[list(x) for x in families],
 audit=dict(all_new_vocabulary_candidates=len(counts),five_year_positive_candidates=len(survivors),
            preexisting_R7_ids=len(oldids),new_candidate_ids=len(survivors-oldids),all_months_checked=True),
 candidates=result,provenance="2026 retrospective Crown quote event timestamps; not contemporaneous executable odds")
assert len(result)==len(survivors)
for z in result:
 key=z["id"]
 for y in map(str,range(2019,2024)):
  assert z["years"][y]["n"]==counts[key][y][0]
  assert abs(z["years"][y]["net_U"]-counts[key][y][1])<.0001
 assert sum(x["n"] for x in z["months"].values())==z["overall"]["n"]
(P/"expanded_five_year_r9_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (P/"expanded_five_year_r9_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","five_year_n","five_year_net_U","five_year_roi_pct","max_drawdown_U"]+[f"{y}_n,{y}_net_U,{y}_roi_pct" for y in range(2019,2024)])
 for z in result:w.writerow([z["id"],z["overall"]["n"],z["overall"]["net_U"],z["overall"]["roi_pct"],z["max_drawdown_U"]]+[str(z["years"][str(y)]["n"])+","+str(z["years"][str(y)]["net_U"])+","+str(z["years"][str(y)]["roi_pct"]) for y in range(2019,2024)])
print("AUDIT",out["audit"])
for z in result[:15]:print(z["id"],z["overall"],"MDD",z["max_drawdown_U"],"YEARS",[(y,z["years"][str(y)]["net_U"]) for y in range(2019,2024)])
