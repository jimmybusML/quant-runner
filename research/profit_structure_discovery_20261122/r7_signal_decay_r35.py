#!/usr/bin/env python3
"""R35 R7 original signal identity contribution vs 2023-2024 quote-capture diagnostics."""
import collections,json,runpy,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
r=runpy.run_path(str(P/"r7_composition_shift_r34.py"))
rows=r["rows"];ids=r["ids"];train=r["train"];test=r["test"]
source=r["source"]
# Each portfolio order allocates its PnL equally among all winning-side candidates
# (at the chosen horizon); this is attribution, not separately tradable orders.
candidate=collections.defaultdict(lambda:collections.defaultdict(lambda:dict(exposure=0.,net_U=0.,orders=0)))
for k,z in rows.items():
 group=(train if z["year"]=="2023" else test)[k]
 winners=[c for c,p in group[z["side"]] if c in ids]
 assert winners
 for c in winners:
  a=candidate[c][z["year"]];a["exposure"]+=1/len(winners);a["net_U"]+=z["pnl"]/len(winners);a["orders"]+=1
# Quote metadata for portfolio chosen horizon, and data coverage for all AH rows
meta={}
all_years=collections.defaultdict(lambda:collections.Counter())
for raw in source.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a.get("year")) not in ("2023","2024"):continue
 y=str(a["year"]);all_years[y]["all_AH_rows"]+=1
 if a.get("window_ticks_available") is not None:all_years[y]["tick_nonmissing"]+=1
 if a.get("first_available_quote"):all_years[y]["first_quote_nonmissing"]+=1
 if a.get("same_line_reference_quote"):all_years[y]["reference_quote_nonmissing"]+=1
 k=(a["kickoff_utc"],str(a["fixture_id"]),int(a["entry_horizon_hours"]))
 if k not in rows:continue
 first=a.get("first_available_quote") or {}
 ref=a.get("same_line_reference_quote") or {}
 meta[k]=dict(year=y,ticks=int(a.get("window_ticks_available") or 0),
 quote_time=a.get("quote_time_utc"),first_time=first.get("time"),
 ref_time=ref.get("time"),actual_hours=float(a["actual_hours_before_kickoff"]),
 horizon=int(a["entry_horizon_hours"]))
assert len(meta)==len(rows),(len(meta),len(rows))
def stats(v):
 n=len(v);return dict(n=n,net_U=round(sum(z["pnl"] for z in v),3),roi_pct=round(100*sum(z["pnl"] for z in v)/n,4) if n else None)
summary={}
for y in ("2023","2024"):
 keys=[k for k in rows if rows[k]["year"]==y];vs=[meta[k] for k in keys]
 summary[y]=dict(portfolio=stats([rows[k] for k in keys]),
  total_AH_ledger_rows=all_years[y]["all_AH_rows"],
  portfolio_quote_time_equals_first_pct=round(100*sum(v["quote_time"]==v["first_time"] for v in vs)/len(vs),3),
  portfolio_reference_quote_available_pct=round(100*sum(bool(v["ref_time"]) for v in vs)/len(vs),3),
  portfolio_ticks_mean=round(statistics.mean(v["ticks"] for v in vs),3),
  portfolio_ticks_median=statistics.median(v["ticks"] for v in vs),
  portfolio_actual_hours_mean=round(statistics.mean(v["actual_hours"] for v in vs),3),
  portfolio_actual_hours_median=round(statistics.median(v["actual_hours"] for v in vs),3),
  ledger_first_quote_nonmissing_pct=round(100*all_years[y]["first_quote_nonmissing"]/all_years[y]["all_AH_rows"],3),
  ledger_reference_quote_nonmissing_pct=round(100*all_years[y]["reference_quote_nonmissing"]/all_years[y]["all_AH_rows"],3))
attr=[]
for c in sorted(ids):
 a=candidate[c]
 attr.append(dict(candidate=c,years={y:dict(exposure=round(a[y]["exposure"],4),net_U=round(a[y]["net_U"],4),
  weighted_roi_pct=round(100*a[y]["net_U"]/a[y]["exposure"],4) if a[y]["exposure"] else None,
  contributing_orders=a[y]["orders"]) for y in ("2023","2024")}))
# Decomposition across winning candidate identities: weights normalized by portfolio order count.
# Every order's PnL is fractionally allocated; sum of candidate exposures equals portfolio n.
n0=summary["2023"]["portfolio"]["n"];n1=summary["2024"]["portfolio"]["n"]
assert abs(sum(candidate[c]["2023"]["exposure"] for c in ids)-n0)<1e-7
assert abs(sum(candidate[c]["2024"]["exposure"] for c in ids)-n1)<1e-7
# Use 2023 reference only if all 2024 positive-exposure candidates existed in 2023.
if all(candidate[c]["2023"]["exposure"]>0 for c in ids if candidate[c]["2024"]["exposure"]):
 mix=sum((candidate[c]["2024"]["exposure"]/n1-candidate[c]["2023"]["exposure"]/n0)*
         (candidate[c]["2023"]["net_U"]/candidate[c]["2023"]["exposure"])
         for c in ids if candidate[c]["2023"]["exposure"])
 within=sum(candidate[c]["2024"]["exposure"]/n1*
         (candidate[c]["2024"]["net_U"]/candidate[c]["2024"]["exposure"]-
          candidate[c]["2023"]["net_U"]/candidate[c]["2023"]["exposure"])
         for c in ids if candidate[c]["2024"]["exposure"])
 decomp=dict(candidate_mix_pp=round(100*mix,4),within_candidate_pp=round(100*within,4),
  total_pp=round(100*(mix+within),4))
else:decomp=dict(status="Candidate with 2024 exposure missing 2023 reference")
out=dict(scope="Original R7 all27 portfolio 2023 vs 2024 signal identity and quote metadata",
 summary=summary,candidate_attribution=attr,candidate_decomposition=decomp,
 caveats=["Equal fractional PnL allocation among winning-side candidate IDs is an accounting attribution, not independent candidate betting PnL or causal influence.",
 "2023 vs 2024 candidate mix decomposition uses 2023 reference returns; all original candidate identities remain fixed.",
 "Quote metadata is from retrospectively collected Crown ledger, not proof that these quote histories existed in live 2023/2024 systems.",
 "Different years may have different league/fixture coverage, not controlled without a fixture-league map.",
 "2019-2023 original R7 in-sample; 2024 repeatedly inspected; no untouched independent validation.",
 "No 2025-2026 or production changes, no new strategy filters."])
(P/"R7_SIGNAL_DECAY_R35.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("SUMMARY",summary,flush=True)
print("DECOMP",decomp,flush=True)
for x in sorted(attr,key=lambda x:x["years"]["2024"]["net_U"]-x["years"]["2023"]["net_U"]):
 print("CAND",x["candidate"],x["years"],flush=True)
