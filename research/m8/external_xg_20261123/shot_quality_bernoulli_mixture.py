#!/usr/bin/env python3
"""Use historic shot-level xG Bernoulli probabilities, no bet-price input.
Forecast next match goals by equal mixture of 3 previous venue-matched match
shot-quality distributions. Independent of xG3 Poisson and M7 model.
Research-only. Dates and venue state strictly pre-game; same-day updated after.
"""
import csv,json,math,hashlib
from pathlib import Path
from collections import defaultdict, Counter
HERE=Path(__file__).resolve().parent
ROOT=HERE/"xgtables_understat_2017_2025"
SOURCE=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
OUTPUT=HERE/"shot_quality_pbmixture_20261123.jsonl"
SUMMARY=HERE/"shot_quality_pbmixture_20261123.json"
baseline={}
for s in SOURCE.open():
    row=json.loads(s)
    baseline[(row["league"],row["season"],row["fixture_id"])]=row

def bernoulli_convolution(probs):
    a=[1.0]
    for p in probs:
        p=max(0.0,min(1.0,p))
        nxt=[0.0]*(len(a)+1)
        for i,v in enumerate(a):
            nxt[i]+=v*(1-p)
            nxt[i+1]+=v*p
        a=nxt
    return a

def mix(ds):
    n=max(len(x) for x in ds)
    ans=[0.0]*n
    for xs in ds:
        for i,p in enumerate(xs):ans[i]+=p/len(ds)
    s=sum(ans)
    return [x/s for x in ans]

def outcome_probs(ph,pa):
    home=draw=0.0
    for i,x in enumerate(ph):
        for j,y in enumerate(pa):
            if i>j:home+=x*y
            elif i==j:draw+=x*y
    away=max(0.,1.-home-draw)
    z=home+draw+away
    return (home/z,draw/z,away/z)

out=[]
source_audit=Counter()
match_quality_discrepancies=[]
for fixture_file in sorted(ROOT.glob("*/*/fixtures.csv")):
    league,year=fixture_file.parts[-3],int(fixture_file.parts[-2])
    shot_file=fixture_file.with_name("shots.csv")
    shots=defaultdict(lambda:{"h":[],"a":[]})
    seen=set()
    with shot_file.open() as f:
        for s in csv.DictReader(f):
            p=float(s["understat_xg"])
            if not 0.0<=p<=1.0:
                raise RuntimeError(("shot p not in [0,1]",s["shot_id"],p))
            shots[s["fixture_id"]][s["side"]].append((p,s["situation"],s["x"],s["y"]))
            seen.add(s["fixture_id"])
    fixtures=list(csv.DictReader(fixture_file.open(encoding="utf-8-sig")))
    state=defaultdict(list)
    by_date=defaultdict(list)
    for r in fixtures:by_date[r["date"]].append(r)
    for day in sorted(by_date):
        todays=by_date[day]
        for r in todays:
            key=(league,year,r["fixture_id"])
            b=baseline.get(key)
            if b is None:continue
            hp=state[(r["home"],"home")]
            ap=state[(r["away"],"away")]
            if len(hp)<3 or len(ap)<3:
                source_audit["xg3_rows_without_three_shot_hists"]+=1
                continue
            mh=mix([z["pmf"] for z in hp[-3:]])
            ma=mix([z["pmf"] for z in ap[-3:]])
            prob=outcome_probs(mh,ma)
            y=b["outcome"]
            summary_features={}
            for z,seq in (("home",hp[-3:]),("away",ap[-3:])):
                nshots=sum(v["shots"] for v in seq)
                totalxg=sum(v["sumxg"] for v in seq)
                total_quality_square=sum(v["sum_p2"] for v in seq)
                summary_features[z]={
                    "mean_shots_per_match":nshots/3,
                    "mean_xg_per_shot":totalxg/nshots if nshots else 0.,
                    "mean_sum_shot_xg_per_match":totalxg/3,
                    "second_shot_quality_moment":total_quality_square/nshots if nshots else 0.,
                    "open_play_xg_share":sum(v["open_play_xg"] for v in seq)/totalxg if totalxg else 0.,
                    "mean_discrepancy_vs_published_xg":sum(v["difference_from_published"] for v in seq)/3
                }
            out.append({"fixture_id":r["fixture_id"],"league":league,"season":year,
                "date":day,"home":r["home"],"away":r["away"],"score":r["score"],
                "outcome":y,
                "home_goal_pmf":mh,"away_goal_pmf":ma,
                "model":"previous_three_venue_bernoulli_quality_distributions_mixture",
                "prob_H":prob[0],"prob_D":prob[1],"prob_A":prob[2],
                "log_loss":-math.log(max(prob[y],1e-15)),
                "brier":sum((prob[i]-float(i==y))**2 for i in range(3)),
                "predicted":max(range(3),key=lambda i:prob[i]),
                "shot_features":summary_features,
                "xg3_baseline_brier":b["xG3"]["brier"],
                "xg3_baseline_log_loss":b["xG3"]["log_loss"]})
        # Store only PRIOR actual fixture shots after all same-day target predictions.
        for r in todays:
            fid=r["fixture_id"]
            if fid not in seen:
                source_audit["fixtures_missing_shots"]+=1
                continue
            for side,team,role,field in (("h",r["home"],"home","home_published_xg"),
                                          ("a",r["away"],"away","away_published_xg")):
                shotseq=shots[fid][side]
                p=[x[0] for x in shotseq]
                pmf=bernoulli_convolution(p)
                rawsum=sum(p)
                published=float(r[field]) if r.get(field) else None
                delta=rawsum-published if published is not None else None
                if delta is not None:
                    match_quality_discrepancies.append({"abs_diff":abs(delta),"lg":league})
                state[(team,role)].append({
                    "pmf":pmf,"shots":len(p),"sumxg":rawsum,
                    "sum_p2":sum(v*v for v in p),
                    "open_play_xg":sum(v for v,situation,_,_ in shotseq if situation=="OpenPlay"),
                    "difference_from_published":delta if delta is not None else 0.0})
            source_audit["shot_fixture_rows_loaded"]+=1

