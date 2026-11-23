#!/usr/bin/env python3
"""R41 read-only audit of pre-existing M7 AH probability/market records.
Do not equate binary positive-return probabilities with Asian full/half settlement EV."""
import collections,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_all_orders.jsonl")
groups=collections.defaultdict(list)
coverage=collections.Counter()
examples=[]
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH":continue
 year=str(a.get("year"));coverage["AH_rows"]+=1
 key=(year,str(a.get("match_id")),str(a.get("window")),str(a.get("direction")))
 if any(a.get(x) is None for x in ("model_probability_positive_return","crown_no_vig_probability","theoretical_ev","net_profit_units")):
  coverage["missing_core"]+=1;continue
 p=float(a["model_probability_positive_return"]);m=float(a["crown_no_vig_probability"]);ev=float(a["theoretical_ev"]);net=float(a["net_profit_units"])
 if not all(map(math.isfinite,(p,m,ev,net))):coverage["nonfinite"]+=1;continue
 if not 0<=p<=1 or not 0<=m<=1:coverage["invalid_prob"]+=1;continue
 row=dict(key=key,year=year,p=p,m=m,ev=ev,net=net,positive=float(net>0),
  quote_class=str(a.get("capture_classification")),model=str(a.get("model")),window=str(a.get("window")),
  model_asof=str(a.get("model_information_cutoff_local")),
  quote_event=str(a.get("quote_event_time_local")))
 groups[year].append(row)
 coverage["complete"]+=1
def summarize(v):
 n=len(v)
 if not n:return dict(n=0)
 mean=lambda field:sum(r[field] for r in v)/n
 return dict(n=n,unique_fixtures=len({r["key"][1] for r in v}),
  mean_model_positive_return_probability=round(mean("p"),6),
  realized_positive_return_rate=round(mean("positive"),6),
  positive_return_probability_bias_pp=round(100*(mean("p")-mean("positive")),4),
  model_binary_brier=round(sum((r["p"]-r["positive"])**2 for r in v)/n,6),
  market_no_vig_share_binary_brier_DIAGNOSTIC_ONLY=round(sum((r["m"]-r["positive"])**2 for r in v)/n,6),
  mean_model_minus_market_no_vig_share=round(mean("p")-mean("m"),6),
  mean_theoretical_EV=round(mean("ev"),6),
  mean_realized_net_U=round(mean("net"),6),
  mean_EV_minus_realized_net_U=round(mean("ev")-mean("net"),6),
  quote_capture_classes=dict(collections.Counter(r["quote_class"] for r in v)),
  model_ids=dict(collections.Counter(r["model"] for r in v)))
def buckets(v,field,edges):
 b=collections.defaultdict(list)
 for r in v:
  ix=sum(r[field]>=e for e in edges)
  b[str(ix)].append(r)
 return {k:summarize(vals) for k,vals in sorted(b.items())}
out=dict(scope="R41 first diagnostic of existing M7 AH model probabilities vs Crown quote prices; separate from R7 494 pattern test",
 source=str(SRC),coverage=dict(coverage),years={y:dict(summary=summarize(v),model_probability_bins=buckets(v,"p",[.4,.5,.6,.7,.8]),model_minus_market_bins=buckets([{**r,"edge":r["p"]-r["m"]} for r in v],"edge",[-.1,0,.1,.2,.3])) for y,v in sorted(groups.items())},
 caveats=[
 "Market no-vig share is a normalized two-side quoted odds share; it is NOT the probability of positive net return for Asian quarter-line or push/half outcomes. Market Brier against positive return is only a deliberately labeled non-comparable diagnostic and cannot rank market vs model.",
 "Model positive-return probability cannot by itself determine full/half-win/half-loss/push EV. Require settlement-class probabilities or exact score matrix for fair price comparison.",
 "These pre-existing M7 records have their own model identity, fixture universe and entry windows, not original R7 27 or all494. Never transfer their predictive metrics to R7.",
 "Historical Crown responses captured after kickoff are not live executable; capture classification must be checked.",
 "Rows can include repeated fixtures across windows, directions or model versions; n is rows, not independent fixture count.",
 "These model forecasts may have been trained or selected on past data; no new strategy selection or production rule.",
 "2026 rows, if present, are an audit of existing records only and do not imply prospective live validation."])
(P/"PREDICTION_MARKET_AUDIT_R41.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R41",json.dumps({y:z["summary"] for y,z in out["years"].items()},ensure_ascii=False),flush=True)
