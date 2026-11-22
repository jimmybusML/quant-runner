#!/usr/bin/env python3
"""R34 R7 2023->2024 mix-versus-within return decomposition; descriptive, not filters."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"r7_complementarity_r31.py"))
ids=r["r7"];train=r["train"];test=r["test"]
def portfolio(groups,year):
 fi=collections.defaultdict(list)
 for k,sides in groups.items():
  if k[0][:4]!=year:continue
  h=[(c,p) for c,p in sides["home"] if c in ids]
  a=[(c,p) for c,p in sides["away"] if c in ids]
  if h or a:fi[k[:2]].append((k,h,a))
 out={}
 for fixture,ks in fi.items():
  k,h,a=max(ks,key=lambda x:x[0][2])
  if len(h)==len(a):continue
  side="home" if len(h)>len(a) else "away"
  out[k]=dict(pnl=(h if side=="home" else a)[0][1],side=side,conflict=bool(h and a),votes=abs(len(h)-len(a)),year=year,horizon=k[2])
 return out
rows={**portfolio(train,"2023"),**portfolio(test,"2024")}
source=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
for line in source.open():
 a=json.loads(line)
 if a.get("market")!="AH" or str(a.get("year")) not in ("2023","2024"):continue
 k=(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]))
 if k not in rows:continue
 z=rows[k];z.update(ticks=int(a.get("window_ticks_available") or 0),
 line=abs(float(a["line"])),odds=float(a["odds"][z["side"]]),
 movement=abs(float(a.get("line_delta_since_first_quote") or 0)),
 hours=float(a["actual_hours_before_kickoff"]))
assert all("ticks" in z for z in rows.values()),"Missing ledger features"
def band(z,f):
 if f=="ticks":return "1" if z["ticks"]==1 else "2" if z["ticks"]==2 else "3-5" if z["ticks"]<=5 else "6+"
 if f=="line":return "0" if z["line"]==0 else "0.25-0.75" if z["line"]<=.75 else "1-1.75" if z["line"]<=1.75 else "2+"
 if f=="horizon":return "T"+str(z["horizon"])
 if f=="movement":return "0" if z["movement"]==0 else "<=0.25" if z["movement"]<=.25 else "<=0.75" if z["movement"]<=.75 else ">0.75"
 if f=="side":return z["side"]
 if f=="conflict":return "yes" if z["conflict"] else "no"
 if f=="odds":return "<1.8" if z["odds"]<1.8 else "1.8-1.9" if z["odds"]<1.9 else "1.9-2.0" if z["odds"]<2 else "2.0-2.1" if z["odds"]<2.1 else "2.1+"
def stat(v):
 n=len(v);p=sum(x["pnl"] for x in v)
 return dict(n=n,net_U=round(p,3),roi_pct=round(100*p/n,4) if n else None)
years={y:[z for z in rows.values() if z["year"]==y] for y in ("2023","2024")}
overall={y:stat(v) for y,v in years.items()}
groups={}
for dims in (("ticks",),("line",),("horizon",),("movement",),("side",),("conflict",),("odds",),("ticks","horizon"),("line","horizon"),("ticks","line")):
 buckets={y:collections.defaultdict(list) for y in years}
 for y,vals in years.items():
  for z in vals:buckets[y]["|".join(band(z,f) for f in dims)].append(z)
 keys=sorted(set(buckets["2023"])|set(buckets["2024"]))
 data={k:{y:stat(buckets[y][k]) for y in years} for k in keys}
 # Exact Oaxaca-like reference decomposition with missing categories handled using pooled means:
 # observed ROI difference = mix effect using 2023 ROI + within effect at 2024 mix;
 # only compute exact when each 2024 category is observed in 2023.
 n0=len(years["2023"]);n1=len(years["2024"])
 if all(buckets["2023"][k] for k in keys if buckets["2024"][k]):
  mix=sum((len(buckets["2024"][k])/n1-len(buckets["2023"][k])/n0)*
          (sum(z["pnl"] for z in buckets["2023"][k])/len(buckets["2023"][k])) for k in keys if buckets["2023"][k])
  within=sum(len(buckets["2024"][k])/n1*
          ((sum(z["pnl"] for z in buckets["2024"][k])/len(buckets["2024"][k]))-
           (sum(z["pnl"] for z in buckets["2023"][k])/len(buckets["2023"][k]))) for k in keys if buckets["2024"][k])
  decomp=dict(mix_roi_percentage_points=round(100*mix,4),within_roi_percentage_points=round(100*within,4),
              total_roi_percentage_points=round(100*(mix+within),4))
 else:decomp=dict(status="Missing 2023 reference for a 2024 stratum; no unsupported decomposition")
 groups[" × ".join(dims)]=dict(buckets=data,decomposition=decomp)
 print("GROUP",dims,decomp,flush=True)
out=dict(scope="Original R7 all27, fixture-deduplicated earliest equal-net, 2023 vs 2024",
 overall=overall,groups=groups,caveats=[
 "Mix decomposition is a descriptive accounting identity using 2023 category ROI as reference, not a causal estimate.",
 "Separate one-variable decompositions cannot be summed; interactions and confounding remain.",
 "2019-2023 original R7 was selected in-sample, 2024 repeatedly inspected; no independent forward validation.",
 "The quote tick count may reflect retrospective data capture density rather than historical live availability.",
 "No league analysis without fixture-to-league mapping; no league field in source ledger.",
 "No new filters, gates, production changes, or 2025-2026 results."])
(P/"R7_COMPOSITION_SHIFT_R34.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
