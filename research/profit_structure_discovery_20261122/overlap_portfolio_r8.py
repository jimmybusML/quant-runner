#!/usr/bin/env python3
"""R8: 27 user-review candidates, 2019-2023 only. FID overlap and three
research portfolio accounting alternatives. No candidate approved for production.
"""
import runpy,collections,datetime as dt,json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parent
r=runpy.run_path(str(ROOT/"five_year_review_r7.py"))
ledger=r["ledger"]; candidates=r["candidates"]
ids={k:f"T{k[0]}|{k[1]}|{k[2]}|{k[3]}" for k in candidates}
byfid=collections.defaultdict(list)
for k,rows in ledger.items():
 for date,fid,side,pnl in rows:byfid[fid].append(dict(id=ids[k],h=k[0],date=date,side=side,pnl=pnl))
assert len(byfid)<=14962
pair=collections.defaultdict(lambda:collections.Counter())
for fid,signals in byfid.items():
 for i,x in enumerate(signals):
  for y in signals[i+1:]:
   a,b=sorted((x["id"],y["id"]))
   p=pair[(a,b)];p["same_fixture"]+=1
   p["same_side" if x["side"]==y["side"] else "opposite_side"]+=1
def summarize(vals):
 n=len(vals);equity=peak=dd=0.;peak_at="initial";start=end=None
 months=collections.defaultdict(list);years=collections.defaultdict(list)
 for date,pnl in vals:
  equity+=pnl
  if equity>peak:peak=equity;peak_at=date
  if peak-equity>dd:dd=peak-equity;start=peak_at;end=date
  months[date[:7]].append(pnl);years[date[:4]].append(pnl)
 def stat(a):return dict(n=len(a),net_U=round(sum(a),3),roi_pct=round(100*sum(a)/len(a),4) if a else None)
 return dict(all=stat([v for _,v in vals]),years={str(y):stat(years[str(y)]) for y in range(2019,2024)},
             months={f"{y}-{m:02}":stat(months[f"{y}-{m:02}"]) for y in range(2019,2024) for m in range(1,13)},
             max_drawdown_U=round(dd,3),drawdown_start=start,drawdown_end=end,
             active_months=sum(bool(v) for v in months.values()),negative_months=sum(sum(v)<0 for v in months.values()))
def group_by_horizon(signals):
 # Alternative horizon rule: earliest source-event horizon. Not a production rule.
 h=max(x["h"] for x in signals)
 return [x for x in signals if x["h"]==h]
portfolios=collections.defaultdict(list);audit=collections.Counter()
for fid,signals in byfid.items():
 signals=sorted(signals,key=lambda x:(x["date"],-x["h"],x["id"]))
 date=signals[0]["date"]
 sides={x["side"] for x in signals}
 audit["any_signal_fids"]+=1
 if len(signals)>1:audit["multi_signal_fids"]+=1
 if len(sides)>1:audit["opposite_signal_fids"]+=1
 audit["total_signals"]+=len(signals)
 # Each fixture has one unit exposure. Multiple signals don't create multiple orders.
 # Scenario 1: choose first chronological horizon signal (fixed lexical tie-break).
 early=sorted(signals,key=lambda x:(-x["h"],x["id"]))[0]
 portfolios["earliest_one_signal"].append((date,early["pnl"]))
 # Scenario 2: equal weights across all matched candidate signals; fractional
 # pnl is an accounting blend, NOT executable single-sided order on conflicts.
 portfolios["equal_signal_fractional_blend"].append((date,sum(x["pnl"] for x in signals)/len(signals)))
 # Scenario 3: cancel direction conflict; otherwise use earliest horizon quote.
 if len(sides)==1:portfolios["unanimous_same_side"].append((date,early["pnl"]))
 # Scenario 4: one vote per candidate; majority only if strict majority, use
 # earliest horizon quote for chosen direction; tied fixture has no order.
 counts=collections.Counter(x["side"] for x in signals)
 if counts["home"]!=counts["away"]:
  winning=max(counts,key=counts.get)
  eligible=[x for x in signals if x["side"]==winning]
  chosen=sorted(eligible,key=lambda x:(-x["h"],x["id"]))[0]
  portfolios["majority_vote"].append((date,chosen["pnl"]))
 else:audit["tie_fids"]+=1
out=dict(scope="2019-2023 only, 27 historically positive every-year R1 candidates",
 created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
 provenance="Crown historical event times retrospectively collected in 2026, not pre-match received executable odds",
 audit=dict(audit),pairwise=[],portfolios={})
for (a,b),v in pair.items():
 out["pairwise"].append(dict(candidate_a=a,candidate_b=b,**v))
out["pairwise"].sort(key=lambda x:(-x["same_fixture"],x["candidate_a"],x["candidate_b"]))
for name,vals in portfolios.items():
 vals.sort(key=lambda x:x[0])
 out["portfolios"][name]=summarize(vals)
 assert out["portfolios"][name]["all"]["n"]<=len(byfid)
 assert out["portfolios"][name]["all"]["n"]==sum(x["n"] for x in out["portfolios"][name]["years"].values())
out["audit"]["pair_count_with_overlap"]=len(pair)
out["audit"]["candidate_count"]=len(candidates)
out["audit"]["unique_fids"]=len(byfid)
(ROOT/"overlap_portfolio_r8_results.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
with (ROOT/"overlap_portfolio_r8_pairwise.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["candidate_a","candidate_b","same_fixture","same_side","opposite_side"]);w.writeheader();w.writerows(out["pairwise"])
print("AUDIT",out["audit"])
for name,p in out["portfolios"].items():
 print(name,p["all"],"MDD",p["max_drawdown_U"],"YEARS",p["years"],"negative_months",p["negative_months"])
print("TOP OVERLAPS",out["pairwise"][:8])
