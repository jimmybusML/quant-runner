#!/usr/bin/env python3
"""R4 independent checks and descriptive pre-T12 OU -> post-T12 AH market repricing."""
import collections
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from research.m3.probabilities import settle_score

HERE=Path(__file__).resolve().parent
S=json.load(open(HERE/"crossmarket_event_lead_r4_results.json"))
R2={r["fid"]:r for r in map(json.loads,gzip.open(HERE/"joint_fair_value_r2_research_rows.jsonl.gz","rt"))}
R3={r["fid"]:r for r in map(json.loads,gzip.open(HERE/"independent_team_information_r3_predictions.local.jsonl.gz","rt"))}
T=[r for r in map(json.loads,gzip.open(HERE/"crossmarket_event_lead_r4_predictions.local.jsonl.gz","rt"))]
TR=[r for r in map(json.loads,gzip.open(HERE/"crossmarket_event_lead_r4_training.local.jsonl.gz","rt"))]
OUT=HERE/"crossmarket_event_lead_r4_validation.json"

assert len(R2)==9952 and len(R3)==len(T)==8860 and len(TR)==1092
assert len({r["fid"] for r in T+TR})==9952
audit=collections.Counter()
for r in TR+T:
    base=R2[r["fid"]]
    assert r["ko"]==base["kickoff_utc"]
    assert r["line_early"]==base["line_early"]
    assert r["year"]==base["year"]
    assert abs(r["entry_ah_path_asof_line"]-base["line_early"])<1e-9
    assert len(r["market"])==9 and len(r["events"])==22
    cutoff=dt.datetime.fromisoformat(r["ko"])-dt.timedelta(hours=12)
    assert dt.datetime.fromisoformat(r["t12_ah_quote_event"])<=cutoff
    if r["t12_ou_quote_event"]:
        assert dt.datetime.fromisoformat(r["t12_ou_quote_event"])<=cutoff
    for k in ("home","away"):
        assert abs(r["pnl_"+k]-base["pnl_"+k])<1e-9
        assert abs(r["clv_"+k]-base["clv_"+k])<1e-9
    audit["input_and_asof_verified"]+=1

for r in T:
    base=R2[r["fid"]]
    original=R3[r["fid"]]
    assert np.max(np.abs(np.array(original["feature"]["market"])-np.array(r["market"])))<1e-7
    assert original["predict"]["market_clv_frozen_2025"]==r["pred"]["market_clv_frozen_2025"]
    assert original["predict"]["market_clv_expanding_monthly"]==r["pred"]["market_clv_expanding_monthly"]
    for name in S["variants"]+S["baselines"]:
        side=r["pred"][name]
        assert side in ("home","away")
        vals=base["pnl_"+side]
        assert abs(vals-r["pnl_"+side])<1e-9
    audit["holdout_direction_reconciled"]+=1

# Rebuild every candidate's net units and close-model estimate, independent of summary.
for k,x in S["summary_2026"].items():
    p=[r["pnl_"+r["pred"][k]] for r in T]
    ev=[r["clv_"+r["pred"][k]] for r in T]
    assert x["n"]==len(T)
    assert abs(round(sum(p),3)-x["net_U"])<1e-9
    assert abs(round(100*np.mean(p),4)-x["roi_pct"])<1e-9
    assert abs(round(100*np.mean(ev),4)-x["close_implied_ev_pct"])<1e-9
    audit["variant_results_reconciled"]+=1

# Classify prior event movement only when both T24 and T12 snapshots existed.
def status(r):
    e=r["events"]
    # AH: 24=>12 direction by line or same-contract probability, OU similarly.
    if e[2] or e[13]:
        return "T24_missing"
    amoved=abs(e[0])>1e-9 or abs(e[1])>1e-9
    omoved=abs(e[11])>1e-9 or abs(e[12])>1e-9
    if amoved and omoved:return "AH_and_OU_changed_before_T12"
    if omoved:return "OU_only_changed_before_T12"
    if amoved:return "AH_only_changed_before_T12"
    return "neither_net_changed_before_T12"

