#!/usr/bin/env python3
"""R25: 2024 loss attribution of frozen candidate definitions and unchanged portfolios."""
import collections,json,runpy,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"forward_2024_r24.py"))
catalog=r["catalog"];groups=r["groups"];fids=r["fids"]
candidate=collections.defaultdict(list)
for k,sides in groups.items():
 for side,vals in sides.items():
  for c,pnl in vals:candidate[c].append((k[0],k[1],k[2],side,pnl))
def stats(v):
 n=len(v);s=sum(v)
 return dict(n=n,net_U=round(s,3),roi_pct=round(s/n*100,4) if n else None)
per=[]
for c,meta in catalog.items():
 v=candidate[c];p=[z[4] for z in v]
 per.append(dict(id=c,batch=meta["batch"],train_n=meta["n"],train_roi_pct=round(meta["roi"]*100,4),
  train_net_U=round(meta["roi"]*meta["n"],3),test=stats(p),
  test_months={m:stats([x[4] for x in v if x[0][:7]==m]) for m in sorted({x[0][:7] for x in v})}))
batches={}
for b in sorted({v["batch"] for v in catalog.values()}):
 subset=[x for x in per if x["batch"]==b]
 batches[b]=dict(definitions=len(subset),positive=sum(x["test"]["net_U"]>0 for x in subset),
  negative=sum(x["test"]["net_U"]<0 for x in subset),zero=sum(x["test"]["net_U"]==0 for x in subset),
  aggregate_signal_occurrences=sum(x["test"]["n"] for x in subset),
  aggregate_net_U=round(sum(x["test"]["net_U"] for x in subset),3))
# Group per-fixture earliest quote baseline net, segment by calendar month, horizon, vote counts.
segments=collections.defaultdict(list);orders=[]
for fid,ks in fids.items():
 k=max(ks,key=lambda x:x[2]);sides=groups[k];nh=len(sides["home"]);na=len(sides["away"])
 if nh==na:continue
 side="home" if nh>na else "away";pnl=sides[side][0][1]
 orders.append((k[0],k[1],k[2],side,pnl,nh,na))
 for tag in ("month:"+k[0][:7],"horizon:T"+str(k[2]),"direction:"+side,
             "margin:"+str(min(5,abs(nh-na))),"conflict:"+("both_sides" if nh and na else "one_side")):
  segments[tag].append(pnl)
segment_stats={k:stats(v) for k,v in sorted(segments.items())}
# Distribution by historical ROI quartiles defined using training only.
sorted_c=sorted(per,key=lambda x:(x["train_roi_pct"],x["id"]))
quartiles={}
for i in range(4):
 arr=sorted_c[i*len(sorted_c)//4:(i+1)*len(sorted_c)//4]
 quartiles[str(i+1)]=dict(definitions=len(arr),test_positive=sum(x["test"]["net_U"]>0 for x in arr),
  signal_occurrences=sum(x["test"]["n"] for x in arr),
  test_net_U=round(sum(x["test"]["net_U"] for x in arr),3),
  test_roi_pct=round(100*sum(x["test"]["net_U"] for x in arr)/sum(x["test"]["n"] for x in arr),4) if sum(x["test"]["n"] for x in arr) else None,
  train_roi_range=[arr[0]["train_roi_pct"],arr[-1]["train_roi_pct"]])
out=dict(scope="Frozen 494 R7-R15 structures, 2024 only",candidates=per,
 candidate_summary=dict(total=len(per),positive=sum(x["test"]["net_U"]>0 for x in per),
 negative=sum(x["test"]["net_U"]<0 for x in per),zero=sum(x["test"]["net_U"]==0 for x in per),
 no_2024_signals=sum(x["test"]["n"]==0 for x in per)),
 batches=batches,training_roi_quartiles=quartiles,
 earliest_equal_net_orders=stats([x[4] for x in orders]),segments=segment_stats,
 caveats="Individual candidate results double-count overlaps and horizons; never sum as a feasible portfolio. Segment losses describe same fixed earliest/equal/net 2024 portfolio. All candidates selected on 2019-2023. 2024 retrospective Crown quotes may not be executable. No 2024 reselection, no production change.")
(P/"LOSS_ATTRIBUTION_R25_2024.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("CANDIDATES",out["candidate_summary"],flush=True)
print("BATCHES",batches,flush=True)
print("QUARTILES",quartiles,flush=True)
print("TOP POSITIVE",[(x["id"],x["test"]) for x in sorted(per,key=lambda x:x["test"]["net_U"],reverse=True)[:12]],flush=True)
print("TOP NEGATIVE",[(x["id"],x["test"]) for x in sorted(per,key=lambda x:x["test"]["net_U"])[:12]],flush=True)
print("SEGMENTS",segment_stats,flush=True)
