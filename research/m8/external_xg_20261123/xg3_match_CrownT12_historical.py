#!/usr/bin/env python3
"""Research-only Crown T12 historical pricing comparison for independent xG3.
Build team ID crosswalk using unambiguous league/date/FT anchors (metadata only);
join research predictions by date + both resolved team identities WITHOUT using FT
in the matching key. Confirm exact score AFTER join as audit, never input to model.
Historical odds events source timestamps were retrieved after matches,
NOT actual pregame HTTP receipts. No live strategy or new Gate.
"""
from __future__ import annotations
import sys,json,collections,datetime as dt,math,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson, expected, settle
EXT=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
CROWN=ROOT/"m8_early_joint_market_inventory_20261115.jsonl"
OUT=HERE/"xg3_historical_CrownT12_five_league_20261123.json"
LEDGER=HERE/"xg3_historical_CrownT12_five_league_20261123.jsonl"
LEAGUE={"epl":"1","bundesliga":"16","la-liga":"14","serie-a":"12","ligue-1":"25"}
ext=[json.loads(s) for s in EXT.open(encoding="utf-8") if s.strip()]
market=[json.loads(s) for s in CROWN.open(encoding="utf-8") if s.strip()]
market=[r for r in market if r.get("T")==12 and str(r["league"]) in LEAGUE.values()]
assert len(market)==len({r["fid"] for r in market}),(len(market),len(set(r["fid"] for r in market)))
byext=collections.defaultdict(list)
bycrown=collections.defaultdict(list)
for r in ext:
    lg=LEAGUE[r["league"]]
    byext[(lg,r["date"],r["score"])].append(r)
for r in market:
    bycrown[(str(r["league"]),r["date"],f"{r['hg']}-{r['ag']}")].append(r)
pairs=[]
for key,xs in byext.items():
    cs=bycrown.get(key,[])
    if len(xs)==1 and len(cs)==1:
        pairs.append((xs[0],cs[0]))
votes=collections.defaultdict(collections.Counter)
for x,c in pairs:
    lg=str(c["league"])
    votes[(lg,str(c["home_id"]))][x["home"]]+=1
    votes[(lg,str(c["away_id"]))][x["away"]]+=1
ambiguous={key:v for key,v in votes.items() if len(v)>1}
mapping={}
for key,counts in votes.items():
    maximum=max(counts.values())
    winners=[name for name,n in counts.items() if n==maximum]
    if len(winners)==1:mapping[key]=winners[0]
reverse=collections.defaultdict(set)
for (lg,tid),name in mapping.items():
    reverse[(lg,name)].add(tid)
# For unambiguous identity joins retain both sides only when reverse ID matches.
identity={}
for key,name in mapping.items():
    lg,tid=key
    if len(reverse[(lg,name)])==1:identity[key]=name
byteam=collections.defaultdict(list)
for x in ext:
    byteam[(LEAGUE[x["league"]],x["date"],x["home"],x["away"])].append(x)

counts=collections.Counter()
out=[]
for c in market:
    counts["market_5league_T12_rows"]+=1
    lg=str(c["league"])
    h=identity.get((lg,str(c["home_id"])))
    a=identity.get((lg,str(c["away_id"])))
    if h is None or a is None:
        counts["no_identity_link"]+=1
        continue
    matches=byteam.get((lg,c["date"],h,a),[])
    if len(matches)!=1:
        counts["not_one_exact_date_team_match"]+=1
        continue
    x=matches[0]
    if x["score"]!=f"{c['hg']}-{c['ag']}":
        counts["score_mismatch_after_identity_match"]+=1
        continue
    counts["exact_fid_identity_date_score_joined"]+=1
    if any(not isinstance(c.get(k), (int,float)) or not math.isfinite(float(c[k])) for k in ("al","ah","aa","ol","oo","ou")):
        counts["invalid_market_price"]+=1
        continue
    market_data={
        "AH":{"line":float(c["al"]),"odds":{"home":float(c["ah"]),"away":float(c["aa"])},
              "realized":{"home":float(c["home_U"]),"away":float(c["away_U"])}},
        "OU":{"line":float(c["ol"]),"odds":{"over":float(c["oo"]),"under":float(c["ou"])},
              "realized":{"over":float(c["over_U"]),"under":float(c["under_U"])}}
    }
    if any(z<=1.0 for m in market_data.values() for z in m["odds"].values()):
        counts["odds_not_greater_than_one"]+=1
        continue
    for mname,m in market_data.items():
        checks={}
        for side in m["odds"]:
            p=settle(mname,m["line"],m["odds"][side],side,x["score"])
            checks[side]=p
        for side in checks:
            if abs(checks[side]-m["realized"][side])>1e-7:
                counts["stored_pnl_disagrees_settlement"]+=1
                break
        if any(abs(checks[side]-m["realized"][side])>1e-7 for side in checks):
            continue
        rec={"fid":c["fid"],"understat_fixture_id":x["fixture_id"],"market":mname,
            "league":x["league"],"year":x["season"],"date":c["date"],
            "home":h,"away":a,"score":x["score"],
            "T":12,"quote_type_AH":c["ah_kind"],"quote_type_OU":c["ou_kind"],
            "price_received_live":False,"quote_line":m["line"],"odds":m["odds"],
            "as_of_limit":"historical source event timestamp T12 cutoff, NOT receipt",
            "method":{}}
        side_opts=list(m["odds"].keys())
        for label,feature in (("xG3","xG3"),("goals3","goals3")):
            ph=poisson(x[feature]["lambda_home"])
            pa=poisson(x[feature]["lambda_away"])
            ev={side:expected(mname,m["line"],m["odds"][side],side,ph,pa) for side in side_opts}
            selected=max(side_opts,key=lambda side:ev[side])
            rec["method"][label]={"direction":selected,
                                 "expected_u":ev[selected],
                                 "net_U":checks[selected],
                                 "lambda_home":x[feature]["lambda_home"],
                                 "lambda_away":x[feature]["lambda_away"]}
        out.append(rec)
        counts[f"settled_{mname}"]+=1

