#!/usr/bin/env python3
"""Independent xG attack/defense and cross-season drift experiment.
Same-day-free chronological evaluation. Research specifications only:
- baseline xG3 from original paper-derived ledger, no other M7 predictions;
- venue attack/defense equal mixture from last 3 same-season venue games;
- venue attack/defense multiplicative normalization by previous league mean;
- cross-season dynamic 365-day half-life weighted offense/defense/league mean.
No post-target information, ROI parameter training, EV eligibility or order gates.
"""
import csv,math,json,hashlib,sys,datetime
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
ROOT=HERE/"xgtables_understat_2017_2025"
BASE=HERE/"xg3_vs_goals3_5leagues_20261123.jsonl"
OUT=HERE/"attack_defense_xg_20261123.jsonl"
REP=HERE/"attack_defense_xg_20261123.json"
baseline={}
for line in BASE.open():
    r=json.loads(line);baseline[(r["league"],r["season"],r["fixture_id"])]=r
HALF_LIFE_DAYS=365.
VARIANTS=("xg3","attack_defense_arithmetic3","attack_defense_league_ratio3",
          "dynamic_attack_only365","dynamic_defense_only365","attack_defense_dynamic365")
MIN_LAMBDA=1e-7
MAX_GOALS=20

def pd(x):
    a=[math.exp(-x)]
    for i in range(1,MAX_GOALS+1):
        a.append(a[-1]*x/i)
    s=sum(a)
    return [v/s for v in a]

def predict(h,a):
    if h<=0 or a<=0:return None
    ph,pa=pd(h),pd(a)
    win=draw=0.
    for i,p in enumerate(ph):
        for j,q in enumerate(pa):
            if i>j:win+=p*q
            elif i==j:draw+=p*q
    away=max(0.,1.-win-draw)
    s=win+draw+away
    return [win/s,draw/s,away/s]

def score(probs,y,hg,ag,h,a):
    p=probs
    return {"lambda_home":h,"lambda_away":a,
            "p_home":p[0],"p_draw":p[1],"p_away":p[2],
            "log_loss":-math.log(max(p[y],1e-15)),
            "Brier":sum((p[i]-float(i==y))**2 for i in range(3)),
            "goal_diff_MAE":abs(h-a-(hg-ag)),
            "total_goals_MAE":abs(h+a-(hg+ag)),
            "predicted":max(range(3),key=lambda i:p[i])}

def weighted(events,now,half_life):
    vals=[]
    for time,xf,xa in events:
        if xf is None or xa is None:continue
        days=(now-time).days
        assert days>0,(now,time)
        w=math.exp(-math.log(2)*days/half_life)
        vals.append((w,xf,xa))
    sw=sum(w for w,xf,xa in vals)
    if sw<=0:return None
    return (sum(w*xf for w,xf,xa in vals)/sw,
            sum(w*xa for w,xf,xa in vals)/sw,
            len(vals),sw)

