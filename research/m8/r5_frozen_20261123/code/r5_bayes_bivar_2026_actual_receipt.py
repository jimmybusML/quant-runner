#!/usr/bin/env python3
"""R5 existing 2026/27 *actually pregame received* Crown quote offline research.
Strictly earlier Football-Data xG games matured kickoff+72h proxy.
Same 138 fixtures / 276 AH+OU receipts as preexisting R3 study, not newly
received real trades. Club domestic leagues only, no national teams.
Research Bayesian IG posterior on exponentially-modelled xG and bivar-Poisson
common shock estimated from past league finished-game goal-xG residuals.
"""
import csv,datetime,math,json,hashlib,sys
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
HERE=Path(__file__).resolve().parent
M7=HERE.parent/"m7"
sys.path.insert(0,str(M7))
from m7_actual_receipt_1596_xg_profit_replay_20261116 import load_events,LEAGUE,TZ,DATA,MATURITY_HOURS,MANIFEST
from m7_shot_residual_profit_replay_11league_20261116 import norm,parse_utc
SRC=HERE/"attack_defense_2026_actual_receipt_20261123.jsonl"
OUTPUT=HERE/"r5_bayes_bivar_actual_receipt_20261123.jsonl"
REPORT=HERE/"r5_bayes_bivar_actual_receipt_20261123.json"
source=[json.loads(s) for s in SRC.open() if s.strip()]
source.sort(key=lambda r:(parse_utc(r["receipt_utc"]),r["fid"],r["market"]))
assert len(source)==276
events,_=load_events()
manifest=json.loads(MANIFEST.read_text())
names={str(r["match_id"]):(norm(r.get("home","")),norm(r.get("away",""))) for r in manifest["rows"]}
# Resolve historical match score from original football-data CSV; data is used only
# AFTER kickoff+72h, at which point goals and xG were already from the past.
goals={}
for code,league_id in LEAGUE.items():
    csvpath=DATA/f"2627_{code}.csv"
    if not csvpath.exists():continue
    with csvpath.open(encoding="utf-8-sig") as fd:
        for r in csv.DictReader(fd):
            if not all(str(r.get(k,"")).strip() for k in ("Date","Time","HomeTeam","AwayTeam","FTHG","FTAG","HxG","AxG")):continue
            day=datetime.datetime.strptime(r["Date"],"%d/%m/%Y").date()
            clock=datetime.time.fromisoformat(r["Time"])
            kickoff=datetime.datetime.combine(day,clock).replace(tzinfo=TZ[code]).astimezone(datetime.timezone.utc)
            maturity=kickoff+datetime.timedelta(hours=MATURITY_HOURS)
            key=(league_id,norm(r["HomeTeam"]),norm(r["AwayTeam"]),maturity.isoformat())
            if key in goals:raise ValueError(("duplicate score key",key))
            goals[key]=(int(r["FTHG"]),int(r["FTAG"]))
assert all((e["league_id"],e["home"],e["away"],e["available_at"].isoformat()) in goals for e in events)

HL=365.
MAXGOAL=20
def wmean(seq,now):
    sx=sy=sw=0.
    for available,xg,xa in seq:
        assert available<now
        age=(now-available).total_seconds()/86400
        w=math.exp(-math.log(2)*age/HL)
        sw+=w;sx+=w*xg;sy+=w*xa
    if not sw:return None
    return sx/sw,sy/sw,sw,sx,sy
def covariance_xy(seq):
    if len(seq)<2:return 0.
    x=sum(z[0] for z in seq)/len(seq)
    y=sum(z[1] for z in seq)/len(seq)
    return sum((a-x)*(b-y) for a,b in seq)/(len(seq)-1)
def pois(x):
    a=np.empty(MAXGOAL+1,dtype=float)
    a[0]=math.exp(-x)
    for k in range(1,MAXGOAL+1):a[k]=a[k-1]*x/k
    return a/a.sum()
def joint(h,a,c):
    assert 0<=c<=min(h,a)
    if c==0:return np.outer(pois(h),pois(a))
    x=pois(h-c);y=pois(a-c);w=pois(c)
    z=np.zeros((MAXGOAL+1,MAXGOAL+1),dtype=float)
    for k,p in enumerate(w):
        if p<1e-16:continue
        z[k:,k:]+=p*np.outer(x[:MAXGOAL+1-k],y[:MAXGOAL+1-k])
    return z/z.sum()