def agg(rows,model):
    n=len(rows)
    net=sum(r["method"][model]["net_U"] for r in rows)
    return {"n":n,"net_U":round(net,5),"ROI_pct":round(100*net/n,5) if n else None}
def agg_both(rows):
    return {"xG3":agg(rows,"xG3"),"goals3":agg(rows,"goals3"),
        "xG3_minus_goals3_U":round(sum(r["method"]["xG3"]["net_U"]-r["method"]["goals3"]["net_U"] for r in rows),5),
        "direction_disagreement_n":sum(r["method"]["xG3"]["direction"]!=r["method"]["goals3"]["direction"] for r in rows)}
report={"study":"INDEPENDENT_XG3_VS_GOALS3_HISTORICAL_CROWN_T12_FIVE_LEAGUE_REPLAY_RESEARCH_ONLY",
 "data_sources":{"Crown":str(CROWN),"Understat":str(EXT),
      "Crown_sha256":hashlib.sha256(CROWN.read_bytes()).hexdigest(),
      "Understat_features_sha256":hashlib.sha256(EXT.read_bytes()).hexdigest()},
 "identity_audit":{"unambiguous_date_score_training_anchors":len(pairs),
      "candidate_team_keys":len(mapping),"confirmed_one_to_one_team_keys":len(identity),
      "ambiguous_team_ids_with_multiple_names":len(ambiguous),
      "note":"crosswalk learned retrospectively using final scores for entity identity. Join uses date, league, mapped home/away identities; score is then independently checked."},
 "coverage":dict(counts),
 "all_by_market":{m:agg_both([r for r in out if r["market"]==m]) for m in ("AH","OU")},
 "by_year":{str(y):{m:agg_both([r for r in out if r["year"]==y and r["market"]==m]) for m in ("AH","OU")} for y in sorted({r["year"] for r in out})},
 "by_league":{lg:{m:agg_both([r for r in out if r["league"]==lg and r["market"]==m]) for m in ("AH","OU")} for lg in sorted({r["league"] for r in out})},
 "limitations":[
   "Crown T12 source event timestamps on HISTORICAL post-match retrieval are not actual HTTP receipt or matched executable prices",
   "No future match goal/score used as model feature. Final results used retrospectively for entity ID crosswalk building; mapping is not a pure prospective fixture-ID source",
   "xG vendor's original pregame publication time unavailable; only strict previous game dates used",
   "xG3 calculation uncalibrated for AH/OU; the separate two-season isotonic experiment calibrates 1X2, not Asian quarter outcomes",
   "All matched rows retain profit/ROI including negative studies; research method always takes one side of each market without positive EV eligibility filter",
   "Identities not 1-to-1 or mismatched after match are accounted in coverage, not silently imputed",
   "No implication of formal Telegram betting or actual fill"
 ]}
with LEDGER.open("w") as f:
    for r in out:f.write(json.dumps(r,ensure_ascii=False)+"\n")
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"coverage":dict(counts),"identity":report["identity_audit"],
"all_by_market":report["all_by_market"],
"by_year":report["by_year"]},ensure_ascii=False))
