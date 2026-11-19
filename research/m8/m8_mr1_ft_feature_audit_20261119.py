#!/usr/bin/env python3
"""Read-only research audit of the previously frozen 175 MR1-only Crown FIDs."""
import collections
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/"research/m8/mr1_m8_receipt_coverage_20261119"
OUT=ROOT/"research/m8/mr1_m8_ft_feature_audit_20261119"
MR1=Path("/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23")
HARVEST=Path("/Users/mac/QuantAsiaDesk/repos/mr1/data/strategy-shadow-ledger/result-harvest-state.json")
AUDIT_ASOF="2026-11-19T04:30:00Z"
def utc(s):return dt.datetime.fromisoformat(s.replace("Z","+00:00"))
def main():
    existing=json.loads((PREV/"summary.json").read_text())
    novel=set(existing["unseen_fids"])
    receipts=collections.defaultdict(list)
    for line in (PREV/"verified_receipts.jsonl").open():
        row=json.loads(line)
        if row["fid"] in novel:receipts[row["fid"]].append(row)
    fixture=json.loads((MR1/"fixtures.json").read_text())
    harvest=json.loads(HARVEST.read_text()).get("matches",{})
    out=[]
    for fid in sorted(novel):
        ff=fixture.get(fid) or {}
        rr=sorted(receipts[fid],key=lambda r:r["received_utc"])
        kickoff=ff.get("kickoff_at") or (rr[0]["kickoff_utc"] if rr else None)
        state=harvest.get(fid) or {}
        row={
            "fid":fid,"league":ff.get("league"),"home":ff.get("home"),"away":ff.get("away"),
            "kickoff_utc":kickoff,"fixture_metadata_present":bool(ff),
            "kickoff_reached_asof":bool(kickoff and utc(kickoff)<=utc(AUDIT_ASOF)),
            "mr1_result_harvest_status":state.get("status"),
            "mr1_result_harvest_has_ft_proof":state.get("status")=="FT",
            "verified_ah_receipt_count":len(rr),
            "horizons":sorted({r["horizon"] for r in rr}),
            "first_received_utc":rr[0]["received_utc"] if rr else None,
            "last_received_utc":rr[-1]["received_utc"] if rr else None,
            "research_m8_historical_path_available":False,
            "research_m8_old_receipt_feature_available":False,
            "new_m8_model_signal_generated":False,
            "verified_ft_score":None,
            "settled_research_pnl_u":None,
        }
        out.append(row)
    counts=collections.Counter()
    for x in out:
        counts["total"]+=1
        counts["kickoff_reached" if x["kickoff_reached_asof"] else "kickoff_future"]+=1
        counts["mr1_ft_proof" if x["mr1_result_harvest_has_ft_proof"] else "mr1_no_ft_proof"]+=1
        counts["fixture_meta" if x["fixture_metadata_present"] else "missing_fixture_meta"]+=1
    result={
        "asof_utc":AUDIT_ASOF,
        "note":"Match kickoff time is not equivalent to verified final result. MR1 result-harvest state contains no entry for these FIDs; no new FT/score is asserted.",
        "scope":"175 FIDs beyond four audited M8 lists; not a global claim of research novelty",
        "counts":dict(counts),
        "leagues_past":dict(collections.Counter(x["league"] for x in out if x["kickoff_reached_asof"])),
        "leagues_future":dict(collections.Counter(x["league"] for x in out if not x["kickoff_reached_asof"])),
        "available_m8_historical_fid_features":0,
        "new_research_bets_generated":0,
        "new_verified_ft_via_checked_mr1_harvest":0,
        "roi":"not applicable",
        "production_changes":False
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    with (OUT/"per_fixture.jsonl").open("w") as f:
        for x in out:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
