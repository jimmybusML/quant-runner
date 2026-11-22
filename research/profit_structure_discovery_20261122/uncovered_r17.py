#!/usr/bin/env python3
"""R17 research-only: audit 749 uncovered fixtures and search incremental structures."""
import collections,datetime as dt,json,runpy,csv
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"coverage_494_r16.py"))
uncovered=r["all_fids"]-r["union"];assert len(uncovered)==749
src=r["src"]
def b(v,edges):return sum(v>=e for e in edges)
families=[("line_exact",),("price_neutral",),("move_signed_fine",),("side_price_mid",),
 ("line_exact","price_neutral"),("line_exact","move_signed_fine"),
 ("price_neutral","move_signed_fine"),("line_exact","side_price_mid"),
 ("side_price_mid","move_signed_fine"),("price_neutral","quote_age"),
 ("line_exact","quote_age"),("line_exact","side_price_mid","move_signed_fine")]
def iterate():
 for raw in src.open():
  a=json.loads(raw)
  if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
  h=int(a["entry_horizon_hours"]);fid=str(a["fixture_id"]);y=str(a["year"]);date=a["kickoff_utc"]
  line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
  d=float(a.get("line_delta_since_first_quote") or 0)
  hg,ag=map(int,a["score"].split("-"))
  fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
  dirs=dict(home="home",away="away",favorite=fav,underdog="away" if fav=="home" else "home")
  base=dict(line_exact=b(abs(line),[.125,.25,.5,.75,1,1.5,2,3]),
   price_neutral=b(abs(home-away),[.005,.015,.035,.075,.15,.3]),
   move_signed_fine=b(d,[-.75,-.375,-.125,-.000001,.000001,.125,.375,.75]),
   quote_age=b(float(a["actual_hours_before_kickoff"])-h,[.25,1,3,8]))
  for direction,side in dirs.items():
   fs=dict(base,side_price_mid=b(home if side=="home" else away,[1.7,1.8,1.9,2,2.1,2.2]))
   pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
   for family in families:
    key=f"T{h}|{','.join(family)}|{';'.join(f'{k}={fs[k]}' for k in family)}|{direction}"
    yield key,y,date,fid,side,pnl
counts=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.]))
uncovered_matches=collections.defaultdict(set)
for key,y,date,fid,side,pnl in iterate():
 v=counts[key][y];v[0]+=1;v[1]+=pnl
 if fid in uncovered:uncovered_matches[key].add(fid)
survivors={key for key,v in counts.items() if all(v[str(y)][0]>0 and v[str(y)][1]>0 for y in range(2019,2024))}
incremental={key:uncovered_matches[key] for key in survivors if uncovered_matches[key]}
hit=set().union(*incremental.values()) if incremental else set()
# summarize all candidates that reach previously uncovered matches
ranked=sorted(incremental,key=lambda k:(-len(incremental[k]),-sum(counts[k][y][1] for y in map(str,range(2019,2024))),k))
result=[]
for key in ranked:
 yrs={y:dict(n=counts[key][y][0],net_U=round(counts[key][y][1],3)) for y in map(str,range(2019,2024))}
 n=sum(v["n"] for v in yrs.values());profit=round(sum(v["net_U"] for v in yrs.values()),3)
 result.append(dict(id=key,new_uncovered_fixtures=len(incremental[key]),overall_n=n,overall_net_U=profit,roi_pct=round(profit/n*100,4),years=yrs))
# compare baseline coverage at each horizon and reasons for uncovered: descriptive only
base_byyear=collections.Counter();base_horizon=collections.Counter();uncovered_horizon=collections.Counter()
for raw in src.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
 fid=str(a["fixture_id"])
 if fid in uncovered:
  base_byyear[str(a["year"])]+=1
  uncovered_horizon[int(a["entry_horizon_hours"])]+=1
 base_horizon[int(a["entry_horizon_hours"])]+=1
out=dict(scope="2019-2023 Crown AH",baseline_total=14962,baseline_covered=14213,baseline_uncovered=749,
 searched_definitions=len(counts),positive_each_year=len(survivors),positive_structures_touching_uncovered=len(incremental),
 newly_covered=len(hit),remaining_uncovered=749-len(hit),coverage_after_pct=round((14213+len(hit))/14962*100,4),
 by_year_uncovered_rows=dict(base_byyear),uncovered_horizon_rows=dict(uncovered_horizon),all_horizon_rows=dict(base_horizon),
 candidates=result,limitations="In-sample selected positive five-year strategies, not independent OOS. Overlapping signals are not unique executable orders. No new production rules.")
(P/"uncovered_r17_results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
with (P/"uncovered_r17_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","new_fixtures","n","net_U","ROI"]+[f"{y}_net_U" for y in range(2019,2024)])
 for z in result:w.writerow([z["id"],z["new_uncovered_fixtures"],z["overall_n"],z["overall_net_U"],z["roi_pct"]]+[z["years"][str(y)]["net_U"] for y in range(2019,2024)])
print("R17",json.dumps({k:v for k,v in out.items() if k!="candidates"},ensure_ascii=False))
for z in result[:12]:print("TOP",z)
