#!/usr/bin/env python3
import json,csv
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.load(open(p/"expanded_five_year_r9_results.json"))
with (p/"expanded_five_year_r9_review.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","five_year_n","five_year_net_U","five_year_roi_pct","max_drawdown_U"]+[v for y in range(2019,2024) for v in (f"{y}_n",f"{y}_net_U",f"{y}_roi_pct")])
 for z in a["candidates"]:
  w.writerow([z["id"],z["overall"]["n"],z["overall"]["net_U"],z["overall"]["roi_pct"],z["max_drawdown_U"]]+[z["years"][str(y)][key] for y in range(2019,2024) for key in ("n","net_U","roi_pct")])
with (p/"expanded_five_year_r9_monthly.csv").open("w",newline="") as f:
 w=csv.writer(f);w.writerow(["id","year_month","n","net_U","roi_pct"])
 for z in a["candidates"]:
  for month,v in z["months"].items():w.writerow([z["id"],month,v["n"],v["net_U"],v["roi_pct"]])
lines=["# R9: Expanded five-year positive candidate search (2019-2023 only)","",
"New candidate vocabulary: signed handicap line, actual bet-side odds, same-line no-vig probability movement and interactions. Feature bins are exploratory and not production rules.","",
f"Examined {a['audit']['all_new_vocabulary_candidates']} candidate definitions; {a['audit']['five_year_positive_candidates']} show positive net U in every year 2019-2023. With 27 prior R7 candidates, 88 candidate definitions total, not necessarily independent.","",
"## All 61 candidates, year by year","",
"| Candidate ID | 2019 ROI | 2020 ROI | 2021 ROI | 2022 ROI | 2023 ROI | N | Net U | ROI | Max DD U |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for z in a["candidates"]:
 ys=" | ".join(f"{z['years'][str(y)]['roi_pct']:+.2f}%" for y in range(2019,2024))
 lines.append(f"| {z['id']} | {ys} | {z['overall']['n']} | {z['overall']['net_U']:+.3f} | {z['overall']['roi_pct']:+.2f}% | {z['max_drawdown_U']:.3f} |")
lines+=["","## Monthly performance and drawdowns","",
"All 60 months for all 61 candidates (including zero-activity months): expanded_five_year_r9_monthly.csv. Full year/month and drawdown peak/trough data: expanded_five_year_r9_results.json.","",
"| Candidate ID | Active months | Profitable months | Losing months | Worst month | DD peak | DD trough |","|---|---:|---:|---:|---|---|---|"]
for z in a["candidates"]:
 active=[(k,v) for k,v in z["months"].items() if v["n"]];worst=min(active,key=lambda kv:kv[1]["net_U"])
 lines.append(f"| {z['id']} | {len(active)} | {sum(v['net_U']>0 for _,v in active)} | {sum(v['net_U']<0 for _,v in active)} | {worst[0]} ({worst[1]['net_U']:+.3f}U) | {z['drawdown_from'] or 'initial'} | {z['drawdown_to']} |")
lines+=["","## Audit boundaries","",
"- All candidates were selected within the same 2019-2023 period: five profitable years are NOT independent forward validation; multiple testing and in-sample selection bias apply.",
"- Candidate overlap, opposite-direction conflicts and de-duplicated combination returns are NOT YET computed for these 61 new structures; do not sum profits.",
"- Drawdown uses equal 1U stakes ordered by kickoff, not bankroll percentage.",
"- Same-line no-vig probability change uses source-side1 convention; it must not be assumed to mean odds movement in the selected bet direction.",
"- Crown event timestamps were retrieved retrospectively in 2026, not proof of actual historical executable prices.",
"- 2024-2026 excluded. All 61 are pending user review. Frozen M8 and production unchanged.",""]
(p/"EXPANDED_FIVE_YEAR_R9_2019_2023.md").write_text("\n".join(lines))
h=Path("PROJECT_HANDOFF.md");s=h.read_text();title="## 2026-11-22 | R9 expanded five-year candidate search"
if title not in s:
 note=title+"\n\n- User requested more structures profitable in each year 2019-2023, with individual review, without changing production. Executed expanded_five_year_r9.py on historical Crown AH, 12 new feature families (signed handicap, bet-side odds, same-line no-vig probability movement, interactions). 6,350 new candidate definitions, 61 profitable each of five years; combined with 27 R7 candidates = 88 candidate definitions, not independent strategies. Annual, monthly and max drawdown review published in EXPANDED_FIVE_YEAR_R9_2019_2023.md, expanded_five_year_r9_review.csv, expanded_five_year_r9_monthly.csv and expanded_five_year_r9_results.json. Each candidate's annual net U and count reconciled with discovery pass.\n- In-sample 2019-2023 selection, NOT independent forward validation. No 2024-2026 use. Overlap and unique-FID combination returns of new 61 NOT YET calculated. Retrospective Crown events not actual contemporaneous receipts. All candidates pending user review, no new production rules; M8 and Telegram untouched.\n\n"
 h.write_text(note+s)
print("REPORT",len(lines),"CANDIDATES",len(a["candidates"]))
