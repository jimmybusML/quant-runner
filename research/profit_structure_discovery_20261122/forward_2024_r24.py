#!/usr/bin/env python3
"""Frozen R7-R15 candidate 2024 forward-year evaluation; no candidate refit."""
import ast,collections,datetime as dt,json,math
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
events={}
direction_lookup={}
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a.get("year"))!="2024":continue
 h=int(a["entry_horizon_hours"]);fid=str(a["fixture_id"]);date=a["kickoff_utc"]
 line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
 hg,ag=map(int,a["score"].split("-"))
 fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
 sides={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
 for direction,side in sides.items():direction_lookup[(date,fid,h,direction)]=side
 f=dict(line=b(abs(line),[.25,.75,1.25,2.25]),price=b(home,[1.8,1.9,2,2.1]),
 momentum=b(float(a.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5]),
 age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]))
 for key in bybatch["R7"]:
  hz,family,structure,direction=key.split("|")
  if hz!=f"T{h}" or structure!=";".join(f"{v}={f[v]}" for v in family.split(",")):continue
  side=sides[direction];pnl=settle_score("AH",line,side,hg,ag,home if side=="home" else away)[1]
  k=(date,fid,h,side);events.setdefault(k,[pnl,[]])[1].append(key)
print("R7 2024 events",len(events),flush=True)
for batch in ("R9","R11","R12","R13","R14","R15"):
 path=P/("expanded_five_year_r9.py" if batch=="R9" else f"new_mechanisms_{batch.lower()}.py")
 src=path.read_text().replace('("2019","2020","2021","2022","2023")','("2024",)')
 tree=ast.parse(src);wanted={"iterate","b"} if batch=="R9" else {"gen","b"}
 var="families" if batch=="R9" else "FAMILIES"
 selected=[x for x in tree.body if (isinstance(x,ast.FunctionDef) and x.name in wanted) or (isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==var for t in x.targets))]
 ns=dict(__file__=str(path),SRC=SRC,Path=Path,json=json,dt=dt,settle_score=settle_score)
 exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),"exec"),ns)
 count=0
 for row in ns["iterate"]() if batch=="R9" else ns["gen"]():
  key=row[0]
  if key not in bybatch[batch]:continue
  if batch=="R9":key,y,date,fid,side,pnl=row
  else:
   key,y,date,fid,pnl=row
   side=direction_lookup[(date,fid,int(key.split("|")[0][1:]),key.split("|")[-1])]
  ek=(date,fid,int(key.split("|")[0][1:]),side)
  v=events.setdefault(ek,[pnl,[]])
  if abs(v[0]-pnl)>1e-6:raise AssertionError(("PNL mismatch",batch,ek,v[0],pnl))
  v[1].append(key);count+=1
 print(batch,count,flush=True)
groups=collections.defaultdict(lambda:{"home":[],"away":[]})
for (date,fid,h,side),(pnl,keys) in events.items():
 for key in keys:groups[(date,fid,h)][side].append((key,pnl))
fids=collections.defaultdict(list)
for k in groups:fids[k[:2]].append(k)
def metrics(orders):
 n=len(orders);net=sum(o[4]*o[5] for o in orders)
 eq=peak=dd=0.
 for o in sorted(orders):
  eq+=o[4]*o[5];peak=max(peak,eq);dd=max(dd,peak-eq)
 months=collections.defaultdict(list)
 for o in orders:months[o[0][:7]].append(o[4]*o[5])
 return dict(n=n,net_U=round(net,3),roi_pct=round(100*net/n,4) if n else None,mdd_U=round(dd,3),
 positive_months=sum(sum(v)>0 for v in months.values()),negative_months=sum(sum(v)<0 for v in months.values()),
 monthly={m:dict(n=len(v),net_U=round(sum(v),3)) for m,v in sorted(months.items())})
def orders_for(timing,weight,policy,stake):
 orders=[]
 for fid,ks in fids.items():
  if timing=="earliest":k=max(ks,key=lambda x:x[2])
  elif timing=="latest":k=min(ks,key=lambda x:x[2])
  else:
   possible=[q for q in ks if q[2]==int(timing[1:])]
   if not possible:continue
   k=possible[0]
  sides=groups[k]
  n={s:len(v) for s,v in sides.items()}
  if policy=="skip" and n["home"] and n["away"]:continue
  w={}
  for s,vals in sides.items():
   if weight=="equal":w[s]=len(vals)
   elif weight=="batch":w[s]=len({catalog[c]["batch"] for c,p in vals})
   elif weight=="sqrt_n":w[s]=sum(math.sqrt(catalog[c]["n"]) for c,p in vals)
   elif weight=="train_roi":w[s]=sum(max(0,catalog[c]["roi"]) for c,p in vals)
   else:raise ValueError(weight)
  if w["home"]==w["away"]:continue
  if policy=="margin2" and abs(w["home"]-w["away"])<2:continue
  if policy=="margin3" and abs(w["home"]-w["away"])<3:continue
  if policy=="margin5" and abs(w["home"]-w["away"])<5:continue
  side=max(w,key=w.get)
  if not n[side]:continue
  size=1. if stake=="flat" else min(2.,max(.5,abs(w["home"]-w["away"])/max(w.values()))) if stake=="vote_margin" else None
  orders.append((k[0],k[1],k[2],side,sides[side][0][1],size))
 return orders
records=[]
for timing in ("earliest","latest","T24","T12","T6","T2"):
 for weight in ("equal","batch","sqrt_n","train_roi"):
  for policy in ("skip","net","margin2","margin3","margin5"):
   if weight!="equal" and policy.startswith("margin"):continue
   for stake in ("flat","vote_margin"):
    orders=orders_for(timing,weight,policy,stake)
    records.append(dict(timing=timing,weight=weight,policy=policy,stake=stake,**metrics(orders)))
out=dict(scope="2024 only; frozen 2019-2023 R7-R15 494 candidate definitions",
 candidate_count=len(catalog),fixture_horizon_groups=len(groups),unique_signal_fixtures=len(fids),
 alternatives=records,limitations=[
 "2024 was not used for selecting the 494 candidate identities; 2019-2023 ROI/sample weights are training-only.",
 "All 2024 variants are reported; comparing them ex post is exploration, not a second untouched test.",
 "Historical Crown event-time quotes retrospectively fetched in 2026; execution availability not verified.",
 "2024 dataset coverage may differ from training years; no 2025-2026 or production changes.",
 "Vote-margin stake is an experimental alternative and not an approved bankroll policy."])
(P/"FORWARD_2024_R24_RESULTS.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("SUMMARY",json.dumps({k:v for k,v in out.items() if k!="alternatives"},ensure_ascii=False),flush=True)
for z in records:
 if z["stake"]=="flat" and z["weight"]=="equal" and z["policy"] in ("skip","net","margin2","margin3"):
  print("RESULT",z["timing"],z["policy"],z["n"],z["net_U"],z["roi_pct"],z["mdd_U"],flush=True)
