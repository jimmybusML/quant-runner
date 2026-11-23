#!/usr/bin/env python3
"""Quantify expected payout optimism and side-switch performance without
using EV values as eligibility criteria. For diagnostics only.
"""
import json,hashlib
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE/"attack_defense_CrownT12_20261123.jsonl"
OUT=HERE/"attack_defense_expected_vs_realized_20261123.json"
rows=[json.loads(x) for x in SRC.open() if x.strip()]
names=("xg3","attack_defense_arithmetic3","dynamic_attack_only365",
       "dynamic_defense_only365","attack_defense_dynamic365")
def summarize(group):
    n=len(group)
    out={"n":n}
    for model in names:
        expected=sum(r["models"][model]["ev_at_Crown"] for r in group)
        realized=sum(r["models"][model]["net_U"] for r in group)
        differences=[r for r in group if r["models"][model]["side"]!=r["models"]["xg3"]["side"]]
        same_difference=sum(r["models"][model]["net_U"]-r["models"]["xg3"]["net_U"] for r in differences)
        out[model]={"mean_model_expected_EV":round(expected/n,6) if n else None,
             "realized_ROI":round(realized/n,6) if n else None,
             "net_U":round(realized,5),
             "num_positive_model_EV":sum(r["models"][model]["ev_at_Crown"]>0 for r in group),
             "side_changed_from_xg3":len(differences),
             "side_changed_deltaU_from_xg3":round(same_difference,5)}
    return out
r={
  "research":"MODEL_PREDICTED_CROWN_EV_VS_REALIZED_PNL_DIAGNOSTIC_NO_EV_FILTER",
  "source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
  "by_market":{market:summarize([x for x in rows if x["market"]==market]) for market in ("AH","OU")},
  "epl_ou_by_season":{str(y):summarize([x for x in rows if x["market"]=="OU" and x["league"]=="epl" and x["season"]==y]) for y in range(2019,2026)},
  "cautions":["All historical Crown T12 source event prices, not actual pregame receipts",
      "EV values are diagnostic predictions only, not entry eligibility or threshold",
      "EPL is a post-hoc descriptive subgroup, not user-approved strategy or production filter"]}
OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"by_market":r["by_market"],
     "epl_arithmetic3_OU_yearly":{k:{"n":v["n"],"net_U":v["attack_defense_arithmetic3"]["net_U"]} for k,v in r["epl_ou_by_season"].items()}},ensure_ascii=False))
