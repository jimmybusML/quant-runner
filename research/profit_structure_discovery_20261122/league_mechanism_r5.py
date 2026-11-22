#!/usr/bin/env python3
"""Research diagnostic: league x handicap depth x line movement.
No candidate selection, no thresholds, no production rules. Same fixture/horizon
one home and one away hypothetical outcome, separately (never add both as orders).
"""
import collections,datetime as dt,json,hashlib
from pathlib import Path
from research.m3.probabilities import settle_score
ROOT=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
META=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl")
meta={}
for line in META.open():
 r=json.loads(line);meta[str(r["fixture_id"])]=(str(r.get("league_id") or ""),str(r.get("league") or ""))
assert len(meta)==36343
data=collections.defaultdict(lambda:[0,0.,0.])
paired=collections.defaultdict(lambda:[0,0.,0.])
coverage=collections.Counter()
fids=collections.defaultdict(set)
def bucket(v,edges):return sum(v>=e for e in edges)
for line in SRC.open():
 r=json.loads(line)
 if r.get("market")!="AH":continue
 year=str(r["year"]);h=int(r["entry_horizon_hours"]);fid=str(r["fixture_id"])
 assert fid not in fids[(year,h)]
 fids[(year,h)].add(fid)
 league,name=meta.get(fid,("",""))
 if not league:coverage["missing_league"]+=1
 coverage["all_rows"]+=1
 if h!=12:continue
 line_=float(r["line"]);home=float(r["odds"]["home"]);away=float(r["odds"]["away"])
 hg,ag=map(int,r["score"].split("-"))
 fav="home" if line_<0 else "away" if line_>0 else "home" if home<away else "away"
 side="away" if fav=="home" else "home"
 pnl=settle_score("AH",line_,side,hg,ag,home if side=="home" else away)[1]
 depth=bucket(abs(line_),[.25,.75,1.25,2.25])
 movement=bucket(float(r.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5])
 price=bucket(float(r.get("same_line_no_vig_probability_delta_side1") or 0),[-.02,-.005,.005,.02])
 # full cross of price and depth with league, and movement x depth with league.
 for family,key in (("depth_price",(depth,price)),("depth_line_move",(depth,movement)),("depth_only",(depth,))):
  for scope in ("ALL",league or "UNKNOWN"):
   k=(year,family,scope,key);v=data[k];v[0]+=1;v[1]+=pnl;v[2]+=pnl*pnl
 # Same-fixture comparison: league-vs-pooled diagnostics later use identical fixtures
 coverage["T12_rows"]+=1
def stats(v):
 n,s,ss=v
 return dict(n=n,net_U=round(s,3),roi_pct=round(100*s/n,4) if n else None,
             std_U=round(max(0,ss/n-(s/n)**2)**.5,4) if n else None)
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 source=str(SRC),metadata_source=str(META),
 provenance="Historical Crown source-event timestamps retrieved post-match in 2026, NOT historical real pre-match receipts",
 scope="T12 underdog direction, descriptive league x handicap-depth x price-movement interactions; no selection or live orders",
 audit=dict(coverage),years={},league_names={v[0]:v[1] for v in meta.values() if v[0]})
for year in map(str,range(2019,2027)):
 entries={}
 for (yy,family,league,key),v in data.items():
  if yy!=year:continue
  entries[f"{family}|{league}|{','.join(map(str,key))}"]=stats(v)
 out["years"][year]=entries
# Discovery-only: fixed 2019-23 candidate profitability ranking, 2024-26 results for same exact cells.
summary=[]
for (year,family,league,key),v in data.items():
 if year not in map(str,range(2019,2024)) or league in ("ALL","UNKNOWN"):continue
 identity=(family,league,key)
 paired[identity][0]+=v[0];paired[identity][1]+=v[1];paired[identity][2]+=v[2]
for (family,league,key),v in paired.items():
 summary.append(dict(family=family,league_id=league,league=out["league_names"].get(league,""),
                     bins=list(key),discovery=stats(v),
                     future={y:stats(data.get((y,family,league,key),[0,0.,0.])) for y in ("2024","2025","2026")}))
summary.sort(key=lambda z:(z["discovery"]["net_U"],z["discovery"]["n"]),reverse=True)
out["discovery_ranked_league_cells"]=summary
out["audit"]["discovery_league_cells"]=len(summary)
out["audit"]["top_discovery_20_positive_all_future"]=sum(all(z["future"][y]["roi_pct"] is not None and z["future"][y]["roi_pct"]>0 for y in ("2024","2025","2026")) for z in summary[:20])
out["audit"]["top_discovery_20_positive_2026"]=sum(z["future"]["2026"]["roi_pct"] is not None and z["future"]["2026"]["roi_pct"]>0 for z in summary[:20])
(ROOT/"league_mechanism_r5_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("AUDIT",out["audit"])
for z in summary[:12]:
 print("DISCOVERY",z["family"],z["league"],z["bins"],z["discovery"],"2024",z["future"]["2024"],"2025",z["future"]["2025"],"2026",z["future"]["2026"])
