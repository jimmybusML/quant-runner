#!/usr/bin/env python3
"""Read-only M8/MR1 Crown receipt coverage comparison; no trading or data import."""
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
WORK = Path("/Users/mac/QuantAsiaDesk/research-work")
DB = Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
MR1 = Path("/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23")
AUDIT = ROOT / "research/m8/m8_batch_actual_receipt_independently_audited_20261118.jsonl"
OUT = ROOT / "research/m8/mr1_m8_receipt_coverage_20261119"
CUT = "2026-11-14T01:25:02"

def iso(x):
    return dt.datetime.fromisoformat(x.replace("Z", "+00:00"))

def ids(path):
    with path.open() as f:
        return {str(json.loads(line)["fid"]) for line in f if line.strip()}

def main():
    sets = {
        "m8_frozen": ids(WORK/"m8_foundation_20261115/historical_membership.jsonl"),
        "m8_historical_paths": ids(WORK/"m8_late_full_path_water_features_20261114.jsonl"),
        "m8_previous_actual_receipts": ids(AUDIT),
    }
    db = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    rows = db.execute("""SELECT fixture_id, response_received_at_utc FROM capture
      WHERE data_layer='summary' AND capture_mode='live'
      AND prospective_observation=1 AND status='QUOTES_SAVED'""").fetchall()
    sets["m7_shared_live"] = {str(fid) for fid, _ in rows}
    output = []
    failures = collections.Counter()
    index = MR1 / "snapshot-index.jsonl"
    with index.open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("classification") != "SNAPSHOT_OK" or r.get("committed_at", "") <= CUT:
                continue
            p = MR1 / r["snapshot_path"]
            s = json.loads(p.read_text())
            ah = s.get("AH") or {}
            if not (s.get("source_bookmaker") == "crown" and
                    s.get("source_bookmaker_verified") and
                    s.get("received_at") and s.get("kickoff_at") and
                    ah.get("line") is not None and
                    ah.get("home_price") is not None and ah.get("away_price") is not None):
                failures["unverified_or_missing"] += 1
                continue
            if iso(s["received_at"]) >= iso(s["kickoff_at"]):
                failures["not_pregame"] += 1
                continue
            if ah.get("observed_at_utc") and iso(ah["observed_at_utc"]) > iso(s["received_at"]):
                failures["source_after_receipt"] += 1
                continue
            output.append({
                "fid": str(r["match_id"]), "horizon": r["target_horizon"],
                "received_utc": s["received_at"], "kickoff_utc": s["kickoff_at"],
                "ah_source_utc": ah.get("observed_at_utc"),
                "crown_ah_home_line": ah["line"], "home_decimal": ah["home_price"],
                "away_decimal": ah["away_price"],
                "snapshot_sha256": r["snapshot_sha256"],
                "mr1_snapshot_key": r["key"],
                "in_m7_live": str(r["match_id"]) in sets["m7_shared_live"],
                "in_m8_historical": str(r["match_id"]) in sets["m8_historical_paths"],
                "in_m8_frozen": str(r["match_id"]) in sets["m8_frozen"],
                "in_previous_actual_receipts": str(r["match_id"]) in sets["m8_previous_actual_receipts"],
            })
    all_old = set.union(*sets.values())
    fids = {r["fid"] for r in output}
    out = {
        "purpose": "read-only data coverage; NOT new settled bets",
        "cutoff_utc": CUT, "m8_inventory_fids": {k: len(v) for k,v in sets.items()},
        "mr1_newer_verified_receipt_snapshots": len(output),
        "mr1_newer_verified_fids": len(fids),
        "overlap_fids": {k:len(fids&v) for k,v in sets.items()},
        "fid_unseen_in_checked_m8_inventories": len(fids - all_old),
        "unseen_fids": sorted(fids - all_old),
        "snapshot_horizon_distribution": dict(collections.Counter(r["horizon"] for r in output)),
        "skip_reasons": dict(failures),
        "independent_ft_checked": False,
        "production_changes": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
    with (OUT/"verified_receipts.jsonl").open("w") as f:
        for r in output:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="unseen_fids"},ensure_ascii=False))
if __name__ == "__main__":
    main()
