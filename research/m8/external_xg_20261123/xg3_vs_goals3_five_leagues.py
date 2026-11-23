#!/usr/bin/env python3
"""Cross-season independent xG signal test using historical Understat fixtures.
No bookmaker odds are used. Both xG and goals-only references use identical
previous-3 venue-specific matches, restricted to same season / earlier dates.
The '3' is the cited external paper's research specification, not a trading rule.
"""
from __future__ import annotations
import csv, json, math, hashlib
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE/"xgtables_understat_2017_2025"
LEDGER=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
REPORT=HERE/"xg3_vs_goals3_5leagues_20261123.json"
MAX_GOALS=20

def probs(lh,la):
    def mass(x):
        x=max(float(x),1e-10)
        a=[math.exp(-x)]
        for k in range(1,MAX_GOALS+1):a.append(a[-1]*x/k)
        tot=sum(a)
        return [v/tot for v in a]
    h=mass(lh); a=mass(la)
    home=sum(ph*pa for i,ph in enumerate(h) for j,pa in enumerate(a) if i>j)
    draw=sum(x*y for x,y in zip(h,a))
    away=max(0.0,1-home-draw)
    tot=home+draw+away
    return (home/tot,draw/tot,away/tot)

def scores(p,y):
    logloss=-math.log(max(p[y],1e-15))
    brier=sum((q-float(i==y))**2 for i,q in enumerate(p))
    return logloss,brier

def agg(rows,model):
    n=len(rows)
    keys=("log_loss","brier","goal_diff_mae","total_goals_mae")
    res={"n":n}
    for k in keys:
        res[k]=round(sum(r[model][k] for r in rows)/n,7) if n else None
    res["classification_accuracy_pct"]=round(100*sum(r[model]["predicted"]==r["outcome"] for r in rows)/n,4) if n else None
    return res

predictions=[]
source_counts=defaultdict(int)
source_files=[]
for csv_file in sorted(ROOT.glob("*/*/fixtures.csv")):
    league,season=csv_file.parts[-3],csv_file.parts[-2]
    source_files.append({"file":str(csv_file.relative_to(ROOT)), "sha256":hashlib.sha256(csv_file.read_bytes()).hexdigest()})
    with csv_file.open(encoding="utf-8-sig",newline="") as f:
        data=list(csv.DictReader(f))
    source_counts[f"{league}/{season}"]=len(data)
    state=defaultdict(list)
    by_date=defaultdict(list)
    for r in data:
        by_date[r["date"]].append(r)
    for day in sorted(by_date):
        todays=by_date[day]
        for r in todays:
            raw_score=r["score"]
            try:
                hg,ag=map(int,raw_score.replace(" ","").split("-"))
            except (ValueError,AttributeError):
                continue
            hp=state[(r["home"],"home")]
            ap=state[(r["away"],"away")]
            if len(hp)>=3 and len(ap)>=3 and all(v[1] is not None for v in hp[-3:]+ap[-3:]):
                lxh=sum(z[1] for z in hp[-3:])/3
                lxa=sum(z[1] for z in ap[-3:])/3
                lgh=sum(z[0] for z in hp[-3:])/3
                lga=sum(z[0] for z in ap[-3:])/3
                outcome=0 if hg>ag else (2 if ag>hg else 1)
                row={"fixture_id":r["fixture_id"],"league":league,"season":int(season),
                    "date":day,"home":r["home"],"away":r["away"],"score":raw_score,
                    "outcome":outcome, "context_home_n":len(hp),"context_away_n":len(ap)}
                for name,lh,la in (("xG3",lxh,lxa),("goals3",lgh,lga)):
                    p=probs(lh,la)
                    ll,br=scores(p,outcome)
                    row[name]={"lambda_home":lh,"lambda_away":la,"p_H":p[0],"p_D":p[1],"p_A":p[2],
                        "log_loss":ll,"brier":br,"goal_diff_mae":abs(lh-la-(hg-ag)),
                        "total_goals_mae":abs(lh+la-(hg+ag)),"predicted":max(range(3),key=lambda i:p[i])}
                predictions.append(row)
        # Same calendar day cannot use results/xG of the same day as pre-match inputs.
        for r in todays:
            try:
                hg,ag=map(int,r["score"].replace(" ","").split("-"))
                hx=float(r["home_published_xg"]) if r.get("home_published_xg") else None
                ax=float(r["away_published_xg"]) if r.get("away_published_xg") else None
                if r.get("totals_unreliable","").lower()=="true":
                    hx=ax=None
            except (ValueError,AttributeError):
                continue
            state[(r["home"],"home")].append((hg,hx))
            state[(r["away"],"away")].append((ag,ax))

def totals(rows):
    return {"xG3":agg(rows,"xG3"),"goals3":agg(rows,"goals3"),
        "delta_xG3_minus_goals3":{
            k:round(agg(rows,"xG3")[k]-agg(rows,"goals3")[k],7)
            if agg(rows,"xG3")[k] is not None else None
            for k in ("log_loss","brier","goal_diff_mae","total_goals_mae")}}

result={"type":"INDEPENDENT_XG3_VS_GOALS3_PREGAME_RESEARCH_ONLY",
    "source":"Understat historical archive via xGTables",
    "input_index":"https://www.xgtables.io/history/index.json",
    "all_archive_fixture_count":sum(source_counts.values()),
    "match_rows_compared":len(predictions),
    "source_csv_files":len(source_files),
    "source_files_sha256":source_files,
    "specification":"previous 3 same-season home xG for home team / previous 3 same-season away xG for away team, versus previous 3 actual goals; independent Poisson 1X2 forecast, no prices",
    "information_order":"only prior fixture dates within same league-season; same-date fixtures updated after all predictions",
    "full_comparison":totals(predictions),
    "by_league":{lg:totals([x for x in predictions if x["league"]==lg]) for lg in sorted({x["league"] for x in predictions})},
    "by_season":{str(season):totals([x for x in predictions if x["season"]==season]) for season in sorted({x["season"] for x in predictions})},
    "limitations":["xG from historical archive cannot establish original provider availability timestamp",
        "calibration and actual AH/Crown settlement not part of this source-only comparison",
        "source-only results are forecast-quality metrics, not gambling returns, and are not formal Telegram outcomes"]}

with LEDGER.open("w",encoding="utf-8") as f:
    for r in predictions:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"source_fixture_count":result["all_archive_fixture_count"],
    "compared":result["match_rows_compared"],
    "overall":result["full_comparison"],
    "by_league":{k:v["delta_xG3_minus_goals3"] for k,v in result["by_league"].items()},
    "by_season":{k:v["delta_xG3_minus_goals3"] for k,v in result["by_season"].items()}},ensure_ascii=False))