GRID_H=np.arange(MAXGOAL+1,dtype=float)[:,None]
GRID_A=np.arange(MAXGOAL+1,dtype=float)[None,:]
def legs(line):
    q=round(line*4)
    assert abs(line-q/4)<1e-8,line
    return [(line,1.)] if q%2==0 else [(math.floor(line*2)/2,.5),(math.ceil(line*2)/2,.5)]
def contract(market,line,odd,side,h,a):
    z=0.
    for leg,w in legs(line):
        d=h-a+leg if side=="home" else a-h-leg if side=="away" else h+a-leg if side=="over" else leg-h-a
        z+=w*((odd-1.) if d>1e-9 else (-1. if d<-1e-9 else 0.))
    return z

history=defaultdict(list)
leaguehist=defaultdict(list)
resids=defaultdict(list)
audit=Counter()
ei=0;output=[]
for src in source:
    time=parse_utc(src["receipt_utc"])
    assert time<parse_utc(src["kickoff_utc"])
    while ei<len(events) and events[ei]["available_at"]<time:
        e=events[ei];lg=e["league_id"]
        t=e["available_at"];hx=e["home_xg"];ax=e["away_xg"]
        history[(lg,e["home"],"home")].append((t,hx,ax))
        history[(lg,e["away"],"away")].append((t,ax,hx))
        leaguehist[lg].append((t,hx,ax))
        gh,ga=goals[(lg,e["home"],e["away"],t.isoformat())]
        resids[lg].append((gh-hx,ga-ax))
        ei+=1
    lg=src["league_id"];team_names=names.get(src["fid"])
    if team_names is None:raise RuntimeError(("no team names for matched R3",src["fid"]))
    ht=history[(lg,team_names[0],"home")];at=history[(lg,team_names[1],"away")]
    if min(len(ht),len(at))<3:raise RuntimeError(("R3 sample unexpectedly missing 3 history games",src["fid"]))
    if max(ht[-1][0],at[-1][0])>=time:raise RuntimeError(("history not matured",src["fid"]))
    # Match old R3 arithmetic baseline (equal previous three with no time weights).
    h3=sum(v[1] for v in ht[-3:])/3;ha3=sum(v[2] for v in ht[-3:])/3
    a3=sum(v[1] for v in at[-3:])/3;aa3=sum(v[2] for v in at[-3:])/3
    old=src["models"]["attack_defense_arithmetic3"]
    if max(abs((h3+aa3)/2-old["lambda_home"]),abs((a3+ha3)/2-old["lambda_away"]))>1e-8:
        audit["old_R3_baseline_lambda_mismatch"]+=1
    wm_h=wmean(ht,time);wm_a=wmean(at,time);wm_l=wmean(leaguehist[lg],time)
    assert wm_h and wm_a and wm_l
    lhbase=wm_h[0]*wm_a[1]/wm_l[0]
    labase=wm_a[0]*wm_h[1]/wm_l[1]
    cov=covariance_xy(resids[lg])
    if cov>0:audit["positive_raw_residual_covariance"]+=1
    else:audit["nonpositive_raw_residual_covariance"]+=1
    modes={"old_arithmetic3_independent":(old["lambda_home"],old["lambda_away"],0.),
           "same_season_ratio_independent":(lhbase,labase,0.),
           "same_season_ratio_bivar_empirical":(lhbase,labase,min(max(0.,cov),lhbase,labase)),
           "same_season_ratio_bivar_fixed_c010":(lhbase,labase,min(.1,lhbase,labase))}
    for k in (1,2,5):
        H=(k*wm_l[0]+wm_h[3])/(k+wm_h[2])
        AD=(k*wm_l[0]+wm_a[4])/(k+wm_a[2])
        A=(k*wm_l[1]+wm_a[3])/(k+wm_a[2])
        HD=(k*wm_l[1]+wm_h[4])/(k+wm_h[2])
        ph=H*AD/wm_l[0];pa=A*HD/wm_l[1]
        modes[f"bayes_{k}_independent"]=(ph,pa,0.)
        if k==2:
            modes["bayes_2_bivar_empirical"]=(ph,pa,min(max(0.,cov),ph,pa))
            modes["bayes_2_bivar_fixed_c010"]=(ph,pa,min(.1,ph,pa))
    gh,ga=map(int,src["score"].split("-"))
    record={"fid":src["fid"],"market":src["market"],"league_id":lg,
        "source_Crown_raw_sha256":src["raw_sha256"],
        "Crown_quote_received_utc":src["receipt_utc"],
        "source_xG_maturity_latest_utc":max(ht[-1][0],at[-1][0]).isoformat(),
        "source_xG_actual_publication_time":"unknown; 72 hours after source game is research asof proxy",
        "kickoff_utc":src["kickoff_utc"],"line":src["line"],"odds":src["odds"],
        "score":src["score"],"past_league_goal_xG_residual_covariance":cov,
        "old_original_independent_xG3_PnL":src["models"]["independent_xg3"]["realized_U"],
        "old_M7_PnL":src["base_M7_U"],
        "models":{}}
    hh=GRID_H;aa=GRID_A
    for name,(lh,la,c) in modes.items():
        matrix=joint(lh,la,c)
        EVs={}
        for side,odd in src["odds"].items():
            ev=0.
            for v,w in legs(src["line"]):
                if src["market"]=="AH":
                    d=hh-aa+v if side=="home" else aa-hh-v
                else:
                    d=hh+aa-v if side=="over" else v-hh-aa
                ev+=w*float(np.sum(matrix*np.where(d>1e-9,odd-1,np.where(d<-1e-9,-1,0))))
            EVs[side]=ev
        chosen=max(src["odds"],key=lambda s:EVs[s])
        outcome=contract(src["market"],src["line"],src["odds"][chosen],chosen,gh,ga)
        record["models"][name]={"side":chosen,"net_U":outcome,"expected_U":EVs[chosen],
                                "lambda_home":lh,"lambda_away":la,"c":c}
        if name=="old_arithmetic3_independent":
            if abs(outcome-old["realized_U"])>1e-8:audit["old_R3_arithmetic_pnl_mismatch"]+=1
            if old["side"]!=chosen:audit["old_R3_arithmetic_side_mismatch"]+=1
    output.append(record)
