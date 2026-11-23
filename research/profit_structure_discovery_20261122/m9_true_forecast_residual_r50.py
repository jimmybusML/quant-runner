#!/usr/bin/env python3
"""R50 true forecast-error residual, season-forward, independent M3 bivariate OOS source.
NOT production M9 replay. All calibration inputs are previous-season predictions and outcomes."""
import json,math,collections
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent;repo=P.parents[1]
report=json.loads((repo/"research/m3/results/latest_penaltyblog_oos_report.json").read_text())
df=pd.read_csv(repo/report["prediction_artifact"])
df=df[(df.model=="bivariate_poisson")&(df.prediction_status=="predicted")].copy()
df["season"]=df.season.astype(int)
df["truth"]=df.actual_result_1x2.map({"H":0,"D":1,"A":2})
df=df[df.truth.notna()]
seasons=sorted(df.season.unique())
def fit(rows):
 team=collections.defaultdict(lambda:[0.,0])
 for r in rows.itertuples():
  eh=float(r.p_home)+.5*float(r.p_draw)
  actual=1 if r.truth==0 else .5 if r.truth==1 else 0
  for name,res in ((str(r.home_team),actual-eh),(str(r.away_team),eh-actual)):
   team[name][0]+=res;team[name][1]+=1
 return {k:v[0]/v[1] for k,v in team.items()}
def calc(row,res,mode):
 p=[float(row.p_home),float(row.p_draw),float(row.p_away)]
 if mode!="original":
  h=res.get(str(row.home_team),0);a=res.get(str(row.away_team),0)
  d=h-a
  p=[p[0]*math.exp(d),p[1],p[2]*math.exp(-d)]
  total=sum(p);p=[x/total for x in p]
 y=int(row.truth)
 return (-math.log(max(p[y],1e-12)),sum((v-(k==y))**2 for k,v in enumerate(p)))
out={"source":report["prediction_artifact"],"source_generated_utc":report["generated_utc"],
"scope":"Independent M3 penaltyblog bivariate OOS, not production M9 and not full score grid",
"method":"Previous one or two full seasons per league: actual team points (win=1, draw=.5) minus model forecast expected points (Pwin+.5*Pdraw), divided by games; home minus away residual as exponential offsets to home/away 1X2. Test season is entirely held out; zero test-season results in calibration. No future information. Two-season variant pools all available prior two seasons' OOS predictions, not raw goal difference.",
"results":[],"errors":[]}
for i in range(2,len(seasons)):
 year=int(seasons[i]);recent=int(seasons[i-1]);old=int(seasons[i-2])
 test=df[df.season==year];prior1=df[df.season==recent];prior2=df[df.season.isin((recent,old))]
 fitted={}
 for league in test.league.unique():
  fitted[league]={"prior1":fit(prior1[prior1.league==league]),"prior2":fit(prior2[prior2.league==league])}
 scores={mode:[] for mode in ("original","prior1","prior2")}
 by_league=collections.defaultdict(lambda:collections.defaultdict(list))
 for r in test.itertuples():
  for mode in scores:
   result=calc(r,fitted[r.league].get(mode,{}),mode)
   scores[mode].append(result);by_league[r.league][mode].append(result)
 def agg(v):
  return {"n":len(v),"logloss":sum(x[0] for x in v)/len(v),"brier":sum(x[1] for x in v)/len(v)}
 record={"season":year,"prior_seasons":[old,recent],"metrics":{k:agg(v) for k,v in scores.items()},
 "by_league":{league:{mode:agg(vals) for mode,vals in v.items()} for league,v in by_league.items()}}
 out["results"].append(record)
 if year>=2324:print(year,record["metrics"],flush=True)
(P/"M9_TRUE_FORECAST_RESIDUAL_R50.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
out["caveats"]=["True prior-season model forecast residual, unlike R49 raw goal difference.","These are 1X2 post-processing corrections to independent M3 season-forward bivariate predictions, NOT refitted M9 goal intensities or full score grid.","Model source contains date-only fixtures, different training/league universe than production M9.","No Crown AH quotes, historical receipt timestamps, Telegram orders, or ROI.","No production logic, rules or order counts changed."]
(P/"M9_TRUE_FORECAST_RESIDUAL_R50.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
