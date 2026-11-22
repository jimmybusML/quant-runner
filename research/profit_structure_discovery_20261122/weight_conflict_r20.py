#!/usr/bin/env python3
"""R20: historical comparison of weighting and conflict policies, not production."""
import ast,collections,csv,datetime as dt,json,math
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
files={"R7":"five_year_review_r7_results.json","R9":"expanded_five_year_r9_results.json",**{f"R{i}":f"new_mechanisms_r{i}_results.json" for i in range(11,16)}}
catalog={};bybatch={}
for batch,fn in files.items():
 c=json.load(open(P/fn))["candidates"];bybatch[batch]={z["id"] for z in c}
 for z in c:catalog[z["id"]]=dict(batch=batch,n=z["overall"]["n"],roi=z["overall"]["roi_pct"]/100,annual=z["years"])
assert len(catalog)==494
def b(v,edges):return sum(v>=e for e in edges)
def reconstruct():
 # (date, fixture, horizon, side) -> (pnl, list of candidate ids)
 events={}
 for raw in SRC.open():
  a=json.loads(raw)
  if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
  h=int(a["entry_horizon_hours"]);fid=str(a["fixture_id"]);date=a["kickoff_utc"]
  line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
  hg,ag=map(int,a["score"].split("-"))
  fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
  sides={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
  f=dict(line=b(abs(line),[.25,.75,1.25,2.25]),price=b(home,[1.8,1.9,2,2.1]),
   momentum=b(float(a.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5]),
   age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]))
  for key in bybatch["R7"]:
   hz,family,structure,direction=key.split("|")
   if hz!=f"T{h}" or structure!=";".join(f"{v}={f[v]}" for v in family.split(",")):continue
   side=sides[direction];pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
   k=(date,fid,h,side);v=events.setdefault(k,[pnl,[]]);v[1].append(key)
 print("R7",len(events),flush=True)
 for batch in ("R9","R11","R12","R13","R14","R15"):
  path=P/("expanded_five_year_r9.py" if batch=="R9" else f"new_mechanisms_{batch.lower()}.py")
  tree=ast.parse(path.read_text());wanted={"iterate","b"} if batch=="R9" else {"gen","b"}
  var="families" if batch=="R9" else "FAMILIES"
  selected=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in wanted or isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==var for t in x.targets)]
  ns=dict(__file__=str(path),SRC=SRC,Path=Path,json=json,dt=dt,settle_score=settle_score)
  exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),"exec"),ns)
  count=0
  for row in ns["iterate"]() if batch=="R9" else ns["gen"]():
   key=row[0]
   if key not in bybatch[batch]:continue
   if batch=="R9":key,y,date,fid,side,pnl=row
   else:
    key,y,date,fid,pnl=row;direction=key.split("|")[-1]
    # Side is deterministic from the corresponding source row; retrieve from a fixture/horizon event-side lookup
    # If same pnl happens on both sides, resolve by direct candidate-direction source side via index below.
    side=None
   k=(date,fid,int(key.split("|")[0][1:]))
   if side is None:
    # Better direct lookup using prebuilt market-side mapping
    side=side_by_event_direction[(date,fid,k[2],direction)]
   ek=(*k,side)
   v=events.setdefault(ek,[pnl,[]])
   if abs(v[0]-pnl)>1e-6:raise AssertionError(("PNL mismatch",batch,ek,v[0],pnl))
   v[1].append(key);count+=1
  expected=sum(z["n"] for z in (catalog[q] for q in bybatch[batch]))
  assert count==expected,(batch,count,expected)
  print(batch,count,len(events),flush=True)
 return events
# Map exact direction to physical side at each quote horizon, used for R11-R15 generators.
side_by_event_direction={}
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
 line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
 fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
 for direction,side in {"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}.items():
  side_by_event_direction[(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]),direction)]=side
print("SIDE INDEX",len(side_by_event_direction),flush=True)
events=reconstruct()
# Aggregate by fixture and horizon: each candidate's one quote is one vote, regardless of alias direction.
groups=collections.defaultdict(lambda:{"home":[],"away":[]})
for (date,fid,h,side),(pnl,keys) in events.items():
 for key in keys:groups[(date,fid,h)][side].append((key,pnl))
