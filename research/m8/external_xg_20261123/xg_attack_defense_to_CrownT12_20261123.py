#!/usr/bin/env python3
"""Same-fixture Crown AH/OU historical comparison of independent xG attack and defense.
Pre-game predictor uses only xG and earlier dates. Crown odds enter ONLY
which side yields higher five-state expected value. Every match has a side.
No EV filter or live workflow changes.
"""
import json,math,hashlib,sys
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson,expected,settle
CROWN=HERE/"xg3_historical_CrownT12_five_league_20261123.jsonl"
PRED=HERE/"attack_defense_xg_20261123.jsonl"
OUTPUT=HERE/"attack_defense_CrownT12_20261123.jsonl"
SUMMARY=HERE/"attack_defense_CrownT12_20261123.json"
models=("xg3","attack_defense_arithmetic3","attack_defense_league_ratio3",
        "dynamic_attack_only365","dynamic_defense_only365","attack_defense_dynamic365")
byfid={}
for line in PRED.open():
    r=json.loads(line)
    key=(r["league"],r["fixture_id"])
    if key in byfid:raise RuntimeError(("duplicate prediction",key))
    byfid[key]=r
rows=[];checks=Counter();margin_bins=Counter()
for line in CROWN.open():
    r=json.loads(line)
    key=(r["league"],r["understat_fixture_id"])
    p=byfid.get(key)
    if p is None:
        checks["missing_feature_row"]+=1
        continue
    if (p["score"],p["date"],p["season"])!=(r["score"],r["date"],r["year"]):
        checks["mismatched_identity_or_score"]+=1
        continue
    lineprice=float(r["quote_line"])
    sideopts=tuple(r["odds"].keys())
    if r["market"]=="AH" and set(sideopts)!={"home","away"}:raise RuntimeError(("AH side mismatch",r["fid"]))
    if r["market"]=="OU" and set(sideopts)!={"over","under"}:raise RuntimeError(("OU side mismatch",r["fid"]))
    entry={"fid":r["fid"],"understat_fixture_id":key[1],
      "league":r["league"],"season":r["year"],"date":r["date"],
      "home":r["home"],"away":r["away"],"score":r["score"],
      "market":r["market"],"quote_line":lineprice,"odds":r["odds"],
      "quote_provenance":"historical Crown T12 source event, retrieved after match, NOT actual pre-match receipt",
      "models":{}}
    for name in models:
        if name not in p["models"]:
            checks["missing_"+name]+=1
            continue
        feat=p["models"][name]
        lh,la=feat["lambda_home"],feat["lambda_away"]
        h=poisson(lh);a=poisson(la)
        ev={side:expected(r["market"],lineprice,float(r["odds"][side]),side,h,a)
            for side in sideopts}
        side=max(sideopts,key=lambda s:ev[s])
        u=settle(r["market"],lineprice,float(r["odds"][side]),side,r["score"])
        entry["models"][name]={"side":side,"net_U":u,"ev_at_Crown":ev[side],
                              "lambda_home":lh,"lambda_away":la}
    if abs(entry["models"]["xg3"]["net_U"]-r["method"]["xG3"]["net_U"])>1e-8:
        checks["raw_xg3_realizedU_not_reproduced"]+=1
    if entry["models"]["xg3"]["side"]!=r["method"]["xG3"]["direction"]:
        checks["raw_xg3_direction_not_reproduced"]+=1
    rows.append(entry)
def agg(items):
    n=len(items);ret={"n":n}
    for name in models:
        taken=[r["models"][name] for r in items if name in r["models"]]
        den=len(taken)
        net=sum(x["net_U"] for x in taken)
        ret[name]={"n":den,"net_U":round(net,5),"ROI_pct":round(100*net/den,5) if den else None,
              "changed_side_vs_xg3":sum(r["models"][name]["side"]!=r["models"]["xg3"]["side"] for r in items
                                      if name in r["models"])}
    return ret
report={"research":"INDEPENDENT_XG_ATTACK_DEFENSE_CROWN_T12_AH_OU_COMPARISON",
    "base_crown_sha256":hashlib.sha256(CROWN.read_bytes()).hexdigest(),
    "attack_defense_feature_sha256":hashlib.sha256(PRED.read_bytes()).hexdigest(),
    "base_model_names":models,"checks":dict(checks),
    "same_fixture_sample":{m:agg([r for r in rows if r["market"]==m]) for m in ("AH","OU")},
    "by_season":{str(y):{m:agg([r for r in rows if r["season"]==y and r["market"]==m]) for m in ("AH","OU")}
           for y in sorted({r["season"] for r in rows})},
    "by_league":{lg:{m:agg([r for r in rows if r["league"]==lg and r["market"]==m]) for m in ("AH","OU")}
           for lg in sorted({r["league"] for r in rows})},
    "limitations":["Research parameters not fitted on ROI, no post-hoc threshold selected",
        "Every matched historical fixture-market retains one chosen side, no positive EV eligibility",
        "Historical Crown T12 quote event timestamps from later collection; not real HTTP pre-game received price",
        "Team ID crosswalk was reconstructed with retrospective score anchors",
        "Historical xG release timestamps not independently proven to predate each quoted kickoff",
        "Study period previously explored; this is not a blinded forward betting strategy",
        "No user-approved M8 structural rules, formal Telegram orders or production code touched"]}
with OUTPUT.open("w") as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"count":len(rows),"checks":report["checks"],
 "all":report["same_fixture_sample"],
 "AH_by_year":{yr:x["AH"] for yr,x in report["by_season"].items()}},ensure_ascii=False))
