#!/usr/bin/env python3
"""Read-only R2: Crown early AH+OU->joint score distribution, 1X2 divergence, and cross-line CLV.

Uses 2025/2026 T-12h Crown historical movement quotes from an existing
asof inventory and late pre-kickoff Crown AH/OU quotes, all retrieved after
the matches. Closing quotes only value existing early contracts AFTER the
fact; they never inform early selections.
"""
from __future__ import annotations

import collections
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from research.m3.probabilities import settle_score

B=Path("/Users/mac/QuantAsiaDesk/research-work")
EARLY=B/"m8_early_joint_market_inventory_20261115.jsonl"
CLOSE=B/"m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl"
OUT=Path(__file__).with_name("joint_fair_value_r2_results.json")
ROWS=Path(__file__).with_name("joint_fair_value_r2_research_rows.jsonl.gz")
SUPPLEMENT=Path(__file__).with_name("m5_2026_close_supplement.local.jsonl")

K=40
HG=np.arange(K)[None,:]
COUNTS=collections.Counter()


def time(s):
    t=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if t.tzinfo is None:
        raise ValueError("Missing timezone")
    return t.astimezone(dt.timezone.utc)


def pmf(lam):
    a=np.empty((len(lam),K),dtype=float)
    a[:,0]=np.exp(-lam)
    for k in range(1,K):
        a[:,k]=a[:,k-1]*lam/k
    return a


def cdf_at(C,indices):
    idx=np.clip(indices.astype(int),0,K-1)
    vals=np.take_along_axis(C,idx,axis=1)
    return np.where(indices<0,0,np.where(indices>=K,1,vals))


def halves(line):
    return (np.floor(line*2+1e-8)/2, np.ceil(line*2-1e-8)/2)


def ou_components(total,line):
    C=pmf(total).cumsum(1)
    W=np.zeros(len(line));L=W.copy()
    for v in halves(line):
        W+=1-cdf_at(C,np.floor(v)[:,None])[:,0]
        L+=cdf_at(C,(np.ceil(v)-1)[:,None])[:,0]
    return W/2,L/2


def ah_components(total,frac,line):
    h=pmf(total*frac)
    a=pmf(total*(1-frac)).cumsum(1)
    W=np.zeros(len(line));L=W.copy()
    for v in halves(line):
        W+=(h*cdf_at(a,np.ceil(HG+v[:,None])-1)).sum(1)
        L+=(h*(1-cdf_at(a,np.floor(HG+v[:,None])))).sum(1)
    return W/2,L/2


def ah_share(total,frac,line):
    w,l=ah_components(total,frac,line)
    return w/np.maximum(w+l,1e-10)


def ou_share(total,line):
    w,l=ou_components(total,line)
    return w/np.maximum(w+l,1e-10)


def inverse(target,lo,hi,fn):
    a=np.full(len(target),lo,dtype=float);b=np.full(len(target),hi,dtype=float)
    exists=(fn(a)<=target+1e-6)&(fn(b)>=target-1e-6)
    for _ in range(28):
        m=(a+b)/2
        low=fn(m)<target
        a=np.where(low,m,a)
        b=np.where(low,b,m)
    x=(a+b)/2
    error=np.abs(fn(x)-target)
    return x,exists,error


def latent(ahline,hou,haw,ouline,oov,uuv):
    pa=(1/hou)/(1/hou+1/haw)
    po=(1/oov)/(1/oov+1/uuv)
    total,ok0,err0=inverse(po,.02,15,lambda x:ou_share(x,ouline))
    frac,ok1,err1=inverse(pa,.0001,.9999,lambda x:ah_share(total,x,ahline))
    ok=ok0&ok1&(err0<1e-5)&(err1<1e-5)
    return total,frac,ok,err0,err1


def onex2(total,frac):
    h=pmf(total*frac)
    a=pmf(total*(1-frac))
    p_home=(h*np.column_stack((np.zeros(len(total)),a.cumsum(1)[:,:-1]))).sum(1)
    p_draw=(h*a).sum(1)
    p_away=np.maximum(0,1-p_home-p_draw)
    return p_home,p_draw,p_away


