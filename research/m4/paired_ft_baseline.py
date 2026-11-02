#!/usr/bin/env python3
"""M4 read-only paired MR1 forward/FT evaluation. Run inside checkout of MR1 state."""
import json, pathlib, collections, datetime
R=pathlib.Path("data/mr1-v6-cross-market")
F=R/"forward/records"
FT=pathlib.Path("data/strategy-shadow-ledger/results")
OUT=pathlib.Path("m4_paired_research.json")
def parse(s):
 try:return datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
 except (AttributeError,ValueError):return None
def get(row,market):
 e=row.get("evaluation",{})
 if not isinstance(e,dict) or e.get("status")!="ok":return None
 v=e.get(market,{})
 if not isinstance(v,dict):return None
 return v.get("selected")
def settlement(side,line,price,hg,ag,market):
 if side not in (("home","away") if market=="AH" else ("over","under")):return None
 try:line=float(line);price=float(price)
 except (TypeError,ValueError):return None
 if price<=1 or abs(line*4-round(line*4))>1e-8:return None
 # Side-relative Asian handicap lines; OU line is total threshold.
 if abs(line*2-round(line*2))<1e-8:parts=[line,line]
 else:parts=[int(line*2//1)/2, int(line*2//1)/2+0.5]
 outcome=0
 for part in parts:
  delta=(hg-ag if side=="home" else ag-hg)+part if market=="AH" else (hg+ag-part)*(1 if side=="over" else -1)
  outcome+=(price-1 if delta>1e-9 else -1 if delta< -1e-9 else 0)/2
 return outcome
results={}
for f in FT.glob("*.json"):
 try:
  x=json.loads(f.read_text())
  if x.get("status")=="FT" and str(x.get("match_id"))==f.stem and all(isinstance(x.get(z),int) and x[z]>=0 for z in ("home_goals","away_goals")):
   results[f.stem]=x
 except (OSError,ValueError):continue
group=collections.defaultdict(list);counts=collections.Counter(); inventory=collections.defaultdict(lambda:{"files":0,"matches":set()}); valid_leagues=collections.defaultdict(set)
for f in F.glob("*.json"):
 counts["forward_files"]+=1
 match=f.name.split("-")[0];ft=results.get(match)
 try:x=json.loads(f.read_text())
 except (OSError,ValueError):counts["bad_json"]+=1;continue
 lname=str(x.get("league") or "UNKNOWN");inventory[lname]["files"]+=1;inventory[lname]["matches"].add(match)
 if not ft:continue
 kickoff=parse(x.get("kickoff_at"));received=parse(x.get("received_at"));observed=parse(ft.get("observed_at"))
 if not kickoff or not received or received>=kickoff or not observed or observed<=kickoff:
  counts["invalid_time"]+=1;continue
 if x.get("source_bookmaker")!="crown" or x.get("source_bookmaker_verified") is not True:
  counts["unverified_crown"]+=1;continue
 if str(x.get("match_id"))!=match:counts["wrong_identity"]+=1;continue
 counts["paired_valid_forward"]+=1
 group[match].append((x,ft));valid_leagues[lname].add(match)
agg=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"positive_ev_n":0})
league=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"positive_ev_n":0})
def add(d,key,pnl,ev):
 z=d[key];z["n"]+=1;z["pnl"]+=pnl;z["positive_ev_n"]+=int(ev>0) if isinstance(ev,(float,int)) else 0
# Same-match multi-horizon comparison: one record per match per horizon/market.
for match,entries in group.items():
 for market in ("AH","OU"):
  seen=set()
  for x,ft in sorted(entries,key=lambda p:p[0].get("received_at","")):
   h=x.get("horizon")
   if h in seen:continue
   c=get(x,market)
   if not c:continue
   side=c.get("side");line=c.get("line");price=c.get("price")
   p=settlement(side,line,price,ft["home_goals"],ft["away_goals"],market)
   if p is None:counts["invalid_contract"]+=1;continue
   seen.add(h)
   add(agg,(market,h),p,c.get("EV"))
   add(league,(str(x.get("league") or "UNKNOWN"),market,h),p,c.get("EV"))
   counts["settled_counterfactual_records"]+=1
   # This is synthetic replay of saved historical model choices, not real trades.
def formatted(d):
 return {("|".join(map(str,k)) if isinstance(k,tuple) else str(k)):{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"positive_ev_count":v["positive_ev_n"]} for k,v in sorted(d.items()) if v["n"]}
output={"protocol":"M4_MR1_PAIRED_FT_READ_ONLY_V1","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"MR1 saved forward Crown quotes and TotalCorner FT records","unique_valid_paired_matches":len(group),"counts":dict(counts),"per_market_horizon":formatted(agg),"per_league_market_horizon":formatted(league),"league_inventory":{k:{"snapshot_files":v["files"],"unique_matches":len(v["matches"]),"valid_ft_matches":len(valid_leagues[k])} for k,v in sorted(inventory.items())},"note":"Retrospective counterfactual, not Telegram trades or out-of-sample M4 improvement. Same match repeated across horizons; each horizon independently counts at most one observation per match. No new gate or trade rules."}
OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(output,ensure_ascii=False))
