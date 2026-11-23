#!/usr/bin/env python3
"""R42 exact AH five-state settlement calibration and price audit of existing M5/M7 rows."""
import collections,json,math
from pathlib import Path
from research.m3.probabilities import settle_score,expected_unit_return
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_all_orders.jsonl")
STATES=("FULL_LOSS","HALF_LOSS","PUSH","HALF_WIN","FULL_WIN")
bins=collections.defaultdict(list);coverage=collections.Counter();mismatches=[]
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH":continue
 coverage["AH_rows"]+=1
 try:
  c=a["m5_settlement_class_probabilities"];bl=a["blended_class_probabilities"]
  if not isinstance(c,list) or len(c)!=5 or not isinstance(bl,list) or len(bl)!=5:coverage["missing_class_vector"]+=1;continue
  price=float(a["crown_odds"]);line=float(a["line"]);side=a["direction"]
  hg,ag=map(int,a["final_score"].split("-"))
  state,pnl=settle_score("AH",line,side,hg,ag,price)
  if abs(pnl-float(a["net_profit_units"]))>1e-6:
   coverage["settlement_mismatch"]+=1
   if len(mismatches)<5:mismatches.append(dict(id=a.get("match_id"),line=line,side=side,score=a["final_score"],calculated=pnl,recorded=a["net_profit_units"]))
   continue
  if abs(sum(c)-1)>1e-6 or abs(sum(bl)-1)>1e-6:coverage["invalid_vector"]+=1;continue
  ev=expected_unit_return(dict(zip(STATES,c)),price)
  if abs(ev-float(a["theoretical_ev"]))>1e-5:
   coverage["model_ev_mismatch"]+=1
   if len(mismatches)<5:mismatches.append(dict(id=a.get("match_id"),calculated_ev=ev,recorded_ev=a["theoretical_ev"]))
   continue
  blend_ev=expected_unit_return(dict(zip(STATES,bl)),price)
  if a.get("blend_selected_ev") is not None and abs(blend_ev-float(a["blend_selected_ev"]))>1e-5:coverage["blend_ev_mismatch"]+=1
  y=str(a["year"]);row=dict(id=str(a["match_id"]),state=state,price=price,model=list(map(float,c)),blend=list(map(float,bl)),ev=ev,blend_ev=blend_ev,pnl=pnl,
    quote_class=a.get("capture_classification"),model_cutoff=a.get("model_information_cutoff_local"),quote_time=a.get("quote_event_time_local"))
  bins[y].append(row);coverage["validated"]+=1
 except Exception as exc:
  coverage["invalid_row"]+=1
  if len(mismatches)<5:mismatches.append(str(exc))
def summ(v):
 n=len(v)
 if not n:return dict(n=0)
 mean=lambda f:sum(f(r) for r in v)/n
 states={s:sum(r["state"]==s for r in v) for s in STATES}
 def scores(key):
  brier=mean(lambda r:sum((r[key][i]-(r["state"]==s))**2 for i,s in enumerate(STATES)))
  logloss=mean(lambda r:-math.log(max(r[key][STATES.index(r["state"])],1e-12)))
  return dict(multiclass_brier=round(brier,6),multiclass_logloss=round(logloss,6),
   predicted_state_rates={s:round(mean(lambda r:r[key][i]),6) for i,s in enumerate(STATES)})
 return dict(n=n,unique_fixtures=len({r["id"] for r in v}),actual_state_counts=states,
  actual_state_rates={s:round(states[s]/n,6) for s in STATES},
  m5=scores("model"),market_adjusted_blend=scores("blend"),
  model_predicted_EV=round(mean(lambda r:r["ev"]),6),
  blend_predicted_EV=round(mean(lambda r:r["blend_ev"]),6),
  realized_net_U_per_order=round(mean(lambda r:r["pnl"]),6),
  mean_model_EV_error=round(mean(lambda r:r["ev"]-r["pnl"]),6),
  mean_blend_EV_error=round(mean(lambda r:r["blend_ev"]-r["pnl"]),6),
  source_capture_classes=dict(collections.Counter(r["quote_class"] for r in v)))
out=dict(scope="R42 exact five-state Asian settlement calibration; M5 annual score-grid and pre-existing market-adjusted blend, not R7",
 source=str(SRC),class_order=list(STATES),coverage=dict(coverage),mismatches=mismatches,
 years={y:summ(v) for y,v in sorted(bins.items())},
 caveats=["Verified class order by independently recomputing theoretical EV and AH settlement from raw line, side, score and odds.",
 "Market-adjusted blend is not an independent bookmaker probability distribution: it incorporates model information; no pure Crown five-state market distribution is identified from a single two-sided AH quote.",
 "Five-state multiclass Brier and logloss compare M5 and pre-existing blend on same outcome target, but market-independent superiority cannot be inferred.",
 "M5 forecasts and blend may have different information provenance or hindsight model-selection; not a prospectively registered experiment.",
 "All price-paired historical Crown records were retrieved after kickoff, not proof of real-time executable odds.",
 "2025 and 2026 are existing M5/M7 historical research cohorts, not original R7 or official Telegram wagers.",
 "No new strategy, thresholds, portfolio changes or production writes."])
(P/"SETTLEMENT_PRICING_AUDIT_R42.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R42",json.dumps(dict(coverage=out["coverage"],mismatches=out["mismatches"],years={y:dict(n=v["n"],m5=v["m5"]["multiclass_brier"],blend=v["market_adjusted_blend"]["multiclass_brier"],model_EV=v["model_predicted_EV"],blend_EV=v["blend_predicted_EV"],realized=v["realized_net_U_per_order"]) for y,v in out["years"].items()}),ensure_ascii=False),flush=True)
