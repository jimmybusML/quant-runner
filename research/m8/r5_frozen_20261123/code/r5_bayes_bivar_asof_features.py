#!/usr/bin/env python3
"""R5 research-only as-of features:
- domestic club leagues only (five Understat league codes)
- identical fixture cohort as R4, no future result used for model features
- compare original R4 independent Poisson lambdas
- empirical bivariate-Poisson common goal covariance, strictly past season only
- proper inverse-Gamma Bayesian posterior on season xGF/xGA: xG per match
  assumed exponentially distributed with latent mean theta. Prior IG(a,b)
  with league-derived prior mean and k=a-1 equivalent observations; weighted
  likelihood uses 365-day fading (generalized Bayes / power posterior).
  No outcomes/ROI used to optimize the shrinkage strengths.
All research assumptions, not user-approved betting rules.
"""
import csv,json,math,hashlib,datetime
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
DATA=HERE/"xgtables_understat_2017_2025"
BASE=HERE/"r4_season_scope_xg_predictions_20261123.jsonl"
OUT=HERE/"r5_bayes_bivar_asof_features_20261123.jsonl"
REPORT=HERE/"r5_bayes_bivar_feature_summary_20261123.json"
baseline={(z["league"],z["season"],z["fid"]):z for z in map(json.loads,BASE.open())}
HL=365.
LEAGUES={"epl","bundesliga","serie-a","la-liga","ligue-1"}
STRENGTHS=(1.,2.,5.) # prior pseudo-observations, research sensitivity, not gates
audit=Counter();out=[]
def effective(hist,day):
    sx=sy=ws=0.0
    for old,xg_for,xg_against in hist:
        if xg_for is None or xg_against is None:continue
        age=(day-old).days
        assert age>0
        w=math.exp(-math.log(2)*age/HL)
        sx+=w*xg_for;sy+=w*xg_against;ws+=w
    if not ws:return None
    return {"xg_for_sum":sx,"xga_sum":sy,"effective_count":ws,
            "mean_for":sx/ws,"mean_against":sy/ws}

def covariance(prev):
    # Welford covariance from COMPLETED prior matches in same league+season.
    n=len(prev)
    if n<2:return 0.0
    mx=sum(x for x,y in prev)/n
    my=sum(y for x,y in prev)/n
    return sum((x-mx)*(y-my) for x,y in prev)/(n-1)

