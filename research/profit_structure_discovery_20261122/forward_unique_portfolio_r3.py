#!/usr/bin/env python3
"""Frozen-discovery candidate replay. Research scenarios, not production policies.

2019-23 rankings are frozen before 2024-26. Alternative rank metrics are
explicitly analytical scenarios, NOT user-defined gates/priority/rules.
One fixture can trigger many candidates; portfolio scenarios use deterministic
one fixture per candidate horizon and one fixture across horizons.
"""
import collections,datetime as dt,json,hashlib
from pathlib import Path
from research.m3.probabilities import settle_score
from research.profit_structure_discovery_20261122.structure_discovery_r1 import features,FAMILIES
ROOT=Path(__file__).resolve().parent
SOURCE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
M8=Path("/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/mechanism_discovery_20261119/frozen_eight_fixture_mechanism_rows.jsonl")
R1=json.load(open(ROOT/"structure_discovery_r1_results.json"))
m8={}
for line in M8.open():
 x=json.loads(line);m8[str(x["fid"])]=x
# Distinct pre-declared research comparisons: discovery ROI vs discovery total U;
# top 1 and top 3 per horizon, and early-first vs late-first across horizons.
# They are scenario dimensions, not production quantity limits or precedence rules.
rankings={}
for h,arr in R1["by_horizon"].items():
 for metric in ("discovery_roi","discovery_net_u"):
  key="roi_pct" if metric=="discovery_roi" else "net_U"
  ranking=sorted(arr,key=lambda r:(r["discovery"][key],r["discovery"]["n"],r["family"],r["structure"],r["direction"]),reverse=True)
  rankings[(int(h),metric)]=ranking
orders=[]
audit=collections.Counter()
for line in SOURCE.open():
 r=json.loads(line)
 if r.get("market")!="AH" or str(r["year"]) not in ("2024","2025","2026"):continue
 year=str(r["year"]);h=int(r["entry_horizon_hours"]);fid=str(r["fixture_id"])
 x=dict(line=float(r["line"]),home=float(r["odds"]["home"]),away=float(r["odds"]["away"]),
        delta=float(r.get("line_delta_since_first_quote") or 0),
        age=float(r["actual_hours_before_kickoff"])-h)
 hg,ag=map(int,r["score"].split("-"))
 pnl={"home":settle_score("AH",x["line"],"home",hg,ag,x["home"])[1],
      "away":settle_score("AH",x["line"],"away",hg,ag,x["away"])[1]}
 fav="home" if x["line"]<0 else "away" if x["line"]>0 else "home" if x["home"]<x["away"] else "away"
 dirs={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
 fs=features(x)
 signatures={",".join(f):";".join(f"{k}={fs[k]}" for k in f) for f in FAMILIES}
 row=dict(fid=fid,year=year,h=h,kickoff=r["kickoff_utc"],line=x["line"],
          odds_home=x["home"],odds_away=x["away"],pnl=pnl,dirs=dirs,
          signatures=signatures,overlaps_m8=fid in m8,
          m8_direction=m8[fid]["direction"] if fid in m8 else None)
 orders.append(row)
 audit["forward_market_rows"]+=1
assert len({(r["fid"],r["h"]) for r in orders})==len(orders)
def stats(rows):
 vals=[r["pnl"][r["side"]] for r in rows]
 return dict(n=len(vals),unique_fids=len({r["fid"] for r in rows}),
             net_U=round(sum(vals),3),roi_pct=round(100*sum(vals)/len(vals),4) if vals else None)
def reconcile(z):
 return dict(all=stats(z),outside_M8=stats([r for r in z if not r["overlaps_m8"]]),
   M8_same_direction=stats([r for r in z if r["overlaps_m8"] and r["side"]==r["m8_direction"]]),
   M8_opposite_direction=stats([r for r in z if r["overlaps_m8"] and r["side"]!=r["m8_direction"]]))
def match(r,c):
 return r["signatures"][c["family"]]==c["structure"] and r["dirs"][c["direction"]] in ("home","away")
def selections(rows,metric,topk):
 selected=[]
 for r in rows:
  ranked=rankings[(r["h"],metric)][:topk]
  for index,c in enumerate(ranked):
   if match(r,c):
    selected.append(dict(fid=r["fid"],year=r["year"],h=r["h"],kickoff=r["kickoff"],
       side=r["dirs"][c["direction"]],pnl=r["pnl"],overlaps_m8=r["overlaps_m8"],
       m8_direction=r["m8_direction"],candidate_rank=index+1,
       candidate=f'{c["family"]}|{c["structure"]}|{c["direction"]}'))
    break
 return selected
def unique_fixture(rows,early_first):
 # Deterministic research alternative for comparing horizons; not a production priority.
 key=lambda r:(-r["h"] if early_first else r["h"],r["candidate_rank"],r["candidate"],r["side"])
 by=collections.defaultdict(list)
 for r in rows:by[r["fid"]].append(r)
 return [min(v,key=key) for v in by.values()]
out=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 source=str(SOURCE),frozen_m8_sha256=hashlib.sha256(M8.read_bytes()).hexdigest(),
 frozen_m8_unique_fids=len(m8),research_scenarios={},audit=dict(audit),
 protocol="2019-23 discovery rankings frozen before 2024-26. No future year used to choose candidates. Top1/Top3, ROI/net-U ranking, earliest/latest horizon are descriptive scenario alternatives only; not production rules.",
 provenance="Crown historical event-time after-match retrieved; no proof of actual historical executable receipt.")
