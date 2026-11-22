#!/usr/bin/env python3
"""R4: can already-observed Crown OU repricing precede later Crown AH repricing?

Every original R2 fixture (2025+2026 9,952) remains; no selection/EV gates.
Use complete historical Crown AH and OU list events strictly before T12.
Closing-Crown expected return and Asian settlement from R2 are labels ONLY.
All raw HTTP responses received in 2026 after match: NOT tradable historical receipt.
"""
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

ROOT=Path("/Users/mac/QuantAsiaDesk/research-work")
HERE=Path(__file__).resolve().parent
INDEX=ROOT/"m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl"
SUP=HERE/"m5_2026_close_supplement.local.jsonl"
R2=HERE/"joint_fair_value_r2_research_rows.jsonl.gz"
R3=HERE/"independent_team_information_r3_predictions.local.jsonl.gz"
OUT=HERE/"crossmarket_event_lead_r4_results.json"
DETAIL=HERE/"crossmarket_event_lead_r4_predictions.local.jsonl.gz"
COUNT=collections.Counter()

def timestamp(z):
    t=dt.datetime.fromisoformat(str(z).replace("Z","+00:00").replace(" ","T"))
    return t.astimezone(dt.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(dt.timezone.utc)

def market_path(book,field):
    a=[]
    for q in book.get(field+"_list") or []:
        try:
            t=timestamp(q[4]);v=[float(q[1]),float(q[2]),float(q[3])]
            if all(math.isfinite(x) for x in v) and abs(v[0]*4-round(v[0]*4))<1e-7 and min(v[1:])>1:
                a.append((t,*v))
        except (IndexError,ValueError,TypeError,OverflowError):
            COUNT["malformed_market_path"]+=1
    for tag in ("open","close"):
        z=(book.get(field) or {}).get(tag)
        if not isinstance(z,dict):continue
        try:
            t=timestamp(z["time"])
            sides=("home","away") if field=="asian" else ("over","under")
            v=[float(z["line"]),float(z[sides[0]]),float(z[sides[1]])]
            if all(math.isfinite(x) for x in v) and abs(v[0]*4-round(v[0]*4))<1e-7 and min(v[1:])>1:
                a.append((t,*v))
        except (KeyError,ValueError,TypeError,OverflowError):
            COUNT["malformed_market_snapshot"]+=1
    # Deduplicate source event exact duplicates.
    return sorted(set(a))

def asof(path,t):
    valid=[z for z in path if z[0]<=t]
    return valid[-1] if valid else None

def p1(q):
    a,b=1/q[2],1/q[3]
    return a/(a+b)

def market_temporal(path,ko,field):
    cut=ko-dt.timedelta(hours=12)
    obs=[q for q in path if q[0]<=cut]
    known={k:asof(obs,ko-dt.timedelta(hours=k)) for k in (24,18,12)}
    def motion(start,end):
        a,b=known[start],known[end]
        if a is None or b is None:return (0.0,0.0,1.0)
        # AH home strengthens as the home handicap becomes more negative;
        # OU over strengthens as the goal line goes higher.
        change=(-1 if field=="asian" else 1)*(b[1]-a[1])
        same=abs(a[1]-b[1])<1e-9
        pdelta=(p1(b)-p1(a)) if same else 0.0
        return change,pdelta,0.0
    move24=motion(24,12)
    move18=motion(18,12)
    states=[q for i,q in enumerate(obs) if i==0 or q[1:]!=obs[i-1][1:]]
    newer=[q for q in states if q[0]>ko-dt.timedelta(hours=24)]
    last=states[-1] if states else None
    return [
        *move24,*move18,
        math.log1p(len(newer)),
        math.log1p(len(obs)),
        math.log1p((cut-last[0]).total_seconds()/3600) if last else 0.0,
        1.0 if last is None else 0.0,
        math.log1p(len(states))
    ],known

r2={}
with gzip.open(R2,"rt") as f:
    for line in f:
        z=json.loads(line)
        assert z["fid"] not in r2
        r2[z["fid"]]=z
baseline={}
with gzip.open(R3,"rt") as f:
    for line in f:
        z=json.loads(line);baseline[z["fid"]]=z
assert len(r2)==9952 and len(baseline)==8860
sources={}
with INDEX.open() as f:
    for line in f:
        r=json.loads(line)
        fid=str(r["fixture_id"])
        if fid in r2:sources[fid]=r
with SUP.open() as f:
    for line in f:
        r=json.loads(line)
        fid=str(r["fixture_id"])
        if fid in r2:sources[fid]=r
assert len(sources)==len(r2)
rows=[]
for fid,r in r2.items():
    c=sources[fid]
    raw=Path(c["source_file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=c["raw_sha256"]:
        COUNT["hash_mismatch"]+=1;continue
    COUNT["raw_sha_verified"]+=1
    data=json.loads(raw)
    entry=next((z for z in data.get("data",[]) if str(z.get("id"))==fid),None)
    if not entry or entry.get("status")!="full":
        COUNT["not_full_or_no_identity"]+=1;continue
    book=next((z for z in entry.get("bookmakers",[]) if z.get("slug")=="crown"),None)
    if not book:
        COUNT["no_crown_book"]+=1;continue
    ko=timestamp(entry["start"])
    # Source timestamp must be same as R2 reference identity.
    if ko!=timestamp(r["kickoff_utc"]) or f'{entry["hg"]}-{entry["ag"]}' != sources[fid]["score"]:
        COUNT["score_or_kickoff_mismatch"]+=1;continue
    ah=market_path(book,"asian")
    ou=market_path(book,"goal")
    ah_feat,ah_known=market_temporal(ah,ko,"asian")
    ou_feat,ou_known=market_temporal(ou,ko,"goal")
    if not ah_known[12] or not ou_known[12]:
        COUNT["missing_quote_at_cut"]+=1
    if ah_known[24] is None:COUNT["AH_T24_unavailable"]+=1
    if ou_known[24] is None:COUNT["OU_T24_unavailable"]+=1
    # No future events enter the features: all market_path features from [T24,T12].
    assert not ah_known[12] or ah_known[12][0]<=ko-dt.timedelta(hours=12)
    assert not ou_known[12] or ou_known[12][0]<=ko-dt.timedelta(hours=12)
    # R3 market features already calculated at T12 for matching 2026 fixture.
    original=r3=baseline.get(fid)
    # 2025 market base rebuilt from 2025 R2 market-implied distribution.
    ahline=float(r["line_early"])
    # 2025 model comparability achieved by using same 9-column R3 market vector
    # reconstructed directly from R2 and raw entry quote, not future labels.
    early_ah_quote=ah_known[12]
    if not early_ah_quote:
        COUNT["missing_current_quote_in_raw"]+=1
        continue
    odds_h,odds_a=early_ah_quote[2],early_ah_quote[3]
    eprob=(1/odds_h)/(1/odds_h+1/odds_a)
    market_features=[
        ahline,eprob-0.5,math.log(odds_h/odds_a),
        r["early_total_lambda"],r["early_home_lambda"],
        2*r["early_home_lambda"]-r["early_total_lambda"],
        math.log1p(max(0.0,r["age_ah_h"])),math.log1p(max(0.0,r["age_ou_h"])),
        math.log1p(max(0.0,r["age_ah_h"]-r["age_ou_h"]))
    ]
    if original:
        # Compare asof Crown AH raw to R3 market feature.
        if max(abs(v-w) for v,w in zip(original["feature"]["market"],market_features))>0.0001:
            COUNT["R3_market_feature_mismatch"]+=1
            market_features=original["feature"]["market"]
    events=ah_feat+ou_feat
    row=dict(fid=fid,year=r["year"],month=r["kickoff_utc"][:7],
             ko=r["kickoff_utc"],line_early=r["line_early"],
             entry_ah_path_asof_line=early_ah_quote[1],
             t12_ah_quote_event=early_ah_quote[0].isoformat(),
             t12_ou_quote_event=ou_known[12][0].isoformat() if ou_known[12] else None,
             events=events, market=market_features,
             event_n_ah=len(ah),event_n_ou=len(ou),
             pnl_home=r["pnl_home"],pnl_away=r["pnl_away"],
             clv_home=r["clv_home"],clv_away=r["clv_away"],
             baseline_r3=original["predict"] if original else None)
    if original:
        assert len(market_features)==9
    rows.append(row)
    COUNT["event_features_built"]+=1

assert COUNT["hash_mismatch"]==0,COUNT
train=[r for r in rows if r["year"]==2025]
test=[r for r in rows if r["year"]==2026]
COUNT["train"]=len(train);COUNT["test"]=len(test)
if len(train)<100 or len(test)<1000:raise RuntimeError("Unexpected cohort shrinkage")

def feature(r,name):
    if name=="market":return r["market"]
    if name=="event":return r["events"]
    return r["market"]+r["events"]

def fit(rs,features,target,alpha=50):
    X=np.asarray([feature(r,features) for r in rs])
    Y=np.asarray([r[target+"_home"]-r[target+"_away"] for r in rs])
    mean=X.mean(0);sd=X.std(0);sd=np.where(sd<1e-8,1.0,sd)
    Z=np.c_[np.ones(len(X)),(X-mean)/sd]
    pen=np.eye(Z.shape[1])*alpha;pen[0,0]=0
    beta=np.linalg.solve(Z.T@Z+pen,Z.T@Y)
    return beta,mean,sd

def pred(model,rs,features):
    beta,mean,sd=model
    X=np.asarray([feature(r,features) for r in rs])
    Z=np.c_[np.ones(len(X)),(X-mean)/sd]
    return Z@beta

def stats(rs,name):
    side=[r["pred"][name] for r in rs]
    vals=[r["pnl_"+s] for r,s in zip(rs,side)]
    clv=[r["clv_"+s] for r,s in zip(rs,side)]
    return dict(n=len(rs),net_U=round(sum(vals),3),
                roi_pct=round(100*sum(vals)/len(rs),4),
                close_implied_ev_pct=round(100*sum(clv)/len(rs),4),
                positive_price_value_fraction=round(sum(v>0 for v in clv)/len(rs),4),
                predicted_home_pct=round(100*sum(s=="home" for s in side)/len(rs),3))

test.sort(key=lambda r:(r["ko"],r["fid"]))
for r in test:
    r["pred"]={}
    for key in ("market_clv_frozen_2025","market_clv_expanding_monthly",
                "team_clv_expanding_monthly","combined_clv_expanding_monthly",
                "R2_stale_1x2_residual"):
        if r["baseline_r3"]:
            r["pred"]["R3_"+key]=r["baseline_r3"][key]
    r["pred"]["always_home"]="home"
    r["pred"]["always_away"]="away"

variants=[]
for training in ("frozen_2025","expanding_monthly"):
    for month in sorted({r["month"] for r in test}):
        sub=[r for r in test if r["month"]==month]
        first_asof=min(timestamp(r["ko"])-dt.timedelta(hours=12) for r in sub)
        past=(train+[r for r in test if r["month"]<month
                     and timestamp(r["ko"])+dt.timedelta(hours=3)<=first_asof]
              if training=="expanding_monthly" else train)
        for scope in ("market","event","market_plus_event"):
            for target in ("clv","pnl"):
                name=f"{scope}_{target}_{training}"
                if name not in variants:variants.append(name)
                estimator=fit(past,scope,target)
                predictions=pred(estimator,sub,scope)
                for r,val in zip(sub,predictions):
                    r["pred"][name]="home" if val>=0 else "away"
                COUNT["monthly_estimators_fit"]+=1
names=list(test[0]["pred"])
assert all(set(r["pred"])==set(names) for r in test)
results={
    "protocol":"CROWN_AH_OU_EARLY_EVENT_LEAD_R4",
    "created_at":dt.datetime.now(dt.timezone.utc).isoformat(),
    "provenance":"Historical Crown raw response files SHA-verified; source timestamps reconstructed asof T12; responses received postmatch in 2026",
    "method":"2025 Nov-Dec 1092 training 2026 full-period test, frozen 2025 versus monthly expanding with premonth matured labels; every fixture gets an AH direction. No EV cutoff.",
    "limitations":[
        "Crown OU and AH are SAME bookmaker markets. OU earlier movements do not establish independent news or causal leadership.",
        "No corresponding true historical pregame receipt for 2025 and 2026; this is not executable P&L.",
        "2025 T12 full dynamic OU path covers only November-December; date distribution shifts in 2026.",
        "Mixed price movement across handicap line changes is not compared as same contract. R2 late AH+OU Poisson valued original contract.",
        "The close-implied EV is model-derived; not observed exit trade or true realized value."
    ],
    "audit":dict(COUNT),
    "baselines":[x for x in names if x.startswith("R3_") or x.startswith("always_")],
    "variants":variants,
    "summary_2026":{name:stats(test,name) for name in names},
    "by_month_2026":{month:{name:stats([r for r in test if r["month"]==month],name) for name in names}
                  for month in sorted({r["month"] for r in test})}
}
# Paired UTC calendar week bootstraps; descriptive only.
weekly=collections.defaultdict(list)
for r in test:
    iso=timestamp(r["ko"]).date().isocalendar()
    weekly[(iso.year,iso.week)].append(r)
weeks=list(weekly.values())
rng=np.random.default_rng(20261122)
for name in variants:
    ref="market_clv_"+name.split("_")[-2]+"_"+name.split("_")[-1] if False else (
        "market_clv_expanding_monthly" if name.endswith("expanding_monthly") else "market_clv_frozen_2025")
    # Assure fair matched baseline within same time-training plan.
    if ref==name:continue
    group=[(len(week),
            sum(r["pnl_"+r["pred"][name]]-r["pnl_"+r["pred"][ref]] for r in week),
            sum(r["clv_"+r["pred"][name]]-r["clv_"+r["pred"][ref]] for r in week))
           for week in weeks]
    z=np.array(group)
    sample=rng.integers(0,len(z),size=(3000,len(z)))
    rec=z[sample].sum(1)
    rois=100*rec[:,1]/rec[:,0]
    clvs=100*rec[:,2]/rec[:,0]
    results.setdefault("paired_week_bootstrap_vs_market_clv_same_training",{})[name]={
        "baseline":ref,"delta_roi_pp":round(100*z[:,1].sum()/z[:,0].sum(),4),
        "roi_95pct_interval":[round(float(x),4) for x in np.quantile(rois,[.025,.975])],
        "delta_close_model_value_pp":round(100*z[:,2].sum()/z[:,0].sum(),4),
        "close_value_95pct_interval":[round(float(x),4) for x in np.quantile(clvs,[.025,.975])],
    }

# Correlation: OU observed T24->T12 movement and *future AH close value* is not the same as
# direct AH line movement. Report both plus event visibility.
for year in (2025,2026):
    rs=train if year==2025 else test
    available_ou=[r for r in rs if r["events"][13]==0] # OU 24->12 availability marker (AH 11 columns first)
    results.setdefault("event_structure",{})[str(year)]={
        "n":len(rs),
        "OU_T24_to_T12_available":len(available_ou),
        "early_AH_raw_line_mismatch_vs_R2":sum(abs(r["entry_ah_path_asof_line"]-r["line_early"])>1e-7 for r in rs),
        "OU_events_median":float(np.median([r["event_n_ou"] for r in rs])),
        "AH_events_median":float(np.median([r["event_n_ah"] for r in rs])),
    }

with gzip.open(DETAIL,"wt") as f:
    for r in test:
        f.write(json.dumps(r,ensure_ascii=False)+"\n")
with gzip.open(HERE/"crossmarket_event_lead_r4_training.local.jsonl.gz","wt") as f:
    for r in train:
        f.write(json.dumps(r,ensure_ascii=False)+"\n")
OUT.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n")
print("COMPLETE",json.dumps(dict(COUNT),ensure_ascii=False))
for name in ("R3_market_clv_frozen_2025","market_clv_frozen_2025","event_clv_frozen_2025",
             "market_plus_event_clv_frozen_2025","R3_market_clv_expanding_monthly",
             "market_clv_expanding_monthly","event_clv_expanding_monthly",
             "market_plus_event_clv_expanding_monthly"):
    print(name,results["summary_2026"].get(name))
print("RESULT_FILE",OUT)
