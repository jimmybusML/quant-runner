#!/usr/bin/env python3
"""R17 research-only: audit 749 uncovered fixtures and search incremental structures."""
import collections,datetime as dt,json,runpy,csv
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"coverage_494_r16.py"))
prev=runpy.run_path(str(P/"uncovered_r17.py"))
uncovered=(r["all_fids"]-r["union"])-prev["hit"];assert len(uncovered)==638
src=r["src"]
def b(v,edges):return sum(v>=e for e in edges)
families=[("line_side_signed",),("price_side_bias",),("price_gap_extreme",),
 ("line_side_signed","price_side_bias"),("line_side_signed","quote_age"),
 ("price_side_bias","move_signed_fine"),("price_gap_extreme","line_exact"),
 ("price_gap_extreme","quote_age"),("line_side_signed","price_gap_extreme"),
 ("line_side_signed","side_price_mid"),("price_side_bias","quote_age"),
 ("line_side_signed","price_side_bias","move_signed_fine")]

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
   base_side=dict(base,line_side_signed=b(line if side=="home" else -line,[-2,-1,-.5,-.125,.125,.5,1,2]),
     price_side_bias=b((home-away) if side=="home" else (away-home),[-.2,-.1,-.03,.03,.1,.2]),
     price_gap_extreme=b(abs(home-away),[.01,.03,.07,.12,.22,.4]))
   fs=dict(base_side,side_price_mid=b(home if side=="home" else away,[1.7,1.8,1.9,2,2.1,2.2]))
   pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
   for family in families:
    key=f"T{h}|{','.join(family)}|{';'.join(f'{k}={fs[k]}' for k in family)}|{direction}"
    yield key,y,date,fid,side,pnl

counts=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.]))
uncovered_matches=collections.defaultdict(set)
rows=collections.defaultdict(list)
for key,y,date,fid,side,pnl in iterate():
 v=counts[key][y];v[0]+=1;v[1]+=pnl
 if fid in uncovered:uncovered_matches[key].add(fid)
survivors={key for key,v in counts.items() if all(v[str(y)][0]>0 and v[str(y)][1]>0 for y in range(2019,2024))}
incremental={key:uncovered_matches[key] for key in survivors if uncovered_matches[key]}
for key,y,date,fid,side,pnl in iterate():
 if key in incremental:rows[key].append((date,fid,side,pnl))
hit=set().union(*incremental.values()) if incremental else set()
results=[]
for key,rr in rows.items():
 rr.sort()
 annual={y:dict(n=counts[key][y][0],net_U=round(counts[key][y][1],3)) for y in map(str,range(2019,2024))}
 newrows=[x for x in rr if x[1] in uncovered]
 n=len(rr);net=round(sum(x[3] for x in rr),3)
 # For each structure, distinguish all-hit historical PnL from the newly covered subset's actual historical PnL
 eq=peak=mdd=0
 for date,fid,side,pnl in rr:
  eq+=pnl;peak=max(peak,eq);mdd=max(mdd,peak-eq)
 results.append(dict(id=key,incremental_fixtures=len(incremental[key]),overall_n=n,overall_net_U=net,roi_pct=round(100*net/n,4),
  incremental_n=len(newrows),incremental_net_U=round(sum(x[3] for x in newrows),3),
  incremental_roi_pct=round(100*sum(x[3] for x in newrows)/len(newrows),4) if newrows else None,
  max_drawdown_U=round(mdd,3),annual=annual))
results.sort(key=lambda x:(-x["incremental_fixtures"],-x["overall_net_U"]))
out=dict(scope="2019-2023 Crown AH research only",previous_covered=14324,previous_uncovered=638,
 searched_definitions=len(counts),positive_each_year=len(survivors),touching_uncovered=len(incremental),
 added_unique_fixtures=len(hit),remaining_uncovered=638-len(hit),new_total_covered=14324+len(hit),
 new_coverage_pct=round(100*(14324+len(hit))/14962,4),
 warning="Incremental ROI per structure includes only fixtures previously uncovered by R7-R17; these subsets overlap. No combined portfolio ROI implied.",
 candidates=results)
(P/"uncovered_r18_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (P/"uncovered_r18_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","new_unique","all_n","all_net_U","all_roi_pct","new_n","new_net_U","new_roi_pct","max_drawdown_U"]+[f"{y}_U" for y in range(2019,2024)])
 for z in results:w.writerow([z["id"],z["incremental_fixtures"],z["overall_n"],z["overall_net_U"],z["roi_pct"],z["incremental_n"],z["incremental_net_U"],z["incremental_roi_pct"],z["max_drawdown_U"]]+[z["annual"][str(y)]["net_U"] for y in range(2019,2024)])
print("R18",json.dumps({k:v for k,v in out.items() if k!="candidates"},ensure_ascii=False),flush=True)
for z in results[:12]:print("TOP",z,flush=True)
