#!/usr/bin/env python3
"""Independent 2026/27 current-season attack/defense xG3 comparison on actually
received pregame Crown prices. Offline receipt replay, NOT Telegram betting.
Football-Data xG is assumed matured 72h after source game kickoff; true
publication timestamp unverified. One side each fixture-market, no EV gate.
"""
import json,hashlib,sys
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_actual_receipt_1596_xg_profit_replay_20261116 import load_events,read_jsonl,MANIFEST
from m7_shot_residual_profit_replay_11league_20261116 import norm,parse_utc,poisson,expected,settle
M7=HERE.parent/"m7"
SRC=M7/"m7_actual_receipt_1596_xg_profit_replay_20261116.jsonl"
OUTPUT=HERE/"attack_defense_2026_actual_receipt_20261123.jsonl"
REPORT=HERE/"attack_defense_2026_actual_receipt_20261123.json"
events,files=load_events()
manifest=json.loads(MANIFEST.read_text())
names={str(r["match_id"]):(norm(r.get("home","")),norm(r.get("away",""))) for r in manifest["rows"]}
targets=list(read_jsonl(SRC))
targets.sort(key=lambda r:(parse_utc(r["quote_received_utc"]),r["fixture_id"],r["market"]))
states=defaultdict(list);ei=0;output=[]
audit=Counter()
for r in targets:
    time=parse_utc(r["quote_received_utc"])
    if time>=parse_utc(r["kickoff_utc"]):raise RuntimeError(("quote late",r["fixture_id"]))
    while ei<len(events) and events[ei]["available_at"]<time:
        e=events[ei]
        lg=e["league_id"]
        states[(lg,e["home"],"home")].append((e["available_at"],e["home_xg"],e["away_xg"]))
        states[(lg,e["away"],"away")].append((e["available_at"],e["away_xg"],e["home_xg"]))
        ei+=1
    pair=names.get(r["fixture_id"])
    lg=r["league_id"]
    if not pair:
        audit["no_team_names"]+=1
        continue
    h=states[(lg,pair[0],"home")]
    a=states[(lg,pair[1],"away")]
    if min(len(h),len(a))<3:
        audit["less_than_three_prior_venue_matches"]+=1
        continue
    home_for=sum(x[1] for x in h[-3:])/3
    home_against=sum(x[2] for x in h[-3:])/3
    away_for=sum(x[1] for x in a[-3:])/3
    away_against=sum(x[2] for x in a[-3:])/3
    parameters={
        "independent_xg3":(home_for,away_for),
        "attack_defense_arithmetic3":((home_for+away_against)/2,(away_for+home_against)/2)}
    ent={"fid":r["fixture_id"],"market":r["market"],"league_id":lg,
         "kickoff_utc":r["kickoff_utc"],"receipt_utc":r["quote_received_utc"],
         "raw_sha256":r["raw_sha256"],"line":r["line"],"odds":r["odds"],
         "score":r["score"],"base_M7_direction":r["base_direction"],
         "base_M7_U":r["base_realized_U"],
         "old_residual_adjusted_U":r["xg_realized_U"],
         "latest_history_maturity_utc":max(h[-1][0],a[-1][0]).isoformat(),
         "models":{}}
    for name,(lh,la) in parameters.items():
        sides=("home","away") if r["market"]=="AH" else ("over","under")
        p_h=poisson(lh);p_a=poisson(la)
        expect={side:expected(r["market"],r["line"],r["odds"][side],side,p_h,p_a)
                for side in sides}
        side=max(sides,key=lambda s:expect[s])
        u=settle(r["market"],r["line"],r["odds"][side],side,r["score"]) if r["score"] else None
        ent["models"][name]={"side":side,"expected_U":expect[side],
                             "realized_U":u,"lambda_home":lh,"lambda_away":la}
    output.append(ent)
def agg(rs):
    base=[r for r in rs if r["score"] is not None]
    ret={"eligible":len(rs),"settled":len(base),"pending":len(rs)-len(base)}
    for name in ("base_M7","old_residual_adjusted","independent_xg3","attack_defense_arithmetic3"):
        key=name+"_U" if name in ("base_M7","old_residual_adjusted") else None
        net=sum((r[key] if key is not None else r["models"][name]["realized_U"]) for r in base)
        ret[name]={"U":round(net,5),"ROI_pct":round(100*net/len(base),5) if base else None}
    ret["arithmetic3_vs_xg3_changed_sides"]=sum(r["models"]["independent_xg3"]["side"]!=r["models"]["attack_defense_arithmetic3"]["side"] for r in rs)
    return ret
report={"study":"CURRENT_SEASON_2026_ACTUAL_CROWN_RECEIPT_ATTACK_DEFENSE_XG_RESEARCH",
"receipt_source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
"source_xg_manifest_sha256":hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
"sample":{"input_rows":len(targets),"source_xg_events":len(events),
     "matched":len(output),"unmatched":dict(audit)},
"all":{m:agg([r for r in output if r["market"]==m]) for m in ("AH","OU")},
"by_league":{lg:{m:agg([r for r in output if r["league_id"]==lg and r["market"]==m]) for m in ("AH","OU")}
              for lg in sorted({r["league_id"] for r in output})},
"limitations":["This model uses only 2026/27 Football-Data current-season xG; cross-season Understat dynamic365 cannot be replicated from this xG history alone",
    "The Crown prices are genuine previously received pre-kickoff HTTP quotes, but an offline replay with already known results, not new live execution or formal TG bets",
    "xG publication time is unproven; source kickoff+72h is only an as-of proxy",
    "This receipt cohort has been studied before; not a pristine independent future holdout",
    "No new eligibility gate or live model/Telegram rules added"]}
with OUTPUT.open("w") as f:
    for r in output:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"all":report["all"],"sample":report["sample"]},ensure_ascii=False))
