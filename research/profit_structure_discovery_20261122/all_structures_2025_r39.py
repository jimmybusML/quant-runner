#!/usr/bin/env python3
"""R39 2025 historical holdout: ALL frozen original R7-R15 494, R7 focus.
No 2025-informed candidate selection. Flat 1U fixture dedup equal-net original research convention."""
import collections,datetime as dt,json
from pathlib import Path
from research.m3.probabilities import settle_score
P=Path(__file__).resolve().parent
SRC=Path("/Users/mac/QuantAsiaDesk/research-work/m7/m7_original49_historical_Crown_entry_horizon_movement_ledger_20261114.jsonl")
R30=json.loads((P/"TRAIN_ONLY_ORIGINAL_COMBINATIONS_R30.json").read_text())
R32=json.loads((P/"R7_MARGINAL_COVERAGE_R32.json").read_text())
catalog={}
for name,v in R30["sets"].items():
 if name=="all_494":catalog=set(v["candidate_ids"])
assert len(catalog)==494
by_signature=collections.defaultdict(list)
for cid in catalog:
 h,fam,structure,direction=cid.split("|")
 by_signature[(int(h[1:]),direction,fam)].append((cid,structure))
sets={name:set(v["candidate_ids"]) for name,v in R30["sets"].items()}
greedy=[x["added"] for x in R32["greedy_historical_coverage"]]
assert len(greedy)==27 and set(greedy)==sets["original_batch_R7"]
for i in range(1,len(greedy)+1):sets[f"R7_historical_coverage_prefix_{i}"]=set(greedy[:i])
def b(v,edges):return sum(v>=e for e in edges)
groups=collections.defaultdict(lambda:{"home":[],"away":[]})
individual=collections.defaultdict(list)
coverage=collections.Counter()
for raw in SRC.open():
 a=json.loads(raw)
 if a.get("market")!="AH" or str(a.get("year"))!="2025":continue
 coverage["AH_quote_rows"]+=1
 h=int(a["entry_horizon_hours"]);date=a["kickoff_utc"];fid=str(a["fixture_id"])
 line=float(a["line"]);home=float(a["odds"]["home"]);away=float(a["odds"]["away"])
 hg,ag=map(int,a["score"].split("-"))
 fav="home" if line<0 else "away" if line>0 else "home" if home<away else "away"
 sides={"home":"home","away":"away","favorite":fav,"underdog":"away" if fav=="home" else "home"}
 d=float(a.get("line_delta_since_first_quote") or 0)
 pr=float(a.get("same_line_no_vig_probability_delta_side1") or 0)
 kick=dt.datetime.fromisoformat(date.replace("Z","+00:00"))
 f=dict(
  line=b(abs(line),[.25,.75,1.25,2.25]),
  price=b(home,[1.8,1.9,2,2.1]),
  momentum=b(d,[-.5,-.125,.125,.5]),
  age=b(float(a["actual_hours_before_kickoff"])-h,[.5,2,6,12]),
  signed_line=b(line,[-2,-1,-.25,.25,1,2]),
  prob_delta=b(pr,[-.02,-.005,.005,.02]),
  line_delta_sign=b(d,[-.000001,.000001]),
  prob_sign=b(pr,[-.000001,.000001]),
  odds_spread=b(abs(home-away),[.02,.05,.1,.2]),
  quote_age=b(float(a["actual_hours_before_kickoff"])-h,[.25,1,3,8]),
  price_imbalance=b(home-away,[-.15,-.05,0,.05,.15]),
  prob_magnitude=b(abs(pr),[.002,.01,.03,.06]),
  line_change_size=b(abs(d),[.125,.375,.75,1.25]),
  book_overround=b(1/home+1/away-1,[.015,.025,.035,.05]),
  odds_product=b(home*away,[3.4,3.7,4,4.3]),
  weekday=kick.weekday(),
  kickoff_hour=b(kick.hour,[4,8,12,16,20]),
  calendar_month=b(kick.month,[3,5,7,9,11]),
  line_quarter=b(abs(line),[.125,.375,.625,.875,1.125,1.625,2.625]),
  line_move_quarter=b(abs(d),[.0625,.1875,.3125,.5625,.875]),
  price_gap_fine=b(home-away,[-.2,-.1,-.025,.025,.1,.2]))
 for direction,side in sides.items():
  odds=home if side=="home" else away
  ff=dict(f,side_price=b(odds,[1.8,1.9,2,2.1]),
   side_price_fine=b(odds,[1.75,1.825,1.875,1.925,1.975,2.025,2.075,2.15]),
   side_implied_prob=b((1/odds)/((1/home)+(1/away)),[.44,.47,.5,.53,.56]),
   side_prob_change=b(pr if side=="home" else -pr,[-.02,-.005,.005,.02]))
  pnl=settle_score("AH",line,side,hg,ag,odds)[1]
  for (hh,dd,family),choices in by_signature.items():
   if hh!=h or dd!=direction:continue
   signature=";".join(f"{k}={ff[k]}" for k in family.split(","))
   for cid,structure in choices:
    if signature!=structure:continue
    groups[(date,fid,h)][side].append((cid,pnl))
    individual[cid].append(pnl)
    coverage["candidate_occurrences"]+=1
