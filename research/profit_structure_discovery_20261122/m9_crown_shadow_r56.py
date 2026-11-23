#!/usr/bin/env python3
"""Read-only retrospective same-fixture Crown AH original-vs-residual research pilot.
Uses latest historical cache filtered by fixture kickoff, NOT verified as-of receipt."""
import json,datetime as dt,collections,math
from pathlib import Path
import numpy as np,pandas as pd
from penaltyblog.models import BivariatePoissonGoalModel
from research.m3.probabilities import settle_score
from research.m3.totalcorner_forward_ev import calculate
P=Path(__file__).resolve().parent;ROOT=Path.home()/"QuantAsiaDesk"
events=[json.loads(s) for s in (ROOT/"state/m9_formal_events.jsonl").read_text().splitlines() if s.strip()]
orders=collections.defaultdict(dict)
for e in events:
 if e.get("order_key"):orders[e["order_key"]][e["kind"]]=e
def fit(rows):
 f=pd.DataFrame(rows,columns=["t","home_team","away_team","home_goals","away_goals"])
 m=BivariatePoissonGoalModel(f.home_goals,f.away_goals,f.home_team,f.away_team);m.fit();return m
def grid(m,h,a):return np.asarray(m.predict(h,a).grid,dtype=float)
def masses(g):return float(np.tril(g,-1).sum()),float(np.trace(g))
def tilt(g,d):
 i,j=np.indices(g.shape);v=g*np.exp(np.clip(d*(i-j),-30,30));return v/v.sum()
def choose(g,line):
 scores={s:calculate(g.tolist(),"AH",line,s,2.0) for s in ("home","away")}
 return max(("home","away"),key=lambda s:(scores[s],s=="home"))
out={"method":"Same-fixture retrospective research on actual Crown quote and settlement receipts, with model-class M9 bivariate grids fitted on latest snapshot historical cache filtered by kickoff before earliest quote receipt in each league; true previous-year prior-model forecast residual, full score-grid exp(0.1*residual*score-difference) correction. Does not reproduce production M9 exact original predictions or prove as-of historical availability.",
"rows":[],"errors":[],"skipped":[]}
for lid in ("1","12","61"):
 group=[ev for ev in orders.values() if ev.get("M9_PREPARED",{}).get("league_id")==lid and "M9_TG_SENT" in ev and "M9_SETTLED" in ev]
 if not group:continue
 cache=json.loads((ROOT/"repos/m1/data/m1_history_cache"/(lid+".json")).read_text())
 rows={}
 for r in cache["rows"]:
  if r.get("status")!="full":continue
  try:
   t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
   rows[str(r["id"])]=(t,str(r["h_id"]),str(r["a_id"]),int(r["hg"]),int(r["ag"]))
  except (KeyError,TypeError,ValueError):continue
 cut=min(dt.datetime.fromisoformat(ev["M9_PREPARED"]["crown"]["received_at"]) for ev in group)
 calstart=dt.datetime(2025,1,1,tzinfo=dt.timezone(dt.timedelta(hours=8)))
 prevstart=dt.datetime(2026,1,1,tzinfo=dt.timezone(dt.timedelta(hours=8)))
 earlier=[r for r in rows.values() if r[0]<calstart]
 previous=[r for r in rows.values() if calstart<=r[0]<prevstart]
 training=[r for r in rows.values() if r[0]<cut]
 if not earlier or not training:continue
 try:
  old=fit(earlier);known={r[1] for r in earlier}|{r[2] for r in earlier}
  acc=collections.defaultdict(lambda:[0.,0])
  for t,h,a,gh,ga in previous:
   if h not in known or a not in known:continue
   ph,pdraw=masses(grid(old,h,a));expected=ph+.5*pdraw;actual=1 if gh>ga else .5 if gh==ga else 0
   for team,delta in ((h,actual-expected),(a,expected-actual)):
    acc[team][0]+=delta;acc[team][1]+=1
  residual={k:v[0]/v[1] for k,v in acc.items()}
  baseline=fit(training);teams={r[1] for r in training}|{r[2] for r in training}
  for ev in group:
   prep=ev["M9_PREPARED"];settled=ev["M9_SETTLED"];fid=str(prep["fid"])
   match=rows.get(fid)
   if not match or match[1] not in teams or match[2] not in teams:
    out["skipped"].append({"fid":fid,"reason":"fixture_or_team_missing"});continue
   t,h,a,gh,ga=match
   if t>=dt.datetime.fromisoformat(prep["kickoff_utc"])+dt.timedelta(hours=1):
    out["skipped"].append({"fid":fid,"reason":"cache_time_mismatch"});continue
   g=grid(baseline,h,a);g2=tilt(g,.1*(residual.get(h,0)-residual.get(a,0)))
   line=float(prep["line"]);side0=choose(g,line);side1=choose(g2,line)
   p0=float(prep["home_decimal"] if side0=="home" else prep["away_decimal"])
   p1=float(prep["home_decimal"] if side1=="home" else prep["away_decimal"])
   state0,pnl0=settle_score("AH",line,side0,int(settled["home_goals"]),int(settled["away_goals"]),p0)
   state1,pnl1=settle_score("AH",line,side1,int(settled["home_goals"]),int(settled["away_goals"]),p1)
   out["rows"].append({"fid":fid,"league_id":lid,"original_rebuilt_side":side0,"corrected_side":side1,
    "actual_production_side":prep["side"],"original_rebuilt_pnl":pnl0,"corrected_pnl":pnl1,
    "actual_production_pnl":settled["pnl_u"],"same_side":side0==side1,"baseline_matches_production":side0==prep["side"],
    "received_at":prep["crown"]["received_at"],"quote_line":line})
  print(lid,"completed",len([x for x in out["rows"] if x["league_id"]==lid]),flush=True)
 except Exception as e:out["errors"].append({"league":lid,"error":str(e)});print(lid,"ERROR",e,flush=True)
