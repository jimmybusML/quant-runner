#!/usr/bin/env python3
"""Early price discovery R3: independent team FT history vs Crown market repricing.

Research-only. Historical Crown quotes were retrieved after games, not genuine
received executable snapshots. Team features only use prior finished matches
with an explicit kickoff +3h completion proxy before T-12h; this is not a
verified historical receipt. R2 label is the closing market's model-implied
value of the ORIGINAL Crown T-12h AH contract, not profit or an exact CLV.
No selection gates or production rules: every matched AH fixture gets a side.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
DATA=Path("/Users/mac/QuantAsiaDesk/research-work")
OLD=DATA/"m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl"
SUP=HERE/"m5_2026_close_supplement.local.jsonl"
EARLY=DATA/"m8_early_joint_market_inventory_20261115.jsonl"
R2=HERE/"joint_fair_value_r2_research_rows.jsonl.gz"
SUMMARY=HERE/"independent_team_information_r3_results.json"
PRED=HERE/"independent_team_information_r3_predictions.local.jsonl.gz"
AUDIT=collections.Counter()

def UTC(s):
    d=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if not d.tzinfo: raise ValueError("timezone naive")
    return d.astimezone(dt.timezone.utc)

def clean_match(fid,ko,home,away,league,score):
    try:
        home=str(home or "");away=str(away or "");league=str(league or "")
        if not home or not away or home==away or not league:
            AUDIT["invalid_team_or_league_identity"]+=1;return None
        t=UTC(ko);h,a=map(int,score.split("-"))
        if h<0 or a<0 or h>40 or a>40:
            AUDIT["invalid_score"]+=1;return None
        return dict(fid=str(fid),ko=t,available=t+dt.timedelta(hours=3),
                    home=home,away=away,league=league,hg=h,ag=a)
    except Exception:
        AUDIT["malformed_training_fixture"]+=1;return None

# R2 holdout entries and earlier Crown market snapshot (T12 information).
holdout={}
with gzip.open(R2,"rt") as f:
    for line in f:
        r=json.loads(line)
        assert r["fid"] not in holdout
        holdout[r["fid"]]=r
early={}
source_team2026={}
with EARLY.open() as f:
    for line in f:
        e=json.loads(line)
        if e["T"]!=12:
            continue
        if e["year"]==2026:
            source_team2026[str(e["fid"])]=e
        if str(e["fid"]) in holdout:
            early[str(e["fid"])]=e
assert len(early)==len(holdout)

# Historical completed match inventory; all records remain historical not prospective.
hist={}
with OLD.open() as f:
    for line in f:
        c=json.loads(line)
        if c.get("capture_mode")!="historical": continue
        m=clean_match(c["fixture_id"],c["kickoff_utc"],c.get("home_id"),
                      c.get("away_id"),c.get("league_id"),c.get("score",""))
        if m:hist[m["fid"]]=m
AUDIT["old_unique_completed_matches"]=len(hist)
supp=0
with SUP.open() as f:
    for line in f:
        c=json.loads(line)
        fid=str(c["fixture_id"])
        e=source_team2026.get(fid)
        # Supplement quotes were obtained for 2026 fixture inventory, including
        # matches excluded from R2 price pairing. Team IDs are provider verified.
        if not e:
            AUDIT["supplement_missing_team_id_source"]+=1;continue
        m=clean_match(fid,c["kickoff_utc"],e.get("home_id"),e.get("away_id"),
                      e.get("league"),c.get("score",""))
        if m:
            old=hist.get(fid)
            if old and (old["ko"]!=m["ko"] or (old["hg"],old["ag"])!=(m["hg"],m["ag"])
                        or (old["home"],old["away"])!=(m["home"],m["away"])):
                AUDIT["supplement_fixture_conflicts"]+=1
                continue
            hist[fid]=m
            supp+=1
AUDIT["supplement_valid_matches"]=supp
AUDIT["history_unique_completed_matches"]=len(hist)

entries=[]
for fid,r in holdout.items():
    e=early[fid]
    t=UTC(r["kickoff_utc"])
    if r["year"]!=t.year:
        AUDIT["year_mismatch"]+=1;continue
    if str(e["home_id"])==str(e["away_id"]):
        AUDIT["same_team_holdout"]+=1;continue
    if fid not in hist:
        AUDIT["holdout_missing_history_identity"]+=1;continue
    m=hist[fid]
    if (str(e["home_id"]),str(e["away_id"]))!=(m["home"],m["away"]):
        AUDIT["holdout_team_identity_conflict"]+=1;continue
    early_home=float(e["ah"]);early_away=float(e["aa"])
    if not all(math.isfinite(x) for x in [early_home,early_away]) or min(early_home,early_away)<=1:
        AUDIT["invalid_entry_prices"]+=1;continue
    entries.append(dict(**r,home_id=m["home"],away_id=m["away"],
                        price_home=early_home,price_away=early_away,
                        T12=t-dt.timedelta(hours=12)))
AUDIT["holdout_matched"]=len(entries)

history_events=sorted(hist.values(),key=lambda x:(x["available"],x["ko"],x["fid"]))
entries.sort(key=lambda x:(x["T12"],x["fid"]))
H=collections.defaultdict(list)
E=collections.defaultdict(lambda:1500.0)
history_cursor=0

def recent(team,asof_ko,venue):
    a=H[team]
    n=len(a)
    def shrink_mean(field,number,where=None):
        obs=(v[field] for v in reversed(a) if where is None or v["venue"]==where)
        z=[]
        for v in obs:
            z.append(v)
            if len(z)>=number:break
        return sum(z)/(len(z)+5) # empirical shrink to neutral using prior matches
    last=a[-1]["ko"] if a else None
    rest=(asof_ko-last).total_seconds()/86400 if last else 0
    return dict(n=n,
        gd5=shrink_mean("gd",5), gd15=shrink_mean("gd",15),
        gf5=shrink_mean("gf",5),ga5=shrink_mean("ga",5),
        gf15=shrink_mean("gf",15),ga15=shrink_mean("ga",15),
        ppg5=shrink_mean("points_minus_one",5),
        venue_gd=shrink_mean("gd",10,venue),
        rest_days=max(0,rest),missing=int(not bool(a)))

def update(m):
    home=m["home"];away=m["away"];hg=m["hg"];ag=m["ag"]
    hr=E[home];ar=E[away]
    # Plain independent result-based Elo; the algorithm constants are
    # research-estimator parameters, NOT betting thresholds or user rules.
    expected=1/(1+10**(-(hr+60-ar)/400))
    actual=1 if hg>ag else 0.5 if hg==ag else 0
    gain=20*(actual-expected)*(1+0.15*min(3,abs(hg-ag)))
    E[home]=hr+gain;E[away]=ar-gain
    for team,own,conceded,venue in (
        (home,hg,ag,"home"),(away,ag,hg,"away")):
        H[team].append(dict(ko=m["ko"],venue=venue,gf=own,ga=conceded,
                gd=own-conceded,points_minus_one=(2 if own>conceded else 0 if own==conceded else -1)))
    AUDIT["historical_events_matured"]+=1

rows=[]
for r in entries:
    while history_cursor<len(history_events) and history_events[history_cursor]["available"]<=r["T12"]:
        event=history_events[history_cursor]
        assert event["available"]<=r["T12"]
        update(event)
        history_cursor+=1
    hm=recent(r["home_id"],r["T12"],"home")
    am=recent(r["away_id"],r["T12"],"away")
    # INDEPENDENT features: no Crown data, no late quote, no market label.
    ehome=E[r["home_id"]]
    eaway=E[r["away_id"]]
    team=[
        (ehome+60-eaway)/400,
        hm["gd5"]-am["gd5"],
        hm["gd15"]-am["gd15"],
        hm["gf5"]-am["ga5"],
        am["gf5"]-hm["ga5"],
        hm["gf15"]-am["ga15"],
        am["gf15"]-hm["ga15"],
        hm["ppg5"]-am["ppg5"],
        hm["venue_gd"]-am["venue_gd"],
        math.log1p(hm["n"]),math.log1p(am["n"]),
        math.log1p(min(180,hm["rest_days"]))-math.log1p(min(180,am["rest_days"])),
        hm["missing"],am["missing"]
    ]
    # MARKET features: only quotes asof T12 (1x2 omitted due to stale snapshots).
    p=(1/r["price_home"])/(1/r["price_home"]+1/r["price_away"])
    market=[
        r["line_early"],p-0.5,math.log(r["price_home"]/r["price_away"]),
        r["early_total_lambda"],r["early_home_lambda"],
        2*r["early_home_lambda"]-r["early_total_lambda"],
        math.log1p(max(0,r["age_ah_h"])),
        math.log1p(max(0,r["age_ou_h"])),
        math.log1p(max(0,r["age_ah_h"]-r["age_ou_h"])),
    ]
    features=dict(team=team,market=market,combined=market+team)
    if not all(math.isfinite(z) for f in features.values() for z in f):
        AUDIT["nonfinite_feature"]+=1;continue
    row=dict(fid=r["fid"],year=r["year"],month=r["kickoff_utc"][:7],
             ko=r["kickoff_utc"],T12=r["T12"].isoformat(),
             n_history_home=hm["n"],n_history_away=am["n"],
             history_max_available=history_events[history_cursor-1]["available"].isoformat() if history_cursor else None,
             team_missing_any=bool(hm["missing"] or am["missing"]),
             feature=features,early_favorite=("home" if r["line_early"]<0 else
                       "away" if r["line_early"]>0 else ("home" if r["price_home"]<r["price_away"] else "away")),
             r2_residual=r["predicted_residual_side"],
             pnl_home=r["pnl_home"],pnl_away=r["pnl_away"],
             clv_home=r["clv_home"],clv_away=r["clv_away"],
             y_pnl=r["pnl_home"]-r["pnl_away"],
             y_clv=r["clv_home"]-r["clv_away"])
    rows.append(row)
    AUDIT["feature_rows"]+=1
AUDIT["history_events_consumed"]=history_cursor
AUDIT["history_events_not_yet_matured"]=len(history_events)-history_cursor
AUDIT["teams_never_seen_any_prior_games"]=sum(r["team_missing_any"] for r in rows)
AUDIT["team_history_5_each"]=sum(r["n_history_home"]>=5 and r["n_history_away"]>=5 for r in rows)
assert AUDIT["feature_rows"]==AUDIT["holdout_matched"],AUDIT
assert not AUDIT["holdout_team_identity_conflict"]

# All 2026 fixture rows are scored; no EV/size/quality selection conditions.
train=[r for r in rows if r["year"]==2025]
test=[r for r in rows if r["year"]==2026]
assert len(train)==1092 and len(test)==8860,(len(train),len(test))
test.sort(key=lambda r:(r["T12"],r["fid"]))

def ridge_estimator(sample,feat,target,alpha=50):
    x=np.array([r["feature"][feat] for r in sample])
    y=np.array([r["y_"+target] for r in sample])
    mean=x.mean(0);sd=x.std(0);sd=np.where(sd<1e-8,1,sd)
    design=np.column_stack((np.ones(len(x)),(x-mean)/sd))
    regularization=np.eye(design.shape[1])*alpha
    regularization[0,0]=0
    b=np.linalg.solve(design.T@design+regularization,design.T@y)
    return b,mean,sd

def ridge_prediction(model,rs,feat):
    b,mean,sd=model
    x=np.array([r["feature"][feat] for r in rs])
    return np.column_stack((np.ones(len(x)),(x-mean)/sd))@b

def calc(rs,name):
    v=[r["predict"][name] for r in rs]
    pnl=[r["pnl_"+side] for r,side in zip(rs,v)]
    clv=[r["clv_"+side] for r,side in zip(rs,v)]
    n=len(rs)
    return dict(n=n,win=sum(x>1e-9 for x in pnl),loss=sum(x<-1e-9 for x in pnl),
        push=sum(abs(x)<=1e-9 for x in pnl),
        net_U=round(float(sum(pnl)),4),
        roi_pct=round(100*sum(pnl)/n,4) if n else None,
        crossline_close_implied_ev_pct=round(100*sum(clv)/n,4) if n else None,
        positive_close_value_fraction=round(sum(x>1e-9 for x in clv)/n,4) if n else None,
        home_pct=round(100*sum(s=="home" for s in v)/n,3) if n else None)

baselines=["always_home","always_away","early_favorite","R2_stale_1x2_residual"]
variants=[f"{scope}_{target}_{mode}" for mode in ("frozen_2025","expanding_monthly")
          for scope in ("market","team","combined") for target in ("clv","pnl")]
for r in test:
    r["predict"]={"always_home":"home","always_away":"away",
       "early_favorite":r["early_favorite"],
       "R2_stale_1x2_residual":r["r2_residual"]}
for mode in ("frozen_2025","expanding_monthly"):
    for month in sorted({r["month"] for r in test}):
        zz=[r for r in test if r["month"]==month]
        # Frozen only older-year training; monthly expanding uses earlier 2026 months.
        # Monthly estimator fits at the first T12 as-of of the test month.
        # Prior-month FT labels must have matured before that instant, too.
        month_fit_asof=min(UTC(r["T12"]) for r in zz)
        tt=(train+[r for r in test if r["month"]<month and
             UTC(r["ko"])+dt.timedelta(hours=3)<=month_fit_asof]
             if mode=="expanding_monthly" else train)
        assert all(r["year"]==2025 or
                   (r["month"]<month and UTC(r["ko"])+dt.timedelta(hours=3)<=month_fit_asof)
                   for r in tt)
        AUDIT["fit_"+mode]+=1
        for feat in ("market","team","combined"):
            for target in ("clv","pnl"):
                est=ridge_estimator(tt,feat,target)
                pred=ridge_prediction(est,zz,feat)
                name=f"{feat}_{target}_{mode}"
                for r,v in zip(zz,pred):
                    r["predict"][name]="home" if float(v)>=0 else "away"

result=dict(protocol="EARLY_CROWN_R3_PRIOR_TEAM_INFORMATION_V1",
            generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
            sources=dict(historical_score_inventory=str(OLD),m5_sha_verified_close=str(SUP),t12_early_prices=str(EARLY),r2_holdout=str(R2)),
            provenance="Crown historical events were fetched in 2026 post-kickoff; not recorded live receipt. Historical score-asof proxy uses kickoff+3h, not archived FT availability.",
            model_description="Elo and past-match team form only at T12; ridge reg=50 fixed research estimator. Prior-year frozen and 2026 expanding-monthly matched-panel comparisons. Every matched game receives a side.",
            caveats=[
              "Team match-result data were fetched after fixtures; prior completion is plausible but historical availability not independently proven.",
              "Team features from 2019-2026 match store, not historical lineup/injury data. Team IDs from provider; leagues vary by year.",
              "R2 close-implied EV is independent-Poisson approximation and different from actual CLV cashout.",
              "R3 models frozen in prior year or trained on earlier-month labels; not rolling real-time execution.",
              "Any positive result remains exploratory and is not a new production signal, EV threshold or gate."
            ],
            audit=dict(AUDIT),
            baselines=baselines,
            variants=variants,
            summary_2026={name:calc(test,name) for name in baselines+variants},
            monthly_2026={month:{name:calc([r for r in test if r["month"]==month],name)
                    for name in baselines+variants} for month in sorted({r["month"] for r in test})})
# Deterministic per-week block bootstrap for paired full-sample ROI differences.
rng=np.random.default_rng(20261122)
weeks=collections.defaultdict(list)
for r in test:
    iso=dt.date.fromisoformat(r["ko"][:10]).isocalendar()
    weeks[(iso.year,iso.week)].append(r)
week_sets=list(weeks.values())
result["paired_week_bootstrap"]={}
for name in variants:
    diffs=[]
    for g in week_sets:
        diffs.append((sum(r["pnl_"+r["predict"][name]]-r["pnl_"+r["predict"]["early_favorite"]] for r in g),
                      len(g)))
    sums=np.array([v[0] for v in diffs]);counts=np.array([v[1] for v in diffs])
    picks=rng.integers(0,len(week_sets),size=(3000,len(week_sets)))
    samples=100*sums[picks].sum(1)/counts[picks].sum(1)
    result["paired_week_bootstrap"][name]={
        "weeks":len(week_sets),
        "delta_roi_pctpoints_vs_favorite":round(100*sums.sum()/counts.sum(),4),
        "bootstrap95_pctpoints":[round(float(v),4) for v in np.quantile(samples,[.025,.975])]
    }
with gzip.open(PRED,"wt") as f:
    for r in test:
        f.write(json.dumps(r,ensure_ascii=False,default=str)+"\n")
SUMMARY.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
print("OUTPUT",SUMMARY)
print("AUDIT",json.dumps(result["audit"],ensure_ascii=False))
for m in baselines+variants:
    a=result["summary_2026"][m]
    print(m,a["n"],"ROI",a["roi_pct"],"CLV_EVpct",a["crossline_close_implied_ev_pct"],
          "delta_vs_favorite",result["paired_week_bootstrap"].get(m,{}).get("delta_roi_pctpoints_vs_favorite"),
          flush=True)
