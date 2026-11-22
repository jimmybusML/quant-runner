#!/usr/bin/env python3
"""R32: R7 fixture-level leave-one-out and historical-only ordering, no new production filters."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"r7_complementarity_r31.py"))
r7=r["r7"];train=r["train"];test=r["test"];evaluate=r["evaluate"];trc=r["trc"];tec=r["tec"]
def stats(v):
 n=len(v);p=sum(v);return dict(n=n,net_U=round(p,3),roi_pct=round(p/n*100,4) if n else None)
def get(groups,ids):
 z=evaluate(groups,ids)
 return z["policies"]["equal_net"]["overall"],z["overlap"]
base_train,_=get(train,r7);base_test,_=get(test,r7)
# Compare complete R7 with R7-minus-one, respecting reselected earliest eligible horizon.
leave=[]
for c in sorted(r7):
 a,ao=get(train,r7-{c});b,bo=get(test,r7-{c})
 leave.append(dict(candidate=c,train_without=a,test_without=b,
 train_net_delta_U=round(base_train["net_U"]-a["net_U"],3),
 test_net_delta_U=round(base_test["net_U"]-b["net_U"],3),
 train_order_delta=base_train["n"]-a["n"],test_order_delta=base_test["n"]-b["n"]))
# Historical-only greedy ordering: add the candidate with greatest training fixture coverage gain;
# ties broken by training net profit gain then candidate ID. Research ranking, not live selection.
chosen=set();greedy=[]
while chosen!=r7:
 current,_=get(train,chosen) if chosen else (dict(n=0,net_U=0),{})
 options=[]
 for c in sorted(r7-chosen):
  m,_=get(train,chosen|{c})
  options.append((m["n"]-current["n"],m["net_U"]-current["net_U"],c,m))
 _,_,winner,_=max(options,key=lambda v:(v[0],v[1],v[2]))
 chosen.add(winner)
 a,ao=get(train,chosen);b,bo=get(test,chosen)
 greedy.append(dict(step=len(chosen),added=winner,train=a,test=b,
 train_overlap=ao,test_overlap=bo))
 print("STEP",len(chosen),winner,"train",a,"test",b,flush=True)
out=dict(scope="R7 27 original candidate fixture marginal coverage, 2019-2023 historical-only ordering vs 2024",
 baseline=dict(train=base_train,test=base_test),leave_one_out=leave,
 greedy_historical_coverage=greedy,
 caveats=["Greedy ordering is a research diagnostic of historical incremental fixture coverage, not a new strategy rule or selection gate.",
 "Training ranking uses only 2019-2023, but the original R7 candidates were selected on those years and 2024 has been repeatedly inspected.",
 "Removing or adding a candidate can change earliest eligible horizon and majority direction; net-U differences are portfolio-level and not causal contribution.",
 "The 27 step counts are descriptive; do not interpret any step as an approved portfolio size.",
 "2025-2026 not used; no production or Telegram changes; retrospective Crown prices are not proven executable."])
(P/"R7_MARGINAL_COVERAGE_R32.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
