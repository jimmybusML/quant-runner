#!/usr/bin/env python3
"""R36 Crown retrospective 2023/24 capture provenance and fixture coverage audit."""
import collections,datetime as dt,hashlib,json,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
REPORT=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_report_20261114.json")
s={y:dict(rows=0,fixtures=set(),fixture_months=collections.Counter(),horizons=collections.Counter(),
 received_days=collections.Counter(),received_years=collections.Counter(),layers=collections.Counter(),
 refs=collections.Counter(),sha_nonempty=0,ref_nonempty=0,first_nonempty=0,source_after_match=0,
 quote_first_same=0,ticks=[],quote_offsets_hours=[],actual_hours=[],unique_source_shas=set(),
 first_quote_times=set(),missing_league=0,fixture_horizons=collections.defaultdict(set)) for y in ("2023","2024")}
for raw in SRC.open():
 a=json.loads(raw)
 y=str(a.get("year"))
 if y not in s or a.get("market")!="AH":continue
 z=s[y];z["rows"]+=1
 fid=str(a["fixture_id"]);z["fixtures"].add(fid);z["fixture_months"][a["kickoff_utc"][:7]]+=1
 z["horizons"][str(a["entry_horizon_hours"])]+=1;z["fixture_horizons"][fid].add(int(a["entry_horizon_hours"]))
 z["missing_league"]+=int(not bool(a.get("league_id") or a.get("league")))
 first=a.get("first_available_quote") or {}
 if first:
  z["first_nonempty"]+=1
  rec=first.get("received")
  if rec:z["received_days"][rec[:10]]+=1;z["received_years"][rec[:4]]+=1
  z["layers"][str(first.get("layer"))]+=1
  z["refs"][str(first.get("ref","")).split("[")[0]]+=1
  if first.get("sha"):z["sha_nonempty"]+=1;z["unique_source_shas"].add(first["sha"])
  if first.get("ref"):z["ref_nonempty"]+=1
  if first.get("time"):z["first_quote_times"].add(first["time"])
  if first.get("time")==a.get("quote_time_utc"):z["quote_first_same"]+=1
  if rec and rec[:4]>y:z["source_after_match"]+=1
 z["ticks"].append(int(a.get("window_ticks_available") or 0))
 z["actual_hours"].append(float(a["actual_hours_before_kickoff"]))
 z["quote_offsets_hours"].append((dt.datetime.fromisoformat(a["kickoff_utc"])-dt.datetime.fromisoformat(a["quote_time_utc"])).total_seconds()/3600)
out={"source_path":str(SRC),"source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
 "source_report_protocol":json.loads(REPORT.read_text()).get("protocol"),
 "source_report_entry_policy":json.loads(REPORT.read_text()).get("entry_policy"),
 "years":{},"caveats":[
 "The received timestamp is a 2026 retrospective ingestion timestamp, not a historical 2023/2024 pregame receipt.",
 "Archive event-time quotes are not proof of live historical accessibility or executability.",
 "The report entry policy is a retrospective quote selection procedure and must not be confused with live reception.",
 "No fixture-league mapping in this feature ledger, so league mix cannot be compared here.",
 "Different match/fixture coverage or source availability may confound 2023-2024 ROI; this audit does not estimate causality.",
 "No new strategy gates, production changes or 2025-2026 outcomes."]}
for y,z in s.items():
 n=z["rows"]
 out["years"][y]=dict(AH_rows=n,unique_fixtures=len(z["fixtures"]),
 unique_fixture_months=len(z["fixture_months"]),
 rows_by_month=dict(sorted(z["fixture_months"].items())),
 horizon_rows=dict(z["horizons"]),horizons_per_fixture=dict(collections.Counter(map(len,z["fixture_horizons"].values()))),
 first_quote_populated_pct=round(100*z["first_nonempty"]/n,3),
 first_quote_received_after_match_year_pct=round(100*z["source_after_match"]/n,3),
 first_quote_received_years=dict(z["received_years"]),first_quote_received_days=dict(z["received_days"]),
 first_quote_layers=dict(z["layers"]),first_quote_ref_prefixes=dict(z["refs"]),
 source_sha_populated_pct=round(100*z["sha_nonempty"]/n,3),distinct_source_sha=len(z["unique_source_shas"]),
 first_quote_equals_selected_quote_pct=round(100*z["quote_first_same"]/n,3),
 ticks_mean=round(statistics.mean(z["ticks"]),3),ticks_median=statistics.median(z["ticks"]),
 actual_hours_mean=round(statistics.mean(z["actual_hours"]),3),actual_hours_median=statistics.median(z["actual_hours"]),
 selected_quote_hours_before_kickoff_median=round(statistics.median(z["quote_offsets_hours"]),3),
 league_missing_pct=round(100*z["missing_league"]/n,3))
print("AUDIT",json.dumps({y:{k:v for k,v in a.items() if k not in ("rows_by_month","first_quote_received_days")} for y,a in out["years"].items()},ensure_ascii=False),flush=True)
(P/"CROWN_PROVENANCE_R36.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
