#!/usr/bin/env python3
"""R30: pre-2024 ranking and coverage of original frozen 494, no 2024 selection."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
z=runpy.run_path(str(P/"profitable_original_combinations_r29.py"))
catalog=z["r24"]["catalog"];tr=z["r20"]["groups"];te=z["r24"]["groups"];evaluate=z["evaluate"]
ids=set(catalog)
rank_roi=sorted(ids,key=lambda c:(-catalog[c]["roi"],c))
rank_net=sorted(ids,key=lambda c:(-catalog[c]["n"]*catalog[c]["roi"],c))
rank_n=sorted(ids,key=lambda c:(-catalog[c]["n"],c))
# Original research batch and original 2019-23 ranking only. Counts 6,12,27,61,208 are descriptive comparisons, not limits.
sets={"all_494":ids}
for n in (6,12,27,61,208):
 for label,ranking in (("historical_ROI",rank_roi),("historical_net_U",rank_net),("historical_sample_n",rank_n)):
  sets[f"train_{label}_top{n}"]=set(ranking[:n])
for b in sorted({v["batch"] for v in catalog.values()}):
 sets[f"original_batch_{b}"]={c for c in ids if catalog[c]["batch"]==b}
out=dict(scope="Train-only candidate ranking 2019-2023, fixed original 494; 2024 is inspected after all rankings defined",
 ranking_definition={"historical_ROI":"Descending 2019-2023 candidate ROI","historical_net_U":"Descending 2019-2023 candidate net U","historical_sample_n":"Descending 2019-2023 candidate sample n"},
 sets={},caveats=["The 494 original structures were selected on 2019-2023 outcomes; training ROI is selection-biased.",
 "The ranking metrics and candidate sets use no 2024 outcomes, but this is an exploratory 2024 analysis after previous rounds exposed 2024.",
 "Top6/top12/top27/top61/top208 are research comparisons, NOT strategy limits or gates.",
 "One fixture one order, earliest eligible horizon and equal-net vote. Different subsets may choose different horizons.",
 "2025-2026 remain untouched, no production changes."])
for name,subset in sets.items():
 print("RUN",name,flush=True)
 a=evaluate(tr,subset);b=evaluate(te,subset)
 out["sets"][name]=dict(definitions=len(subset),candidate_ids=sorted(subset),historical=a,year2024=b)
 print("DONE",name,a["policies"].get("equal_net",{}).get("overall"),b["policies"].get("equal_net",{}).get("overall"),flush=True)
(P/"TRAIN_ONLY_ORIGINAL_COMBINATIONS_R30.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
