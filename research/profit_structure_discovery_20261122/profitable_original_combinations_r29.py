#!/usr/bin/env python3
"""R29: 2024-observed profitable ORIGINAL candidate overlaps and fixture-deduplicated portfolios."""
import collections,json,runpy,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
diag=json.loads((P/"LOSS_ATTRIBUTION_R25_2024.json").read_text())
ranked=sorted(diag["candidates"],key=lambda c:c["test"]["net_U"],reverse=True)
winners={c["id"] for c in ranked if c["test"]["net_U"]>0}
top6={c["id"] for c in ranked[:6]}
top12={c["id"] for c in ranked[:12]}
r24=runpy.run_path(str(P/"forward_2024_r24.py"))
r20=runpy.run_path(str(P/"weight_conflict_r20.py"))
def metric(vals):
 n=len(vals);p=sum(vals)
 return dict(n=n,net_U=round(p,3),roi_pct=round(p/n*100,4) if n else None)
def evaluate(groups,selected):
 # one candidate per fixture-horizon-side; earliest horizon with any eligible original signal
 fi=collections.defaultdict(list);single=collections.defaultdict(list)
 for k,sides in groups.items():
  byside={}
  for side in ("home","away"):
   matched=[(cid,p) for cid,p in sides[side] if cid in selected]
   if matched:byside[side]=matched
   for cid,p in matched:single[cid].append((k[:2],k[2],side,p))
  if byside:fi[k[:2]].append((k,byside))
 outcomes=collections.defaultdict(list)
 overlap=collections.Counter()
 for fixture,ks in fi.items():
  k,sides=max(ks,key=lambda v:v[0][2])
  home=sides.get("home",[]);away=sides.get("away",[])
  count=len(home)+len(away)
  overlap["fixtures_any"]+=1
  overlap["fixtures_multiple_candidates"]+=count>1
  overlap["fixtures_opposed"]+=bool(home and away)
  overlap["fixtures_one_side"]+=bool(home)^bool(away)
  overlap["fixtures_tied"]+=len(home)==len(away)
  overlap["signal_occurrences_at_selected_horizon"]+=count
  if len(home)==len(away):continue
  side="home" if len(home)>len(away) else "away"
  p=(home if side=="home" else away)[0][1]
  outcomes["equal_net"].append((k[0][:4],p))
  if not(home and away):outcomes["skip_opposite"].append((k[0][:4],p))
  if abs(len(home)-len(away))>=2:outcomes["margin2_descriptive"].append((k[0][:4],p))
 bypolicy={}
 for policy,vals in outcomes.items():
  bypolicy[policy]=dict(overall=metric([p for y,p in vals]),
   years={str(y):metric([p for year,p in vals if year==str(y)]) for y in range(2019,2025) if any(year==str(y) for year,p in vals)})
 return dict(overlap=dict(overlap),policies=bypolicy)
sets={"all_494":set(r24["catalog"]),"2024_profitable_208_POSTHOC":winners,
 "top6_by_2024_net_POSTHOC":top6,"top12_by_2024_net_POSTHOC":top12}
out={"scope":"Frozen 494 original R7-R15 candidates. 2024 profitability observed after the fact; no 2024 validation of selected winners.",
 "sets":{},"candidates_top12":[dict(id=c["id"],train_n=c["train_n"],train_roi_pct=c["train_roi_pct"],test=c["test"]) for c in ranked[:12]],
 "caveats":["The 208/top6/top12 sets are selected with 2024 outcomes; 2024 performance is selection-biased and NOT a forward test.",
 "Training 2019-2023 already used to select original 494; historical outcomes are in-sample.",
 "Every fixture counted once per portfolio; choose earliest eligible signal horizon and majority side at that horizon.",
 "When the selected candidate set changes, the earliest eligible horizon can change, so comparisons are not identical-order marginal contributions.",
 "Skip-opposite and margin2 are research descriptive alternative policies, not new user-approved production gates.",
 "Retrospective Crown quotes are not proven executable. No 2025-2026 or production changes."]}
for name,ids in sets.items():
 print("RUN",name,len(ids),flush=True)
 out["sets"][name]={"definitions":len(ids),"historical":evaluate(r20["groups"],ids),"year2024":evaluate(r24["groups"],ids)}
 print("DONE",name,"train",out["sets"][name]["historical"]["policies"].get("equal_net",{}).get("overall"),
 "2024",out["sets"][name]["year2024"]["policies"].get("equal_net",{}).get("overall"),flush=True)
(P/"PROFITABLE_ORIGINAL_COMBINATIONS_R29.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