ledger=[]
for metric in ("discovery_roi","discovery_net_u"):
 for k in (1,3):
  s=selections(orders,metric,k)
  for scope in ("each_horizon","unique_earliest","unique_latest"):
   if scope=="each_horizon":
    scopes={str(h):[r for r in s if r["h"]==h] for h in (24,12,6,2)}
   else:scopes={"all_horizons":unique_fixture(s,scope=="unique_earliest")}
   for h,rr in scopes.items():
    scenario=f"{metric}_top{k}_{scope}_{h}"
    out["research_scenarios"][scenario]={
      "discovery_candidates":[dict(h=hh,rank=i+1,family=c["family"],structure=c["structure"],direction=c["direction"],discovery=c["discovery"]) for hh in ((int(h),) if scope=="each_horizon" else (24,12,6,2)) for i,c in enumerate(rankings[(hh,metric)][:k])],
      "years":{y:reconcile([r for r in rr if r["year"]==y]) for y in ("2024","2025","2026")},
      "all_future":reconcile(rr)}
    for r in rr:
     ledger.append(dict(scenario=scenario,year=r["year"],fid=r["fid"],h=r["h"],kickoff=r["kickoff"],side=r["side"],
       pnl_U=r["pnl"][r["side"]],m8_same_fixture=r["overlaps_m8"],
       m8_same_direction=(r["side"]==r["m8_direction"] if r["overlaps_m8"] else None),
       selected_discovery_rank=r["candidate_rank"],selected_discovery_candidate=r["candidate"]))
    print(scenario,"all",out["research_scenarios"][scenario]["all_future"]["all"],
          "outsideM8",out["research_scenarios"][scenario]["all_future"]["outside_M8"])
for scenario,z in out["research_scenarios"].items():
 for y in ("2024","2025","2026"):
  v=z["years"][y]
  assert v["all"]["n"]==sum(v[k]["n"] for k in ("outside_M8","M8_same_direction","M8_opposite_direction"))
  assert v["all"]["unique_fids"]==v["all"]["n"]
out["audit"].update(dict(scenarios=len(out["research_scenarios"]),ledger_rows=len(ledger),
                          all_forward_unique_fids=len({r["fid"] for r in orders})))
(ROOT/"forward_unique_portfolio_r3_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (ROOT/"forward_unique_portfolio_r3_ledger.local.jsonl").open("w") as f:
 for r in ledger:f.write(json.dumps(r,ensure_ascii=False)+"\n")
print("VERIFIED",out["audit"])
