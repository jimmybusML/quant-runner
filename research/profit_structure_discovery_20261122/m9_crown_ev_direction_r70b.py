#!/usr/bin/env python3
"""R70B: isolate max-of-two-side selection effect in archived Crown Asian replay.

Independent state reversal recovers fixed HOME and AWAY wager probabilities from
the stored five-state vector of the model-selected side. This is possible
because each 1U Asian settlement state has an exact opposite on the other side.
No production action, gates, or historically live executable return implied.
"""
import json,collections,datetime as dt
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
ROOT=Path.home()/"QuantAsiaDesk"
SOURCE=json.loads((ROOT/"state/m9_r68_lead_crown_private.json").read_text())["rows"]
Q={(str(q["fid"]),q["kind"]):q for q in SOURCE}
MODELS=("annual_bp","annual_dc","dynamic_ekf")
LEADS=("lead6h","lead12h")
YEARS=(2023,2024,2025,2026)
a=collections.defaultdict(list)
checks=collections.Counter()
def unit_return(probs,odd):
    return float((probs[0]+probs[1]*.5)*(odd-1)-probs[3]*.5-probs[4])
def pnl(state_i,odd):
    return (odd-1,(odd-1)/2,0.,-.5,-1.)[state_i]
for shard in range(4):
    recs=json.loads((ROOT/f"state/m9_r66_replay_shard{shard}_lead_private.json").read_text())["rows"]
    for record in recs:
        q=Q[(str(record["fid"]),record["kind"])]
        odds={"home":float(q["home_decimal"]),"away":float(q["away_decimal"])}
        for model in MODELS:
            s=record["results"][model]
            chosen=s["ev_side"]
            p=np.asarray(s["ev_choice"]["probabilities"],dtype=float)
            i=("FULL_WIN","HALF_WIN","PUSH","HALF_LOSS","FULL_LOSS").index(s["ev_choice"]["state"])
            results={}
            for side in ("home","away"):
                probs=p if side==chosen else p[::-1]
                state_idx=i if side==chosen else 4-i
                odd=odds[side]
                results[side]={
                    "ev":unit_return(probs,odd),"pnl":pnl(state_idx,odd),
                    "p_fullwin":float(probs[0]),"p_fullloss":float(probs[-1]),
                    "observed_fullwin":int(state_idx==0),
                    "observed_fullloss":int(state_idx==4)}
            assert abs(results[chosen]["ev"]-s["ev_choice"]["ev"])<1e-8
            assert abs(results[chosen]["pnl"]-s["ev_choice"]["pnl_u"])<1e-8
            assert results[chosen]["ev"]+1e-8>=results["home" if chosen=="away" else "away"]["ev"]
            a[(record["kind"],model)].append({"year":int(record["year"]),
                 "league":record["league"],"chosen":chosen,
                 "home":results["home"],"away":results["away"]})
            checks["exact_reverse_settlement_and_selected_ev"]+=1

def stats(rows,side):
    n=len(rows)
    if side=="selected":
        results=[z[z["chosen"]] for z in rows]
    elif side=="unselected":
        results=[z["home" if z["chosen"]=="away" else "away"] for z in rows]
    else:results=[z[side] for z in rows]
    return {"n":n,
            "model_ev_pct":100*sum(x["ev"] for x in results)/n,
            "simulated_roi_pct":100*sum(x["pnl"] for x in results)/n,
            "gap_pp":100*sum(x["ev"]-x["pnl"] for x in results)/n,
            "predicted_fullwin_pct":100*sum(x["p_fullwin"] for x in results)/n,
            "observed_fullwin_pct":100*sum(x["observed_fullwin"] for x in results)/n,
            "predicted_fullloss_pct":100*sum(x["p_fullloss"] for x in results)/n,
            "observed_fullloss_pct":100*sum(x["observed_fullloss"] for x in results)/n}
out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
    "scope":"Only R66 archived historical Crown fixture and 6h/12h source quotes. No formal M9 orders.",
    "concept":"Selected side = maximum model EV across two book odds. Fixed-side analyses simulate the same historic quote on home or away irrespective of model choice. This distinguishes unconditional and side-conditioned calibration; cannot establish causal market profitability.",
    "checks":dict(checks),"models":{}}
for lead in LEADS:
    out["models"][lead]={}
    for model in MODELS:
        records=a[(lead,model)]
        vals={k:stats(records,k) for k in ("selected","unselected","home","away")}
        byyear={str(y):{side:stats([z for z in records if z["year"]==y],side)
                  for side in ("selected","unselected","home","away")} for y in YEARS}
        out["models"][lead][model]={"all":vals,"by_year":byyear}
file=P/"M9_CROWN_EV_DIRECTION_R70B.json"
file.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
for lead in LEADS:
    for model in MODELS:
        print(lead,model,json.dumps(out["models"][lead][model]["all"],ensure_ascii=False))
        if model=="dynamic_ekf":
            print("YEARS",lead,json.dumps(out["models"][lead][model]["by_year"],ensure_ascii=False))
print("validated",out["checks"]["exact_reverse_settlement_and_selected_ev"])
