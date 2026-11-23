#!/usr/bin/env python3
"""Shot quality distribution sensitivity: preserve previous-match published
Understat xG exactly, changing ONLY the shot-level goal PMF shape.
Research-only, no actual betting changes. All target fixtures retained.
"""
import csv,json,math,hashlib
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
ROOT=HERE/"xgtables_understat_2017_2025"
BASE=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
OUT=HERE/"shot_quality_same_mean_20261123.jsonl"
REPORT=HERE/"shot_quality_same_mean_20261123.json"
base={}
for line in BASE.open():
    x=json.loads(line);base[(x["league"],x["season"],x["fixture_id"])]=x

def scale(probs,target):
    """Monotone capped rescaling to match fixture-level published xG mean."""
    if target is None:return probs,"missing_published_xg"
    if not probs:
        return probs,"empty_shot_list" if target>1e-7 else "exact"
    if target<1e-9:return [0.]*len(probs),"exact"
    nonzero=sum(p>0 for p in probs)
    if target>nonzero+1e-6:return probs,"unreachable_target"
    lo,hi=0.0,max(1.0,target/max(1e-10,sum(probs)))
    for i in range(30):
        if sum(min(1.,hi*p) for p in probs)>=target:break
        hi*=2
    for _ in range(40):
        m=(lo+hi)/2
        if sum(min(1.,m*p) for p in probs)<target:lo=m
        else:hi=m
    new=[min(1.,hi*p) for p in probs]
    if abs(sum(new)-target)>1e-5:return probs,"mean_not_matched"
    return new,"exact"

def pb(probs):
    a=[1.]
    for p in probs:
        nxt=[0.]*(len(a)+1)
        for i,v in enumerate(a):
            nxt[i]+=v*(1-p);nxt[i+1]+=v*p
        a=nxt
    return a

def mix(dist):
    n=max(map(len,dist));o=[0.]*n
    for seq in dist:
        for i,z in enumerate(seq):o[i]+=z/len(dist)
    return o

def prediction(ph,pa):
    hw=dr=0.
    for i,p in enumerate(ph):
        for j,q in enumerate(pa):
            if i>j:hw+=p*q
            elif i==j:dr+=p*q
    return (hw,dr,max(0.,1-hw-dr))

out=[];audit=Counter();max_mu_dev=0.
for f in sorted(ROOT.glob("*/*/fixtures.csv")):
    lg,year=f.parts[-3],int(f.parts[-2])
    shots=defaultdict(lambda:{"h":[],"a":[]})
    with f.with_name("shots.csv").open() as sf:
        for s in csv.DictReader(sf):
            shots[s["fixture_id"]][s["side"]].append(float(s["understat_xg"]))
    fixture=list(csv.DictReader(f.open(encoding="utf-8-sig")))
    bydate=defaultdict(list)
    for r in fixture:bydate[r["date"]].append(r)
    state=defaultdict(list)
    for day in sorted(bydate):
        for r in bydate[day]:
            b=base.get((lg,year,r["fixture_id"]))
            if b is None:continue
            h=state[(r["home"],"home")];a=state[(r["away"],"away")]
            if len(h)<3 or len(a)<3:
                audit["missing_prior_three"]+=1;continue
            ph=mix([p["pmf"] for p in h[-3:]])
            pa=mix([p["pmf"] for p in a[-3:]])
            lm_h=sum(i*v for i,v in enumerate(ph))
            lm_a=sum(i*v for i,v in enumerate(pa))
            target_h=b["xG3"]["lambda_home"];target_a=b["xG3"]["lambda_away"]
            max_mu_dev=max(max_mu_dev,abs(lm_h-target_h),abs(lm_a-target_a))
            if max(abs(lm_h-target_h),abs(lm_a-target_a))>1e-4:
                audit["forecast_mean_mismatch"]+=1
            prob=prediction(ph,pa);y=b["outcome"]
            out.append({"league":lg,"season":year,"date":day,"fixture_id":r["fixture_id"],
                        "score":r["score"],"outcome":y,
                        "home_goal_pmf":ph,"away_goal_pmf":pa,
                        "mean_home_goals":lm_h,"mean_away_goals":lm_a,
                        "p_H":prob[0],"p_D":prob[1],"p_A":prob[2],
                        "Brier":sum((prob[i]-float(i==y))**2 for i in range(3)),
                        "logloss":-math.log(max(prob[y],1e-15)),
                        "xg3_Brier":b["xG3"]["brier"],
                        "xg3_logloss":b["xG3"]["log_loss"]})
        # Same day never enters past information until all that day's predictions are computed.
        for r in bydate[day]:
            if r["fixture_id"] not in shots:
                audit["missing_source_shots"]+=1
            for side,team,role,key in (
                ("h",r["home"],"home","home_published_xg"),
                ("a",r["away"],"away","away_published_xg")):
                src=shots[r["fixture_id"]][side]
                target=float(r[key]) if r.get(key) else None
                if r.get("totals_unreliable","").lower()=="true":target=None
                adjusted,status=scale(src,target)
                audit[status]+=1
                state[(team,role)].append({"pmf":pb(adjusted),"scale_status":status})

def summarize(rows):
    n=len(rows)
    def mean(k):return sum(r[k] for r in rows)/n if n else None
    return {"n":n,"shape_Brier":round(mean("Brier"),7),"original_xg3_Brier":round(mean("xg3_Brier"),7),
            "shape_logloss":round(mean("logloss"),7),"original_xg3_logloss":round(mean("xg3_logloss"),7)}
rep={"type":"SHOT_PB_MIXTURE_EXACT_SAME_MEAN_XG3_RESEARCH_ONLY",
     "baseline_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
     "method":"rescale each previous shot xG with monotone capped transform to exactly match reported previous fixture published xG, then average prior-three Poisson-binomial goal PMFs; no ROI tuning",
     "coverage":dict(audit),"forecast_max_abs_expected_goal_mismatch":max_mu_dev,
     "overall":summarize(out),
     "by_league":{lg:summarize([r for r in out if r["league"]==lg]) for lg in sorted({r["league"] for r in out})},
     "by_season":{str(yr):summarize([r for r in out if r["season"]==yr]) for yr in sorted({r["season"] for r in out})},
     "limitations":["Source xG publication timestamp unknown; historical data only",
         "Infeasible or missing published totals retained in audit; no model eligibility Gate",
         "This checks distribution shape holding means constant, not a separate trading rule"]}
with OUT.open("w") as f:
    for r in out:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(out),"overall":rep["overall"],
  "max_abs_mu_dev":max_mu_dev,"audit":dict(audit)},ensure_ascii=False))
