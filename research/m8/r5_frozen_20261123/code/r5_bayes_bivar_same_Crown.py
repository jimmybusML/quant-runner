#!/usr/bin/env python3
"""R5 simultaneous fair AH+OU and 1X2 comparison:
base independent Poisson, same-mean bivariate Poisson with empirical
past-league residual covariance, fixed c=.10 sensitivity,
true generalized Bayes IG posterior means with prior pseudoobs k=1,2,5,
and Bayes(k=2)+bivariate empirical/fixed.
All same 13,312 club predictions / 9,908 Crown historical T12 fixtures.
No ROI-based tuning, no EV threshold, no national teams, no production edits.
"""
import json,math,hashlib
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
HERE=Path(__file__).resolve().parent
FEAT=HERE/"r5_bayes_bivar_asof_features_20261123.jsonl"
R4=HERE/"r4_season_scope_CrownT12_20261123.jsonl"
PRED=HERE/"r5_bayes_bivar_prediction_scores_20261123.jsonl"
LEDGER=HERE/"r5_bayes_bivar_CrownT12_20261123.jsonl"
REPORT=HERE/"r5_bayes_bivar_comparison_20261123.json"
NMAX=20
SCORES=np.arange(NMAX+1,dtype=float)
H=SCORES[:,None]
A=SCORES[None,:]
METHODS=("independent_poisson",
         "bivar_empirical_c",
         "bivar_fixed_c010",
         "bayes_prior_1_independent",
         "bayes_prior_2_independent",
         "bayes_prior_5_independent",
         "bayes_prior_2_bivar_empirical_c",
         "bayes_prior_2_bivar_fixed_c010")
priceidx=defaultdict(dict)
for line in R4.open():
    r=json.loads(line)
    key=(r["league"],r["understat_fixture_id"])
    assert r["market"] not in priceidx[key]
    priceidx[key][r["market"]]=r
audit=Counter()
for key,p in priceidx.items():
    assert set(p)=={"AH","OU"},(key,p.keys())
assert len(priceidx)==9908
def poisson_arr(lam):
    result=np.empty(NMAX+1,dtype=float)
    result[0]=math.exp(-lam)
    for k in range(1,NMAX+1):result[k]=result[k-1]*lam/k
    return result / result.sum()

def joint(lh,la,c=0.):
    # H=X+W, A=Y+W, independent X,Y,W Poisson intensities
    assert min(lh,la)>=c>=0,(lh,la,c)
    if c==0:
        out=np.outer(poisson_arr(lh),poisson_arr(la))
    else:
        p_h=poisson_arr(lh-c)
        p_a=poisson_arr(la-c)
        p_shared=poisson_arr(c)
        out=np.zeros((NMAX+1,NMAX+1),dtype=float)
        for w,pw in enumerate(p_shared):
            if pw<1e-16:continue
            n=NMAX+1-w
            out[w:,w:]+=pw*np.outer(p_h[:n],p_a[:n])
        out/=out.sum()
    assert abs(float(out.sum())-1)<1e-10
    return out

def line_legs(line):
    n=round(line*4)
    if abs(n/4-line)>1e-9:raise ValueError(line)
    return [(line,1.)] if n%2==0 else [(math.floor(line*2)/2.,.5),(math.ceil(line*2)/2.,.5)]

def contract_ret(market,line,odds,side,hg,ag):
    z=0.
    for leg,w in line_legs(line):
        if market=="AH":d=hg-ag+leg if side=="home" else ag-hg-leg
        else:d=hg+ag-leg if side=="over" else leg-hg-ag
        z+=w*((odds-1.) if d>1e-9 else (-1. if d<-1e-9 else 0.))
    return z

def payoff_grid(market,line,odds,side):
    result=np.zeros_like(H+A)
    for leg,w in line_legs(line):
        if market=="AH":margin=H-A+leg if side=="home" else A-H-leg
        else:margin=H+A-leg if side=="over" else leg-H-A
        result+=w*np.where(margin>1e-9,odds-1,np.where(margin< -1e-9,-1.,0.))
    return result

