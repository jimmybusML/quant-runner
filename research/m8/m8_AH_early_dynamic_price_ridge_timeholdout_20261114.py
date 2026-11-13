import json, collections, math, datetime
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
source=P/'m8_early_AH_same_line_water_movement_2019to2026_20261114.jsonl'
# Feature extraction at fixed pregame research cutoffs T-12 and T-6. The all-fixture selection isn't a production rule.
R=collections.defaultdict(list)
for rec in map(json.loads,source.open()):
 if rec['window'] not in ('24->12','24->6'):continue
 R[rec['window']].append(rec)
def featurize(r):
 start=r['start_line'];end=r['end_line'];dl=end-start
 h0=r['start_home_odds'];a0=r['start_away_odds']
 h=r['end_home_odds'];a=r['end_away_odds']
 dh=r['homechange'];da=r['awaychange']
 # score is excluded from features, so no result leakage
 return np.array([1.,start,end,abs(end),dl,abs(dl),h,a,h-a,
 h0,a0,dh,da,dh-da,abs(dh-da),
 h*end,a*end,dl*end,dh*end,da*end,
 end**2,dl**2,dh**2,da**2,
 float(dl>0),float(dl<0),float(dl==0),float(end==0),
 float(dh>0),float(da>0),float(dh>da),float(dh<da),
 math.sin((int(r['month'][-2:])-1)*math.pi/6),math.cos((int(r['month'][-2:])-1)*math.pi/6),
 ],dtype=float)
def calc(obs,field):
 n=len(obs);p=sum(v[field] for v in obs)
 return {'n':n,'net_U':round(p,3),'ROI_pct':round(100*p/n,3) if n else None}
RESULT={}
for w,items in R.items():
 train=[r for r in items if r['year']<=2023]
 val=[r for r in items if 2024<=r['year']<=2025]
 hold=[r for r in items if r['year']==2026]
 a=np.stack([featurize(r) for r in train]);means=a.mean(axis=0);sd=a.std(axis=0)
 means[0]=0;sd[0]=1;sd[sd<1e-10]=1
 a=(a-means)/sd
 y=np.array([[r['home_U'],r['away_U']] for r in train])
 # Numeric ridge shrinkage, research estimator only; absolutely not a production Gate or selection condition.
 alpha=100.
 reg=np.eye(a.shape[1])*alpha;reg[0,0]=0
 coef=np.linalg.solve(a.T@a+reg,a.T@y)
 def evaluate(items):
  x=np.stack([featurize(r) for r in items])
  pred=((x-means)/sd)@coef
  choose_home=pred[:,0]>=pred[:,1]
  realized=np.array([r['home_U'] if choose_home[i] else r['away_U'] for i,r in enumerate(items)])
  # Research-only strata of ranking predicted advantage over break-even, no cutoffs introduced to production
  maxpred=pred.max(axis=1)
  groups={}
  for quant in (0.1,0.2,0.4,0.6,1.0):
   take=np.argsort(-maxpred)[:max(1,int(len(items)*quant))]
   profit=float(realized[take].sum())
   groups[f'top_{round(quant*100)}pct']={'n':len(take),'net_U':round(profit,3),'ROI_pct':round(profit*100/len(take),3)}
  pnl=float(realized.sum())
  return {'all_matches':len(items),'predict_home_count':int(choose_home.sum()),'predict_away_count':int((~choose_home).sum()),'full_coverage_net_U':round(pnl,3),'full_coverage_ROI_pct':round(100*pnl/len(items),3),'home_benchmark':calc(items,'home_U'),'away_benchmark':calc(items,'away_U'),'ranked_groups_research_only':groups}
 res={'train_2019_23':evaluate(train),'validation_2024_25':evaluate(val),'descriptive_2026':evaluate(hold),'sample_counts':{'2019_23':len(train),'2024_25':len(val),'2026':len(hold)},'estimator':'ridge regression two 1U settlement returns, penalty=100 for numerical stability, no outcome/FT features, fixed 24h to 12h / 24h to 6h Crown snapshots; study-only, no production controls'}
 RESULT[w]=res
 print('MODEL',w,json.dumps(res,ensure_ascii=False),flush=True)
P.joinpath('m8_AH_early_dynamic_price_ridge_timeholdout_20261114.json').write_text(json.dumps({'comparison':'Chronological score-prediction exploratory; trained on 2019-23, evaluated on 2024-25 and 2026, no formal order or selection rule changed','models':RESULT},ensure_ascii=False,indent=2))
