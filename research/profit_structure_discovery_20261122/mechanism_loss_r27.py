#!/usr/bin/env python3
"""R27: original 494 mechanism overlap and 2024 fixed portfolio loss characteristics."""
import collections,json,runpy,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"forward_2024_r24.py"))
groups=r["groups"];fids=r["fids"];catalog=r["catalog"]
selected={}
for fid,ks in fids.items():
 k=max(ks,key=lambda x:x[2]);s=groups[k];h=len(s["home"]);a=len(s["away"])
 if h==a:continue
 side="home" if h>a else "away"
 selected[(k[0],k[1],k[2])]=dict(horizon=k[2],pnl=s[side][0][1],side=side,home_votes=h,away_votes=a,
   chosen_batches=sorted({catalog[c]["batch"] for c,p in s[side]}),
   opposed_batches=sorted({catalog[c]["batch"] for c,p in s["away" if side=="home" else "home"]}),
   chosen_candidates=[c for c,p in s[side]],opposed_candidates=[c for c,p in s["away" if side=="home" else "home"]])
# Source row audit, only selected 2024 horizon; no league metadata.
for line in r["SRC"].open():
 a=json.loads(line)
 if str(a.get("year"))!="2024" or a.get("market")!="AH":continue
 k=(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]))
 if k not in selected:continue
 z=selected[k]
 z.update(line=abs(float(a["line"])),signed_line=float(a["line"]),
  odds=float(a["odds"][z["side"]]),overround=1/float(a["odds"]["home"])+1/float(a["odds"]["away"])-1,
  hours=float(a["actual_hours_before_kickoff"]),ticks=int(a.get("window_ticks_available") or 0),
  movement=abs(float(a.get("line_delta_since_first_quote") or 0)),
  prob_movement=abs(float(a.get("same_line_no_vig_probability_delta_side1") or 0)))
assert all("line" in z for z in selected.values())
def stat(vals):
 n=len(vals);s=sum(vals)
 return dict(n=n,net_U=round(s,3),roi_pct=round(100*s/n,4) if n else None)
dimensions=collections.defaultdict(lambda:collections.defaultdict(list))
for z in selected.values():
 pnl=z["pnl"]
 features={
 "line_abs": "0" if z["line"]==0 else "0.25-0.75" if z["line"]<=.75 else "1-1.75" if z["line"]<=1.75 else "2+",
 "odds": "<1.8" if z["odds"]<1.8 else "1.8-1.9" if z["odds"]<1.9 else "1.9-2.0" if z["odds"]<2 else "2.0-2.1" if z["odds"]<2.1 else "2.1+",
 "overround": "<3%" if z["overround"]<.03 else "3-5%" if z["overround"]<.05 else "5-7%" if z["overround"]<.07 else "7%+",
 "line_movement": "0" if z["movement"]==0 else "<=0.25" if z["movement"]<=.25 else "<=0.75" if z["movement"]<=.75 else ">0.75",
 "ticks": "1" if z["ticks"]==1 else "2" if z["ticks"]==2 else "3-5" if z["ticks"]<=5 else "6+",
 "vote_support": "1" if len(z["chosen_candidates"])==1 else "2" if len(z["chosen_candidates"])==2 else "3-5" if len(z["chosen_candidates"])<=5 else "6+",
 "distinct_batches":str(len(z["chosen_batches"])),
 "direction":z["side"],
 "conflict":"yes" if z["opposed_candidates"] else "no",
 "horizon":"T"+str(z["horizon"]),
 }
 for dim,group in features.items():dimensions[dim][group].append(pnl)
 for b in z["chosen_batches"]:dimensions["batch_present_chosen"][b].append(pnl)
 for b in z["opposed_batches"]:dimensions["batch_present_opposed"][b].append(pnl)
result={d:{k:stat(v) for k,v in sorted(groups.items())} for d,groups in dimensions.items()}
# 2024 sensitivity without new candidate definitions: leave one existing research batch out, same earliest quote and equal vote
ablation={}
for remove in sorted(set(v["batch"] for v in catalog.values())):
 pnl=[]
 for k in selected:
  sides=groups[k]
  count={s:sum(catalog[c]["batch"]!=remove for c,p in sides[s]) for s in ("home","away")}
  if count["home"]==count["away"]:continue
  side="home" if count["home"]>count["away"] else "away"
  pnl.append(sides[side][0][1])
 ablation[remove]=stat(pnl)
out=dict(scope="2024 only, frozen original 494 definitions; earliest quote equal-net fixed portfolio",
 baseline=stat([z["pnl"] for z in selected.values()]),dimensions=result,
 batch_leave_one_out_2024_exploratory=ablation,
 caveats=["All dimension bands are descriptive, not new user rules or recommended filters.",
 "2024 leave-one-batch-out is post-hoc sensitivity, not a preselected 2024 portfolio or independent proof.",
 "Batch-presence segments overlap, so do not add their net returns.",
 "Retrospective Crown quotes do not establish historical live availability.",
 "No 2025-2026 outcomes or production modifications."])
(P/"MECHANISM_LOSS_R27_2024.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("BASELINE",out["baseline"],flush=True)
for d in ("line_abs","odds","overround","line_movement","ticks","vote_support","distinct_batches","batch_present_chosen","batch_present_opposed"):
 print("DIM",d,result[d],flush=True)
print("ABLATION",ablation,flush=True)
