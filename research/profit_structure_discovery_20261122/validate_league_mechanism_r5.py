#!/usr/bin/env python3
import json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent
a=json.load(open(ROOT/"league_mechanism_r5_results.json"))
assert a["audit"]["T12_rows"]==34713
assert a["audit"]["discovery_league_cells"]==len(a["discovery_ranked_league_cells"])==1227
assert len(a["years"])==8
# Independently reconcile every year and structure family from league rows to pooled rows.
for year,rows in a["years"].items():
 for k,v in rows.items():
  family,league,bins=k.split("|",2)
  if league!="ALL":continue
  matches=[w for kk,w in rows.items() if kk.startswith(f"{family}|") and kk.endswith("|"+bins) and kk.split("|")[1]!="ALL"]
  assert v["n"]==sum(w["n"] for w in matches),(year,k)
  assert abs(v["net_U"]-round(sum(w["net_U"] for w in matches),3))<.00001,(year,k)
for z in a["discovery_ranked_league_cells"]:
 for year in ("2024","2025","2026"):
  k=f'{z["family"]}|{z["league_id"]}|{",".join(map(str,z["bins"]))}'
  assert a["years"][year].get(k,{"n":0})["n"]==z["future"][year]["n"]
  if z["future"][year]["n"]:
   assert a["years"][year][k]["net_U"]==z["future"][year]["net_U"]
out=dict(validated=True,source_T12_rows=a["audit"]["T12_rows"],discovery_league_cells=len(a["discovery_ranked_league_cells"]),
         all_pooled_league_year_cell_counts_and_netU_reconciled=True,
         all_discovery_candidate_future_years_reconciled=True,
         note="No minimum sample or production gates. Retrospective historical quote events, not verified executable receipts.")
(ROOT/"league_mechanism_r5_validation.json").write_text(json.dumps(out,indent=2)+"\n")
print("VALIDATED",out)
