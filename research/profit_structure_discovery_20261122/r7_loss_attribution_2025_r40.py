#!/usr/bin/env python3
"""R40 descriptive attribution of 2025 R7 27 loss; no new selection."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"all_structures_2025_r39.py"))
groups=r["groups"];r7=r["sets"]["original_batch_R7"]
source=r["SRC"]
INV=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_T30_2h_movement_inventory_20261114.jsonl")
def stat(v):
 n=len(v);u=sum(x["pnl"] for x in v)
 return dict(n=n,net_U=round(u,4),roi_pct=round(100*u/n,4) if n else None)
fi=collections.defaultdict(list)
for k,sides in groups.items():
 home=[c for c,p in sides["home"] if c in r7]
 away=[c for c,p in sides["away"] if c in r7]
 if home or away:fi[k[:2]].append((k,home,away,sides))
orders={}
for fixture,ks in fi.items():
 k,home,away,sides=max(ks,key=lambda x:x[0][2])
 if len(home)==len(away):continue
 side="home" if len(home)>len(away) else "away"
 pnl=next(p for c,p in sides[side] if c in r7)
 orders[k]=dict(year="2025",month=k[0][:7],horizon=k[2],side=side,pnl=pnl,
  selected_ids=sorted(home if side=="home" else away),
  opposing_ids=sorted(away if side=="home" else home),conflict=bool(home and away))
assert stat(orders.values())["n"]==1694
lookup={}
for raw in INV.open():
 a=json.loads(raw)
 if str(a.get("year",a["kickoff_utc"][:4]))!="2025":continue
 lookup[(a["kickoff_utc"],str(a["fixture_id"]))]=str(a["league_id"])
missing=[]
for k,z in orders.items():
 if k[:2] not in lookup:missing.append(k)
 else:z["league_id"]=lookup[k[:2]]
quote={}
for raw in source.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a.get("year"))!="2025":continue
 k=(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]))
 if k not in orders:continue
 z=orders[k];z.update(ticks=int(a.get("window_ticks_available") or 0),
  abs_line=abs(float(a["line"])),odds=float(a["odds"][z["side"]]),
  quote_age_hours=float(a["actual_hours_before_kickoff"])-int(a["entry_horizon_hours"]),
  line_move=abs(float(a.get("line_delta_since_first_quote") or 0)))
 quote[k]=True
assert len(quote)==len(orders)
def bucket(z,f):
 if f=="month":return z["month"]
 if f=="horizon":return "T"+str(z["horizon"])
 if f=="side":return z["side"]
 if f=="league":return z.get("league_id","unmapped")
 if f=="ticks":return "1" if z["ticks"]==1 else "2" if z["ticks"]==2 else "3-5" if z["ticks"]<=5 else "6+"
 if f=="line":return "0" if z["abs_line"]==0 else "0.25-0.75" if z["abs_line"]<=.75 else "1-1.75" if z["abs_line"]<=1.75 else "2+"
 if f=="odds":return "<1.8" if z["odds"]<1.8 else "1.8-1.9" if z["odds"]<1.9 else "1.9-2" if z["odds"]<2 else "2-2.1" if z["odds"]<2.1 else "2.1+"
 if f=="quote_age":return "<0.5h" if z["quote_age_hours"]<.5 else "0.5-2h" if z["quote_age_hours"]<2 else "2-6h" if z["quote_age_hours"]<6 else "6h+"
 if f=="line_move":return "0" if z["line_move"]==0 else "<=0.25" if z["line_move"]<=.25 else ">0.25"
 if f=="conflict":return "opposed" if z["conflict"] else "single-side"
 if f=="votes":return "1" if len(z["selected_ids"])==1 else "2" if len(z["selected_ids"])==2 else "3+"
def split(f):
 b=collections.defaultdict(list)
 for z in orders.values():b[bucket(z,f)].append(z)
 return {k:stat(v) for k,v in sorted(b.items())}
candidates={}
for cid in sorted(r7):
 selected=[z for z in orders.values() if cid in z["selected_ids"]]
 opposed=[z for z in orders.values() if cid in z["opposing_ids"]]
 candidates[cid]=dict(selected_portfolio_orders=stat(selected),opposed_portfolio_orders=stat(opposed),
  individual_2025=next(x for x in json.loads((P/"ALL_STRUCTURES_2025_R39.json").read_text())["individual_candidates"] if x["id"]==cid))
out=dict(scope="R40 original R7 27 2025 loss descriptive attribution; same 1694 fixture-dedup orders as R39",
 mapping=dict(orders=len(orders),league_mapped=len(orders)-len(missing),league_unmapped=len(missing),quote_mapped=len(quote)),
 total=stat(orders.values()),dimensions={f:split(f) for f in ("month","horizon","side","league","ticks","line","odds","quote_age","line_move","conflict","votes")},
 candidate_participation=candidates,
 caveats=["Each dimension is an independent accounting split of the SAME 1694 orders; do not add across dimensions.",
 "Candidate participation overlaps on the same selected portfolio orders; sum of candidate contribution is not portfolio net.",
 "League IDs from original Crown historical inventory; names unavailable, do not invent.",
 "2025 historical quote events were retrospectively received in 2026, not proven executable.",
 "2025 has now been inspected; positive slices cannot be called independent forward validation or converted to strategy rules.",
 "No candidate or portfolio change; no 2026 inspection or production changes."])
(P/"R7_LOSS_ATTRIBUTION_2025_R40.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R40 SUMMARY",json.dumps(dict(mapping=out["mapping"],total=out["total"],dimensions={k:v for k,v in out["dimensions"].items() if k in ("month","horizon","ticks","conflict")}),ensure_ascii=False),flush=True)
