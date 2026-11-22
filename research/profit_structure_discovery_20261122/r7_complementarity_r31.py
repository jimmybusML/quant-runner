#!/usr/bin/env python3
"""R31: R7 original 27 structures, overlap, yearly returns and batch complementarity."""
import collections,itertools,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"train_only_original_combinations_r30.py"))
catalog=r["catalog"];train=r["tr"];test=r["te"];evaluate=r["evaluate"]
r7={c for c,v in catalog.items() if v["batch"]=="R7"}
def metric(v):
 n=len(v);s=sum(v)
 return dict(n=n,net_U=round(s,3),roi_pct=round(100*s/n,4) if n else None)
def candidate_events(groups,ids):
 out=collections.defaultdict(dict)
 for k,sides in groups.items():
  for side,vals in sides.items():
   for c,p in vals:
    if c in ids:out[c][(k[:2],k[2])]=(side,p)
 return out
trc=candidate_events(train,r7);tec=candidate_events(test,r7)
individual=[]
for c in sorted(r7):
 a=trc[c];b=tec[c]
 yearly={str(y):metric([p for (fid,h),(s,p) in a.items() if fid[0][:4]==str(y)]) for y in range(2019,2024)}
 individual.append(dict(id=c,horizon=c.split("|")[0],train=metric([p for s,p in a.values()]),test=metric([p for s,p in b.values()]),train_years=yearly))
pairs=[]
for c1,c2 in itertools.combinations(sorted(r7),2):
 a=set(trc[c1]);b=set(trc[c2]);ta=set(tec[c1]);tb=set(tec[c2])
 # overlap at fixture level regardless of horizon
 f1={k[0] for k in a};f2={k[0] for k in b};g1={k[0] for k in ta};g2={k[0] for k in tb}
 pairs.append(dict(a=c1,b=c2,train_shared_fixtures=len(f1&f2),test_shared_fixtures=len(g1&g2)))
sets={"R7_all27":r7}
for b in sorted({v["batch"] for v in catalog.values()}-{"R7"}):
 sets["R7_plus_"+b]=r7|{c for c,v in catalog.items() if v["batch"]==b}
out=dict(scope="Original R7 27 candidate complementarity and original-batch union, 2019-23 and 2024",
 individual=individual,pair_overlap=pairs,sets={},caveats=[
 "R7 is a historical 2019-2023 selected candidate batch; its historical profitability is in-sample.",
 "All R7 candidate definitions and original batches unchanged; 2024 outcomes not used to choose membership.",
 "R7+batch combinations are exploratory research comparisons; 2024 has already been inspected in earlier rounds.",
 "Individual candidate results overlap in fixtures and must not be summed.",
 "Pair overlap counts same fixture even if candidate horizons differ; per-fixture portfolio deduplicates at earliest eligible horizon.",
 "No 2025-2026 or production changes. Retrospective quotes not proven executable."])
for name,ids in sets.items():
 a=evaluate(train,ids);b=evaluate(test,ids)
 out["sets"][name]=dict(definitions=len(ids),historical=a,year2024=b)
 print("SET",name,a["policies"]["equal_net"]["overall"],b["policies"]["equal_net"]["overall"],flush=True)
print("INDIVIDUAL 2024 winners",sum(x["test"]["net_U"]>0 for x in individual),"/",len(individual),flush=True)
print("PAIRS",len(pairs),"overlap",sum(x["test_shared_fixtures"]>0 for x in pairs),flush=True)
(P/"R7_COMPLEMENTARITY_R31.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
