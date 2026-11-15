import json,math,collections,datetime
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
gids={(r['year'],r['fid']) for r in G[('shape_relation','reverted','agree')]}
allprior=set(prior)|gids
remaining=[r for r in A if (r['year'],r['fid']) not in allprior]
assert len(allprior)==8956 and len(remaining)==30145
# Historical settlements on both sides, available from earlier calendar dates.
# Use all AH observations for historical features, not just selected or winning records.
hist=collections.defaultdict(lambda:np.zeros(6))
recent=collections.defaultdict(lambda:np.zeros(6))
bydate=collections.defaultdict(list)
for i,r in enumerate(A):
 r['score_ev_home']=float(e1h[i]);r['score_ev_away']=float(e1a[i])
 bydate[r['date']].append(r)
days=sorted(bydate);j=0
def role(r,s):
 return 'zero' if r['end_zero'] else 'favorite' if (s=='home')==(r['end_line']<0) else 'dog'
def keys(r,s):
 z=S[r['fid']];team=z[s];league=r['league'];ro=role(r,s)
 return [('team',team),('team_role',team,ro),('team_venue',team,s),('league_role',league,ro),('league_venue',league,s)]
def update(r,date):
 z=S[r['fid']]
 for side in ('home','away'):
  other='away' if side=='home' else 'home';u=r['end_'+side+'_U'];price=r[side+'_price'];p=resid=u-r['score_ev_'+side]
  goals=(z['hg']-z['ag'])*(1 if side=='home' else -1)
  forecast=z['lambda_'+side+'_0.025']-z['lambda_'+other+'_0.025']
  v=np.array([1.,u,p,goals-forecast,(u/(price-1) if u>0 else 0.),(-u if u<0 else 0.)])
  for k in keys(r,side):
   hist[k]+=v
   # Exponential recency with a 365-day half-life, research estimator only.
   if k in last:recent[k]*=2**(-(date-last[k]).days/365)
   recent[k]+=v;last[k]=date
last={}
for date in days:
 now=datetime.date.fromisoformat(date)
 while j<len(days) and (now-datetime.date.fromisoformat(days[j])).days>=2:
  earlier=datetime.date.fromisoformat(days[j])
  for r in bydate[days[j]]:update(r,earlier)
  j+=1
 for r in bydate[date]:
  fs={}
  for side in ('home','away'):
   vals=[]
   for k in keys(r,side):
    a=hist[k];b=recent[k]*(2**(-(now-last[k]).days/365)) if k in last else recent[k]
    vals.extend([math.log1p(a[0]),a[1]/(a[0]+20),a[2]/(a[0]+20),a[3]/(a[0]+20),b[1]/(b[0]+20),b[2]/(b[0]+20),b[3]/(b[0]+20)])
   fs[side]=vals
  r['history_feat']=fs
def features(r,kind):
 l0,l1=r['start_line'],r['end_line'];ph,pa=r['home_price'],r['away_price'];h0,a0=r['start_home_price'],r['start_away_price']
 p0=a0/(h0+a0);p1=pa/(ph+pa);z=S[r['fid']]
 f=[1,l0,l1,abs(l1),l1-l0,p0,p1,p1-p0,ph,pa,ph-h0,pa-a0,(p1-p0)*l1,math.log1p(r['n_line_changes']),math.log1p(r['n_events']),r['line_range'],r['final_line_minutes']/300,r['late_event_age_min']/60]
 f.extend(float(r['path_shape']==s) for s in ('never_changed','one_way','reverted','oscillating'))
 f.extend([z['lambda_home_0.025'],z['lambda_away_0.025'],z['lambda_home_0.06'],z['lambda_away_0.06'],r['score_ev_home'],r['score_ev_away'],(r['score_ev_home']-r['score_ev_away'])*(p1-p0)])
 if kind=='team_league_history':
  h=r['history_feat']['home'];a=r['history_feat']['away'];f.extend(h+a)
  f.extend(x-y for x,y in zip(h,a))
 return f
def metrics(v):
 n=len(v);u=float(sum(v));return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def fit(tr,te,kind):
 x=np.array([features(r,kind) for r in tr]);y=np.array([[r['end_home_U'],r['end_away_U']] for r in tr])
 mu=x.mean(0);sd=x.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(x-mu)/sd;reg=np.eye(X.shape[1])*100;reg[0,0]=0
 coef=np.linalg.solve(X.T@X+reg,X.T@y)
 pred=((np.array([features(r,kind) for r in te])-mu)/sd)@coef
 pnl=np.where(pred[:,0]>=pred[:,1],[r['end_home_U'] for r in te],[r['end_away_U'] for r in te]);best=pred.max(1)
 return {'all':metrics(pnl),'positive_estimate_diagnostic':metrics(pnl[best>0]),'home_estimate':int((pred[:,0]>=pred[:,1]).sum())},pnl,best
out={'source':'Full 39101 Crown AH event paths; exact eight prior research cohort IDs excluded from prediction test; all paths used for prior team history, earliest UTC date at least two calendar days before current; not actual FT receipt. Historical prior-cohort definitions selected on same data so validation is temporal for estimator, not genuinely unseen full strategy. Research shrinkage 20 and ridge 100 are numerical experiment choices.','coverage':len(remaining),'years':{},'diagnostics':{}}
for year in (2024,2025,2026):
 tr=[r for r in remaining if r['year']<year];te=[r for r in remaining if r['year']==year]
 b,bp,be=fit(tr,te,'price_score');a,ap,ae=fit(tr,te,'team_league_history')
 out['years'][str(year)]={'train_n':len(tr),'test_n':len(te),'price_score':b,'team_league_history':a}
 print('ANNUAL',year,out['years'][str(year)],flush=True)
 if year==2026:
  for g in ('never_changed','reverted','one_way','oscillating'):
   ix=np.array([r['path_shape']==g for r in te])
   out['diagnostics'][g]={'price_score':metrics(bp[ix]),'team_league_history':metrics(ap[ix])}
  for period in ('H1','H2'):
   ix=np.array([(r['month']<='2026-06')==(period=='H1') for r in te])
   out['diagnostics'][period]={'price_score':metrics(bp[ix]),'team_league_history':metrics(ap[ix])}
  print('2026_DETAIL',out['diagnostics'],flush=True)
# Independent diagnostics: relative historical team market residual strengthens or opposes score-model direction.
groups=collections.defaultdict(list)
for r in remaining:
 # index 2 of team historical block is historical signed return residual
 val=r['history_feat']['home'][2]-r['history_feat']['away'][2]
 s=direction(val);model=direction(r['score_ev_home']-r['score_ev_away'])
 relation='flat' if s=='flat' or model=='flat' else 'agree' if s==model else 'disagree'
 groups[('all',relation)].append(r)
 groups[(r['path_shape'],relation)].append(r)
out['history_score_relationship']={}
for k,z in sorted(groups.items()):
 v={side:summary(z,side) for side in ('ind_U','contra_U')}
 out['history_score_relationship']['|'.join(k)]=v
 if k[0]=='all' or any(all(x[p]['ROI'] is not None and x[p]['ROI']>0 for p in ('2019-23','2024-25','2026')) for x in v.values()):
  print('RELATION',k,{side:{p:x[p] for p in ('2019-23','2024-25','2026','2026_H1','2026_H2')} for side,x in v.items()},flush=True)
(P/'m8_team_league_market_residual_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print('DONE',len(A),len(remaining),flush=True)
