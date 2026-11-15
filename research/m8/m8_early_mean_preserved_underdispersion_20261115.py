import json,math
from pathlib import Path
import numpy as np
from scipy.special import gammaln,bdtr,logsumexp,xlogy
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_distribution_shape_20261115.py').read_text()
exec(s[:s.index('out={}\nfor T in')])
# T12 as a practical early-time research comparison; no production constraint.
z=[r for r in rows if r['T']==12];valid=[]
for st in range(0,len(z),4000):
 v=z[st:st+4000];ol,al=arr(v,'ol'),arr(v,'al')
 op=arr(v,'ou')/(arr(v,'oo')+arr(v,'ou'));ap=arr(v,'aa')/(arr(v,'ah')+arr(v,'aa'))
 tot,ok1,er1=solve(op,.0001,20.,lambda x:ou_share(x,ol))
 fra,ok2,er2=solve(ap,.00001,.99999,lambda x:ah_share(tot,x,al))
 for i,r in enumerate(v):
  if ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5:
   r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]));valid.append(r)
assert len(valid)==41059
# Conway-Maxwell-Poisson total, parameterized by the unchanged mean.
# nu > 1 underdispersed. Grid is a numerical research comparison, no eligibility filter.
n=np.arange(50)[None,:];fac=gammaln(n+1)
t=arr(valid,'mh')+arr(valid,'ma');obs=(arr(valid,'hg')+arr(valid,'ag')).astype(int)
assert obs.max()<50
def cmp(mean,nu):
 loglam=nu*np.log(mean)
 for i in range(20):
  v=loglam[:,None]*n-nu*fac
  p=np.exp(v-logsumexp(v,axis=1,keepdims=True))
  m=(p*n).sum(1);variance=(p*(n-m[:,None])**2).sum(1)
  diff=np.clip((mean-m)/np.maximum(variance,1e-9),-1,1);loglam+=diff
  if np.abs(mean-m).max()<1e-8:break
 v=loglam[:,None]*n-nu*fac;lp=v-logsumexp(v,axis=1,keepdims=True);p=np.exp(lp)
 assert np.max(np.abs((p*n).sum(1)-mean))<1e-6
 return lp,p
def evaluate(z,p,lp):
 h=arr(z,'mh');a=arr(z,'ma');t=h+a;f=h/t;hg=arr(z,'hg');ag=arr(z,'ag');obs=(hg+ag).astype(int)
 al=arr(z,'al');ol=arr(z,'ol')
 aw=np.zeros(len(z));aloss=aw.copy();ow=aw.copy();oloss=aw.copy()
 def bc(i):
  return np.where(i<0,0,np.where(i>=n,1,bdtr(np.clip(i,0,n),n,f[:,None])))
 for q in halves(al):
  cut=(n-q[:,None])/2;aw+=(p*(1-bc(np.floor(cut)))).sum(1)/2;aloss+=(p*bc(np.ceil(cut)-1)).sum(1)/2
 for q in halves(ol):
  ow+=(p*(n>q[:,None])).sum(1)/2;oloss+=(p*(n<q[:,None])).sum(1)/2
 scorelog=lp[np.arange(len(z)),obs]+gammaln(obs+1)-gammaln(hg+1)-gammaln(ag+1)+xlogy(hg,f)+xlogy(ag,1-f)
 return {'AH':bets(z,aw,aloss,'AH'),'OU':bets(z,ow,oloss,'OU'),'NLL':round(float(-scorelog.mean()),7),'expected_tail':round(float(p[:,5:].sum(1).mean()),6),'observed_tail':round(float((obs>=5).mean()),6)}
grid=[1,1.025,1.05,1.1,1.2,1.35,1.5]
years=np.array([r['year'] for r in valid])
training={}
for nu in grid:
 lp,p=cmp(t,nu);ll=lp[np.arange(len(valid)),obs]
 training[nu]={str(y):float(-ll[years<y].mean()) for y in (2024,2025,2026)}
 print('FIT',nu,training[nu],flush=True)
out={'T':12,'training_NLL':training,'tests':{}}
for y in (2024,2025,2026):
 nu=min(grid,key=lambda v:training[v][str(y)])
 te=[r for r in valid if r['year']==y];mean=t[years==y]
 lp,p=cmp(mean,nu);lp0,p0=cmp(mean,1)
 res={'nu':nu,'n':len(te),'base':evaluate(te,p0,lp0),'CMP':evaluate(te,p,lp)}
 out['tests'][str(y)]=res;print('CMP',y,json.dumps(res),flush=True)
(P/'m8_early_mean_preserved_underdispersion_20261115.json').write_text(json.dumps(out,indent=2))