out["limitations"]=["Historical training cache is latest snapshot, filtered by kickoff only; NOT a point-in-time as-of model input archive.","Original baseline refit once per league at earliest quote receipt; not exact production per-run M9 grid, so baseline side may differ from actual production.","Actual Crown quote and settlement are verified by R55; challenger decision is retrospective, not a live pre-registered shadow.","Small sample from three leagues; no inference of long-term ROI.","No Telegram send or formal ledger change."]
public={k:v for k,v in out.items() if k not in ("rows","skipped")}
public["sample_n"]=len(out["rows"])
public["skipped_count"]=len(out["skipped"])
public["skipped_reasons"]=dict(collections.Counter(x["reason"] for x in out["skipped"]))
public["league_sample_counts"]=dict(collections.Counter(x["league_id"] for x in out["rows"]))
public["same_side_count"]=sum(x["same_side"] for x in out["rows"])
public["baseline_matches_production_count"]=sum(x["baseline_matches_production"] for x in out["rows"])
public["pnl_by_version"]={k:sum(x[k] for x in out["rows"]) for k in ("original_rebuilt_pnl","corrected_pnl","actual_production_pnl")}
(P/"M9_CROWN_SHADOW_R56.json").write_text(json.dumps(public,ensure_ascii=False,indent=2)+"\n")
print("SUMMARY",len(out["rows"]),"errors",out["errors"],"skipped",len(out["skipped"]))
if out["rows"]:
 for k in ("original_rebuilt_pnl","corrected_pnl","actual_production_pnl"):
  print(k,sum(x[k] for x in out["rows"]),sum(x[k] for x in out["rows"])/len(out["rows"]))
 print("changed sides",sum(not x["same_side"] for x in out["rows"]),"baseline matches production",sum(x["baseline_matches_production"] for x in out["rows"]))
