#!/usr/bin/env python3
"""Exact union of 2019-23 fixtures hit by R7/R9/R11-R15 positive candidates."""
import ast,collections,json,datetime as dt
from research.m3.probabilities import settle_score
from pathlib import Path
P=Path(__file__).resolve().parent
files={ "R7":"five_year_review_r7_results.json","R9":"expanded_five_year_r9_results.json",
"R11":"new_mechanisms_r11_results.json","R12":"new_mechanisms_r12_results.json",
"R13":"new_mechanisms_r13_results.json","R14":"new_mechanisms_r14_results.json",
"R15":"new_mechanisms_r15_results.json"}
ids={k:{x["id"] for x in json.load(open(P/v))["candidates"]} for k,v in files.items()}
assert sum(map(len,ids.values()))==494
bybatch=collections.defaultdict(set);byyear=collections.defaultdict(set);all_fids=set()
src=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
def b(v,edges):return sum(v>=e for e in edges)
# R7 original feature vocabulary
for raw in src.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a["year"]) not in ("2019","2020","2021","2022","2023"):continue
 fid=str(a["fixture_id"]);y=str(a["year"]);h=int(a["entry_horizon_hours"])
 all_fids.add(fid);byyear[y].add(fid)
 line=float(a["line"]);home=float(a["odds"]["home"])
 f=dict(line=b(abs(line),[.25,.75,1.25,2.25]),price=b(home,[1.8,1.9,2,2.1]),
 momentum=b(float(a.get("line_delta_since_first_quote") or 0),[-.5,-.125,.125,.5]),
 age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]))
 for key in ids["R7"]:
  hz,family,structure,direction=key.split("|")
  if hz!=f"T{h}":continue
  if structure==";".join(f"{v}={f[v]}" for v in family.split(",")):bybatch["R7"].add(fid)
print("R7",len(bybatch["R7"]),flush=True)
# Extract only source generator definition and its declared feature vocabulary; do not execute module top-level reporting.
for batch in ["R9","R11","R12","R13","R14","R15"]:
 name={"R9":"expanded_five_year_r9.py"}.get(batch,f"new_mechanisms_{batch.lower()}.py")
 path=P/name
 tree=ast.parse(path.read_text(),filename=str(path))
 if batch=="R9":
  # R9 uses iterate() and different feature naming, but outputs same (key,year,date,fid,side,pnl)
  wanted={"iterate","b"};vars={"families"}
 else:wanted={"gen","b"};vars={"FAMILIES"}
 selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,)) and node.name in wanted or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in vars for t in node.targets)]
 namespace={"__file__":str(path),"__name__":f"coverage_{batch}","SRC":src,"json":json,"dt":dt,"settle_score":settle_score,"Path":Path}
 exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),"exec"),namespace)
 iterator=namespace["iterate"]() if batch=="R9" else namespace["gen"]()
 matched=0
 for row in iterator:
  key=row[0];fid=row[3]
  if key in ids[batch]:bybatch[batch].add(fid);matched+=1
 assert matched==sum(x["overall"]["n"] for x in json.load(open(P/files[batch]))["candidates"]),(batch,matched)
 print(batch,len(bybatch[batch]),matched,flush=True)
union=set().union(*bybatch.values())
assert union<=all_fids
year_union={y:len(union & fids) for y,fids in sorted(byyear.items())}
out=dict(scope="2019-2023 only",all_unique_fixtures=len(all_fids),covered_unique_fixtures=len(union),
 coverage_pct=round(len(union)/len(all_fids)*100,4),uncovered_unique_fixtures=len(all_fids-union),
 candidates=494,by_batch_unique={k:len(bybatch[k]) for k in files},
 by_year={y:dict(all_fixtures=len(byyear[y]),covered=len(union&byyear[y]),
 uncovered=len(byyear[y]-union),coverage_pct=round(100*len(union&byyear[y])/len(byyear[y]),4)) for y in sorted(byyear)},
 incremental_unique={},
 audit="exact fixture-id union, candidate match logic extracted from original R7/R9/R11-R15 source; each later batch's matched signal count reconciles with original candidate results")
running=set()
for batch in files:
 out["incremental_unique"][batch]=len(bybatch[batch]-running)
 running|=bybatch[batch]
assert running==union
(P/"coverage_494_r16_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("COVERAGE",json.dumps(out,ensure_ascii=False),flush=True)
