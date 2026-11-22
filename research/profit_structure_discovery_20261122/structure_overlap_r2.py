#!/usr/bin/env python3
"""Audit all R1 candidates against M8 frozen fixtures and league/year structure.
No strategy selection, sample/ROI threshold, or production gate.
"""
import collections,datetime as dt,hashlib,json
from pathlib import Path
from research.m3.probabilities import settle_score
from research.profit_structure_discovery_20261122.structure_discovery_r1 import features,FAMILIES
ROOT=Path(__file__).resolve().parent
M8=Path("/Users/mac/Documents/ChatGPT/m8-m9-group-research/research/m8/mechanism_discovery_20261119/frozen_eight_fixture_mechanism_rows.jsonl")
SOURCE=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
META=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T1157Z.jsonl")
R1=json.load(open(ROOT/"structure_discovery_r1_results.json"))
frozen={}
for line in M8.open():
 r=json.loads(line);fid=str(r["fid"])
 assert fid not in frozen
 frozen[fid]=r
assert len(frozen)==10294
meta={}
for line in META.open():
 r=json.loads(line);meta[str(r["fixture_id"])]=str(r.get("league_id") or "")
assert len(meta)>30000
candidates={}
for h,rs in R1["by_horizon"].items():
 for r in rs:
  key=(int(h),r["family"],r["structure"],r["direction"])
  assert key not in candidates
  candidates[key]=r
totals=collections.Counter()
acc=collections.defaultdict(lambda:dict(all=collections.defaultdict(list),m8_same=collections.defaultdict(list),
 m8_other=collections.defaultdict(list),outside=collections.defaultdict(list),league=collections.defaultdict(lambda:collections.defaultdict(list)),
 overlap_fids=collections.defaultdict(set)))
fids_by_h=collections.defaultdict(set)
for line in SOURCE.open():
 r=json.loads(line)
 if r.get("market")!="AH":continue
 year=str(r["year"]);h=int(r["entry_horizon_hours"]);fid=str(r["fixture_id"])
 if year not in map(str,range(2019,2027)):continue
 assert fid not in fids_by_h[h],("duplicate same fixture horizon",fid,h)
 fids_by_h[h].add(fid)
 odds=r["odds"];home=float(odds["home"]);away=float(odds["away"])
 hg,ag=map(int,r["score"].split("-"))
 x=dict(line=float(r["line"]),home=home,away=away,delta=float(r.get("line_delta_since_first_quote") or 0),age=float(r["actual_hours_before_kickoff"])-h)
 pnl={"home":settle_score("AH",x["line"],"home",hg,ag,home)[1],"away":settle_score("AH",x["line"],"away",hg,ag,away)[1]}
 fav="home" if x["line"]<0 else "away" if x["line"]>0 else "home" if home<away else "away"
 pnl["favorite"]=pnl[fav];pnl["underdog"]=pnl["away" if fav=="home" else "home"]
 dirs={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
 fs=features(x)
 m8=frozen.get(fid);league=meta.get(fid,"")
 if not league:totals["missing_league"]+=1
 if m8 and league and str(m8["league"])!=league:totals["m8_league_mismatch"]+=1
 for family in FAMILIES:
  signature=";".join(f"{k}={fs[k]}" for k in family)
  for label,ret in pnl.items():
   key=(h,",".join(family),signature,label)
   if key not in candidates:continue
   z=acc[key]
   z["all"][year].append(ret)
   z["league"][(year,league)]["pnl"].append(ret)
   if m8:
    z["overlap_fids"][year].add(fid)
    if dirs[label]==m8["direction"]:
     z["m8_same"][year].append(ret)
    else:z["m8_other"][year].append(ret)
   else:z["outside"][year].append(ret)
 totals["rows"]+=1
def stats(v):
 return dict(n=len(v),net_U=round(sum(v),3),roi_pct=round(100*sum(v)/len(v),4) if v else None)
out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 frozen_m8_sha256=hashlib.sha256(M8.read_bytes()).hexdigest(),
 frozen_m8_fids=len(frozen),metadata_fids=len(meta),
 source=str(SOURCE),candidate_count=len(candidates),source_rows=dict(totals),
 provenance="2026 retrospective Crown event-time quotes, NOT pregame received executable quotes",
 scope="All R1 candidate structures preserved, league breakdown and M8 same-fid overlap; each horizon independent, no production gates",
 by_horizon={})
for key,original in candidates.items():
 h,family,signature,label=key
 a=acc[key]
 # Audit exact R1 yearly results and n for every candidate.
 for year in map(str,range(2019,2027)):
  assert stats(a["all"].get(year,[]))==original["years"][year],(key,year)
  assert len(a["all"].get(year,[]))==len(a["outside"].get(year,[]))+len(a["m8_same"].get(year,[]))+len(a["m8_other"].get(year,[]))
 z=dict(family=family,structure=signature,direction=label,
        discovery=original["discovery"],
        years={y:dict(total=original["years"][y],
                      outside_M8=stats(a["outside"].get(y,[])),
                      M8_same_side=stats(a["m8_same"].get(y,[])),
                      M8_opposite_side=stats(a["m8_other"].get(y,[])),
                      overlap_fids=len(a["overlap_fids"].get(y,set())))
               for y in ("2024","2025","2026")},
        league_by_year={y:{league:stats(vals["pnl"]) for (yy,league),vals in a["league"].items() if yy==y}
                        for y in ("2024","2025","2026")})
 out["by_horizon"].setdefault(str(h),[]).append(z)
for h,rows in out["by_horizon"].items():
 rows.sort(key=lambda z:(z["discovery"]["roi_pct"],z["discovery"]["n"]),reverse=True)
 out.setdefault("horizon_audit",{})[h]=dict(
  candidate_count=len(rows),
  candidates_overlapping_M8_2026=sum(z["years"]["2026"]["overlap_fids"]>0 for z in rows),
  candidates_positive_2024_2025_2026=sum(all(z["years"][y]["total"]["roi_pct"] is not None and z["years"][y]["total"]["roi_pct"]>0 for y in ("2024","2025","2026")) for z in rows),
  candidates_positive_2024_2025_2026_outside_M8=sum(all(z["years"][y]["outside_M8"]["roi_pct"] is not None and z["years"][y]["outside_M8"]["roi_pct"]>0 for y in ("2024","2025","2026")) for z in rows))
print("AUDIT",out["horizon_audit"],"SOURCE",dict(totals))
(ROOT/"structure_overlap_r2_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