def hist(outcomes):
    return {
        "n":len(outcomes),
        "Brier":round(sum(z["brier"] for z in outcomes)/len(outcomes),7) if outcomes else None,
        "logloss":round(sum(z["logloss"] for z in outcomes)/len(outcomes),7) if outcomes else None,
        "accuracy_pct":round(100*sum(z["correct"] for z in outcomes)/len(outcomes),4) if outcomes else None
    }
def agg(rs):
    n=len(rs);a={"n":n}
    for model in METHODS:
        vals=[r["models"][model] for r in rs if model in r["models"]]
        k=len(vals);u=sum(z["net_U"] for z in vals)
        a[model]={"n":k,"net_U":round(u,5),"ROI_pct":round(100*u/k,5) if k else None,
           "mean_model_expected_EV":round(sum(z["expected_U"] for z in vals)/k,5) if k else None,
           "side_changes_vs_independent_poisson":sum(r["models"][model]["side"]!=r["models"]["independent_poisson"]["side"] for r in rs if model in r["models"])}
    return a

preds=[];bets=[]
nfeat=0
for line in FEAT.open():
    f=json.loads(line);nfeat+=1
    key=(f["league"],f["fixture_id"])
    quote=priceidx.get(key)
    hg,ag=map(int,f["score"].split("-"))
    correct_out=0 if hg>ag else 1 if hg==ag else 2
    x={}
    base_h,base_a=f["candidate_lambda"]["independent_poisson"]
    raw_cov=f["asof_residual_covariance"]
    def empirical_c(lh,la):
        c=min(max(0.,raw_cov),lh,la)
        if c<raw_cov and raw_cov>0:audit["empirical_c_clipped_on_min_lambda"]+=1
        return c
    modes={
     "independent_poisson":(base_h,base_a,0.),
     "bivar_empirical_c":(base_h,base_a,empirical_c(base_h,base_a)),
     "bivar_fixed_c010":(base_h,base_a,min(.1,base_h,base_a))}
    for prior in (1,2,5):
        bh,ba=f["candidate_lambda"]["bayes_prior_"+str(prior)]
        modes[f"bayes_prior_{prior}_independent"]=(bh,ba,0.)
        if prior==2:
            modes["bayes_prior_2_bivar_empirical_c"]=(bh,ba,empirical_c(bh,ba))
            modes["bayes_prior_2_bivar_fixed_c010"]=(bh,ba,min(.1,bh,ba))
    assert set(modes)==set(METHODS)
    row={"fixture_id":f["fixture_id"],"league":f["league"],"season":f["season"],"date":f["date"],
         "score":f["score"],"raw_prior_residual_covariance":raw_cov,
         "models":{}}
    betrows={}
    if quote:
        audit["Crown_unique_fixtures"]+=1
        for market,p in quote.items():
            assert p["score"]==f["score"] and p["date"]==f["date"]
            betrows[market]={"fid":p["fid"],"league":f["league"],"fixture_id":f["fixture_id"],
                             "season":f["season"],"date":f["date"],"score":f["score"],
                             "market":market,"line":p["quote_line"],"odds":p["odds"],
                             "quote_provenance":"Crown historical source-event retrieved AFTER match, NOT actual pregame HTTP receipt",
                             "models":{}}
        gains={
            market:{side:payoff_grid(market,p["quote_line"],odds,side)
                for side,odds in p["odds"].items()}
            for market,p in quote.items()}
    for name,(lh,la,c) in modes.items():
        m=joint(lh,la,c)
        ph=float(np.tril(m,-1).sum())
        pd=float(np.trace(m))
        pa=float(np.triu(m,1).sum())
        ps=[ph,pd,pa]
        assert abs(sum(ps)-1)<1e-8,(key,name,ps)
        prior={"lambda_home":lh,"lambda_away":la,"common_shock_covariance":c,
               "Brier":sum((p-float(i==correct_out))**2 for i,p in enumerate(ps)),
               "logloss":-math.log(max(ps[correct_out],1e-15)),
               "correct":int(int(np.argmax(ps))==correct_out)}
        row["models"][name]=prior
        if quote:
            for market,p in quote.items():
                ev={side:float(np.sum(m*g)) for side,g in gains[market].items()}
                side=max(p["odds"],key=lambda x:ev[x])
                u=contract_ret(market,p["quote_line"],p["odds"][side],side,hg,ag)
                betrows[market]["models"][name]={"side":side,"expected_U":ev[side],
                     "net_U":u,"lambda_home":lh,"lambda_away":la,"common_shock_c":c}
    if quote:
        for market,p in quote.items():
            old=p["models"]["ratio_decay_same_season"]
            ours=betrows[market]["models"]["independent_poisson"]
            if abs(ours["net_U"]-old["realized_U"])>1e-8:
                audit["baseline_cash_mismatch"]+=1
            if ours["side"]!=old["side"]:
                audit["baseline_side_mismatch"]+=1
            if abs(ours["lambda_home"]-old["lambda_home"])>1e-8 or abs(ours["lambda_away"]-old["lambda_away"])>1e-8:
                audit["baseline_lambda_mismatch"]+=1
        bets+=list(betrows.values())
    preds.append(row)
