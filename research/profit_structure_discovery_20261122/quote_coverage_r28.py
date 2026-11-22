#!/usr/bin/env python3
"""R28: same frozen 494 candidates, same earliest/equal-net portfolio, 2019-23 vs 2024 quote coverage."""
import collections,json,runpy,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
train=runpy.run_path(str(P/"weight_conflict_r20.py"))
test=runpy.run_path(str(P/"forward_2024_r24.py"))
def build(groups):
 fids=collections.defaultdict(list)
 for k in groups:fids[k[:2]].append(k)
 out={}
 for fid,ks in fids.items():
  k=max(ks,key=lambda x:x[2]);s=groups[k]
  nh=len(s["home"]);na=len(s["away"])
  if nh==na:continue
  side="home" if nh>na else "away"
  out[k]=dict(pnl=s[side][0][1],side=side,conflict=bool(nh and na),votes=abs(nh-na))
 return out
tr=build(train["groups"]);te=build(test["groups"])
def read_features(rows,years):
 for raw in train["SRC"].open():
  a=json.loads(raw)
  if a.get("market")!="AH" or str(a.get("year")) not in years:continue
  k=(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]))
  if k not in rows:continue
  z=rows[k]
  first=a.get("first_available_quote") or {}
  ref=a.get("same_line_reference_quote") or {}
  z.update(ticks=int(a.get("window_ticks_available") or 0),
   line=abs(float(a["line"])),odds=float(a["odds"][z["side"]]),
   movement=abs(float(a.get("line_delta_since_first_quote") or 0)),
   quote_time=a["quote_time_utc"],first_time=first.get("time"),
   reference_time=ref.get("time"),hours=float(a["actual_hours_before_kickoff"]),
   year=str(a["year"]),horizon=k[2])
read_features(tr,set(map(str,range(2019,2024))))
read_features(te,{"2024"})
assert all("ticks" in z for z in tr.values()) and all("ticks" in z for z in te.values())
def band(z,field):
 if field=="ticks":return "1" if z["ticks"]==1 else "2" if z["ticks"]==2 else "3-5" if z["ticks"]<=5 else "6+"
 if field=="line":return "0" if z["line"]==0 else "0.25-0.75" if z["line"]<=.75 else "1-1.75" if z["line"]<=1.75 else "2+"
 if field=="horizon":return "T"+str(z["horizon"])
 if field=="movement":return "0" if z["movement"]==0 else "<=0.25" if z["movement"]<=.25 else "<=0.75" if z["movement"]<=.75 else ">0.75"
 if field=="conflict":return "yes" if z["conflict"] else "no"
 if field=="odds":return "<1.8" if z["odds"]<1.8 else "1.8-1.9" if z["odds"]<1.9 else "1.9-2.0" if z["odds"]<2 else "2.0-2.1" if z["odds"]<2.1 else "2.1+"
def stats(zs):
 n=len(zs);p=sum(z["pnl"] for z in zs)
 return dict(n=n,net_U=round(p,3),roi_pct=round(100*p/n,4) if n else None,
 pct_timestamps_identical=round(100*sum(z["first_time"]==z["quote_time"] for z in zs)/n,3) if n else None,
 pct_zero_movement=round(100*sum(z["movement"]==0 for z in zs)/n,3) if n else None)
def aggregate(rows,fields):
 d=collections.defaultdict(list)
 for z in rows.values():d["|".join(band(z,f) for f in fields)].append(z)
 return {k:stats(v) for k,v in sorted(d.items())}
fields=[["ticks"],["line"],["horizon"],["movement"],["conflict"],["odds"],["ticks","line"],["ticks","horizon"],["ticks","movement"]]
res={}
for f in fields:
 name=" × ".join(f);a=aggregate(tr,f);b=aggregate(te,f)
 res[name]={k:dict(train=a.get(k),test=b.get(k)) for k in sorted(set(a)|set(b))}
# Separate training-year baseline for consistent 2019-23 historical comparison.
years={}
for y in range(2019,2025):
 v=[z for z in (te if y==2024 else tr).values() if z["year"]==str(y)]
 years[str(y)]=stats(v)
out=dict(scope="Frozen 494 candidate earliest equal-net 1U per fixture; 2019-23 vs 2024",
 years=years,overall=dict(train=stats(list(tr.values())),test=stats(list(te.values()))),
 groups=res,
 caveats=["All groupings are descriptive and not new rules.",
 "2019-2023 candidates were selected on their full historical outcomes; training group results are selection-biased.",
 "2024 tick count groups were noticed after seeing 2024 returns; positive groups are not independent strategy validation.",
 "The window_ticks_available count may reflect retrospective collection density, not actual 2024 live quote availability.",
 "Retrospectively collected Crown event timestamps are not proof of executable historical prices.",
 "No 2025-2026, M8, Telegram or production changes."])
(P/"QUOTE_COVERAGE_R28.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("YEARS",years,flush=True)
for k in ("ticks","line","movement","ticks × line","ticks × horizon","ticks × movement"):
 print("GROUP",k,res[k],flush=True)
