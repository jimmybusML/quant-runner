#!/usr/bin/env python3
"""Rolling league-interaction research, no minimum sample/ROI gate.
Each target year trains on strictly earlier years; per-fixture unique horizon.
Pooled and league-specific historical net-U rankings are *research scenarios*.
"""
import collections,datetime as dt,hashlib,json
from pathlib import Path
from research.m3.probabilities import settle_score
from research.profit_structure_discovery_20261122.structure_discovery_r1 import features,FAMILIES
ROOT=Path(__file__).resolve().parent
SOURCE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
META=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl")
M8=Path("/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/mechanism_discovery_20261119/frozen_eight_fixture_mechanism_rows.jsonl")
leagues={}
for line in META.open():
 r=json.loads(line);leagues[str(r["fixture_id"])]=str(r.get("league_id") or "")
m8={}
for line in M8.open():
 r=json.loads(line);m8[str(r["fid"])]=r["direction"]
# Each candidate = (horizon, feature family, signature, side).
# Historical year+league aggregates; no future outcome used for target year.
history=collections.defaultdict(lambda:[0,0.0])
events=collections.defaultdict(list)
audit=collections.Counter()
for line in SOURCE.open():
 r=json.loads(line)
 if r.get("market")!="AH":continue
 year=int(r["year"]);h=int(r["entry_horizon_hours"]);fid=str(r["fixture_id"])
 if year not in range(2019,2027):continue
 league=leagues.get(fid,"")
 if not league:audit["missing_league"]+=1
 hg,ag=map(int,r["score"].split("-"))
 x=dict(line=float(r["line"]),home=float(r["odds"]["home"]),away=float(r["odds"]["away"]),
        delta=float(r.get("line_delta_since_first_quote") or 0),age=float(r["actual_hours_before_kickoff"])-h)
 pnl={"home":settle_score("AH",x["line"],"home",hg,ag,x["home"])[1],
      "away":settle_score("AH",x["line"],"away",hg,ag,x["away"])[1]}
 fav="home" if x["line"]<0 else "away" if x["line"]>0 else "home" if x["home"]<x["away"] else "away"
 fs=features(x)
 dirs={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
 # Distinct outcomes may share same candidate signature; both are preserved as candidates.
 signatures=[(h,",".join(f),";".join(f"{k}={fs[k]}" for k in f),direction)
             for f in FAMILIES for direction in dirs]
 if year<=2025:
  for c in signatures:
   side=dirs[c[-1]]
   for l in ("ALL",league):
    if l=="ALL" or league: # no invented league ID for missing rows
     z=history[(year,l,c)];z[0]+=1;z[1]+=pnl[side]
 if year>=2024:
  events[year].append(dict(fid=fid,h=h,league=league,pnl=pnl,dirs=dirs,
                           signatures=signatures,m8_direction=m8.get(fid)))
 audit["market_rows"]+=1
def stat(rows):
 n=len(rows);s=sum(r["pnl"][r["side"]] for r in rows)
 return dict(n=n,unique_fids=len({r["fid"] for r in rows}),net_U=round(s,3),
             roi_pct=round(100*s/n,4) if n else None)
def breakdown(rows):
 return dict(all=stat(rows),outside_M8=stat([r for r in rows if r["m8_direction"] is None]),
  M8_same_side=stat([r for r in rows if r["m8_direction"]==r["side"]]),
  M8_opposite_side=stat([r for r in rows if r["m8_direction"] is not None and r["m8_direction"]!=r["side"]]))
def pick(rows,early):
 by=collections.defaultdict(list)
 for r in rows:by[r["fid"]].append(r)
 return [min(rr,key=lambda r:(-r["h"] if early else r["h"],r["candidate"])) for rr in by.values()]
out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 protocol="For 2024/25/26 rank all candidates using only prior years 2019..target-1. Compare pooled and league-specific historical net-U ranking, one top candidate per league/horizon or pooled/horizon; earliest/latest unique-FID conflict scenarios are research parameters, not production rules or gates. No sample minimum or ROI threshold.",
 source=str(SOURCE),m8_sha256=hashlib.sha256(M8.read_bytes()).hexdigest(),
 metadata_fids=len(leagues),m8_fids=len(m8),audit=dict(audit),scenarios={})
ledger=[]
for target in (2024,2025,2026):
 # Ranking is computed from historical outcomes before the target year.
 rank=collections.defaultdict(lambda:None)
 for (year,l,c),(n,pnl) in history.items():
  if year>=target:continue
  key=(l,c)
  if rank[key] is None:rank[key]=[0,0.0]
  rank[key][0]+=n;rank[key][1]+=pnl
 best={}
 for (l,c),(n,profit) in rank.items():
  h=c[0];key=(l,h)
  # tie-break independent of target-year returns
  candidate=(profit,n,str(c))
  if key not in best or candidate>best[key][0]:
   best[key]=(candidate,c)
 for mode in ("pooled","league"):
  for early in (True,False):
   chosen=[]
   for e in events[target]:
    l=e["league"] if mode=="league" else "ALL"
    c=best.get((l,e["h"]))
    if c is None:continue
    cand=c[1]
    if cand not in e["signatures"]:continue
    side=e["dirs"][cand[-1]]
    chosen.append(dict(fid=e["fid"],h=e["h"],year=target,league=e["league"],
                       side=side,pnl=e["pnl"],candidate=str(cand),
                       m8_direction=e["m8_direction"]))
   unique=pick(chosen,early)
   name=f"{mode}_{'earliest' if early else 'latest'}"
   scenario=out["scenarios"].setdefault(name,dict(years={},selected_by_year={}))
   scenario["years"][str(target)]=breakdown(unique)
   scenario["selected_by_year"][str(target)]={"horizons":{str(h):str(best.get((l,h),("",None))[1]) for h in (24,12,6,2) for l in (("ALL",) if mode=="pooled" else ())},
      "training_end_year":target-1,
      "eligible_leagues":len({l for l,h in best if l!="ALL"}) if mode=="league" else None,
      "candidate_count":len(best)}
   for r in unique:
    ledger.append(dict(scenario=name,year=target,fid=r["fid"],h=r["h"],league=r["league"],
                       side=r["side"],pnl_U=r["pnl"][r["side"]],candidate=r["candidate"],
                       m8_direction=r["m8_direction"]))
   print(target,name,scenario["years"][str(target)])
for name,scenario in out["scenarios"].items():
 scenario["total"]={key:dict(n=sum(scenario["years"][str(y)][key]["n"] for y in (2024,2025,2026)),
  net_U=round(sum(scenario["years"][str(y)][key]["net_U"] for y in (2024,2025,2026)),3))
  for key in ("all","outside_M8")}
 for key,z in scenario["total"].items():
  z["roi_pct"]=round(100*z["net_U"]/z["n"],4) if z["n"] else None
out["audit"]["scenario_ledger_rows"]=len(ledger)
(ROOT/"rolling_league_interaction_r4_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (ROOT/"rolling_league_interaction_r4_ledger.local.jsonl").open("w") as f:
 for r in ledger:f.write(json.dumps(r,ensure_ascii=False)+"\n")
print("COMPLETE",out["audit"])
