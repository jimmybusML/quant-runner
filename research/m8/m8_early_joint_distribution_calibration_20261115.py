import json,collections,math
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=list(map(json.loads,(P/'m8_early_joint_market_inventory_20261115.jsonl').open()))
# Reuse exact quarter-line pricing math from prior latent pricing study, without old dataset or tests.
s=(P/'m8_cross_market_latent_pricing_20261114.py').read_text()
exec(s[s.index('K=40;'):s.index('for suffix,ahkey')])
def ah_wl(total,frac,line):
 h=pmf(total*frac);a=pmf(total*(1-frac)).cumsum(axis=1)
 w=np.zeros(len(total));l=w.copy()
 for q in halves(line):
  w+=(h*cdf_at(a,np.ceil(goals+q[:,None])-1)).sum(axis=1)/2
  l+=(h*(1-cdf_at(a,np.floor(goals+q[:,None])))).sum(axis=1)/2
 return w,l
def ou_wl(total,line):
 c=pmf(total).cumsum(axis=1);w=np.zeros(len(total));l=w.copy()
 for q in halves(line):
  w+=(1-cdf_at(c,np.floor(q)[:,None])[:,0])/2
  l+=cdf_at(c,(np.ceil(q)-1)[:,None])[:,0]/2
 return w,l
def vec(z,k):return np.array([r[k] for r in z],float)
def stat(v):
 n=len(v);u=float(v.sum())
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def goals_predict(X,y,offset,Xtest,offtest):
 # Penalized Poisson likelihood, IRLS with market implied rate as offset. Parameters experimental only.
 mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;Xt=(Xtest-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for i in range(20):
  u=np.exp(np.clip(offset+X@b,-7,5));step=np.linalg.solve(X.T@(u[:,None]*X)+pen,X.T@(y-u)-pen@b);b+=step
  if np.max(np.abs(step))<1e-7:break
 return np.exp(np.clip(offtest+Xt@b,-7,3))
def evaluate(z,h,a):
 total=h+a;frac=h/total
 out={'goal_logloss_without_factorial':round(float(np.mean(h-vec(z,'hg')*np.log(h)+a-vec(z,'ag')*np.log(a))),6),'goal_mae':round(float(np.mean(np.abs(total-vec(z,'hg')-vec(z,'ag')))),6)}
 for market,l,pa,pb,sa,sb in [('AH','al','ah','aa','home_U','away_U'),('OU','ol','oo','ou','over_U','under_U')]:
  w,l=ah_wl(total,frac,vec(z,l)) if market=='AH' else ou_wl(total,vec(z,l))
  ea=w*(vec(z,pa)-1)-l;eb=l*(vec(z,pb)-1)-w
  pnl=np.where(ea>=eb,vec(z,sa),vec(z,sb))
  out[market]={'all':stat(pnl),'positive_model_EV_diagnostic':stat(pnl[np.maximum(ea,eb)>1e-9])}
 return out
out={'method':'Crown AH and OU independent Poisson implied goal means; annual chronological Poisson likelihood correction, market offset; three alternative forecast models. Positive EV is research-only diagnostic, each AH/OU evaluated independently.','horizons':{}}
for T in (24,12,6):
 z=[r for r in rows if r['T']==T];valid=[]
 for st in range(0,len(z),4000):
  v=z[st:st+4000];ol,al=vec(v,'ol'),vec(v,'al')
  op=vec(v,'ou')/(vec(v,'oo')+vec(v,'ou'));ap=vec(v,'aa')/(vec(v,'ah')+vec(v,'aa'))
  tot,ok1,er1=solve(op,.0001,20.,lambda x:ou_share(x,ol))
  fra,ok2,er2=solve(ap,.00001,.99999,lambda x:ah_share(tot,x,al))
  for i,r in enumerate(v):
   if ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5:
    r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]));valid.append(r)
 print('LATENT',T,len(z),len(valid),flush=True)
 z=valid;leagues=sorted({r['league'] for r in z})
 def features(r,kind):
  h,a=r['mh'],r['ma'];f=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
  if kind in ('league','league_1X2'):
   f += [float(r['league']==l) for l in leagues]
  if kind=='league_1X2':
   p=r.get('p1x2',[0,0,0]);f += p+[float('p1x2' in r),np.log1p(r.get('age_1x2',0))]
  return f
 rec={'n':len(z),'year_counts':dict(collections.Counter(r['year'] for r in z)),'tests':{}}
 for y in (2024,2025,2026):
  tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y]
  if not tr or not te:continue
  h,a=vec(te,'mh'),vec(te,'ma');r={'market_implied':evaluate(te,h,a)}
  for kind in ('global','league','league_1X2'):
   X=np.array([features(x,kind) for x in tr]);Xt=np.array([features(x,kind) for x in te])
   ph=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(h))
   pa=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(a))
   r[kind]=evaluate(te,ph,pa)
  rec['tests'][str(y)]=r
  print('TEST',T,y,json.dumps(r),flush=True)
 out['horizons'][str(T)]=rec
(P/'m8_early_joint_distribution_calibration_20261115.json').write_text(json.dumps(out,indent=2))
