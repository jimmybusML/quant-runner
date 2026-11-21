#!/usr/bin/env python3
"""Forward-only portability and uncertainty audit for frozen M8 base/A-G.

Research only. Inputs are the already built complete Crown historical event
paths. This script does not collect data or change any production behavior.
"""
from __future__ import annotations
import collections, datetime as dt, gzip, hashlib, json, math, pathlib, random

HERE = pathlib.Path(__file__).resolve().parent
INPUT = HERE / "exact_rule_cross_league_all_complete_paths.jsonl.gz"
ORDERS = HERE / "exact_rule_cross_league_orders.jsonl.gz"
OUT_JSON = HERE / "cross_league_transfer_inference_20261120.json"
OUT_LEDGER = HERE / "cross_league_transfer_inference_orders_20261120.jsonl.gz"
OUT_SELECTOR_LEDGER = HERE / "prior_year_group_selector_orders_20261120.jsonl.gz"
FROZEN = pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl")
GROUPS = ("base", "A", "B", "C", "D", "E", "F", "G")
SEED = 20261120
N_BOOT = 20000

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def settle(line, side, hg, ag, odds):
    legs = [float(line)] if abs(float(line)*2-round(float(line)*2)) < 1e-8 else [math.floor(float(line)*2)/2, math.ceil(float(line)*2)/2]
    pnl=[]; states=[]
    for leg in legs:
        margin = hg-ag+leg if side == "home" else ag-hg-leg
        if margin > 1e-9: pnl.append(odds-1); states.append("win")
        elif margin < -1e-9: pnl.append(-1.); states.append("loss")
        else: pnl.append(0.); states.append("push")
    value = sum(pnl)/len(pnl)
    state = "full_win" if all(x=="win" for x in states) else "half_win" if "win" in states else "push" if all(x=="push" for x in states) else "half_loss" if "push" in states else "full_loss"
    return value,state

def metrics(rows, observation_weeks=None):
    n=len(rows); pnl=sum(r["net_u"] for r in rows)
    d=collections.defaultdict(float)
    for r in rows: d[r["date"]]+=r["net_u"]
    c=peak=mdd=0.
    for _,x in sorted(d.items()):
        c+=x; peak=max(peak,c); mdd=max(mdd,peak-c)
    weeks=sorted({r["iso_week"] for r in rows})
    denominator=len(observation_weeks) if observation_weeks is not None else len(weeks)
    return {"orders":n,"net_u":round(pnl,6),"roi_pct":round(100*pnl/n,6) if n else None,"mdd_u":round(mdd,6),"active_iso_weeks":len(weeks),"active_week_avg":round(n/len(weeks),6) if weeks else 0,"observation_iso_weeks":denominator,"observation_week_avg":round(n/denominator,6) if denominator else 0}

def calendar_span_weeks(dates):
    ds=[dt.date.fromisoformat(x) for x in dates]
    if not ds: return 0
    a=min(ds); b=max(ds); keys=set()
    for i in range((b-a).days+1):
        iso=(a+dt.timedelta(days=i)).isocalendar(); keys.add((iso.year,iso.week))
    return len(keys)

def percentile(v,p):
    v=sorted(v); z=(len(v)-1)*p; lo=math.floor(z); hi=math.ceil(z)
    return v[lo]+(v[hi]-v[lo])*(z-lo)

def stratified_week_bootstrap(rows, reps=N_BOOT, seed=SEED):
    """Resample ISO weeks within year, preserving each year’s observation span."""
    by_year=collections.defaultdict(lambda:collections.defaultdict(list))
    for r in rows: by_year[r["year"]][r["iso_week"]].append(r)
    rng=random.Random(seed); pnl_dist=[]; roi_dist=[]
    for _ in range(reps):
        n=0; pnl=0.
        for y,wm in by_year.items():
            keys=list(wm)
            for _j in keys:
                block=wm[rng.choice(keys)]
                n+=len(block); pnl+=sum(x["net_u"] for x in block)
        pnl_dist.append(pnl); roi_dist.append(100*pnl/n if n else 0)
    return {"method":"stratified ISO-week cluster bootstrap within calendar year; descriptive uncertainty, not a guarantee","replicates":reps,
            "net_u_95pct":[round(percentile(pnl_dist,.025),6),round(percentile(pnl_dist,.975),6)],
            "roi_pct_95pct":[round(percentile(roi_dist,.025),6),round(percentile(roi_dist,.975),6)],
            "probability_net_positive":round(sum(x>0 for x in pnl_dist)/reps,6)}

