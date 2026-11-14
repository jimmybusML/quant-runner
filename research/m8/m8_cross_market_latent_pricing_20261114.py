import json,math,collections
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
R=[json.loads(l) for l in (P/'m8_cross_market_aligned_20261114.jsonl').open()]
K=40; goals=np.arange(K)[None,:]
def pmf(lam):
 a=np.empty((len(lam),K),float);a[:,0]=np.exp(-lam)
 for k in range(1,K):a[:,k]=a[:,k-1]*lam/k
 return a
def cdf_at(c,i):
 ix=np.clip(i.astype(int),0,K-1)
 val=np.take_along_axis(c,ix,axis=1)
 return np.where(i<0,0,np.where(i>=K,1,val))
def halves(l):return np.floor(l*2+1e-8)/2,np.ceil(l*2-1e-8)/2
def ou_share(lam,line):
 c=pmf(lam).cumsum(axis=1);W=np.zeros(len(lam));L=W.copy()
 for l in halves(line):
  W+=1-cdf_at(c,np.floor(l)[:,None])[:,0];L+=cdf_at(c,(np.ceil(l)-1)[:,None])[:,0]
 return W/np.maximum(W+L,1e-12)
def ah_share(total,frac,line):
 h=pmf(total*frac);a=pmf(total*(1-frac)).cumsum(axis=1)
 W=np.zeros(len(total));L=W.copy()
 for l in halves(line):
  W+=(h*cdf_at(a,np.ceil(goals+l[:,None])-1)).sum(axis=1)
  L+=(h*(1-cdf_at(a,np.floor(goals+l[:,None])))).sum(axis=1)
 return W/np.maximum(W+L,1e-12)
def solve(target,lo,hi,fun):
 lo=np.full(len(target),lo);hi=np.full(len(target),hi)
 valid=(fun(lo)<=target+1e-7)&(fun(hi)>=target-1e-7)
 for k in range(25):
  m=(lo+hi)/2;v=fun(m);lt=v<target
  lo=np.where(lt,m,lo);hi=np.where(lt,hi,m)
 est=(lo+hi)/2
 return est,valid,np.abs(fun(est)-target)
for suffix,ahkey in [('0','start_line'),('1','end_line')]:
 ol=np.array([r['OU_l'+suffix] for r in R]);op=np.array([r['OU_p'+suffix] for r in R])
 al=np.array([r[ahkey] for r in R]);ap=np.array([r['AH_p'+suffix] for r in R])
 total,ok1,err1=solve(op,.0001,20.,lambda x:ou_share(x,ol))
 fraction,ok2,err2=solve(ap,.00001,.99999,lambda x:ah_share(total,x,al))
 ok=ok1&ok2&(err1<1e-5)&(err2<1e-5)
 for i,r in enumerate(R):
  r['latent_valid_'+suffix]=bool(ok[i]);r['latent_total_'+suffix]=float(total[i]);r['latent_margin_'+suffix]=float(total[i]*(2*fraction[i]-1))
 print('PRICING_FIT',suffix,'valid',int(ok.sum()),'all',len(R),'max_accepted_error',float(max(err1[ok].max(),err2[ok].max())),flush=True)
# Comparative regressions: identical matched population; research-only penalty=100.
def part(r):return '2025' if r['year']==2025 else 'H1' if r['month']<='2026-06' else 'H2'
def stat(v):
 n=len(v);u=float(sum(v));return {'n':n,'U':round(u,3),'ROI':round(u/n*100,3) if n else None}
def feature(r,kind):
 a0,a3,a1=[r['AH_p'+k] for k in ('0','3','1')];l0,l1=r['start_line'],r['end_line']
 f=[1,l0,l1,abs(l1),l1-l0,a0,a3,a1,a1-a0,a3-a0,a1-a3,(a1-a0)*l1,r['home_price'],r['away_price'],r['line_range'],math.log1p(r['n_line_changes']),math.log1p(r['n_events']),r['end_zero']]
 if kind!='AH':
  u0,u3,u1=[r['OU_l'+k] for k in ('0','3','1')];o0,o3,o1=[r['OU_p'+k] for k in ('0','3','1')]
  f.extend([u0,u3,u1,u1-u0,u3-u0,u1-u3,o0,o3,o1,o1-o0,o3-o0,o1-o3,r['OU_over_odds'],r['OU_under_odds'],l1*u1,(l1-l0)*(u1-u0),(a1-a0)*(o1-o0),l1*(u1-u0),l1*(o1-o0)])
 if kind=='AH_OU_latent':
  t0,t1=r['latent_total_0'],r['latent_total_1'];m0,m1=r['latent_margin_0'],r['latent_margin_1']
  dt=t1-t0;dm=m1-m0
  f.extend([t0,t1,m0,m1,dt,dm,m1*dt,m1*dm,dt*dm,dt**2,dm**2,abs(m1)-abs(m0)])
 return f
def evaluate(tr,te,kind):
 x=np.array([feature(r,kind) for r in tr]);y=np.array([[r['end_home_U'],r['end_away_U']] for r in tr]);mu=x.mean(0);sd=x.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 x=(x-mu)/sd;reg=np.eye(x.shape[1])*100;reg[0,0]=0
 b=np.linalg.solve(x.T@x+reg,x.T@y);p=((np.array([feature(r,kind) for r in te])-mu)/sd)@b
 v=np.where(p[:,0]>=p[:,1],[r['end_home_U'] for r in te],[r['end_away_U'] for r in te])
 return {'all':stat(v),'positive_estimate_comparison':stat(v[p.max(1)>0]),'train_n':len(tr)}
L=[r for r in R if not r['prior'] and r['latent_valid_0'] and r['latent_valid_1']]
res={'pricing':'Independent Poisson pricing translation: remove vig using normalized reciprocal prices; solve OU for total and AH conditional win stake share for home goal fraction, quarter lines split into adjacent half lines. Not actual forecast probability; model approximation, no new production rule.','coverage_by_period':dict(collections.Counter(part(r) for r in L)),'all_joint_remaining':sum(not r['prior'] for r in R),'models':{},'groups':{}}
for target in ('H1','H2'):
 tr=[r for r in L if part(r)=='2025' or (target=='H2' and part(r)=='H1')];te=[r for r in L if part(r)==target]
 res['models'][target]={k:evaluate(tr,te,k) for k in ('AH','AH_OU','AH_OU_latent')}
 print('LATENT_MODEL',target,res['models'][target],flush=True)
# Show all price-implied scoring translation group comparisons on AH unchanged fixtures.
g=collections.defaultdict(list)
for r in L:
 if r['path_shape']!='never_changed' or r['end_zero']:continue
 z=lambda x:'up' if x>1e-6 else 'down' if x<-1e-6 else 'flat'
 dt=r['latent_total_1']-r['latent_total_0'];dm=(r['latent_margin_1']-r['latent_margin_0'])*(-1 if r['end_line']>0 else 1)
 g[(z(dt),z(dm))].append(r)
for k,rs in sorted(g.items()):
 r={side:{p:stat([x[side] for x in rs if part(x)==p]) for p in ('2025','H1','H2')}|{'2026':stat([x[side] for x in rs if x['year']==2026])} for side in ('end_dog_U','end_fav_U')}
 res['groups']['|'.join(k)]=r
 print('LATENT_GROUP',k,r,flush=True)
(P/'m8_cross_market_latent_pricing_20261114.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
