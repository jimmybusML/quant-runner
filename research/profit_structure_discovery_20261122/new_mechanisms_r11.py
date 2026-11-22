#!/usr/bin/env python3
"""R11 fresh structure vocabulary, 2019-23 only; no production changes."""
import collections,json,csv,datetime as dt
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
FAMILIES=[("line_delta_sign",),("prob_sign",),("odds_spread",),("line_delta_sign","side_price"),("prob_sign","side_price"),("odds_spread","line"),
 ("odds_spread","prob_sign"),("signed_line","prob_sign"),("line","line_delta_sign"),("side_price","odds_spread"),
 ("prob_sign","line_delta_sign"),("odds_spread","momentum"),("signed_line","odds_spread"),
 ("line","prob_sign","odds_spread"),("side_price","prob_sign","line_delta_sign")]
def b(v,edges):return sum(v>=e for e in edges)
def gen():
 for raw in SRC.open():
  a=json.loads(raw)
  if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
  h=int(a["entry_horizon_hours"]);year=str(a["year"]);date=a["kickoff_utc"];fid=str(a["fixture_id"])
  line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"]);hg,ag=map(int,a["score"].split("-"))
  fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
  sides=dict(home="home",away="away",favorite=fav,underdog="away" if fav=="home" else "home")
  d=float(a.get("line_delta_since_first_quote") or 0);pr=float(a.get("same_line_no_vig_probability_delta_side1") or 0)
  f=dict(line=b(abs(line),[.25,.75,1.25,2.25]),signed_line=b(line,[-2,-1,-.25,.25,1,2]),
    momentum=b(d,[-.5,-.125,.125,.5]),line_delta_sign=b(d,[-.000001,.000001]),
    prob_sign=b(pr,[-.000001,.000001]),odds_spread=b(abs(home-away),[.02,.05,.1,.2]))
  for direction,side in sides.items():
   ff=dict(f,side_price=b(home if side=="home" else away,[1.8,1.9,2,2.1]))
   pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
   for family in FAMILIES:
    key=f"T{h}|{','.join(family)}|{';'.join(f'{k}={ff[k]}' for k in family)}|{direction}"
    yield key,year,date,fid,pnl
counts=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.]))
for key,year,date,fid,pnl in gen():
 v=counts[key][year];v[0]+=1;v[1]+=pnl
survivors={key for key,v in counts.items() if all(v[str(y)][0]>0 and v[str(y)][1]>0 for y in range(2019,2024))}
rows=collections.defaultdict(list)
for key,year,date,fid,pnl in gen():
 if key in survivors:rows[key].append((date,fid,pnl))
def stats(v):
 return dict(n=len(v),net_U=round(sum(v),3),roi_pct=round(100*sum(v)/len(v),4) if v else None)
results=[]
for key,rr in rows.items():
 rr.sort(key=lambda x:(x[0],x[1]))
 years={str(y):stats([x[2] for x in rr if x[0][:4]==str(y)]) for y in range(2019,2024)}
 months={f"{y}-{m:02}":stats([x[2] for x in rr if x[0][:7]==f"{y}-{m:02}"]) for y in range(2019,2024) for m in range(1,13)}
 eq=peak=dd=0.;at="initial";ds=de=None
 for date,fid,pnl in rr:
  eq+=pnl
  if eq>peak:peak=eq;at=date
  if peak-eq>dd:dd=peak-eq;ds=at;de=date
 assert all(years[str(y)]["n"]==counts[key][str(y)][0] and abs(years[str(y)]["net_U"]-counts[key][str(y)][1])<.0001 for y in range(2019,2024))
 assert sum(v["n"] for v in months.values())==len(rr)
 results.append(dict(id=key,overall=stats([x[2] for x in rr]),years=years,months=months,max_drawdown_U=round(dd,3),drawdown_from=ds,drawdown_to=de,unique_fids=len({x[1] for x in rr})))
results.sort(key=lambda x:x["overall"]["net_U"],reverse=True)
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),scope="2019-2023 only",
 audit=dict(all_candidate_definitions=len(counts),positive_every_year=len(results)),families=[list(x) for x in FAMILIES],candidates=results,
 limitations="Same 2019-2023 used to select and evaluate; in-sample multiple testing. Historical Crown quote events retrospectively collected 2026.")
(P/"new_mechanisms_r11_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (P/"new_mechanisms_r11_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","n","net_U","roi_pct","max_drawdown_U"]+[v for y in range(2019,2024) for v in (f"{y}_n",f"{y}_net_U",f"{y}_roi_pct")])
 for z in results:w.writerow([z["id"],z["overall"]["n"],z["overall"]["net_U"],z["overall"]["roi_pct"],z["max_drawdown_U"]]+[z["years"][str(y)][k] for y in range(2019,2024) for k in ("n","net_U","roi_pct")])
with (P/"new_mechanisms_r11_monthly.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","month","n","net_U","roi_pct"])
 for z in results:
  for m,v in z["months"].items():w.writerow([z["id"],m,v["n"],v["net_U"],v["roi_pct"]])
print("AUDIT",out["audit"])
for z in results[:12]:print(z["id"],z["overall"],"MDD",z["max_drawdown_U"],"YEARS",[(y,z["years"][str(y)]["net_U"]) for y in range(2019,2024)])