print("GROUPS",len(groups),flush=True)
# Baselines / research alternatives: equal-weight vote, weight by sample-size shrinkage,
# historical in-sample ROI, rolling prior-year ROI; conflict skip, net, best side.
def evaluate(policy,weighting):
 orders=[]
 conflicts=0;both=0;same=0
 for (date,fid,h),sides in groups.items():
  year=int(date[:4])
  def wt(k):
   z=catalog[k]
   if weighting=="equal":return 1.
   if weighting=="sample":return math.sqrt(z["n"])
   if weighting=="full_roi":return max(0,z["roi"])
   if weighting=="prior_roi":
    prev=[z["annual"][str(y)] for y in range(2019,year)]
    n=sum(x["n"] for x in prev);u=sum(x["net_U"] for x in prev)
    return max(0,u/n) if n else 0
   raise ValueError(weighting)
  a={side:sum(wt(k) for k,pnl in vals) for side,vals in sides.items()}
  n={side:len(vals) for side,vals in sides.items()}
  if n["home"] and n["away"]:conflicts+=1
  if n["home"]+n["away"]>1:same+=1
  if policy=="skip_conflict" and n["home"] and n["away"]:continue
  if policy=="net" and a["home"]==a["away"]:continue
  if policy=="both":
   for side in ("home","away"):
    if n[side]:orders.append((date,fid,h,side,sides[side][0][1],1.))
   continue
  if policy=="net":
   side="home" if a["home"]>a["away"] else "away"
  elif policy=="best":
   side=max(("home","away"),key=lambda x:a[x])
   if a[side]==0:continue
  elif policy=="skip_conflict":
   side="home" if n["home"] else "away"
  else:raise ValueError(policy)
  if not n[side]:continue
  orders.append((date,fid,h,side,sides[side][0][1],1.))
 return orders,dict(conflicts=conflicts,multi_signal_groups=same,group_count=len(groups))
def metrics(orders):
 n=len(orders);net=sum(o[4]*o[5] for o in orders)
 eq=peak=dd=0
 for o in sorted(orders):
  eq+=o[4]*o[5];peak=max(peak,eq);dd=max(dd,peak-eq)
 annual={str(y):{"n":sum(o[0][:4]==str(y) for o in orders),"net_U":round(sum(o[4]*o[5] for o in orders if o[0][:4]==str(y)),3)} for y in range(2019,2024)}
 return dict(n=n,unique_fixtures=len({o[1] for o in orders}),net_U=round(net,3),roi_pct=round(100*net/n,4) if n else None,mdd_U=round(dd,3),annual=annual)
results=[]
for weighting in ("equal","sample","full_roi","prior_roi"):
 for policy in ("both","skip_conflict","net","best"):
  orders,info=evaluate(policy,weighting)
  results.append(dict(weighting=weighting,conflict_policy=policy,**metrics(orders),**info))
print("RESULTS",json.dumps(results,ensure_ascii=False),flush=True)
# Fixture-level comparison, one quote horizon per fixture
original_groups=groups
fixture_horizons=collections.defaultdict(list)
for (date,fid,h) in original_groups:fixture_horizons[(date,fid)].append(h)
fixture_results=[]
for choice in ("earliest_quote","latest_quote"):
 chosen={(date,fid,max(hs) if choice=="earliest_quote" else min(hs)) for (date,fid),hs in fixture_horizons.items()}
 groups={k:v for k,v in original_groups.items() if k in chosen}
 for weighting in ("equal","sample","full_roi","prior_roi"):
  for policy in ("skip_conflict","net","best"):
   orders,info=evaluate(policy,weighting)
   fixture_results.append(dict(horizon_choice=choice,weighting=weighting,conflict_policy=policy,**metrics(orders),**info))
 groups=original_groups
print("FIXTURE_RESULTS",json.dumps(fixture_results,ensure_ascii=False),flush=True)
out=dict(scope="2019-2023 Crown AH, 494 R7-R15 definitions",candidates=len(catalog),unique_fixture_horizon_groups=len(groups),
 alternatives=results,fixture_level_alternatives=fixture_results,limitations=[
 "R7-R15 candidates were selected by all five years positive; full_roi and even prior_roi suffer future-data candidate-selection leakage.",
 "Orders deduplicated only within the same fixture and quote horizon; multiple horizons can still bet same fixture.",
 "Both sides policies include opposite-side orders and may incur economically offsetting bets.",
 "This is a retrospective simulation using 2026-retrieved Crown event-time quotes, not proven executable odds.",
 "No production or M8 changes. Sample-size, ROI and prior-ROI weights are experimental comparisons, not approved rules."
])
(P/"weight_conflict_r20_results.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
with (P/"weight_conflict_r20_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["weighting","conflict_policy","orders","unique_fixtures","net_U","roi_pct","mdd_U"]+[f"{y}_net_U" for y in range(2019,2024)])
 for z in results:w.writerow([z["weighting"],z["conflict_policy"],z["n"],z["unique_fixtures"],z["net_U"],z["roi_pct"],z["mdd_U"]]+[z["annual"][str(y)]["net_U"] for y in range(2019,2024)])
