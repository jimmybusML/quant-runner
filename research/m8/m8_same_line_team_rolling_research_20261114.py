import json,collections,datetime,math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_same_line_probability_path_20261114.jsonl').open()]
def epoch(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
def stats(v):
 n=len(v);s=sum(v);return {'n':n,'net_U':round(s,3),'ROI':round(100*s/n,3) if n else None}
# Team identity and history known before each match. Only update from an earlier UTC day whose last known kickoff
# is at least 24h before current T1, so no same/near-date result leakage. Approximation, not actual historical FT receipt.
# Research shrinkage 20 observations, decayed alternative across previous 365 days, not a gate.
byday=collections.defaultdict(list)
for r in rows:byday[r['date']].append(r)
history=collections.defaultdict(list)
days=sorted(byday);i=0
for day in days:
 now=datetime.date.fromisoformat(day)
 while i<len(days) and (now-datetime.date.fromisoformat(days[i])).days>=2:
  for old in byday[days[i]]:
   for k,side in [('home_team','home'),('away_team','away')]:
    history[old[k]].append((datetime.date.fromisoformat(days[i]),old['end_'+side+'_U']))
  i+=1
 for r in byday[day]:
  for k,side in [('home_team','home'),('away_team','away')]:
   h=history[r[k]];recent=[v for t,v in h if (now-t).days<=365]
   r[side+'_hist_n']=len(h);r[side+'_hist_return']=sum(v for t,v in h)/(len(h)+20)
   r[side+'_recent_return']=sum(recent)/(len(recent)+20)
   r[side+'_recent_n']=len(recent)
def features(r,use_team):
 p0,p3,p1,me,lo,hi,sd=[r[k] for k in ('p0','p3','p1','pmean','pmin','pmax','pstd')]
 line=r['end_line'];m=p1-p0;d1=p3-p0;d2=p1-p3
 f=[1,line,abs(line),p0,p1,me,d1,d2,m,hi-lo,p1-me,p1-lo,hi-p1,sd,r['variation'],math.log1p(r['n_price_moves']),r['last_move'],r['home_price'],r['away_price'],line*m,line*d2,m*m,d1*d2]
 if use_team:
  h,a=r['home_hist_return'],r['away_hist_return'];hr,ar=r['home_recent_return'],r['away_recent_return']
  f.extend([h,a,h-a,hr,ar,hr-ar,h*m,a*m,math.log1p(r['home_hist_n']),math.log1p(r['away_hist_n']),math.log1p(r['home_recent_n']),math.log1p(r['away_recent_n'])])
 return f
def fit(train,test,use_team):
 X=np.asarray([features(r,use_team) for r in train]);Y=np.array([[r['end_home_U'],r['end_away_U']] for r in train])
 mean=X.mean(0);sd=X.std(0);mean[0]=0;sd[0]=1;sd[sd<1e-10]=1;X=(X-mean)/sd
 ridge=np.eye(X.shape[1])*100;ridge[0,0]=0
 beta=np.linalg.solve(X.T@X+ridge,X.T@Y)
 p=((np.asarray([features(r,use_team) for r in test])-mean)/sd)@beta
 profit=np.where(p[:,0]>=p[:,1],[r['end_home_U'] for r in test],[r['end_away_U'] for r in test])
 return {'all':stats(profit.tolist()),'positive_predicted_research':stats(profit[p.max(1)>0].tolist()),'nonzero':stats([float(v) for r,v in zip(test,profit) if not r['end_zero']])}
out={'description':'Same handicap sample; rolling annual fit from earlier calendar years. Team residual AH return history from earlier UTC dates (2 calendar days prior or older); proxy for availability, not exact FT retrieval. Team IDs from raw response. All available samples evaluated; positive prediction threshold is comparison only, not production rule.','annual':{}}
for year in (2024,2025,2026):
 tr=[r for r in rows if r['year']<year];te=[r for r in rows if r['year']==year]
 a=fit(tr,te,False);b=fit(tr,te,True)
 out['annual'][str(year)]={'train_n':len(tr),'price_path':a,'price_path_and_team':b,'team_prior_on_either':sum(r['home_hist_n']>0 or r['away_hist_n']>0 for r in te)}
 print('ROLLING',year,out['annual'][str(year)],flush=True)
(P/'m8_same_line_team_rolling_research_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
