#!/usr/bin/env python3
"""Read-only R47: prior-two-season team strength change-speed test, independent M3 bivariate 1X2 OOS archive."""
import json,math,collections
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent
root=P.parents[1]
r=json.loads((root/"research/m3/results/latest_penaltyblog_oos_report.json").read_text())
df=pd.read_csv(root/r["prediction_artifact"])
df=df[(df.model=="bivariate_poisson")&(df.prediction_status=="predicted")].copy()
df["season"]=df.season.astype(int)
df["truth"]=df.actual_result_1x2.map({"H":0,"D":1,"A":2})
df=df[df.truth.notna()]
seasons=sorted(df.season.unique())
def team_residual(frame):
 t=collections.defaultdict(lambda:[0.,0])
 for row in frame.itertuples():
  p=float(row.p_home)+.5*float(row.p_draw)
  actual=1 if row.truth==0 else .5 if row.truth==1 else 0
  for team,res in ((str(row.home_team),actual-p),(str(row.away_team),p-actual)):
   t[team][0]+=res;t[team][1]+=1
 return {k:v[0]/v[1] for k,v in t.items()}
def probabilities(row,old,new,mode):
 p=[float(row.p_home),float(row.p_draw),float(row.p_away)]
 def adjust(team):
  recent=new.get(team,0.)
  if mode=="base":return 0.
  if mode=="recent":return recent
  earlier=old.get(team,recent)
  velocity=recent-earlier
  if mode=="velocity":return velocity
  if mode=="recent_plus_velocity":return recent+velocity
  if mode=="two_season_mean":return .5*(recent+earlier)
  raise ValueError(mode)
 delta=adjust(str(row.home_team))-adjust(str(row.away_team))
 v=[p[0]*math.exp(delta),p[1],p[2]*math.exp(-delta)]
 s=sum(v)
 return [x/s for x in v]
modes=["base","recent","velocity","recent_plus_velocity","two_season_mean"]
out={"source":r["prediction_artifact"],"source_generated_utc":r["generated_utc"],
"method":"All variants are exploratory probability post-processing, not M9 parameter refitting. Each test season uses the two strictly prior seasons, per-league previous-season team point residuals (actual minus model expected). Velocity = most-recent prior-season residual minus earlier prior-season residual. No current-season results are used.",
"years":{}}
for i in range(2,len(seasons)):
 year=int(seasons[i]);old=df[df.season==seasons[i-2]];recent=df[df.season==seasons[i-1]];test=df[df.season==year]
 fits={}
 for league in set(old.league)|set(recent.league):
  fits[league]=(team_residual(old[old.league==league]),team_residual(recent[recent.league==league]))
 values={mode:[] for mode in modes}
 for row in test.itertuples():
  a,b=fits.get(row.league,({},{}))
  for mode in modes:
   p=probabilities(row,a,b,mode);truth=int(row.truth)
   values[mode].append((-math.log(max(p[truth],1e-12)),sum((v-(k==truth))**2 for k,v in enumerate(p))))
 scores={mode:{"n":len(v),"logloss":round(sum(x for x,y in v)/len(v),8),"brier":round(sum(y for x,y in v)/len(v),8)} for mode,v in values.items() if v}
 out["years"][str(year)]={"previous_seasons":[int(seasons[i-2]),int(seasons[i-1])],"scores":scores}
out["caveats"]=["Source is independent M3 penaltyblog season-forward model, not production M9 training and fixture universe.","Season-aggregated residual change is a proxy for speed, not rolling-match temporal update or dynamic goal-intensity fitting.","No Asian handicap quote pairing or ROI; not evidence of betting edge.","No model gates, quantity restrictions, production or Telegram changes."]
(P/"M9_STRENGTH_VELOCITY_R47.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
for y,z in out["years"].items():
 if int(y)>=2324:print(y,z["scores"])
