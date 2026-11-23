#!/usr/bin/env python3
"""R43 trace source training/selection and verify exact odds calibration effect."""
import ast,collections,hashlib,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_all_orders.jsonl")
CODE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend.py")
SUMMARY=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_frozen_market_probability_blend_summary.json")
summary=json.loads(SUMMARY.read_text());rows=collections.defaultdict(list);bad=collections.Counter()
for line in SRC.open():
 r=json.loads(line)
 if r.get("market")!="AH":continue
 y=str(r["year"]);od=float(r["crown_odds"]);opp=float(r["opposite_crown_odds"])
 p=list(map(float,r["m5_settlement_class_probabilities"]))
 a=list(map(float,r["crown_market_adjusted_class_probabilities"]))
 b=list(map(float,r["blended_class_probabilities"]))
 q=float(r["crown_no_vig_probability"])
 qfrom=(1/od)/((1/od)+(1/opp))
 if abs(q-qfrom)>1e-8:bad["no_vig_mismatch"]+=1
 def eff(x):
  w=x[4]+.5*x[3];l=x[0]+.5*x[1]
  return w/(w+l) if w+l>0 else None
 fair=eff(a)
 if fair is None or abs(fair-q)>1e-8:bad["adjusted_effective_win_share_mismatch"]+=1
 if abs(a[2]-p[2])>1e-8:bad["push_changed"]+=1
 if max(abs(x-y) for x,y in zip(a,b))>1e-8:bad["blend_not_full_market_adjusted"]+=1
 def ev(x):return (x[4]+.5*x[3])*(od-1)-x[0]-.5*x[1]
 margin=1/od+1/opp-1
 rows[y].append(dict(market_margin=margin,raw_ev=ev(p),adjusted_ev=ev(a),adjusted_effective_share=fair,
  model_effective_share=eff(p),market_share=q,actual=float(r["net_profit_units"]),
  positive_adjusted=ev(a)>1e-10,positive_raw=ev(p)>1e-10,
  source_class=r.get("capture_classification"),weight=float(r["market_blend_weight_2025"]),
  model_cutoff=r.get("model_information_cutoff_local"),quote_event=r.get("quote_event_time_local")))
def summ(rs):
 n=len(rs);mean=lambda k:sum(x[k] for x in rs)/n
 return dict(n=n,market_margin_mean=round(mean("market_margin"),6),
  raw_ev_mean=round(mean("raw_ev"),6),adjusted_ev_mean=round(mean("adjusted_ev"),6),
  actual_mean=round(mean("actual"),6),
  raw_effective_win_share_mean=round(mean("model_effective_share"),6),
  market_effective_win_share_mean=round(mean("market_share"),6),
  mean_raw_minus_market_share=round(mean("model_effective_share")-mean("market_share"),6),
  positive_raw_ev_count=sum(x["positive_raw"] for x in rs),
  positive_adjusted_ev_count=sum(x["positive_adjusted"] for x in rs),
  adjusted_ev_max=round(max(x["adjusted_ev"] for x in rs),8),
  adjusted_ev_min=round(min(x["adjusted_ev"] for x in rs),8),
  weight_values=sorted(set(x["weight"] for x in rs)),
  capture_classes=dict(collections.Counter(x["source_class"] for x in rs)))
out=dict(scope="R43 provenance and exact pricing identity for R42 M5/M7 AH model",
 code_path=str(CODE),code_sha256=hashlib.sha256(CODE.read_bytes()).hexdigest(),
 summary_path=str(SUMMARY),summary_sha256=hashlib.sha256(SUMMARY.read_bytes()).hexdigest(),
 source_rows=str(SRC),source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),
 source_training_2025_AH=summary["blend_weights"]["AH"],
 source_checks=summary["checks"],
 source_2026_AH_portfolio=summary["results"]["2026"]["AH"],
 audit_errors=dict(bad),years={y:summ(v) for y,v in sorted(rows.items())},
 pricing_identity="For adjusted vector, effective win share q=(1/selected_odds)/(1/selected_odds+1/opposite_odds). With W=p_fullwin+0.5*p_halfwin and L=p_fullloss+0.5*p_halfloss, W/(W+L)=q, hence EV_adjusted=W*(odds-1)-L=(W+L)*(q*odds-1), strictly negative for positive bookmaker overround and W+L>0. Therefore 100% market-adjusted weight cannot have positive EV for either side at quoted odds.",
 caveats=["This is an algebraic result of the market_adjust function, not evidence of discovered predictive mispricing.",
 "2025 blend weight chosen using 2025 actual settlement outcomes; 2025 model-vs-blend logloss comparison is in-sample.",
 "2026 frozen weight is later historical test, but Crown responses were retrieved after kickoff, not live executable.",
 "The 2026 positive-EV portfolio has 0 orders by construction when AH weight=1 and both sides use same odds-derived q; this is not evidence of a successful profitable selection strategy.",
 "No pure independent Crown five-class distribution is observed. The adjusted distribution retains M5 push and full/half mix.",
 "This is M5/M7 historical research, NOT R7 27, all494 or official Telegram orders.",
 "No production changes, new filters, thresholds, or gates."])
(P/"BLEND_PROVENANCE_R43.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R43",json.dumps(dict(audit_errors=out["audit_errors"],years=out["years"],fit=out["source_training_2025_AH"],portfolio=out["source_2026_AH_portfolio"]),ensure_ascii=False),flush=True)
