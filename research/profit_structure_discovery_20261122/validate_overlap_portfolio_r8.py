#!/usr/bin/env python3
import json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
a=json.load(open(P/"overlap_portfolio_r8_results.json"))
r=json.load(open(P/"five_year_review_r7_results.json"))
assert a["audit"]["candidate_count"]==len(r["candidates"])==27
assert a["audit"]["total_signals"]==sum(z["overall"]["n"] for z in r["candidates"])
assert a["audit"]["unique_fids"]==a["audit"]["any_signal_fids"]==2527
assert a["audit"]["opposite_signal_fids"]<=a["audit"]["multi_signal_fids"]
assert a["audit"]["pair_count_with_overlap"]==len(a["pairwise"])
for pair in a["pairwise"]:
 assert pair["same_fixture"]==pair.get("same_side",0)+pair.get("opposite_side",0)
for name,z in a["portfolios"].items():
 assert z["all"]["n"]==sum(v["n"] for v in z["years"].values())
 assert abs(z["all"]["net_U"]-sum(v["net_U"] for v in z["years"].values()))<.002
 assert z["all"]["n"]==sum(v["n"] for v in z["months"].values())
 assert abs(z["all"]["net_U"]-sum(v["net_U"] for v in z["months"].values()))<.035
 assert z["max_drawdown_U"]>=0
 assert z["all"]["n"]<=a["audit"]["unique_fids"]
assert a["portfolios"]["earliest_one_signal"]["all"]["n"]==a["audit"]["unique_fids"]
assert a["portfolios"]["equal_signal_fractional_blend"]["all"]["n"]==a["audit"]["unique_fids"]
assert a["portfolios"]["unanimous_same_side"]["all"]["n"]==a["audit"]["unique_fids"]-a["audit"]["opposite_signal_fids"]
assert a["portfolios"]["majority_vote"]["all"]["n"]==a["audit"]["unique_fids"]-a["audit"]["tie_fids"]
out={"validated":True,"candidate_count":27,"signal_count":a["audit"]["total_signals"],"unique_fids":a["audit"]["unique_fids"],
"pairwise_side_reconciliation":True,"year_month_portfolio_reconciliation":True,
"portfolio_counts_match_conflict_and_tie_counts":True,
"limitations":"Cross-checks against R7 totals, not independent re-settlement of raw market source. All scenarios selected in-sample."}
(P/"overlap_portfolio_r8_validation.json").write_text(json.dumps(out,indent=2)+"\n")
print("VALIDATED",out)
