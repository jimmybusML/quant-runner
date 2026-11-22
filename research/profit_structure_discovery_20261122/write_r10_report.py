#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.load(open(p/"combined_88_r10_results.json"))
lines=["# R10 | Combined 88 five-year-positive candidates, 2019-2023 only","",
"27 R7 and 61 R9 candidate definitions, each selected for positive annual net U in 2019-2023. The selection and portfolio accounting are in-sample, NOT independent forward validation.","",
"## Coverage and conflicts","",
f"Signals {a['audit']['signal_hits']}; unique FIDs {a['audit']['unique_fids']}; multi-signal FIDs {a['audit']['multi_signal_fids']}; opposite-side FIDs {a['audit']['conflict_fids']}; R7-R9 overlap FIDs {a['audit']['old_new_overlap_fids']}; tied majority FIDs {a['audit']['tied_vote_fids']}; candidate pairs with overlap {a['audit']['pairwise_overlap_pairs']}.","",
"## Portfolio scenarios","",
"Each scenario counts at most one fixture exposure (1U). Earliest picks greatest horizon and lexical tie-break. Unanimous and majority are exploratory non-production filtering variants. Fractional equal-weight mixing opposite sides is theoretical accounting, not a single executable bet.","",
"| Scenario | 2019 n/netU | 2020 n/netU | 2021 n/netU | 2022 n/netU | 2023 n/netU | Total N | Net U | ROI | MDD U | Losing months |",
"|---|---|---|---|---|---|---:|---:|---:|---:|---:|"]
for name,z in a["portfolios"].items():
 years=" | ".join(f"{z['years'][str(y)]['n']} / {z['years'][str(y)]['net_U']:+.3f}" for y in range(2019,2024))
 lines.append(f"| {name} | {years} | {z['overall']['n']} | {z['overall']['net_U']:+.3f} | {z['overall']['roi_pct']:+.4f}% | {z['max_drawdown_U']:.3f} | {z['losing_months']} |")
lines+=["","## Pairwise redundancy","",
"All pairwise candidate intersections, same/opposite direction, in combined_88_r10_pairwise.csv.","",
"| Candidate A | Candidate B | Shared fixtures | Same direction | Opposite direction |",
"|---|---|---:|---:|---:|"]
for x in a["pairwise"][:15]:
 lines.append(f"| {x['candidate_a']} | {x['candidate_b']} | {x['shared']} | {x['same']} | {x['opposite']} |")
lines+=["","## Full monthly performance and drawdown","",
"combined_88_r10_monthly.csv includes all months and all six scenarios; combined_88_r10_results.json includes annual and monthly results, drawdown peaks/troughs, and full pairwise results.","",
"## Validation and limitations","",
"- All 88 candidate signal counts and net U were reconciled to the individually published R7/R9 discovery results. Each portfolio year/month count reconciles with its full count; profit totals reconcile to rounding precision.",
"- The R10 old27_only maximum drawdown (23.125U) differs from R8 (23.795U) because fixtures with identical kickoff timestamps are ordered differently. This is a tie-order sensitivity, not a changed set of orders or total profit. Intraday ordering convention must be reconciled before treating max drawdown as final.",
"- Candidate selection used all five years 2019-2023, and the same five years were evaluated: severe in-sample selection/multiple-testing bias. Positive years do not establish predictive ability.",
"- Majority votes count candidate definitions, not independent mechanisms; near-duplicate structures can dominate votes. No correlation-adjusted or truly rolling weight results are claimed.",
"- Historical Crown quote event timestamps were retrieved retrospectively in 2026, not evidence of executable historical quotes.",
"- No 2024-2026 data was used; frozen M8 and production untouched. All combinations are user-review scenarios, not new rules.",""]
(p/"COMBINED_88_R10_2019_2023.md").write_text("\n".join(lines))
h=Path("PROJECT_HANDOFF.md");s=h.read_text();title="## 2026-11-22 | R10 88 candidate overlap and portfolio audit"
if title not in s:
 note=title+"\n\n- User authorized next step to combine 27 R7 and 61 R9 structures for 2019-2023-only fixture de-duplication, direction conflict and yearly/monthly/drawdown audit, without modifying production. Ran combined_88_r10.py: 88 candidates reconcile individually to R7/R9 counts/netU; 14,890 signal hits; 6,753 unique FIDs; 3,849 multi-signal FIDs; 948 conflicting FIDs; 1,249 old/new overlap FIDs; 345 tied votes; 1,357 overlapping candidate pairs. Research scenarios: earliest 6,753 +457.750U/+6.7785% MDD35.820U; equal fractional 6,753 +472.529U/+6.9973% MDD28.294U; unanimous 5,805 +453.395U/+7.8104% MDD31.450U; majority 6,408 +511.700U/+7.9853% MDD23.530U. Annual/monthly, pairwise details in COMBINED_88_R10_2019_2023.md and CSV/JSON.\n- All results in-sample selected 2019-2023, NOT OOS. Majority votes are correlated candidate definitions. Historical Crown quotes retrospectively retrieved in 2026. Note R8 old27 MDD23.795 vs R10 old27 MDD23.125 due same-kickoff ordering sensitivity, not changed profit; resolve before final drawdown assertions. No 2024-2026 used, M8/production unchanged. All scenarios pending user approval.\n\n"
 h.write_text(note+s)
print("REPORT",len(lines))
