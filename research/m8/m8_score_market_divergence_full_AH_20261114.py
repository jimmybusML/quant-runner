import json,math,collections,datetime
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Recreate exact previously published seven candidate membership.
exec((P/'m8_cross_market_aligned_20261114.py').read_text().split('def dt(s):')[0])
P=R
S={r['fid']:r for r in map(json.loads,(P/'m8_independent_score_strength_20261114.jsonl').open())}
A=[r for k,r in base.items() if r['fid'] in S]
assert len(A)==39101,len(A)
K=40;g=np.arange(K)[None,:]
def pmf(lam):
 a=np.empty((len(lam),K));a[:,0]=np.exp(-lam)
 for j in range(1,K):a[:,j]=a[:,j-1]*lam/j
 return a
def cdf_at(c,i):
 ix=np.clip(i.astype(int),0,K-1)
 v=np.take_along_axis(c,ix,axis=1)
 return np.where(i<0,0,np.where(i>=K,1,v))
def implied(rate,line,ph,pa):
 h,a=rate;h=pmf(h);a=pmf(a).cumsum(1)
 w=np.zeros(len(line));l=w.copy()
 for cut in (np.floor(line*2+1e-8)/2,np.ceil(line*2-1e-8)/2):
  w+=(h*cdf_at(a,np.ceil(g+cut[:,None])-1)).sum(1)/2
  l+=(h*(1-cdf_at(a,np.floor(g+cut[:,None])))).sum(1)/2
 return w*(ph-1)-l,l*(pa-1)-w
line=np.array([r['end_line'] for r in A]);ph=np.array([r['home_price'] for r in A]);pa=np.array([r['away_price'] for r in A])
start=np.array([r['start_line'] for r in A])
def rates(lr):
 return tuple(np.array([S[r['fid']]['lambda_'+side+'_'+lr] for r in A]) for side in ('home','away'))
e1h,e1a=implied(rates('0.025'),line,ph,pa);e2h,e2a=implied(rates('0.06'),line,ph,pa)
def direction(x):return 'home' if x>1e-9 else 'away' if x<-1e-9 else 'flat'
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
def st(z,key):
 vals=[r[key] for r in z];n=len(vals);u=sum(vals)
 return {'n':n,'U':round(u,3),'ROI':round(u*100/n,3) if n else None}
def summary(z,key):
 return {p:st([r for r in z if era(r)==p],key) for p in ('2019-23','2024-25','2026')}|{'2026_H1':st([r for r in z if r['year']==2026 and r['month']<='2026-06'],key),'2026_H2':st([r for r in z if r['year']==2026 and r['month']>='2026-07'],key)}
G=collections.defaultdict(list)
for i,r in enumerate(A):
 side=direction(e1h[i]-e1a[i])
 if side=='flat':side='home'
 other='away' if side=='home' else 'home'
 r['ind_U']=r['end_'+side+'_U'];r['contra_U']=r['end_'+other+'_U'];r['expected']=max(e1h[i],e1a[i])
 r['prior_group']=prior.get((r['year'],r['fid']),(None,None))[0]
 if r['prior_group']:
  # Determine original candidate side from rules, not from realized P&L equality.
  g0=r['prior_group'];v=prior[(r['year'],r['fid'])][1]
  r['old_U']=v
  # E/F sign reconstruction via identity and price records is not needed here; compare base (dog) only.
  if g0=='base':
   dog='home' if r['end_line']>0 else 'away';G[('baseline_diagnostic','agree' if side==dog else 'disagree')].append(r)
  continue
 s2=direction(e2h[i]-e2a[i])
 market=direction(-(r['end_line']-r['start_line'])) if r['end_line']!=r['start_line'] else direction(r['away_price']/(r['home_price']+r['away_price'])-r['start_away_price']/(r['start_home_price']+r['start_away_price']))
 relation='flat' if market=='flat' else 'agree' if market==side else 'disagree'
 r['relation']=relation
 r['speed_agree']=side==s2
 G[('remaining_all',)].append(r)
 G[('market_relation',relation)].append(r)
 G[('shape_relation',r['path_shape'],relation)].append(r)
 G[('shape_relation_consensus',r['path_shape'],relation,'both' if r['speed_agree'] else 'different')].append(r)
 if r['path_shape']=='never_changed' and not r['end_zero']:
  G[('fixed_nonzero',relation)].append(r)
 if r['expected']>0:G[('positive_model_EV',relation)].append(r)
out={}
for k,z in sorted(G.items()):
 keys=['old_U'] if k[0]=='baseline_diagnostic' else ['ind_U','contra_U']
 ans={key:summary(z,key) for key in keys}
 out['|'.join(k)]=ans
 if k[0] in ('baseline_diagnostic','fixed_nonzero','market_relation','remaining_all','positive_model_EV'):print('CORE',k,ans,flush=True)
 for key,v in ans.items():
  if all(v[p]['ROI'] is not None and v[p]['ROI']>0 for p in ('2019-23','2024-25','2026')):print('EXPLORATORY_POSITIVE',k,key,v,flush=True)
print('ALL',len(A),'PRIOR',len(prior),'REMAIN',len(G[('remaining_all',)]),flush=True)
(P/'m8_score_market_divergence_full_AH_20261114.json').write_text(json.dumps({'groups':out,'total':len(A),'prior_n':len(prior),'scope':'Research only; independent score-based expectation and AH time direction (line first, otherwise normalized market price share); prior candidates kept intact; full historical 39101 samples'},ensure_ascii=False,indent=2))
