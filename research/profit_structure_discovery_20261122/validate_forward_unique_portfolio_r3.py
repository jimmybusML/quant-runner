#!/usr/bin/env python3
"""Independently reconcile published scenario results with per-fixture ledger."""
import collections,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
a=json.load(open(ROOT/"forward_unique_portfolio_r3_results.json"))
m8=Path("/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/mechanism_discovery_20261119/frozen_eight_fixture_mechanism_rows.jsonl")
assert hashlib.sha256(m8.read_bytes()).hexdigest()==a["frozen_m8_sha256"]
groups=collections.defaultdict(list)
for line in (ROOT/"forward_unique_portfolio_r3_ledger.local.jsonl").open():
 r=json.loads(line)
 assert r["year"] in ("2024","2025","2026")
 assert r["side"] in ("home","away")
 assert r["selected_discovery_rank"] in (1,2,3)
 groups[r["scenario"]].append(r)
assert set(groups).issubset(a["research_scenarios"])
def check(rows,record):
 vals=[r["pnl_U"] for r in rows]
 assert record["n"]==len(rows)
 assert record["unique_fids"]==len({r["fid"] for r in rows})
 assert abs(record["net_U"]-round(sum(vals),3))<1e-8
 assert record["roi_pct"]==(round(100*sum(vals)/len(vals),4) if vals else None)
for name,s in a["research_scenarios"].items():
 rr=groups[name]
 assert len({r["fid"] for r in rr})==len(rr)
 for y in ("2024","2025","2026"):
  z=[r for r in rr if r["year"]==y]
  year=s["years"][y]
  check(z,year["all"])
  check([r for r in z if not r["m8_same_fixture"]],year["outside_M8"])
  check([r for r in z if r["m8_same_fixture"] and r["m8_same_direction"]],year["M8_same_direction"])
  check([r for r in z if r["m8_same_fixture"] and not r["m8_same_direction"]],year["M8_opposite_direction"])
 check(rr,s["all_future"]["all"])
 check([r for r in rr if not r["m8_same_fixture"]],s["all_future"]["outside_M8"])
assert sum(map(len,groups.values()))==a["audit"]["ledger_rows"]
out=dict(validated=True,scenarios=len(groups),ledger_rows=sum(map(len,groups.values())),
           unique_fixture_per_scenario=True,yearly_m8_partition_reconciled=True,
           frozen_m8_sha256=a["frozen_m8_sha256"],
           notes="Historical after-match quote event-time backtest, not verified real pre-match executable odds.")
(ROOT/"forward_unique_portfolio_r3_validation.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("VALIDATED",out)