def stats(rows,side):
    n=len(rows)
    vals=np.array([r["pnl_"+side] for r in rows])
    clv=np.array([r["clv_"+side] for r in rows])
    good=(vals>1e-9).sum();bad=(vals<-1e-9).sum()
    return {
        "n":n,
        "wins":int(good),"losses":int(bad),"pushes":int(n-good-bad),
        "net_U":round(float(vals.sum()),3),
        "roi_pct":round(float(vals.mean())*100,3) if n else None,
        "cross_line_clv_mean_ev_u":round(float(clv.mean()),5) if n else None,
        "cross_line_clv_positive_fraction":round(float((clv>0).mean()),5) if n else None
    }


def subset_stats(rows):
    return {
        "residual_side":stats(rows,"residual"),
        "opposite_side":stats(rows,"opposite"),
        "always_home":stats(rows,"home"),
        "always_away":stats(rows,"away"),
        "early_market_favorite":stats(rows,"favorite"),
        "closing_oracle_nontradable":stats(rows,"oracle"),
    }


def main():
    close={}
    for line in CLOSE.open():
        x=json.loads(line)
        if "AH" in x.get("markets",{}) and "OU" in x.get("markets",{}):
            close[str(x["fixture_id"])]=x
    COUNTS["close_fixture_ah_ou"]=len(close)
    # M5 2026 original Crown raw supplement is independently SHA-verified by the builder.
    # Preserve 2025 historical close inventory, use supplemental latest pre-kickoff
    # source events for 2026; source receipt itself occurred after kickoff.
    if not SUPPLEMENT.is_file():
        raise FileNotFoundError("Run build_2026_close_supplement.py before R2")
    with SUPPLEMENT.open() as f:
        for line in f:
            x=json.loads(line)
            fid=str(x["fixture_id"])
            old=close.get(fid)
            if old and (old["kickoff_utc"]!=x["kickoff_utc"] or old["score"]!=x["score"]):
                COUNTS["supplement_old_identity_or_score_conflict"]+=1
                continue
            close[fid]=x
            COUNTS["supplement_added" if old is None else "supplement_replaced"]+=1
    pairs=[]
    for line in EARLY.open():
        e=json.loads(line)
        if e.get("T")!=12 or e.get("year") not in (2025,2026):
            continue
        COUNTS["early_joint_12h_"+str(e["year"])]+=1
        if e.get("ah_kind")!="list" or e.get("ou_kind")!="list":
            COUNTS["early_not_two_movement_paths_"+str(e["year"])]+=1
            continue
        c=close.get(str(e["fid"]))
        if not c:
            COUNTS["missing_close"]+=1;continue
        ko=time(c["kickoff_utc"])
        cut=ko-dt.timedelta(hours=12)
        try:
            a=c["markets"]["AH"];o=c["markets"]["OU"]
            at=time(a["quote_source_at_utc"]);ot=time(o["quote_source_at_utc"])
            # If "closing" historical quote precedes early cutoff, it adds no follow-up valuation.
            if not (cut<at<ko and cut<ot<ko):
                COUNTS["close_not_after_entry_cutoff"]+=1
                continue
            if f'{e["hg"]}-{e["ag"]}' != c["score"]:
                COUNTS["score_mismatch"]+=1;continue
            vals=[
                e["al"],e["ah"],e["aa"],e["ol"],e["oo"],e["ou"],
                a["line"],a["odds"]["home"],a["odds"]["away"],
                o["line"],o["odds"]["over"],o["odds"]["under"]]
            v=np.array(vals,dtype=float)
            if not np.isfinite(v).all() or min(v[[1,2,4,5,7,8,10,11]])<=1:
                COUNTS["invalid_market_values"]+=1;continue
            if any(abs(float(v[j])*4-round(float(v[j])*4))>1e-7 for j in (0,3,6,9)):
                COUNTS["invalid_line"]+=1;continue
            if len(e.get("p1x2",[]))!=3 or abs(sum(e["p1x2"])-1)>1e-5:
                COUNTS["missing_or_invalid_1x2"]+=1;continue
            if min(e["p1x2"])<=0 or min(e.get("age_1x2",0),e["age_ah"],e["age_ou"])<0:
                COUNTS["invalid_1x2_or_age"]+=1;continue
            pairs.append(dict(fid=str(e["fid"]),year=e["year"],league=e["league"],
                hg=int(e["hg"]),ag=int(e["ag"]),
                p1x2=e["p1x2"], age_1x2=e["age_1x2"],
                age_ah=e["age_ah"],age_ou=e["age_ou"],
                ko=c["kickoff_utc"],tah=at.isoformat(),tou=ot.isoformat(),
                ahline0=e["al"],aho0=e["ah"],aha0=e["aa"],
                ouline0=e["ol"],ovo0=e["oo"],ovu0=e["ou"],
                ahline1=a["line"],aho1=a["odds"]["home"],aha1=a["odds"]["away"],
                ouline1=o["line"],ovo1=o["odds"]["over"],ovu1=o["odds"]["under"]))
            COUNTS["paired_"+str(e["year"])]+=1
        except Exception as ex:
            COUNTS["exception_"+type(ex).__name__]+=1
            if COUNTS["exception_"+type(ex).__name__]<3:
                print("ROW_EXC",repr(ex))
    print("PAIRING",len(pairs),dict(COUNTS),flush=True)
    if not pairs:
        raise RuntimeError("no pairs")
    arr=lambda name:np.array([x[name] for x in pairs],dtype=float)
    eT,eF,eOK,eErr0,eErr1=latent(*[arr(k) for k in ("ahline0","aho0","aha0","ouline0","ovo0","ovu0")])
    cT,cF,cOK,cErr0,cErr1=latent(*[arr(k) for k in ("ahline1","aho1","aha1","ouline1","ovo1","ovu1")])
    eh,ed,ea=onex2(eT,eF)
    ch,cd,ca=onex2(cT,cF)
    # True cross-line repricing: use *closing-implied score distribution*
    # to price the *entry AH contract*, regardless of changed handicap line.
    wh,lh=ah_components(cT,cF,arr("ahline0"))
    wa,la=ah_components(cT,1-cF,-arr("ahline0"))
    vh=(arr("aho0")-1)*wh-lh
    va=(arr("aha0")-1)*wa-la
    # Only for internal diagnostics; never select based on future closing prices.
    E=np.stack([vh,va],axis=1)
    oracle=np.where(E[:,0]>=E[:,1],"home","away")
    residues=np.log(np.array([r["p1x2"][0]/r["p1x2"][2] for r in pairs]))-np.log(np.maximum(eh,1e-9)/np.maximum(ea,1e-9))
    valid=eOK & cOK
    COUNTS["latent_both_fit_ok"]=int(valid.sum())
    COUNTS["latent_early_invalid"]=int((~eOK).sum())
    COUNTS["latent_close_invalid"]=int((~cOK).sum())
    groups=collections.defaultdict(list)
    with gzip.open(ROWS,"wt") as out:
        for i,r in enumerate(pairs):
            if not valid[i]:
                continue
            side="home" if residues[i]>=0 else "away"
            opp="away" if side=="home" else "home"
            fav="home" if r["ahline0"]<0 else "away" if r["ahline0"]>0 else ("home" if r["aho0"]<r["aha0"] else "away")
            record=dict(fid=r["fid"],year=r["year"],league=r["league"],kickoff_utc=r["ko"],
                age_ah_h=r["age_ah"],age_ou_h=r["age_ou"],age_1x2_h=r["age_1x2"],
                line_early=r["ahline0"],line_close=r["ahline1"],
                has_AH_line_change=(r["ahline0"]!=r["ahline1"]),
                has_OU_line_change=(r["ouline0"]!=r["ouline1"]),
                early_total_lambda=round(float(eT[i]),5),
                early_home_lambda=round(float(eT[i]*eF[i]),5),
                closing_total_lambda=round(float(cT[i]),5),
                closing_home_lambda=round(float(cT[i]*cF[i]),5),
                early_joint_implied_home_win=round(float(eh[i]),6),
                early_1x2_home_win=float(r["p1x2"][0]),
                early_1x2_age_h=round(float(r["age_1x2"]),3),
                early_1x2_vs_joint_log_home_away_residual=round(float(residues[i]),6),
                predicted_residual_side=side,
                close_CLV_ev_home=round(float(vh[i]),6),
                close_CLV_ev_away=round(float(va[i]),6),
                pnl_residual=settle_score("AH",r["ahline0"],side,r["hg"],r["ag"],r["aho0"] if side=="home" else r["aha0"])[1],
                pnl_opposite=settle_score("AH",r["ahline0"],opp,r["hg"],r["ag"],r["aho0"] if opp=="home" else r["aha0"])[1],
                pnl_home=settle_score("AH",r["ahline0"],"home",r["hg"],r["ag"],r["aho0"])[1],
                pnl_away=settle_score("AH",r["ahline0"],"away",r["hg"],r["ag"],r["aha0"])[1],
                pnl_favorite=settle_score("AH",r["ahline0"],fav,r["hg"],r["ag"],r["aho0"] if fav=="home" else r["aha0"])[1],
                pnl_oracle=settle_score("AH",r["ahline0"],oracle[i],r["hg"],r["ag"],r["aho0"] if oracle[i]=="home" else r["aha0"])[1],
                clv_residual=float(vh[i] if side=="home" else va[i]),
                clv_opposite=float(va[i] if side=="home" else vh[i]),
                clv_home=float(vh[i]), clv_away=float(va[i]),
                clv_favorite=float(vh[i] if fav=="home" else va[i]),
                clv_oracle=float(max(vh[i],va[i])),
            )
            out.write(json.dumps(record,ensure_ascii=False)+"\n")
            groups[str(r["year"])].append(record)
            groups["all"].append(record)
            groups[str(r["year"])+"|1x2_age<=6h" if r["age_1x2"]<=6 else str(r["year"])+"|1x2_age>6h"].append(record)
            groups[str(r["year"])+"|AH_OU_ages<=6h" if max(r["age_ah"],r["age_ou"])<=6 else str(r["year"])+"|AH_OU_ages>6h"].append(record)
            groups[str(r["year"])+"|line_changed" if record["has_AH_line_change"] else str(r["year"])+"|same_line"].append(record)
    summary=dict(
        protocol="CROWN_T12_CROSSMARKET_JOINT_POISSON_CROSSCONTRACT_CLV_R2",
        generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_quote_status="Crown historical event timestamps, source responses retrieved after games; not actual received entry prices",
        asof_information="Only early same-event-hour Crown AH/OU, historical 1x2 open/close <= T12 used for residual direction; future closing AH/OU used solely for post-hoc CLV",
        caveats=[
            "Independent-Poisson is a market-implied pricing approximation, not a guaranteed true score distribution.",
            "Historical 1x2 snapshots often stale; benchmark reports quote ages, no fresh data invented.",
            "Cross-line CLV uses closing AH+OU fitted probabilities to price original early AH contract; it is NOT same-line price ratio and not observed cashout.",
            "All early/late Crown price responses were fetched in 2026 after matches; no live tradable proof.",
            "Age subgroups are descriptive diagnostics only, not a new gating or filtering rule.",
            "Oracle chooses side using future close and is explicitly NOT a tradable result.",
        ],
        inputs=dict(early=str(EARLY),close=str(CLOSE)),
        counts=dict(COUNTS),
        fit_details=dict(early_error_p99=round(float(np.quantile(np.maximum(eErr0,eErr1)[eOK],.99)),7) if eOK.any() else None,
            close_error_p99=round(float(np.quantile(np.maximum(cErr0,cErr1)[cOK],.99)),7) if cOK.any() else None),
        groups={key:subset_stats(rows) for key,rows in sorted(groups.items())},
        output_rows=str(ROWS)
    )
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print("RESULT",OUT,flush=True)
    for k in ("2025","2026","2025|1x2_age<=6h","2026|1x2_age<=6h","2025|AH_OU_ages<=6h","2026|AH_OU_ages<=6h"):
        if k in summary["groups"]:
            g=summary["groups"][k]
            print(k, "residual",g["residual_side"],"opposite",g["opposite_side"],"oracle (non-tradable)",g["closing_oracle_nontradable"],flush=True)


if __name__=="__main__":
    main()