def main():
    paths=[json.loads(x) for x in gzip.open(INPUT,"rt",encoding="utf-8") if x.strip()]
    original=[json.loads(x) for x in gzip.open(HERE/"exact_rule_cross_league_orders.jsonl.gz","rt",encoding="utf-8") if x.strip()]
    frozen_rows=[json.loads(x) for x in open(FROZEN,encoding="utf-8") if x.strip()]
    frozen_ids={x["fid"] for x in frozen_rows}
    order_by={r["fid"]:r for r in original}
    assert len({r["fid"] for r in paths})==len(paths), "duplicate FID in complete-path inventory"
    assert len(frozen_ids)==10294 and sha(FROZEN)=="6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665"
    assert not ({r["fid"] for r in paths} & frozen_ids), "complete path inventory overlaps frozen eight"
    ledger=[]; raw_by_group={g:[] for g in GROUPS}; selected_by_year=collections.defaultdict(list)
    for r in paths:
        y=int(r["year"]); ko=dt.datetime.fromisoformat(r["kickoff_china"]); iso=ko.date().isocalendar(); wk=f"{iso.year}-W{iso.week:02d}"
        hits=r.get("raw_group_hits") or {}
        for g,side in hits.items():
            u,state=settle(r["end_line"],side,int(r["hg"]),int(r["ag"]),float(r[f"{side}_price"]))
            raw_by_group[g].append({"fid":r["fid"],"year":y,"date":ko.date().isoformat(),"iso_week":wk,"league":r["league"],"group":g,"side":side,"line":r["end_line"],"price":r[f"{side}_price"],"net_u":u,"settlement":state})
        # Primary frozen rule-transfer union (the published priority allocation).
        old=order_by.get(r["fid"])
        if old:
            assert old["group"] in hits and old["side"]==hits[old["group"]]
            action={"group":old["group"],"side":old["side"],"net_u":float(old["net_u"]),"settlement":old["settlement"]}
        else: action=None
        # Same-FID low-price side control on the precise candidate inventory.
        fav="home" if float(r["home_price"])<=float(r["away_price"]) else "away"
        fav_u,fav_state=settle(r["end_line"],fav,int(r["hg"]),int(r["ag"]),float(r[f"{fav}_price"]))
        if action:
            row={"fid":r["fid"],"year":y,"date":ko.date().isoformat(),"iso_week":wk,"league":r["league"],"home":r["home"],"away":r["away"],"hg":r["hg"],"ag":r["ag"],"group":action["group"],"side":action["side"],"line":r["end_line"],"price":r[f"{action['side']}_price"],"settlement":action["settlement"],"net_u":action["net_u"],"favorite_side":fav,"favorite_price":r[f"{fav}_price"],"favorite_settlement":fav_state,"favorite_net_u":fav_u,"source_class":"historical Crown source-event replay"}
            ledger.append(row)
    assert len(ledger)==len(original)==1271
    # One frozen group chosen only by cumulative previous-year returns. Group definitions,
    # directions and settlements are unchanged; this is an experimental selector.
    selector_all=[]
    for y in (2024,2025,2026):
        training=[x for g in GROUPS for x in raw_by_group[g] if x["year"]<y]
        scores={g:sum(x["net_u"] for x in raw_by_group[g] if x["year"]<y) for g in GROUPS}
        pick=max(GROUPS,key=lambda g:(scores[g],-GROUPS.index(g)))
        target=[]
        for r in paths:
            if int(r["year"])!=y: continue
            side=(r.get("raw_group_hits") or {}).get(pick)
            if not side: continue
            ko=dt.datetime.fromisoformat(r["kickoff_china"]); iso=ko.date().isocalendar(); wk=f"{iso.year}-W{iso.week:02d}"
            u,state=settle(r["end_line"],side,int(r["hg"]),int(r["ag"]),float(r[f"{side}_price"]))
            target.append({"fid":r["fid"],"year":y,"date":ko.date().isoformat(),"iso_week":wk,"league":r["league"],"group":pick,"side":side,"line":r["end_line"],"price":r[f"{side}_price"],"settlement":state,"net_u":u})
        selected_by_year[y]={"training_years":[min((x["year"] for x in training),default=None),max((x["year"] for x in training),default=None)],"prior_group_net_u":{g:round(scores[g],6) for g in GROUPS},"selected_group":pick,"test":metrics(target),"test_fids":target}
        selector_all.extend(target)
    # Methods by year, and same-candidate low-price side diagnostic.
    years=sorted({x["year"] for x in ledger})
    observed={}
    for r in paths:
        iso=dt.datetime.fromisoformat(r["kickoff_china"]).date().isocalendar()
        observed.setdefault(int(r["year"]),set()).add((iso.year,iso.week))
    all_observed=set().union(*observed.values())
    path_dates=collections.defaultdict(list)
    for r in paths: path_dates[int(r["year"])].append(dt.datetime.fromisoformat(r["kickoff_china"]).date().isoformat())
    span_by_year={y:calendar_span_weeks(ds) for y,ds in path_dates.items()}
    recent_dates=[d for y,ds in path_dates.items() if y>=2024 for d in ds]
    by_year={str(y):metrics([x for x in ledger if x["year"]==y],observed.get(y,set())) for y in years}
    fav_ledger=[]
    path_by={r["fid"]:r for r in paths}
    for x in ledger:
        p=path_by[x["fid"]]; side="home" if float(p["home_price"])<=float(p["away_price"]) else "away"
        u,s=settle(p["end_line"],side,int(p["hg"]),int(p["ag"]),float(p[f"{side}_price"]))
        fav_ledger.append({**x,"side":side,"price":p[f"{side}_price"],"net_u":u,"settlement":s})
    recent=[x for x in ledger if x["year"]>=2024]
    recent_obs=set().union(*(observed.get(y,set()) for y in (2024,2025,2026)))
    frozen_normalized=[]
    for x in frozen_rows:
        iso=dt.date.fromisoformat(x["date"]).isocalendar()
        frozen_normalized.append({"fid":x["fid"],"year":int(x["year"]),"date":x["date"],"iso_week":f"{iso.year}-W{iso.week:02d}","net_u":float(x["pnl"])})
    frozen_recent=[x for x in frozen_normalized if x["year"]>=2024]
    merged=frozen_normalized+ledger
    merged_recent=frozen_recent+recent
    assert len({x["fid"] for x in merged})==len(merged)
    merged_years={str(y):metrics([x for x in merged if x["year"]==y]) for y in sorted({x["year"] for x in merged})}
    # Candidates from the exact available paths: historic exact transfer; true-receipt intersection is audited separately as zero.
    result={"study":"M8 exact frozen base/A-G transfer inference audit; no new gate or production rule","inputs":{"complete_paths_sha256":sha(INPUT),"published_order_ledger_sha256":sha(HERE/"exact_rule_cross_league_orders.jsonl.gz"),"frozen_membership_sha256":sha(FROZEN)},
      "scope":{"complete_path_fids":len(paths),"incremental_union_orders":len(ledger),"original_eight_overlap":0,"historical_replay_only":True,"true_receipt_incremental_orders":0},
      "coverage_calendar":{"path_covered_iso_weeks":len(all_observed),"calendar_span_iso_weeks":calendar_span_weeks([d for ys in path_dates.values() for d in ys]),"path_covered_iso_weeks_2024_2026":len(recent_obs),"calendar_span_iso_weeks_2024_2026":calendar_span_weeks(recent_dates),"by_year":{str(y):{"path_covered_iso_weeks":len(observed[y]),"calendar_span_iso_weeks":span_by_year[y]} for y in sorted(path_dates)}},
      "exact_rule_union":{"all_years":metrics(ledger,all_observed),"by_year":by_year,"2024_2026":metrics(recent,recent_obs),"stratified_week_bootstrap_all_years":stratified_week_bootstrap(ledger),"stratified_week_bootstrap_2024_2026":stratified_week_bootstrap(recent)},
      "same_fid_lower_price_side_control":{"all_candidate_fids":metrics(fav_ledger,all_observed),"2024_2026":metrics([x for x in fav_ledger if x["year"]>=2024],recent_obs),"incremental_union_minus_control_u":round(sum(x["net_u"] for x in ledger)-sum(x["net_u"] for x in fav_ledger),6)},
      "combined_frozen_eight":{"original_baseline":{"orders":len(frozen_normalized),"net_u":round(sum(x["net_u"] for x in frozen_normalized),6)},"after_increment":{"all_years":metrics(merged),"by_year":merged_years,"2024_2026":metrics(merged_recent),"incremental_net_u_all_years":round(sum(x["net_u"] for x in ledger),6),"incremental_net_u_2024_2026":round(sum(x["net_u"] for x in recent),6)}},
      "prior_year_group_selector":{"selection_basis":"largest cumulative raw group net U in earlier calendar years only; ties use frozen priority","by_test_year":{str(k):{a:b for a,b in v.items() if a!="test_fids"} for k,v in selected_by_year.items()},"combined_test":metrics(selector_all)},
      "raw_group_precedence_diagnostic":{g:{"all_years":metrics(raw_by_group[g],all_observed),"by_year":{str(y):metrics([x for x in raw_by_group[g] if x["year"]==y],observed.get(y,set())) for y in sorted(observed)}} for g in GROUPS},
      "limitations":["historical Crown source-event replay, not actual pre-kick receipt or execution","week bootstrap is descriptive and does not remove repeated model research/selection bias","2026 path inventory ends 2026-06-01","the prior-year group selector is a research ablation, not a production gate"]}
    OUT_JSON.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    with gzip.open(OUT_LEDGER,"wt",encoding="utf-8") as f:
        for x in ledger: f.write(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n")
    with gzip.open(OUT_SELECTOR_LEDGER,"wt",encoding="utf-8") as f:
        for y in sorted(selected_by_year):
            for x in selected_by_year[y]["test_fids"]: f.write(json.dumps(x,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps({"output":str(OUT_JSON),"orders":len(ledger),"all":result["exact_rule_union"]["all_years"],"recent":result["exact_rule_union"]["2024_2026"],"bootstrap":result["exact_rule_union"]["stratified_week_bootstrap_2024_2026"],"selector":result["prior_year_group_selector"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
