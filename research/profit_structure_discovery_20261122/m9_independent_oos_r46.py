#!/usr/bin/env python3
"""R46 independent bivariate OOS research, season-prior-only draw calibration and team-strength residual tests.
NOT production M9 replay: different training universe, no Crown prices or full score grid."""
import json,math,collections
from pathlib import Path
import pandas as pd
P=Path(__file__).resolve().parent
repo=P.parents[1]
report=json.loads((repo/"research/m3/results/latest_penaltyblog_oos_report.json").read_text())
src=repo/report["prediction_artifact"]
df=pd.read_csv(src)
df=df[df.prediction_status.eq("predicted")].copy()
df["season"]=df.season.astype(int)
df["truth"]=df.actual_result_1x2.map({"H":0,"D":1,"A":2})
df=df[df.truth.notna()].copy()
for c in ["p_home","p_draw","p_away"]:df[c]=df[c].astype(float)
def metric(items):
 n=len(items)
 if not n:return {"n":0}
 return {"n":n,"logloss":round(sum(-math.log(max(p[y],1e-12)) for p,y in items)/n,8),
 "brier":round(sum(sum((v-(i==y))**2 for i,v in enumerate(p)) for p,y in items)/n,8)}
def normalize(a):
 s=sum(a);return [max(v,1e-12)/s for v in a]
# The two challengers below are exploratory methods, NOT user-authorized production rules.
# Draw-only: previous season empirical draw/predicted draw ratio, bounded by no hard gate; multiplicative ratio.
# Team strength: previous season team home/away residual (observed points expectation) as logit offsets.
def fit_prior(rows):
 pred_draw=sum(float(r.p_draw) for r in rows); actual_draw=sum(int(r.truth==1) for r in rows)
 draw_mult=(actual_draw+0.5)/(pred_draw+0.5)
 teams=collections.defaultdict(lambda:[0.,0])
 for r in rows:
  ph,pd,pa=float(r.p_home),float(r.p_draw),float(r.p_away)
  obs_h=1 if r.truth==0 else .5 if r.truth==1 else 0
  obs_a=1-obs_h
  exp_h=ph+.5*pd;exp_a=pa+.5*pd
  teams[str(r.home_team)][0]+=obs_h-exp_h;teams[str(r.home_team)][1]+=1
  teams[str(r.away_team)][0]+=obs_a-exp_a;teams[str(r.away_team)][1]+=1
 return draw_mult,teams
def forecast(r,draw_mult,teams,mode):
 p=[float(r.p_home),float(r.p_draw),float(r.p_away)]
 if mode in ("draw","combined"):p=normalize([p[0],p[1]*draw_mult,p[2]])
 if mode in ("team","combined"):
  h=teams.get(str(r.home_team),(0,0));a=teams.get(str(r.away_team),(0,0))
  # Empirical prior-season residual / games, measured without test-season results.
  delta=h[0]/h[1] if h[1] else 0
  delta-=a[0]/a[1] if a[1] else 0
  p=normalize([p[0]*math.exp(delta),p[1],p[2]*math.exp(-delta)])
 return p
results={}
for model in ["bivariate_poisson","poisson","dixon_coles"]:
 sub=df[df.model.eq(model)]
 seasons=sorted(sub.season.unique())
 res={}
 for season in seasons[1:]:
  prior=sub[sub.season.eq(seasons[seasons.index(season)-1])]
  test=sub[sub.season.eq(season)]
  # Use same league and strictly previous season to fit draw calibration and residuals
  fitted={league:fit_prior(list(rows.itertuples())) for league,rows in prior.groupby("league")}
  scores={mode:[] for mode in ("base","draw","team","combined")}
  for r in test.itertuples():
   draw_mult,teams=fitted.get(r.league,(1,{}))
   for mode in scores:
    scores[mode].append((forecast(r,draw_mult,teams,mode),int(r.truth)))
  res[str(season)]={mode:metric(items) for mode,items in scores.items()}
  res[str(season)]["prior_season"]=int(seasons[seasons.index(season)-1])
 results[model]=res
out={"source":str(src),"source_generated_utc":report["generated_utc"],"scope":"Independent M3 penaltyblog season-forward bivariate model, not exact production M9","models":results,
"caveats":["Research exploratory challengers: draw multiplier and team residual offset fitted only from prior-season OOS predictions/outcomes; not full low-score Dixon-Coles correction or refitted bivariate team-strength model.","The test source has date-only fixtures and 6 leagues, different from production M9 training/history/league universe.","No Crown odds/Asian line or official Telegram orders are paired, so no ROI or production improvement claims.","No production code or order rules changed."]}
(P/"M9_INDEPENDENT_OOS_R46.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
for m in results:
 print(m)
 for y,r in results[m].items():
  if int(y)>=2425:print(y,"n",r["base"]["n"],"LL",*[str(k)+":"+str(r[k]["logloss"]) for k in ("base","draw","team","combined")])
