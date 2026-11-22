#!/usr/bin/env python3
"""R38 original R7 shared-league within-market and within-team descriptive diagnostics."""
import collections,json,runpy
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"r7_league_universe_r37.py"))
rows=r["rows"];INV=r["INV"];shared=r["shared"]
teams={}
for raw in INV.open():
 a=json.loads(raw);k=(a["kickoff_utc"],str(a["fixture_id"]))
 if k in teams:continue
 teams[k]=(str(a.get("home_id")),str(a.get("away_id")))
assert all(k[:2] in teams for k in rows)
for k,z in rows.items():
 z["teams"]=teams[k[:2]]
def stat(v):
 n=len(v);net=sum(z["pnl"] for z in v)
 return dict(n=n,net_U=round(net,4),roi_pct=round(100*net/n,4) if n else None)
def binval(z,f):
 if f=="horizon":return "T"+str(z["horizon"])
 if f=="line":return "0" if z["line"]==0 else "0.25-0.75" if z["line"]<=.75 else "1-1.75" if z["line"]<=1.75 else "2+"
 if f=="ticks":return "1" if z["ticks"]==1 else "2" if z["ticks"]==2 else "3-5" if z["ticks"]<=5 else "6+"
 if f=="odds":return "<1.8" if z["odds"]<1.8 else "1.8-1.9" if z["odds"]<1.9 else "1.9-2" if z["odds"]<2 else "2-2.1" if z["odds"]<2.1 else "2.1+"
 if f=="side":return z["side"]
def decomposed(field):
 b={y:collections.defaultdict(list) for y in ("2023","2024")}
 for z in rows.values():
  if z["league_id"] not in shared:continue
  b[z["year"]][(z["league_id"],binval(z,field))].append(z)
 keys=set(b["2023"])|set(b["2024"])
 common={k for k in keys if b["2023"][k] and b["2024"][k]}
 # Treat unmatched league-by-stratum categories separately rather than impute.
 v={y:[z for k in common for z in b[y][k]] for y in b}
 n0=len(v["2023"]);n1=len(v["2024"])
 mix=sum((len(b["2024"][k])/n1-len(b["2023"][k])/n0)*sum(z["pnl"] for z in b["2023"][k])/len(b["2023"][k]) for k in common)
 within=sum(len(b["2024"][k])/n1*(sum(z["pnl"] for z in b["2024"][k])/len(b["2024"][k])-sum(z["pnl"] for z in b["2023"][k])/len(b["2023"][k])) for k in common)
 return dict(matched_cells=len(common),matched={y:stat(v[y]) for y in v},
  excluded_unmatched={y:stat([z for k in keys-common for z in b[y][k]]) for y in b},
  mix_pp=round(100*mix,4),within_pp=round(100*within,4),total_pp=round(100*(mix+within),4))
# Team-universe overlap, not exact fixture matching.
team_ids={y:set() for y in ("2023","2024")}
for z in rows.values():
 if z["league_id"] in shared:team_ids[z["year"]].update((z["league_id"],x) for x in z["teams"])
both=team_ids["2023"]&team_ids["2024"]
team_matched={y:[z for z in rows.values() if z["year"]==y and z["league_id"] in shared and any((z["league_id"],x) in both for x in z["teams"])] for y in ("2023","2024")}
both_teams={y:[z for z in rows.values() if z["year"]==y and z["league_id"] in shared and all((z["league_id"],x) in both for x in z["teams"])] for y in ("2023","2024")}
out=dict(scope="Original R7 27, 2023-24 shared45 league within-market and matched team presence",
 baseline_shared_leagues={y:stat([z for z in rows.values() if z["year"]==y and z["league_id"] in shared]) for y in ("2023","2024")},
 dimensions={f:decomposed(f) for f in ("horizon","line","ticks","odds","side")},
 teams=dict(unique_league_team_ids={y:len(team_ids[y]) for y in team_ids},
  shared_league_team_ids=len(both),
  at_least_one_team_seen_both_years={y:stat(team_matched[y]) for y in team_matched},
  both_teams_seen_both_years={y:stat(both_teams[y]) for y in both_teams}),
 caveats=["All 2023-2024 historical Crown receipts are 2026 retrospective; these are not live-executable results.",
 "League-by-market cell decomposition excludes categories without observations in both years; compare coverage explicitly.",
 "Team matching means a team appeared in both years within the same league, not identical fixture, roster or strength.",
 "The 2024 sample has been repeatedly inspected; do not choose gates or filters using its favorable subgroups.",
 "No 2025-2026 data, no candidate definition or production changes."])
(P/"R7_WITHIN_LEAGUE_R38.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("R38",json.dumps(out,ensure_ascii=False),flush=True)
