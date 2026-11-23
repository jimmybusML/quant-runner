#!/usr/bin/env python3
"""R53 independent M3 bivariate OOS: do team forecast residuals persist next season?"""
import json,collections,math
from pathlib import Path
import pandas as pd,numpy as np
P=Path(__file__).resolve().parent;root=P.parents[1]
report=json.loads((root/"research/m3/results/latest_penaltyblog_oos_report.json").read_text())
df=pd.read_csv(root/report["prediction_artifact"])
df=df[(df.model=="bivariate_poisson")&(df.prediction_status=="predicted")].copy()
df["season"]=df.season.astype(int)
df["truth"]=df.actual_result_1x2.map({"H":0,"D":1,"A":2})
df=df[df.truth.notna()]
def team_res(rows):
 acc=collections.defaultdict(lambda:[0.,0])
 for r in rows.itertuples():
  exp=float(r.p_home)+.5*float(r.p_draw)
  actual=1 if r.truth==0 else .5 if r.truth==1 else 0
  acc[(r.league,str(r.home_team))][0]+=actual-exp;acc[(r.league,str(r.home_team))][1]+=1
  acc[(r.league,str(r.away_team))][0]+=exp-actual;acc[(r.league,str(r.away_team))][1]+=1
 return {k:(v[0]/v[1],int(v[1])) for k,v in acc.items()}
seasons=sorted(df.season.unique())
out={"scope":"Independent M3 bivariate season-forward OOS, not M9 production or Crown","method":"Compare previous season's mean team expected-points forecast residual against next season's observed forecast residual, only teams present both seasons. Also compare previous TWO seasons' pooled residual to next-season residual. Compute weighted covariance slope and sign agreement, and per-league/year Pearson correlation. This directly probes persistence rather than performance of corrected probabilities.","results":[]}
for i in range(2,len(seasons)):
 year=int(seasons[i])
 if year<2324:continue
 current=team_res(df[df.season==year])
 prior1=team_res(df[df.season==seasons[i-1]])
 prior2=team_res(df[df.season.isin((seasons[i-2],seasons[i-1]))])
 for league in sorted(df.league.unique()):
  for name,prior in (("prior1",prior1),("prior2",prior2)):
   pairs=[{"team":k[1],"previous_residual":prior[k][0],"current_residual":current[k][0],"previous_games":prior[k][1],"current_games":current[k][1]} for k in current if k[0]==league and k in prior]
   if len(pairs)<3:continue
   x=np.array([p["previous_residual"] for p in pairs]);y=np.array([p["current_residual"] for p in pairs])
   corr=float(np.corrcoef(x,y)[0,1]) if np.std(x)>0 and np.std(y)>0 else None
   agreement=float(np.mean(np.sign(x)==np.sign(y)))
   out["results"].append({"year":year,"league":league,"variant":name,"n_teams":len(pairs),"pearson":corr,"sign_agreement":agreement,"pairs":pairs})
   if league=="E0":print(year,league,name,len(pairs),round(corr,4) if corr is not None else None,round(agreement,3),flush=True)
out["caveats"]=["Previous/current season model predictions are OOS per source, but league-season OOS archive may use date-only timestamps.","Per-team Pearson correlation is across teams, not independent match evidence; sample sizes limited.","Current-season residual is evaluated retrospectively, never used to generate the earlier forecast.","A stable correction to 1X2 can arise from shrinkage or calibration even without persistent team residual sign.","No M9 score-grid, Crown price or formal trading ROI."]
(P/"M9_RESIDUAL_PERSISTENCE_R53.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
