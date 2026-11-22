#!/usr/bin/env python3
"""R26: compare frozen 2019-23 structure characteristics against 2024 without refitting."""
import json,collections,math,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
z=json.loads((P/"LOSS_ATTRIBUTION_R25_2024.json").read_text())
files={"R7":"five_year_review_r7_results.json","R9":"expanded_five_year_r9_results.json",**{f"R{i}":f"new_mechanisms_r{i}_results.json" for i in range(11,16)}}
train={}
for b,f in files.items():
 for c in json.loads((P/f).read_text())["candidates"]:train[c["id"]]=c
def stat(rows):
 n=sum(x["test"]["n"] for x in rows);p=sum(x["test"]["net_U"] for x in rows)
 return dict(definitions=len(rows),profitable=sum(x["test"]["net_U"]>0 for x in rows),test_n=n,test_net_U=round(p,3),test_roi_pct=round(100*p/n,4) if n else None,
 median_candidate_roi_pct=round(statistics.median(x["test"]["roi_pct"] for x in rows),4) if rows else None)
def quantile(x,field,k=4):
 arr=sorted(x,key=lambda v:(field(v),v["id"]))
 return {str(i+1):dict(train_range=[round(field(arr[i*len(arr)//k]),4),round(field(arr[min(len(arr)-1,(i+1)*len(arr)//k-1)]),4)],**stat(arr[i*len(arr)//k:(i+1)*len(arr)//k])) for i in range(k)}
rows=[]
for x in z["candidates"]:
 t=train[x["id"]]
 annual=[t["years"][str(y)] for y in range(2019,2024)]
 rois=[q["roi_pct"] for q in annual]
 profits=[q["net_U"] for q in annual]
 months=t.get("months",{})
 active=[q for q in months.values() if q["n"]>0]
 x=dict(x,train_year_roi_std=statistics.pstdev(rois),train_worst_year_roi=min(rois),
 train_best_year_roi=max(rois),train_profit_largest_year_share=max(profits)/sum(profits) if sum(profits)>0 else None,
 train_months_active=len(active),train_months_profitable=sum(q["net_U"]>0 for q in active),
 train_month_positive_fraction=sum(q["net_U"]>0 for q in active)/len(active) if active else None,
 train_year_sample_min=min(q["n"] for q in annual),train_year_sample_max=max(q["n"] for q in annual),
 horizon=x["id"].split("|")[0],direction=x["id"].split("|")[-1],
 family=x["id"].split("|")[1])
 rows.append(x)
def pearson(key):
 x=[float(r[key]) for r in rows];y=[float(r["test"]["roi_pct"]) for r in rows]
 mx=statistics.mean(x);my=statistics.mean(y)
 num=sum((a-mx)*(b-my) for a,b in zip(x,y))
 den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
 return round(num/den,5) if den else None
quartiles={k:quantile(rows,lambda r:r[k]) for k in ("train_n","train_roi_pct","train_year_roi_std","train_worst_year_roi","train_profit_largest_year_share","train_month_positive_fraction")}
groups={}
for key in ("batch","horizon","direction"):
 group=collections.defaultdict(list)
 for x in rows:group[x[key]].append(x)
 groups[key]={k:stat(v) for k,v in sorted(group.items())}
families=collections.defaultdict(list)
for x in rows:
 for f in x["family"].split(","):families[f].append(x)
groups["feature_presence"]={k:stat(v) for k,v in sorted(families.items())}
# Train-only monthly stability, year count, etc. Outcome-conditioned groups are diagnostic not selection.
positive=[r for r in rows if r["test"]["net_U"]>0]
negative=[r for r in rows if r["test"]["net_U"]<0]
comparisons={}
for k in ("train_n","train_roi_pct","train_year_roi_std","train_worst_year_roi","train_profit_largest_year_share","train_month_positive_fraction"):
 comparisons[k]=dict(positive_median=round(statistics.median(r[k] for r in positive),5),negative_median=round(statistics.median(r[k] for r in negative),5),
 pearson_vs_test_roi=pearson(k))
out=dict(scope="2019-2023 frozen 494 candidate characteristics vs 2024 descriptive outcomes",
 candidate_summary=z["candidate_summary"],quartiles=quartiles,groups=groups,comparisons=comparisons,
 caveats=["2024 profitable-vs-losing comparison is retrospective and cannot be used to select 2024 winners.",
 "Candidate outcomes overlap and sum of candidate PnL is not a tradable portfolio.",
 "Training all-five-years-positive candidate selection creates strong selection bias.",
 "No independent 2025-2026 evaluation; no Crown live executability proof.",
 "Feature groups overlap, and group totals are not additive."])
(P/"CROSSYEAR_DIAGNOSTICS_R26.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
for k,v in comparisons.items():print("PREDICTOR",k,v,flush=True)
for k,v in quartiles.items():print("QUARTILE",k,[(j,q["profitable"],q["definitions"],q["test_roi_pct"]) for j,q in v.items()],flush=True)
for k in ("batch","horizon","direction"):print("GROUP",k,groups[k],flush=True)
