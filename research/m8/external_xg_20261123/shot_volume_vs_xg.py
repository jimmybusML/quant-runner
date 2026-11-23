#!/usr/bin/env python3
"""Research-only decomposition of raw shot volume, shots on target and xG quality.
One-step-ahead fixture forecasts; previous three same-venue matches; league goal/shot
rates estimated only from strictly earlier dates. No betting price involved.
"""
import csv,json,math,hashlib
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE/"xgtables_understat_2017_2025"
OLD=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
OUT=HERE/"shot_volume_vs_xg3_20261123.json"
LEDGER=HERE/"shot_volume_vs_xg3_20261123.jsonl"
baseline={}
with OLD.open(encoding="utf-8") as f:
    for line in f:
        r=json.loads(line)
        baseline[(r["league"],r["season"],r["fixture_id"])]=r

def posterior_prob(lh,la):
    def poisson(x):
        x=max(float(x),1e-10)
        a=[math.exp(-x)]
        for n in range(1,21):a.append(a[-1]*x/n)
        norm=sum(a)
        return [v/norm for v in a]
    p1,p2=poisson(lh),poisson(la)
    home=draw=0.0
    for i,x in enumerate(p1):
        for j,y in enumerate(p2):
            if i>j:home+=x*y
            elif i==j:draw+=x*y
    away=max(0.0,1-home-draw)
    return (home,draw,away)

results=[]
source_audits=[]
for fixture_file in sorted(ROOT.glob("*/*/fixtures.csv")):
    league,year=fixture_file.parts[-3],int(fixture_file.parts[-2])
    shot_file=fixture_file.with_name("shots.csv")
    shots=defaultdict(lambda:{"h":[0,0,0.0],"a":[0,0,0.0]})
    shot_fids=set()
    with shot_file.open(encoding="utf-8-sig") as f:
        for s in csv.DictReader(f):
            fid=s["fixture_id"];side=s["side"];shot_fids.add(fid)
            t=shots[fid][side]
            t[0]+=1
            if s["result"] in ("Goal","SavedShot"):t[1]+=1
            t[2]+=float(s["understat_xg"])
    fixtures=list(csv.DictReader(fixture_file.open(encoding="utf-8-sig")))
    source_audits.append({"league":league,"year":year,"matches":len(fixtures),
                          "with_shot_maps":len(shot_fids)})
    state=defaultdict(list)
    league_conversion={"h":[0.0,0.0,0.0],"a":[0.0,0.0,0.0]} # goals, shots, sot
    by_day=defaultdict(list)
    for r in fixtures:by_day[r["date"]].append(r)
    for date in sorted(by_day):
        current=by_day[date]
        for r in current:
            fid=r["fixture_id"]
            old=baseline.get((league,year,fid))
            if old is None:continue
            h=state[(r["home"],"home")]
            a=state[(r["away"],"away")]
            if len(h)<3 or len(a)<3:continue
            rh=league_conversion["h"];ra=league_conversion["a"]
            if min(rh[1],rh[2],ra[1],ra[2])<=0:continue
            hg,ag=map(int,r["score"].split("-"))
            y=0 if hg>ag else (2 if ag>hg else 1)
            preds={}
            for typ,idx in (("shots3",0),("sot3",1)):
                scale_idx=1 if typ=="shots3" else 2
                lh=(sum(row[idx] for row in h[-3:])/3.0) * (rh[0]/rh[scale_idx])
                la=(sum(row[idx] for row in a[-3:])/3.0) * (ra[0]/ra[scale_idx])
                probs=posterior_prob(lh,la)
                preds[typ]={"lambda_home":lh,"lambda_away":la,
                    "log_loss":-math.log(max(probs[y],1e-15)),
                    "brier":sum((p-float(i==y))**2 for i,p in enumerate(probs)),
                    "predicted":max(range(3),key=lambda i:probs[i])}
            preds["xg3"]={"log_loss":old["xG3"]["log_loss"],
                "brier":old["xG3"]["brier"],"predicted":old["xG3"]["predicted"]}
            preds["goals3"]={"log_loss":old["goals3"]["log_loss"],
                "brier":old["goals3"]["brier"],"predicted":old["goals3"]["predicted"]}
            results.append({"league":league,"season":year,"fid":fid,"date":date,
                            "outcome":y,"models":preds})
        for r in current:
            fid=r["fixture_id"]
            if fid not in shot_fids:continue
            try:hg,ag=map(int,r["score"].split("-"))
            except ValueError:continue
            hv,av=shots[fid]["h"],shots[fid]["a"]
            state[(r["home"],"home")].append(hv)
            state[(r["away"],"away")].append(av)
            for side,goals,shot in (("h",hg,hv),("a",ag,av)):
                stat=league_conversion[side]
                stat[0]+=goals;stat[1]+=shot[0];stat[2]+=shot[1]

def summarize(rows):
    n=len(rows)
    z={"n":n}
    for model in ("xg3","shots3","sot3","goals3"):
        z[model]={
            "Brier":round(sum(q["models"][model]["brier"] for q in rows)/n,6) if n else None,
            "log_loss":round(sum(q["models"][model]["log_loss"] for q in rows)/n,6) if n else None,
            "accuracy_pct":round(100*sum(q["models"][model]["predicted"]==q["outcome"] for q in rows)/n,4) if n else None}
    return z

report={"status":"RESEARCH_ONLY","source":"Understat via xGTables",
  "description":"Historical season same-date-free preceding three home/away observations; shots and SOT converted using league-to-date empirical goal conversion rate. xg3 and goals3 inherited from separately computed identical fixture keys.",
  "original_xg_matches":len(baseline),"matched_four_way_samples":len(results),
  "overall":summarize(results),
  "by_league":{lg:summarize([r for r in results if r["league"]==lg]) for lg in sorted({r["league"] for r in results})},
  "by_season":{str(y):summarize([r for r in results if r["season"]==y]) for y in sorted({r["season"] for r in results})},
  "shot_source_coverage":source_audits,
  "limitations":["This is a signal-information comparison, not profit or Crown quote simulation",
    "Source timestamps were archived post-match; previous-date replay approximates availability",
    "Simple shot- and SOT-rate baselines are research comparators, not user product rules"]}
with LEDGER.open("w",encoding="utf-8") as f:
    for r in results:f.write(json.dumps(r,ensure_ascii=False)+"\n")
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"matched":len(results),"overall":report["overall"],
"by_league":{k:{"xg3":v["xg3"]["Brier"],"shots3":v["shots3"]["Brier"],"sot3":v["sot3"]["Brier"],"goals3":v["goals3"]["Brier"]} for k,v in report["by_league"].items()}},ensure_ascii=False))
