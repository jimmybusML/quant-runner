#!/usr/bin/env python3
import json
from pathlib import Path
p=Path(__file__).resolve().parent
a=json.load(open(p/"new_mechanisms_r14_results.json"))
lines=["# R14 | New candidate structure search 2019-2023","",
"New exploratory dimensions: kickoff weekday, UTC kickoff-hour bucket, calendar-month bucket and interactions with AH line, price and quote-time offset. No 2024-2026 used.","",
f"Enumerated {a['audit']['all_candidate_definitions']} candidate definitions. {a['audit']['positive_every_year']} have positive net U in each year 2019-2023. R7+R9+R11+R12+R13+R14 counts: 27+61+40+85+42+80=335 candidate definitions, not independent economic strategies.","",
"## Individual 80-strategy annual review","",
"| ID | 2019 ROI | 2020 ROI | 2021 ROI | 2022 ROI | 2023 ROI | Total N | Net U | ROI | Max drawdown U |",
"|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for z in a["candidates"]:
 vals=" | ".join(f"{z['years'][str(y)]['roi_pct']:+.2f}%" for y in range(2019,2024))
 lines.append(f"| {z['id']} | {vals} | {z['overall']['n']} | {z['overall']['net_U']:+.3f} | {z['overall']['roi_pct']:+.2f}% | {z['max_drawdown_U']:.3f} |")
lines+=["","## Month and drawdown","",
"Complete 60-month rows for all 80 candidates: new_mechanisms_r14_monthly.csv; full JSON includes monthly and yearly stats, max drawdown peak and trough timestamps.","",
"| ID | Active months | Profitable months | Losing months | Worst month | DD peak | DD trough |",
"|---|---:|---:|---:|---|---|---|"]
for z in a["candidates"]:
 active=[(k,v) for k,v in z["months"].items() if v["n"]];worst=min(active,key=lambda kv:kv[1]["net_U"])
 lines.append(f"| {z['id']} | {len(active)} | {sum(v['net_U']>0 for _,v in active)} | {sum(v['net_U']<0 for _,v in active)} | {worst[0]} ({worst[1]['net_U']:+.3f}U) | {z['drawdown_from'] or 'initial'} | {z['drawdown_to']} |")
lines+=["","## Interpretation and limits","",
"- Five profitable years selected and evaluated in the same 2019-2023 data: in-sample multiple-testing bias, not independent cross-year out-of-sample proof.",
"- No minimum sample, EV, ROI or drawdown cutoff was applied beyond the user's five positive years criterion.",
"- New structures may overlap R7/R9 and one another. No de-duplicated combined return claimed.",
"- Max drawdown computed per candidate with kickoff and fixture-id ordering, equal 1U; same kickoff tie order can affect drawdown.",
"- Source-side1 no-vig probability sign is not necessarily the chosen bet-side odds movement.",
"- Crown quote events retrospectively retrieved in 2026; historical event timestamps do not prove contemporaneous receipt/execution.",
"- No M8, Telegram, production, settlement, or model rules changed. All 80 candidates pending user approval.",""]
(p/"NEW_MECHANISMS_R14_2019_2023.md").write_text("\n".join(lines))
h=Path("PROJECT_HANDOFF.md");s=h.read_text();title="## 2026-11-22 | R14 new calendar-interaction discovery, 2019-2023"
if title not in s:
 note=title+"\n\n- User agreed to continue searching structures. Executed new_mechanisms_r14.py on 2019-2023 Crown AH history with 17 new exploratory calendar/time families: weekday, UTC kickoff hour bucket, month bucket, interactions with handicap/price/time offset. 10,007 candidate definitions, 80 positive net U in each year 2019-2023. R7 27 + R9 61 + R11 40 + R12 85 + R13 42 + R14 80 = 335 definitions, not independent mechanisms. Annual/monthly/drawdown per candidate: NEW_MECHANISMS_R14_2019_2023.md, new_mechanisms_r14_results.json, new_mechanisms_r14_review.csv, new_mechanisms_r14_monthly.csv. Annual counts and net U reconciled to discovery pass.\n- Calendar features may proxy league schedule and can overfit. All five years used for selection and evaluation (not OOS). No 2024-2026 data, no production changes, M8/Telegram untouched. Historical Crown quote events retrospectively retrieved in 2026, not actual contemporaneous execution. All 80 candidates pending user review.\n\n"
 h.write_text(note+s)
print("REPORT",len(lines))
