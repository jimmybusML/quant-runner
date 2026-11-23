#!/usr/bin/env python3
"""R52 explain E0 R50 improvement at team level, strict prior-season calibration."""
import json,math,collections
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent;repo=P.parents[1]
report=json.loads((repo/"research/m3/results/latest_penaltyblog_oos_report.json").read_text())
df=pd.read_csv(repo/report["prediction_artifact"])
df=df[(df.model=="bivariate_poisson")&(df.prediction_status=="predicted")&(df.league=="E0")].copy()
df["season"]=df.season.astype(int);df["truth"]=df.actual_result_1x2.map({"H":0,"D":1,"A":2})
df=df[df.truth.notna()]
seasons=sorted(df.season.unique())
def fit(rows):
 sums=collections.defaultdict(lambda:[0.,0])
 for r in rows.itertuples():
  expected=float(r.p_home)+.5*float(r.p_draw)
  actual=1 if r.truth==0 else .5 if r.truth==1 else 0
  for team,diff in ((str(r.home_team),actual-expected),(str(r.away_team),expected-actual)):
   sums[team][0]+=diff;sums[team][1]+=1
 return {k:{"residual":v[0]/v[1],"n":v[1]} for k,v in sums.items()}
def prob(r,res):
 p=[float(r.p_home),float(r.p_draw),float(r.p_away)]
 d=res.get(str(r.home_team),{"residual":0})["residual"]-res.get(str(r.away_team),{"residual":0})["residual"]
 q=[p[0]*math.exp(d),p[1],p[2]*math.exp(-d)];s=sum(q);return [v/s for v in q]
out={"source":report["prediction_artifact"],"scope":"E0 independent M3 bivariate OOS 1X2; no production M9 or Crown",
"method":"Train per-team residual = observed points (win 1/draw 0.5) minus predicted points (Pwin+0.5 Pdraw), using ONLY prior two seasons' independent OOS forecasts. Compare 1X2 log loss of baseline vs corrected on next held-out season. Per-team attribution splits each fixture's gain equally between home and away participants; this is attribution, not isolated causal effect.",
"seasons":[]}
for i in range(2,len(seasons)):
 year=int(seasons[i])
 if year<2324:continue
 prior=df[df.season.isin((seasons[i-2],seasons[i-1]))]
 test=df[df.season==year]
 res=fit(prior);teams=collections.defaultdict(lambda:{"games":0,"gain":0.,"baseline":0.,"corrected":0.,"prior_residual":None,"prior_n":0})
 fixtures=[]
 for r in test.itertuples():
  p=[float(r.p_home),float(r.p_draw),float(r.p_away)];q=prob(r,res);truth=int(r.truth)
  old=-math.log(max(p[truth],1e-12));new=-math.log(max(q[truth],1e-12));gain=old-new
  h,a=str(r.home_team),str(r.away_team)
  fixtures.append({"home":h,"away":a,"gain":gain,"baseline_ll":old,"corrected_ll":new})
  for team in (h,a):
   t=teams[team];t["games"]+=1;t["gain"]+=gain/2;t["baseline"]+=old/2;t["corrected"]+=new/2
   t["prior_residual"]=res.get(team,{"residual":0})["residual"];t["prior_n"]=res.get(team,{"n":0})["n"]
 out["seasons"].append({"season":year,"n":len(fixtures),"gain_per_match":sum(x["gain"] for x in fixtures)/len(fixtures),
 "teams":{k:v for k,v in sorted(teams.items())},
 "new_team_fixtures":sum(x["home"] not in res or x["away"] not in res for x in fixtures),
 "fixtures":fixtures})
 print(year,len(fixtures),"gain",round(out["seasons"][-1]["gain_per_match"],6),"unseen-team",out["seasons"][-1]["new_team_fixtures"],flush=True)
out["caveats"]=["R50 independent M3 season-forward model, not M9 production; score-grid and Crown AH unavailable.","Per-team gains allocate shared match gains 50/50, not an independent team effect.","Team residuals are observed from prior two seasons, with promoted teams potentially absent.","This analysis reuses R50 data, not an independent replication.","No statistical uncertainty or bootstrap confidence intervals yet; no production change."]
(P/"M9_E0_TEAM_RESIDUAL_R52.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
