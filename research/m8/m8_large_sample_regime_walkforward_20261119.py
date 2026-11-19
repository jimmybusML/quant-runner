#!/usr/bin/env python3
"""M8 broad-history, research-only Crown AH market-state mechanism walk-forward.

Uses the historical event-time replay (NOT proof of actual pregame receipt);
does not change original eight, trading, Telegram, or production.
Method selection uses only prior calendar-year outcomes, never target-year FT.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA=Path("/Users/mac/QuantAsiaDesk/research-work")
FEATS=DATA/"m8_late_full_path_water_features_20261114.jsonl"
FROZEN=DATA/"m8_foundation_20261115/historical_membership.jsonl"
OUT=ROOT/"research/m8/m8_large_sample_regime_walkforward_20261119"
def sg(v):
    return 1 if v>1e-10 else -1 if v< -1e-10 else 0
def amount(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else 0
    except (TypeError,ValueError):return 0
def true(v):return bool(v)
def period(v):
    if v< -1e-9:return "negative"
    if v>1e-9:return "positive"
    return "flat"
def feature_groups(r):
    line=amount(r["end_line"]); start=amount(r["start_line"])
    h=amount(r["home_price"]); a=amount(r["away_price"])
    sh=amount(r["start_home_price"]);sa=amount(r["start_away_price"])
    dog="home" if line>0 else "away" if line<0 else "level"
    dogprice=h if dog=="home" else a if dog=="away" else 0
    fprice=a if dog=="home" else h if dog=="away" else 0
    d_start=sh if dog=="home" else sa if dog=="away" else 0
    f_start=sa if dog=="home" else sh if dog=="away" else 0
    path=r.get("path_shape") or "unknown"
    rel=sg((dogprice-d_start)-(fprice-f_start)) if dog!="level" else 0
    water=amount(r.get("home_price_vs_timeavg"))-amount(r.get("away_price_vs_timeavg"))
    from_line=sg(abs(line)-abs(start))
    lastprice=(dogprice-d_start) if dog!="level" else (h-sh)-(a-sa)
    n=int(amount(r.get("n_events")))
    return {
      "regime_x_contract":(path, "level" if dog=="level" else "dog_home" if dog=="home" else "dog_away", "quarter" if abs(line*2-round(line*2))>1e-8 else "whole_or_half"),
      "line_direction_x_water":(period(abs(line)-abs(start)),period(lastprice),"dog" if dog!="level" else "level"),
      "elasticity_dislocation":(path,period((dogprice-d_start)-(fprice-f_start)),period(water)),
      "late_vs_early_reprice":(path, period(amount(r.get("fav_last_move"))),period(amount(r.get("fav_end_vs_start")))),
      "time_path_state":(path, "recent" if amount(r.get("late_event_age_min"))<=30 else "older", "dense" if n>=6 else "sparse"),
      "price_contract_tension":(period(h-a),period(h-sh),period(a-sa),"large" if abs(line)>=1 else "small"),
      "water_endpoint_discordance":(period((h-sh)-(a-sa)),period(water),period(abs(line)-abs(start))),
      "market_state_joint":(path,period((h-sh)-(a-sa)),"large" if abs(line)>=1 else "small"),
    }
def min_model_train(rows, year, family, kind):
    # Every train example is strictly earlier calendar year than evaluation target.
    # Smoothed profitability is a *research-side selector*, not a production gate.
    train=collections.defaultdict(list)
    for r in rows:
        if r["year"]>=year:continue
        key=("all",) if family=="global_side" else r["groups"][family]
        train[key].append(r)
    if kind=="global_side":
        train={("all",):[r for r in rows if r["year"]<year]}
    chosen={}
    for key,sub in train.items():
        home=np.mean([r["home_u"] for r in sub])
        away=np.mean([r["away_u"] for r in sub])
        # Shrink each side mean toward 0; same factor to both sides per key.
        coeff=len(sub)/(len(sub)+200)
        chosen[key]={"side":"home" if coeff*home>=coeff*away else "away","training_n":len(sub),
                     "training_h":round(float(home),6),"training_a":round(float(away),6),
                     "training_max":round(float(max(home,away)),6)}
    return chosen
def mdd(rows):
    daily=collections.defaultdict(float)
    for r in rows:daily[r["date"]]+=r["pnl_u"]
    pnl=peak=worst=0.
    for day,u in sorted(daily.items()):
        pnl+=u;peak=max(peak,pnl);worst=max(worst,peak-pnl)
    return round(worst,4)
def stats(rows):
    n=len(rows);u=sum(r["pnl_u"] for r in rows)
    weekly=collections.defaultdict(lambda:[0,0.])
    for r in rows:
        y,w,_=dt.date.fromisoformat(r["date"]).isocalendar()
        k=f"{y}-W{w:02d}"
        weekly[k][0]+=1;weekly[k][1]+=r["pnl_u"]
    return {"n":n,"net_u":round(u,4),"roi_pct":round(u/n*100,4) if n else None,
            "mdd_u":mdd(rows),"weekly":{k:{"n":v[0],"net_u":round(v[1],4)} for k,v in sorted(weekly.items())}}
def run():
    frozen=[json.loads(l) for l in FROZEN.open() if l.strip()]
    fids={str(x["fid"]) for x in frozen}
    assert len(fids)==10294
    rows=[];quality=collections.Counter()
    for line in FEATS.open():
        x=json.loads(line)
        fid=str(x["fid"])
        if fid in fids:
            quality["frozen_excluded"]+=1;continue
        try:
            y=int(x["year"]);h=float(x["end_home_U"]);a=float(x["end_away_U"])
            if not all(math.isfinite(v) for v in (h,a)):raise ValueError("nonfinite")
            groups=feature_groups(x)
            rows.append({"fid":fid,"year":y,"date":x["date"],"home_u":h,"away_u":a,"groups":groups,"league":str(x.get("league"))})
        except Exception:quality["invalid"]+=1
    assert len(rows)==len({r["fid"] for r in rows})
    families=list(rows[0]["groups"])+["global_side"]
    allbets=[];results={}
    for year in (2023,2024,2025,2026):
        test=[r for r in rows if r["year"]==year]
        for family in families:
            models=min_model_train(rows,year,family,"forced_side")
            fallback=min_model_train(rows,year,"global_side","global_side")[("all",)]
            bets=[]
            for r in test:
                key=("all",) if family=="global_side" else r["groups"][family]
                meta=models.get(key) or fallback
                side=meta["side"]
                bet={"fid":r["fid"],"year":year,"date":r["date"],"league":r["league"],"family":family,
                     "side":side,"pnl_u":r["home_u"] if side=="home" else r["away_u"],
                     "training_group_n":meta["training_n"],"used_global_fallback":key not in models,
                     "full_replay_not_HTTP_receipt":True}
                bets.append(bet)
            allbets.extend(bets)
            results.setdefault(family,{})[str(year)]=stats(bets)
    # Exploratory selective variation: fit a market-state expected return on prior
    # years alone; skip only when the prior-year state mean does not exceed zero.
    # This is NOT a formal trading Gate or a change to any frozen strategy.
    for year in (2023,2024,2025,2026):
        test=[r for r in rows if r["year"]==year]
        for family in [f for f in families if f!="global_side"]:
            model=min_model_train(rows,year,family,"exploratory_selective")
            bets=[]
            for r in test:
                meta=model.get(r["groups"][family])
                if not meta or meta["training_max"]<=0:continue
                side=meta["side"]
                bets.append({"fid":r["fid"],"year":year,"date":r["date"],"league":r["league"],
                             "family":family+"__historical_positive_state","side":side,
                             "pnl_u":r["home_u"] if side=="home" else r["away_u"],
                             "training_group_n":meta["training_n"],
                             "source":"historical_event_replay_not_live_receipt",
                             "experimental_condition_not_production_gate":True})
            allbets.extend(bets)
            results.setdefault(family+"__historical_positive_state",{})[str(year)]=stats(bets)
    families=list(results)
    # 2024–26 frozen is archived benchmark, not a recomputed different odds vintage.
    benchmark={"2024_2026_n":6873,"2024_2026_net_u":197.765}
    for family in families:
        years=[r for r in allbets if r["family"]==family and 2024<=r["year"]<=2026]
        results[family]["2024_2026_new"]=stats(years)
        results[family]["2024_2026_combined_retrospective"]={
            "n":benchmark["2024_2026_n"]+len(years),
            "net_u":round(benchmark["2024_2026_net_u"]+sum(r["pnl_u"] for r in years),4),
            "roi_pct":round(100*(benchmark["2024_2026_net_u"]+sum(r["pnl_u"] for r in years))/(benchmark["2024_2026_n"]+len(years)),4)}
    summary={"description":"8 pre-specified market-state families plus global side. Forced directional action per available out-of-eight fixture, trained solely on prior calendar years; no outcome lookup of held-out year. Not 8 new approved trading rules.","source":"2019–2026 Crown historical source-event prices retrieved after results; no historical actual HTTP receipt proof.","foundation_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
            "input_sha256":hashlib.sha256(FEATS.read_bytes()).hexdigest(),
            "historical_rows_ex_frozen":len(rows),"quality":dict(quality),"families":families,"frozen_benchmark":benchmark,
            "results":results,"caution":"All candidate mechanisms investigated after many prior experiments. Any positive slice is exploratory; not fresh independent OOS or production signal."}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    with (OUT/"per_fixture_predictions.jsonl").open("w") as f:
        for r in allbets:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    print("SCOPE",len(rows),quality,flush=True)
    for k in families:
        print(k,[(y,results[k][str(y)]["n"],results[k][str(y)]["net_u"],results[k][str(y)]["roi_pct"]) for y in (2023,2024,2025,2026)],"2024_26",results[k]["2024_2026_new"]["net_u"],flush=True)
if __name__=="__main__":run()