for league_dir in sorted(DATA.iterdir()):
    if not league_dir.is_dir():continue
    league=league_dir.name
    assert league in LEAGUES,("unexpected league file",league)
    bydate=defaultdict(list)
    for fp in sorted(league_dir.glob("*/fixtures.csv")):
        yr=int(fp.parent.name)
        with fp.open(encoding="utf-8-sig") as fd:
            for row in csv.DictReader(fd):
                r=dict(row);r["season"]=yr
                bydate[r["date"]].append(r)
    team=defaultdict(list)
    leaguehist=defaultdict(list)
    season_finish=defaultdict(list)
    for datestr in sorted(bydate):
        day=datetime.date.fromisoformat(datestr)
        todays=bydate[datestr]
        for r in todays:
            key=(league,r["season"],r["fixture_id"])
            old=baseline.get(key)
            if old is None:
                audit["not_in_R4_baseline"]+=1
                continue
            yy=r["season"];home=r["home"];away=r["away"]
            prior_h=effective(team[(yy,home,"home")],day)
            prior_a=effective(team[(yy,away,"away")],day)
            prior_l=effective(leaguehist[yy],day)
            assert prior_h and prior_a and prior_l,key
            league_h=prior_l["mean_for"];league_a=prior_l["mean_against"]
            assert min(league_h,league_a)>0,key
            base_h=prior_h["mean_for"]*prior_a["mean_against"]/league_h
            base_a=prior_a["mean_for"]*prior_h["mean_against"]/league_a
            old_model=old["models"]["ratio_decay_same_season"]
            if max(abs(base_h-old_model["lambda_home"]),
                   abs(base_a-old_model["lambda_away"]))>1e-8:
                raise RuntimeError(("R4 BASE LAMBDA MISMATCH",key,base_h,old_model["lambda_home"],base_a,old_model["lambda_away"]))
            cov=covariance(season_finish[yy])
            if cov>0:audit["positive_past_residual_covariance"]+=1
            else:audit["non_positive_past_residual_covariance"]+=1
            models={"independent_poisson":(base_h,base_a)}
            posterior={}
            for k in STRENGTHS:
                # IG posterior mean for theta. Exponential xG observation model.
                # shape posterior=a+sum_w, scale posterior=b+sum(w*xG),
                # posterior mean=(b+sum(wxG))/(a+sum_w-1)
                h_at=(k*league_h+prior_h["xg_for_sum"])/(k+prior_h["effective_count"])
                a_de=(k*league_h+prior_a["xga_sum"])/(k+prior_a["effective_count"])
                a_at=(k*league_a+prior_a["xg_for_sum"])/(k+prior_a["effective_count"])
                h_de=(k*league_a+prior_h["xga_sum"])/(k+prior_h["effective_count"])
                lh=h_at*a_de/league_h
                la=a_at*h_de/league_a
                tag="bayes_prior_"+str(int(k))
                models[tag]=(lh,la)
                posterior[tag]={"home_attack":h_at,"away_defense":a_de,
                                "away_attack":a_at,"home_defense":h_de}
            hg,ag=map(int,r["score"].split("-"))
            out.append({"fixture_id":r["fixture_id"],"league":league,"season":yy,
                        "date":datestr,"score":r["score"],"home":home,"away":away,
                        "league_mean_home_xg":league_h,"league_mean_away_xg":league_a,
                        "asof_current_season_prior_matches":len(season_finish[yy]),
                        "asof_residual_covariance":cov,
                        "effective_venue_history":{"home":prior_h["effective_count"],
                                                   "away":prior_a["effective_count"],
                                                   "league":prior_l["effective_count"]},
                        "candidate_lambda":models,"posterior_means":posterior,
                        "feature_basis":"xG strict prior match dates only; target score used only for outcome"})
        # Update histories only AFTER all target fixtures on the same calendar day.
        for r in todays:
            home=r["home"];away=r["away"];yr=r["season"]
            hx=float(r["home_published_xg"]) if r.get("home_published_xg") else None
            ax=float(r["away_published_xg"]) if r.get("away_published_xg") else None
            if r.get("totals_unreliable","").lower()=="true":hx=ax=None
            team[(yr,home,"home")].append((day,hx,ax))
            team[(yr,away,"away")].append((day,ax,hx))
            if hx is not None and ax is not None:
                leaguehist[yr].append((day,hx,ax))
                hg,ag=map(int,r["score"].split("-"))
                season_finish[yr].append((hg-hx,ag-ax))
            else:
                audit["missing_historical_xg"]+=1

assert len(out)==len(baseline),(len(out),len(baseline))
report={"study":"R5_BAYES_BIVAR_PREGAME_XG_FEATURES_CLUB_ONLY",
        "research_only":True,"input_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "n":len(out),"audit":dict(audit),
        "method":"Bayes inverse-Gamma prior mean from same-league as-of xG; exponential xG observation likelihood with temporal power weights; prior pseudo-observations k=1,2,5 as research sensitivity; bivariate shared parameter from earlier same-league current-season goal-minus-xG residual sample covariance. No profitability tuning.",
        "source_scope":"Only five European domestic club leagues; zero national teams",
        "limitations":["Research model assumptions not user-approved criteria",
            "xG historical publication timestamp unknown; strict previous match dates only",
            "Bivar Poisson can represent non-negative common-shock covariance only",
            "Retrospective already explored cohort, not independent new real prices"]}
with OUT.open("w") as f:
    for r in out:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(out),"audit":dict(audit),
    "positive_cov_frac":round(audit["positive_past_residual_covariance"]/len(out),5)},ensure_ascii=False))
