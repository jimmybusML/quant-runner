#!/usr/bin/env python3
"""R10: 2019-2023 only, 88 candidate definitions, unique fixture combination audit.
All variants exploratory, not production conditions.
"""
import collections,csv,datetime as dt,json
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
old=json.load(open(P/"five_year_review_r7_results.json"))["candidates"]
new=json.load(open(P/"expanded_five_year_r9_results.json"))["candidates"]
expected={z["id"]:z for z in old+new}
assert len(expected)==88
src=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
def b(v,edges):return sum(v>=e for e in edges)
signals=collections.defaultdict(list);counts=collections.Counter();profits=collections.defaultdict(float)
for raw in src.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
 h=int(a["entry_horizon_hours"]);fid=str(a["fixture_id"]);date=a["kickoff_utc"]
 line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
 hg,ag=map(int,a["score"].split("-"))
 fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
 directions=dict(home="home",away="away",favorite=fav,underdog="away" if fav=="home" else "home")
 base=dict(line=b(abs(line),[.25,.75,1.25,2.25]),price=b(home,[1.8,1.9,2.,2.1]),
  momentum=b(float(a.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5]),
  age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]),
  signed_line=b(line,[-2,-1,-.25,.25,1,2]),
  prob_delta=b(float(a.get("same_line_no_vig_probability_delta_side1") or 0),[-.02,-.005,.005,.02]))
 for direction,side in directions.items():
  fs=dict(base,side_price=b(home if side=="home" else away,[1.8,1.9,2.,2.1]))
  pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
  for family in [("line",),("price",),("momentum",),("age",),("line","price"),("line","momentum"),("price","momentum"),("line","age"),("momentum","age"),("line","price","momentum"),
   ("signed_line",),("side_price",),("prob_delta",),("side_price","signed_line"),("side_price","momentum"),("side_price","prob_delta"),("signed_line","prob_delta"),("line","prob_delta"),("momentum","prob_delta"),("age","prob_delta"),("line","side_price","prob_delta"),("side_price","momentum","prob_delta")]:
   key=f"T{h}|{','.join(family)}|{';'.join(f'{k}={fs[k]}' for k in family)}|{direction}"
   if key in expected:
    signals[fid].append(dict(id=key,h=h,date=date,side=side,pnl=pnl,source="R7" if key in {z["id"] for z in old} else "R9"))
    counts[key]+=1;profits[key]+=pnl
for key,z in expected.items():
 assert counts[key]==z["overall"]["n"],(key,counts[key],z["overall"])
 assert abs(profits[key]-z["overall"]["net_U"])<.0001,(key,profits[key],z["overall"])
def stats(v):
 n=len(v);s=sum(v)
 return dict(n=n,net_U=round(s,3),roi_pct=round(100*s/n,4) if n else None)
def summarize(vals):
 vals.sort(key=lambda x:(x[0],x[2]))
 eq=peak=dd=0.;start="initial";ds=de=None
 byyear=collections.defaultdict(list);bymonth=collections.defaultdict(list)
 for date,pnl,fid in vals:
  eq+=pnl
  if eq>peak:peak=eq;start=date
  if peak-eq>dd:dd=peak-eq;ds=start;de=date
  byyear[date[:4]].append(pnl);bymonth[date[:7]].append(pnl)
 return dict(overall=stats([v for _,v,_ in vals]),years={str(y):stats(byyear[str(y)]) for y in range(2019,2024)},
 months={f"{y}-{m:02}":stats(bymonth[f"{y}-{m:02}"]) for y in range(2019,2024) for m in range(1,13)},
 max_drawdown_U=round(dd,3),drawdown_from=ds,drawdown_to=de,
 profitable_months=sum(sum(v)>0 for v in bymonth.values()),losing_months=sum(sum(v)<0 for v in bymonth.values()))
port=collections.defaultdict(list);pair=collections.defaultdict(lambda:collections.Counter());audit=collections.Counter()
for fid,ss in signals.items():
 ss.sort(key=lambda x:(-x["h"],x["id"]))
 date=ss[0]["date"];audit["unique_fids"]+=1;audit["signal_hits"]+=len(ss)
 if len(ss)>1:audit["multi_signal_fids"]+=1
 sides={x["side"] for x in ss}
 if len(sides)>1:audit["conflict_fids"]+=1
 if any(x["source"]=="R7" for x in ss) and any(x["source"]=="R9" for x in ss):audit["old_new_overlap_fids"]+=1
 for i,x in enumerate(ss):
  for y in ss[i+1:]:
   key=tuple(sorted((x["id"],y["id"])));pair[key]["shared"]+=1
   pair[key]["same" if x["side"]==y["side"] else "opposite"]+=1
 first=ss[0]
 port["earliest_one"].append((date,first["pnl"],fid))
 port["equal_fractional"].append((date,sum(x["pnl"] for x in ss)/len(ss),fid))
 if len(sides)==1:port["unanimous_only"].append((date,first["pnl"],fid))
 vote=collections.Counter(x["side"] for x in ss)
 if vote["home"]!=vote["away"]:
  chosen=next(x for x in ss if x["side"]==max(vote,key=vote.get))
  port["majority_vote"].append((date,chosen["pnl"],fid))
 else:audit["tied_vote_fids"]+=1
 # R7-only and R9-only comparisons on same original fixtures, unique per set
 for source,label in [("R7","old27_only"),("R9","new61_only")]:
  group=[x for x in ss if x["source"]==source]
  if group:port[label].append((date,group[0]["pnl"],fid))
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),scope="2019-2023 only",source=str(src),
 provenance="Retrospective 2026 retrieval of historical Crown event timestamps, not contemporaneously received prices",
 audit=dict(audit),portfolios={name:summarize(v) for name,v in port.items()},
 pairwise=[dict(candidate_a=a,candidate_b=b,shared=v["shared"],same=v["same"],opposite=v["opposite"]) for (a,b),v in pair.items()])
out["pairwise"].sort(key=lambda x:-x["shared"])
out["audit"]["pairwise_overlap_pairs"]=len(out["pairwise"])
for name,z in out["portfolios"].items():
 assert z["overall"]["n"]==sum(x["n"] for x in z["years"].values())
 assert z["overall"]["n"]==sum(x["n"] for x in z["months"].values())
 assert abs(z["overall"]["net_U"]-sum(x["net_U"] for x in z["years"].values()))<.003
assert out["portfolios"]["earliest_one"]["overall"]["n"]==out["audit"]["unique_fids"]
assert out["portfolios"]["unanimous_only"]["overall"]["n"]==out["audit"]["unique_fids"]-out["audit"]["conflict_fids"]
assert out["portfolios"]["majority_vote"]["overall"]["n"]==out["audit"]["unique_fids"]-out["audit"]["tied_vote_fids"]
(P/"combined_88_r10_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (P/"combined_88_r10_pairwise.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["candidate_a","candidate_b","shared","same","opposite"]);w.writeheader();w.writerows(out["pairwise"])
with (P/"combined_88_r10_monthly.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["portfolio","month","n","net_U","roi_pct"])
 for name,z in out["portfolios"].items():
  for month,v in z["months"].items():w.writerow([name,month,v["n"],v["net_U"],v["roi_pct"]])
print("AUDIT",out["audit"])
for name,z in out["portfolios"].items():print(name,z["overall"],"MDD",z["max_drawdown_U"],"YEARS",[(y,z["years"][str(y)]["net_U"]) for y in range(2019,2024)])
print("TOP PAIRS",out["pairwise"][:5])