def avg(rows,key):return sum(x[key] for x in rows)/len(rows) if rows else None
def aggregate(rows):
    n=len(rows)
    return {"n":n,
            "shot_quality_mixture_brier":round(avg(rows,"brier"),7) if n else None,
            "xg3_poisson_brier":round(avg(rows,"xg3_baseline_brier"),7) if n else None,
            "shot_quality_mixture_logloss":round(avg(rows,"log_loss"),7) if n else None,
            "xg3_poisson_logloss":round(avg(rows,"xg3_baseline_log_loss"),7) if n else None,
            "shot_quality_accuracy":round(100*sum(x["predicted"]==x["outcome"] for x in rows)/n,4) if n else None}

report={"study":"HISTORICAL_SHOT_POSITION_QUALITY_PMF_RESEARCH_ONLY",
 "source":"Understat shots via xGTables archival 2017-2025",
 "source_xg3_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 "method":"Each previous-venue match's individual understat_xg probability generates a Bernoulli Poisson-binomial goal PMF, 3 previous venue games mixed equally, two sides independent.",
 "all":aggregate(out),
 "by_year":{str(y):aggregate([r for r in out if r["season"]==y]) for y in sorted({r["season"] for r in out})},
 "by_league":{lg:aggregate([r for r in out if r["league"]==lg]) for lg in sorted({r["league"] for r in out})},
 "source_audit":dict(source_audit),
 "published_xg_vs_sum_shots":{"comparable_sides":len(match_quality_discrepancies),
      "abs_difference_over_0_01":sum(x["abs_diff"]>.01 for x in match_quality_discrepancies),
      "abs_difference_over_0_1":sum(x["abs_diff"]>.1 for x in match_quality_discrepancies),
      "mean_absolute_difference":round(sum(x["abs_diff"] for x in match_quality_discrepancies)/len(match_quality_discrepancies),6)},
 "limitations":["Archived shot probabilities not independently verified at original historical pregame availability timestamp",
   "Shot totals sometimes do not reproduce published fixture xG; do not equate the two without audit",
   "Simple mixture of past match quality profiles may be misspecified, not an exact external paper model",
   "Target FT not used to build its predictor; same-day fixtures excluded from prior features",
   "This is 1X2 prediction quality, not actual Crown AH betting; joined Crown analysis separate"]}
with OUTPUT.open("w") as f:
    for z in out:f.write(json.dumps(z,ensure_ascii=False)+"\n")
SUMMARY.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(out),"overall":report["all"],
 "by_league":report["by_league"],"audit":report["published_xg_vs_sum_shots"]},ensure_ascii=False))