assert len(preds)==13312
assert len(bets)==2*9908
assert all(not audit[key] for key in ("baseline_cash_mismatch","baseline_side_mismatch","baseline_lambda_mismatch")),audit

def predict_agg(rs):
    z={"n":len(rs)}
    for name in METHODS:
        pts=[{"brier":r["models"][name]["Brier"],"logloss":r["models"][name]["logloss"],
              "correct":r["models"][name]["correct"]} for r in rs]
        z[name]=hist(pts)
    return z

summary={"study":"R5_INDEPENDENT_VS_BIVARIATE_VS_EMPIRICAL_BAYES_VS_COMBINATION_CLUB_CROWN",
 "method_count":len(METHODS),"models":list(METHODS),
 "five_state_contract":"Each market both sides and two legs calculated from normalized 21x21 joint score matrix; one chosen side per fixture; no EV eligibility",
 "data_source_sha256":{"features":hashlib.sha256(FEAT.read_bytes()).hexdigest(),
    "Crown":hashlib.sha256(R4.read_bytes()).hexdigest()},
 "audit":dict(audit),
 "prediction":{"overall":predict_agg(preds),
      "by_season":{str(y):predict_agg([r for r in preds if r["season"]==y]) for y in sorted({r["season"] for r in preds})},
      "by_league":{lg:predict_agg([r for r in preds if r["league"]==lg]) for lg in sorted({r["league"] for r in preds})}},
 "Crown_T12":{"overall":{market:agg([r for r in bets if r["market"]==market]) for market in ("AH","OU")},
      "by_season":{str(y):{market:agg([r for r in bets if r["season"]==y and r["market"]==market]) for market in ("AH","OU")}
                   for y in sorted({r["season"] for r in bets})},
      "by_league":{lg:{market:agg([r for r in bets if r["league"]==lg and r["market"]==market]) for market in ("AH","OU")}
                   for lg in sorted({r["league"] for r in bets})}},
 "limitations":["Bivariate Poisson common component c nonnegative only, negative empirical covariance represented as c=0, mathematically required not user gate",
   "Empirical goal residual covariance estimated from earlier same-season league matches strictly before target date; not optimized for profit",
   "Fixed common component c=0.1 is a research sensitivity, not fitted/production default",
   "Inverse-Gamma posterior for xG match totals assumes exponential observed xG; power likelihood for time discount. This is an explicit approximate Bayes model, not the only Bayesian formulation",
   "Bayesian prior pseudocounts 1,2,5 are research sensitivity not ROI chosen settings",
   "Same past-explored matched historical Crown T12 source-event quotes not actually received pregame or executable",
   "Historical xG original publication dates not recovered; target fixture scores NEVER input to predictors",
   "No national teams or non-domestic leagues; no official TG bets or formal M8 structures touched"]}
with PRED.open("w") as f:
 for r in preds:f.write(json.dumps(r,ensure_ascii=False)+"\n")
with LEDGER.open("w") as f:
 for r in bets:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"prediction":summary["prediction"]["overall"],"Crown":summary["Crown_T12"]["overall"],
    "audit":summary["audit"]},ensure_ascii=False))
