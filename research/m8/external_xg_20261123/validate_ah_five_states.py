#!/usr/bin/env python3
"""Independent five-state AH cash and calibrated probability audit."""
import json,math
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE/"xg3_ah_cdf_calibration_20261123.jsonl"
OUT=HERE/"xg3_ah_five_state_independent_validation_20261123.json"
NAMES=("FW","HW","P","HL","FL")
def legs(line):
    q=round(4*line)
    assert abs(q/4-line)<1e-8
    if q%2==0:return [(line,1.)]
    return [(math.floor(2*line)/2.,.5),(math.ceil(2*line)/2.,.5)]
def cash(diff,line,odds,side):
    u=0.
    for leg,w in legs(line):
        v=diff+leg if side=="home" else -diff-leg
        u+=w*((odds-1) if v>1e-9 else (-1. if v<-1e-9 else 0.))
    return u
def state(u,odds):
    candidates=[odds-1.,(odds-1.)/2.,0.,-.5,-1.]
    k=min(range(5),key=lambda i:abs(u-candidates[i]))
    assert abs(u-candidates[k])<1e-8,(u,odds)
    return NAMES[k]
errors=Counter();max_ev_error=0.;minimum_mass=1.;n=0
state_counts=Counter()
for s in SOURCE.open():
    r=json.loads(s);n+=1
    diff=int(r["score"].split("-")[0])-int(r["score"].split("-")[1])
    for model,payload in r["model"].items():
        p={int(k):float(v) for k,v in payload["survival_probs"].items()}
        ts=sorted(p)
        pieces=[(ts[0]-2,1-p[ts[0]])]
        pieces.extend((ts[i]+1,p[ts[i]]-p[ts[i+1]]) for i in range(len(ts)-1))
        pieces.append((ts[-1]+2,p[ts[-1]]))
        mass=sum(x[1] for x in pieces)
        minimum_mass=min(minimum_mass,min(x[1] for x in pieces))
        if abs(mass-1)>1e-8:errors["mass_sum"]+=1
        if min(x[1] for x in pieces)<-1e-8:errors["negative_probability"]+=1
        for side,odds in r["odds"].items():
            ev=sum(prob*cash(diffval,r["line"],odds,side) for diffval,prob in pieces)
            err=abs(ev-payload["five_state_winning_leg_ev"][side])
            max_ev_error=max(max_ev_error,err)
            if err>1e-7:errors["EV"]+=1
            actual=cash(diff,r["line"],odds,side)
            state_counts[(model,side,state(actual,odds))]+=1
            if side==payload["side"] and abs(actual-payload["realized_U"])>1e-8:errors["realized_cash"]+=1
status="PASS" if not errors and n==7073 else "FAIL"
summary={"status":status,"rows":n,"method_side_checks":6*n,"errors":dict(errors),
    "maximum_expected_U_difference":max_ev_error,
    "minimum_piece_probability":minimum_mass,
    "outcome_counts":{"%s/%s/%s"%k:v for k,v in state_counts.items()}}
OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:v for k,v in summary.items() if k!="outcome_counts"},ensure_ascii=False))
assert status=="PASS"