def describe(rs):
    by=collections.defaultdict(list)
    for r in rs:by[status(r)].append(r)
    ret={}
    for name,z in sorted(by.items()):
        futures=[R2[r["fid"]]["line_close"]-r["line_early"] for r in z]
        vals=[r["clv_home"]-r["clv_away"] for r in z]
        ret[name]=dict(n=len(z),
            future_AH_line_changed=sum(abs(x)>1e-9 for x in futures),
            future_AH_line_changed_pct=round(100*sum(abs(x)>1e-9 for x in futures)/len(z),3),
            future_home_handicap_strengthened=sum(x<-1e-9 for x in futures),
            future_home_handicap_weakened=sum(x>1e-9 for x in futures),
            median_future_model_CLV_home_minus_away=round(float(np.median(vals)),5))
        if z[0]["year"]==2026:
            for m in ("market_clv_frozen_2025","event_clv_frozen_2025",
                      "market_plus_event_clv_frozen_2025","market_clv_expanding_monthly",
                      "event_clv_expanding_monthly","market_plus_event_clv_expanding_monthly"):
                ret[name][m+"_roi_pct"]=round(100*sum(a["pnl_"+a["pred"][m]] for a in z)/len(z),3)
    return ret

# Replicate actual live-received archived footprint: separate cohort and not used for R4 historical backtest.
live=Path("/Users/mac/QuantAsiaDesk/research-work/m8_live_HTTP_receipt_availability_inventory_20261113.jsonl")
live_rows=[json.loads(line) for line in live.open()]
recv=[q for x in live_rows for q in x["quotes"]]
true_recv={
    "snapshot_archive_date":"2026-11-13",
    "fixtures":len(live_rows),
    "real_received_quote_snapshots":len(recv),
    "with_multiple_actual_receipts":sum(x["captures"]>1 for x in live_rows),
    "received_AH_repriced_fixtures":sum(x["price_changes_between_received"]>0 for x in live_rows),
    "received_AH_line_changed_fixtures":sum(x["line_changes_between_received"]>0 for x in live_rows),
    "received_at_least_10h_before_kickoff":sum(q["minutes_until_stored_kickoff"]>=600 for q in recv),
    "received_at_least_12h_before_kickoff":sum(q["minutes_until_stored_kickoff"]>=720 for q in recv),
    "received_at_least_20h_before_kickoff":sum(q["minutes_until_stored_kickoff"]>=1200 for q in recv),
    "received_at_least_10h_before_kickoff_fixture_count":len({x["fixture_id"] for x in live_rows for q in x["quotes"] if q["minutes_until_stored_kickoff"]>=600})
}
# Verify deterministic raw hashes of 32 source files from old and M5 supplemental index.
sources={}
with Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl").open() as f:
    for line in f:
        a=json.loads(line)
        if str(a["fixture_id"]) in R2:sources[str(a["fixture_id"])]=a
with (HERE/"m5_2026_close_supplement.local.jsonl").open() as f:
    for line in f:
        a=json.loads(line)
        if str(a["fixture_id"]) in R2:sources[str(a["fixture_id"])]=a
assert len(sources)==len(R2)
for fid in sorted(R2)[::max(1,len(R2)//32)]:
    s=sources[fid]
    assert hashlib.sha256(Path(s["source_file"]).read_bytes()).hexdigest()==s["raw_sha256"]
    audit["sha_sample_checked"]+=1

r=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),validated=True,
       audit=dict(audit),event_window_cases={"2025":describe(TR),"2026":describe(T)},
       archived_real_receipt_footprint=true_recv,
       result_scope="2025 sample Nov-Dec only; 2026 historical 8,860 complete; all quotes retrieved after fixture",
       notes=[
        "Event classification is descriptive, not a signal gate; exact price changes may have reversed within T24->T12 and net to zero.",
        "OU and AH sourced from same bookmaker; observed lead-lag alone does not prove independently early information.",
        "Changing future AH line is only one of many ways market reprices; it does not establish contract value.",
        "All live footprint is last archived on 2026-11-13; it is not a current live monitor.",
        "Multiple models and reporting groups examined; confidence intervals unadjusted for multiple comparisons."
       ])
OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
print("VERIFIED",r["validated"],r["audit"])
print("LIVE",true_recv)
for year,x in r["event_window_cases"].items():
    for k,z in x.items():
        print(year,k,z["n"],"postAHlineChanged%",z["future_AH_line_changed_pct"],
              "event_expandingROI",z.get("event_clv_expanding_monthly_roi_pct"))