output=[];stats=Counter()
for league_dir in sorted(ROOT.iterdir()):
    if not league_dir.is_dir():continue
    league=league_dir.name
    # One league's all seasons processed together chronologically for cross-year time weights.
    by_date=defaultdict(list)
    for csv_path in sorted(league_dir.glob("*/fixtures.csv")):
        season=int(csv_path.parent.name)
        with csv_path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                x=dict(r);x["season_year"]=season
                by_date[x["date"]].append(x)
    team_history=defaultdict(list)
    team_season=defaultdict(list)
    league_history=[]
    for date_string in sorted(by_date):
        day=datetime.date.fromisoformat(date_string)
        todays=by_date[date_string]
        for r in todays:
            fid=r["fixture_id"];year=r["season_year"]
            key=(league,year,fid)
            ref=baseline.get(key)
            if ref is None:
                stats["not_in_fixed_xg3_baseline"]+=1
                continue
            home,away=r["home"],r["away"]
            h=team_season[(year,home,"home")]
            a=team_season[(year,away,"away")]
            assert len(h)>=3 and len(a)>=3,("baseline prior three missing",key)
            if any(z[1] is None or z[2] is None for z in h[-3:]+a[-3:]):
                stats["missing_prior_xg"]+=1
                continue
            att_h=sum(z[1] for z in h[-3:])/3.
            att_a=sum(z[1] for z in a[-3:])/3.
            def_h=sum(z[2] for z in h[-3:])/3.
            def_a=sum(z[2] for z in a[-3:])/3.
            refh=ref["xG3"]["lambda_home"]
            refa=ref["xG3"]["lambda_away"]
            if max(abs(att_h-refh),abs(att_a-refa))>1e-8:
                raise RuntimeError(("source baseline asof mismatch",key,att_h,refh,att_a,refa))
            # Previous league games within season, with simple equal per-fixture means.
            prior_league=[z for z in league_history if z[3]==year]
            prior_home=sum(z[1] for z in prior_league)/len(prior_league) if prior_league else None
            prior_away=sum(z[2] for z in prior_league)/len(prior_league) if prior_league else None
            # With three venue matches, league prior exists for relevant sample.
            assert prior_home is not None and prior_away is not None
            dh=weighted(team_history[(home,"home")],day,HALF_LIFE_DAYS)
            da=weighted(team_history[(away,"away")],day,HALF_LIFE_DAYS)
            lg=weighted([(x[0],x[1],x[2]) for x in league_history],day,HALF_LIFE_DAYS)
            variants={
              "xg3":(att_h,att_a),
              "attack_defense_arithmetic3":((att_h+def_a)/2,(att_a+def_h)/2),
              "attack_defense_league_ratio3":(att_h*def_a/prior_home,att_a*def_h/prior_away)}
            if dh and da and lg and lg[0]>0 and lg[1]>0:
                variants["dynamic_attack_only365"]=(dh[0],da[0])
                variants["dynamic_defense_only365"]=(da[1],dh[1])
                variants["attack_defense_dynamic365"]=(dh[0]*da[1]/lg[0],da[0]*dh[1]/lg[1])
            else:stats["missing_dynamic_source"]+=1
            hg,ag=map(int,r["score"].split("-"))
            y=0 if hg>ag else (2 if hg<ag else 1)
            entry={"fixture_id":fid,"league":league,"season":year,"date":date_string,
                   "home":home,"away":away,"score":r["score"],"outcome":y,
                   "features":{
                      "prior_venue3_home_attack_xG":att_h,
                      "prior_venue3_home_defense_xGA":def_h,
                      "prior_venue3_away_attack_xG":att_a,
                      "prior_venue3_away_defense_xGA":def_a,
                      "league_prior_current_season_home_xG":prior_home,
                      "league_prior_current_season_away_xG":prior_away,
                      "dynamic_home_prior_n":dh[2] if dh else 0,
                      "dynamic_away_prior_n":da[2] if da else 0,
                      "dynamic_league_prior_n":lg[2] if lg else 0},
                   "models":{}}
            for name,(lh,la) in variants.items():
                if not math.isfinite(lh+la) or min(lh,la)<=0:
                    stats[name+"_invalid_goals"]+=1
                    continue
                if max(lh,la)>8.:
                    stats[name+"_lambda_over_8"]+=1
                p=predict(lh,la)
                entry["models"][name]=score(p,y,hg,ag,lh,la)
            output.append(entry)
        # Same calendar date never enters any prediction until all matches processed.
        for r in todays:
            try:
                hg,ag=map(int,r["score"].split("-"))
                hx=float(r["home_published_xg"]) if r.get("home_published_xg") else None
                ax=float(r["away_published_xg"]) if r.get("away_published_xg") else None
                if r.get("totals_unreliable","").lower()=="true":
                    hx=ax=None
            except (ValueError,TypeError):continue
            h,a=r["home"],r["away"]
            yr=r["season_year"]
            team_history[(h,"home")].append((day,hx,ax))
            team_history[(a,"away")].append((day,ax,hx))
            team_season[(yr,h,"home")].append((day,hx,ax))
            team_season[(yr,a,"away")].append((day,ax,hx))
            if hx is not None and ax is not None:
                league_history.append((day,hx,ax,yr))
            else:stats["missing_league_source_xg"]+=1

def summarize(rows):
    result={"n":len(rows)}
    for model in VARIANTS:
        z=[r["models"][model] for r in rows if model in r["models"]]
        n=len(z)
        result[model]={"n":n,
            "Brier":round(sum(v["Brier"] for v in z)/n,7) if n else None,
            "logloss":round(sum(v["log_loss"] for v in z)/n,7) if n else None,
            "goal_diff_MAE":round(sum(v["goal_diff_MAE"] for v in z)/n,7) if n else None,
            "accuracy_pct":round(100*sum(v["predicted"]==r["outcome"] for v,r in zip(z,[r for r in rows if model in r["models"]]))/n,4) if n else None}
    return result

report={
 "research":"INDEPENDENT_XG_ATTACK_DEFENSE_AND_CROSS_SEASON_DYNAMIC_20261123",
 "source":"Understat via xGTables; original archived published fixture xG",
 "base_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
 "sample_construction":"Evaluation on original same-season xG3 rows; all previous games strictly before target calendar date; same-date state updated after prediction",
 "variants":{
 "xg3":"Prior 3 same-venue xG-for only, replicates external xG3 reference",
 "attack_defense_arithmetic3":"Half mean of home-attack xGF and away-defense xGA, and away-attack xGF and home-defense xGA; all 3 prior same-season venue matches",
 "attack_defense_league_ratio3":"Attack xGF * opponent venue-allowed xGA / as-of current season league xG mean for scoring venue",
 "dynamic_attack_only365":"All prior venue games across seasons, time-weighted attacking xGF only (ablation)",
 "dynamic_defense_only365":"All prior venue games across seasons, time-weighted opponent venue-conceded xGA only (ablation)",
 "attack_defense_dynamic365":"All previous league/team same-venue games including earlier seasons, exponential 365-day half-life; attack xGF * opponent venue-allowed xGA / league venue scoring xG"
 },
 "model_parameter_status":"Research hypotheses, not a user-approved rule or gate",
 "source_audit":dict(stats),"overall":summarize(output),
 "by_league":{lg:summarize([r for r in output if r["league"]==lg]) for lg in sorted({r["league"] for r in output})},
 "by_year":{str(yr):summarize([r for r in output if r["season"]==yr]) for yr in sorted({r["season"] for r in output})},
 "limitations":["Offline historical source xG time-of-publication not verified",
  "Not a production model or historical valid traded bet",
  "Original same-season xG3 cohort already studied, not a blind future test",
  "Current-season history not enough for some rows retained in audit; no new betting/pass eligibility gate",
  "No Crown odds used in training prediction; Crown settlement is a separate step"]
}
with OUT.open("w") as f:
    for r in output:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REP.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"rows":len(output),"audit":dict(stats),
  "overall":report["overall"],
  "by_year":{str(y):z for y,z in report["by_year"].items()}},ensure_ascii=False))