assert not any(audit[k] for k in ("old_R3_baseline_lambda_mismatch","old_R3_arithmetic_pnl_mismatch","old_R3_arithmetic_side_mismatch")),audit
assert len(output)==276
METHODS=list(output[0]["models"])
def agg(rows):
    settled=[r for r in rows if r["score"]]
    n=len(settled)
    z={"markets":len(rows),"settled":n,"pending":len(rows)-n}
    for name in METHODS:
        net=sum(r["models"][name]["net_U"] for r in settled)
        z[name]={"U":round(net,5),"ROI_pct":round(100*net/n,5) if n else None,
             "changed_sides_vs_old_arithmetic3":sum(r["models"][name]["side"]!=r["models"]["old_arithmetic3_independent"]["side"] for r in rows)}
    return z
rep={"study":"R5_BAYES_BIVARIATE_OLD_ACTUAL_CROWN_HTTP_RECEIPT_REPLAY",
    "receipt_source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
    "matched_market_count":len(output),"matched_fixtures":len({r["fid"] for r in output}),
    "methods":METHODS,"audit":dict(audit),
    "overall":{m:agg([r for r in output if r["market"]==m]) for m in ("AH","OU")},
    "by_league":{lg:{m:agg([r for r in output if r["league_id"]==lg and r["market"]==m]) for m in ("AH","OU")}
                 for lg in sorted({r["league_id"] for r in output})},
    "limitations":["All market prices were actually received before kickoff, but this is a posthoc offline study on already-known results, not new formal Telegram orders",
      "Source xG actual publication times unavailable, uses game kickoff+72h maturity proxy",
      "Research sample same 138 eligible fixtures as R3, already seen in previous work",
      "Source league event files domestic clubs only; no national teams",
      "Comparison formulas may differ in xG history span from original R3 arithmetic3; each within-model Poisson/bivariate pair uses exact same lambdas",
      "Prior strengths and fixed covariance are research sensitivity only, no ROI-fitted parameters or eligibility gate",
      "No new betting rules, M8 production change or formal ledger change"]}
with OUTPUT.open("w") as f:
    for x in output:f.write(json.dumps(x,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"sample":len(output),"audit":dict(audit),"overall":rep["overall"]},ensure_ascii=False))