def stat(v):
 n=len(v);net=sum(v)
 return dict(n=n,net_U=round(net,4),roi_pct=round(100*net/n,4) if n else None)
def evaluate(subset):
 fi=collections.defaultdict(list)
 for k,sides in groups.items():
  home=[(c,p) for c,p in sides["home"] if c in subset]
  away=[(c,p) for c,p in sides["away"] if c in subset]
  if home or away:fi[k[:2]].append((k,home,away))
 out=[];tied=opposed=0
 for fixture,ks in fi.items():
  k,home,away=max(ks,key=lambda x:x[0][2])
  opposed+=bool(home and away)
  if len(home)==len(away):tied+=1;continue
  out.append((k[0],(home if len(home)>len(away) else away)[0][1]))
 overall=stat([p for _,p in out])
 monthly={}
 for m in sorted({date[:7] for date,p in out}):monthly[m]=stat([p for date,p in out if date[:7]==m])
 return dict(**overall,signal_fixtures=len(fi),tied_fixtures=tied,opposed_at_selected_horizon=opposed,monthly=monthly)
out=dict(scope="2025 retrospective historical Crown AH, frozen original 494 from R7/R9/R11-R15; R7 27 primary",
 source=str(SRC),coverage=dict(coverage),candidate_definitions=len(catalog),
 groups=len(groups),sets={},individual_candidates=[],
 caveats=["2025 is newly inspected in this round; original 494 candidate identities and all tested sets were defined using pre-2025 data.",
 "2024 outcomes have already been repeatedly inspected, so some pre-2025 portfolio choices may have been influenced by 2024 research. This is a temporal holdout, not a pristine prospectively preregistered trial.",
 "2025 historical Crown quote records were retrospectively ingested in 2026; event-time quote is not proof of contemporaneous receipt or executable betting.",
 "The 494 structures were historically selected using 2019-2023 outcomes. This does not evaluate all mathematically conceivable structures.",
 "Each portfolio uses one fixture at earliest eligible horizon, majority equal-net direction, tied skips, flat 1U. These are inherited research evaluation conventions, not newly imposed production rules.",
 "Individual candidate results are non-deduplicated and can overlap the same fixture; do not sum individual nets as a portfolio.",
 "No strategy, production, or Telegram changes."])
for name,subset in sets.items():
 out["sets"][name]=dict(definitions=len(subset),**evaluate(subset))
 print("SET",name,len(subset),out["sets"][name]["n"],out["sets"][name]["net_U"],out["sets"][name]["roi_pct"],flush=True)
for cid in sorted(catalog):
 out["individual_candidates"].append(dict(id=cid,batch=next(name.removeprefix("original_batch_") for name,v in sets.items() if name.startswith("original_batch_") and cid in v),**stat(individual[cid])))
assert len(out["individual_candidates"])==494
(P/"ALL_STRUCTURES_2025_R39.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print("DONE",out["coverage"],flush=True)
