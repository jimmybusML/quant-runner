#!/usr/bin/env python3
"""R4 Crown T12 controlled within-season vs cross-season xG studies.
All fixtures and prices same as R3; no new EV gate, no national teams.
Research-only; source event timestamps are not proof of real pregame receipt.
"""
import json,math,hashlib,sys
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson,settle,split_line
PRED=HERE/"r4_season_scope_xg_predictions_20261123.jsonl"
PRICES=HERE/"xg3_historical_CrownT12_five_league_20261123.jsonl"
OUTPUT=HERE/"r4_season_scope_CrownT12_20261123.jsonl"
SUMMARY=HERE/"r4_season_scope_CrownT12_20261123.json"
MODELS=("xg3_same_season","arithmetic_3_same_season","arithmetic_3_cross_season",
         "arithmetic_decay_same_season","arithmetic_decay_cross_season",
         "ratio_decay_same_season","ratio_decay_cross_season")
pred={}
for line in PRED.open():
    r=json.loads(line)
    key=(r["league"],r["fid"])
    if key in pred:raise ValueError(("duplicate",key))
    pred[key]=r
def pmf(lh,la,market):
    h=poisson(lh);a=poisson(la)
    dist=defaultdict(float)
    for i,p in enumerate(h):
        for j,q in enumerate(a):
            d=i-j if market=="AH" else i+j
            dist[d]+=p*q
    return dist
def exp(dist,market,line,odds,side):
    value=0.
    for v,prob in dist.items():
        profit=0.
        for part,w in split_line(line):
            margin=v+part if side=="home" else -v-part if side=="away" else v-part if side=="over" else part-v
            profit+=w*((odds-1) if margin>1e-9 else (-1 if margin< -1e-9 else 0.))
        value+=prob*profit
    return value
rows=[];checks=Counter();distinct=set()
for textline in PRICES.open():
    price=json.loads(textline)
    match=pred.get((price["league"],price["understat_fixture_id"]))
    if match is None:
        checks["no_feature_join"]+=1
        continue
    if (match["date"],match["score"],match["season"])!=(price["date"],price["score"],price["year"]):
        checks["date_score_season_mismatch"]+=1
        continue
    market=price["market"];line=float(price["quote_line"]);odds=price["odds"]
    key=(price["fid"],market)
    if key in distinct:checks["duplicate_market"]+=1
    distinct.add(key)
    out={"fid":price["fid"],"understat_fixture_id":price["understat_fixture_id"],"market":market,
         "league":price["league"],"season":price["year"],"date":price["date"],
         "score":price["score"],"quote_line":line,"odds":odds,
         "study_scope":"five domestic club leagues only; zero national team matches",
         "price_status":"Crown historical T12 source-event retrieved AFTER match, not actual pregame HTTP receipt",
         "history_counts":match["history_counts"],"models":{}}
    for name in MODELS:
        feature=match["models"].get(name)
        if feature is None:
            checks["missing_"+name]+=1
            continue
        probabilities=pmf(feature["lambda_home"],feature["lambda_away"],market)
        e={side:exp(probabilities,market,line,odd,side) for side,odd in odds.items()}
        chosen=max(e,key=lambda s:e[s])
        u=settle(market,line,odds[chosen],chosen,match["score"])
        out["models"][name]={"side":chosen,"expected_U":e[chosen],
             "realized_U":u,"lambda_home":feature["lambda_home"],"lambda_away":feature["lambda_away"]}
    # Benchmark same exact market/source with previous R3:
    old=price["method"]["xG3"]
    ours=out["models"]["xg3_same_season"]
    if abs(old["net_U"]-ours["realized_U"])>1e-7:
        checks["benchmark_net_does_not_reproduce"]+=1
    if old["direction"]!=ours["side"] and abs(ours["expected_U"]-old["expected_u"])>1e-7:
        checks["benchmark_side_does_not_reproduce"]+=1
    rows.append(out)

def agg(items):
    n=len(items);z={"n":n}
    for name in MODELS:
        a=[r["models"][name] for r in items if name in r["models"]]
        den=len(a);net=sum(x["realized_U"] for x in a)
        z[name]={"n":den,"net_U":round(net,5),
          "ROI_pct":round(100*net/den,5) if den else None,
          "changed_sides_vs_same_arithmetic3":sum(x["models"][name]["side"]!=x["models"]["arithmetic_3_same_season"]["side"] for x in items if name in x["models"])}
    return z
report={"study":"R4_SAME_CLUB_LEAGUE_CROWN_T12_SEASON_SCOPE_CONTROLLED",
    "research_only":True,"input_Crown_sha256":hashlib.sha256(PRICES.read_bytes()).hexdigest(),
    "feature_sha256":hashlib.sha256(PRED.read_bytes()).hexdigest(),
    "checks":dict(checks),"market_scenarios":{m:agg([r for r in rows if r["market"]==m]) for m in ("AH","OU")},
    "by_season":{str(y):{m:agg([r for r in rows if r["season"]==y and r["market"]==m]) for m in ("AH","OU")}
                  for y in sorted({r["season"] for r in rows})},
    "by_league":{lg:{m:agg([r for r in rows if r["league"]==lg and r["market"]==m]) for m in ("AH","OU")}
                  for lg in sorted({r["league"] for r in rows})},
    "limitations":["Retrospective Crown source event quotes are not real received pregame prices",
        "Team-ID crosswalk was reconstructed using historical score anchors",
        "No original xG provider publication timestamps or newly blind out-of-sample data",
        "No user-approved production rules or EV selection gates added",
        "Only domestic club league matches; no national team match studied"]}
with OUTPUT.open("w") as f:
    for item in rows:f.write(json.dumps(item,ensure_ascii=False)+"\n")
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"count":len(rows),"checks":report["checks"],
    "overall":report["market_scenarios"],
    "by_season":{k:{m:{x:dict(n=v["n"],U=v["net_U"]) for x,v in z[m].items() if x!="n"} for m in ("AH","OU")} for k,z in report["by_season"].items()}},ensure_ascii=False))
