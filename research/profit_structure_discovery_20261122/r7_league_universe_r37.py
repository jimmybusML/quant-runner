#!/usr/bin/env python3
"""R37 join historical inventory league IDs to original R7 orders; no selection changes."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"r7_composition_shift_r34.py"))
rows=r["rows"]
INV=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_T30_2h_movement_inventory_20261114.jsonl")
lookup={};duplicates=0;all_fixtures=collections.defaultdict(set);league_names=collections.defaultdict(collections.Counter)
for raw in INV.open():
 a=json.loads(raw);key=(a["kickoff_utc"],str(a["fixture_id"]))
 if key in lookup:
  duplicates+=1
  assert lookup[key]==str(a["league_id"])
 lookup[key]=str(a["league_id"])
 y=a["kickoff_utc"][:4]
 if y in ("2023","2024"):all_fixtures[y].add(key)
 if a.get("league"):league_names[str(a["league_id"])][a["league"]]+=1
missing=[k for k in rows if k[:2] not in lookup]
assert not missing,("unmapped R7 orders",len(missing),missing[:5])
for k,z in rows.items():z["league_id"]=lookup[k[:2]]
def stat(v):
 n=len(v);net=sum(z["pnl"] for z in v)
 return dict(n=n,net_U=round(net,4),roi_pct=round(100*net/n,4) if n else None)
years={y:[z for z in rows.values() if z["year"]==y] for y in ("2023","2024")}
buckets={y:collections.defaultdict(list) for y in years}
for y,vals in years.items():
 for z in vals:buckets[y][z["league_id"]].append(z)
all_leagues=set(buckets["2023"])|set(buckets["2024"])
shared={lid for lid in all_leagues if buckets["2023"][lid] and buckets["2024"][lid]}
new={lid for lid in all_leagues if not buckets["2023"][lid]}
lost={lid for lid in all_leagues if not buckets["2024"][lid]}
# Two-part decomposition: changing shared-league mix vs within shared league;
# entry/exit leagues reported separately and not assigned synthetic reference ROI.
matched={y:[z for z in years[y] if z["league_id"] in shared] for y in years}
n0=len(matched["2023"]);n1=len(matched["2024"])
mix=sum((len(buckets["2024"][lid])/n1-len(buckets["2023"][lid])/n0)*
  (sum(z["pnl"] for z in buckets["2023"][lid])/len(buckets["2023"][lid])) for lid in shared)
within=sum(len(buckets["2024"][lid])/n1*
 ((sum(z["pnl"] for z in buckets["2024"][lid])/len(buckets["2024"][lid]))-
  (sum(z["pnl"] for z in buckets["2023"][lid])/len(buckets["2023"][lid]))) for lid in shared)
decomp=dict(shared_leagues=len(shared),matched_2023=stat(matched["2023"]),matched_2024=stat(matched["2024"]),
 mix_pp=round(100*mix,4),within_pp=round(100*within,4),total_pp=round(100*(mix+within),4))
table=[]
for lid in sorted(all_leagues):
 a=stat(buckets["2023"][lid]);b=stat(buckets["2024"][lid])
 table.append(dict(league_id=lid,league_name=league_names[lid].most_common(1)[0][0] if league_names[lid] else None,
  year2023=a,year2024=b,shared=lid in shared))
out=dict(scope="R7 original27 AH 2023-2024 historical retrospective; league ID joined from original Crown inventory",
 inventory_path=str(INV),inventory_rows=len(lookup),duplicate_fixture_rows=duplicates,
 inventory_unique_fixtures_by_year={y:len(v) for y,v in all_fixtures.items()},
 r7_orders_mapped=len(rows),r7_unmapped=len(missing),
 overall={y:stat(v) for y,v in years.items()},
 league_counts={y:len(buckets[y]) for y in years},
 shared_leagues=len(shared),new_2024_leagues=len(new),lost_2023_leagues=len(lost),
 shared_league_decomposition=decomp,
 shared_only_order_fraction={y:round(len(matched[y])/len(years[y]),4) for y in years},
 nonshared={y:stat([z for z in years[y] if z["league_id"] not in shared]) for y in years},
 league_table=table,
 caveats=[
 "Original inventory is retrospective, and every 2023/2024 feature-ledger quote receipt was in 2026, not actual 2023/2024 live quote receipt.",
 "Matching league ID across years does not match team, season, fixture quality, pricing, or quote capture density.",
 "League-mix decomposition is descriptive and not causal; within-league effects include changed teams, fixtures and market regime.",
 "Original R7 was selected on 2019-2023; 2024 repeatedly inspected; no new filter or candidate selection from 2024 outcomes.",
 "No 2025-2026 evaluation, no production or strategy changes."])
(P/"R7_LEAGUE_UNIVERSE_R37.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R37",json.dumps({k:v for k,v in out.items() if k not in ("league_table","caveats")},ensure_ascii=False),flush=True)
