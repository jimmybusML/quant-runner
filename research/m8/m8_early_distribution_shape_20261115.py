import json,collections,math
from pathlib import Path
import numpy as np
from scipy.special import gammaln,xlogy,bdtr
from scipy.optimize import minimize_scalar
from scipy.stats import poisson,nbinom
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_distribution_calibration_20261115.py').read_text()
# Reuse inventory and validated quarter-line Poisson pricing helpers.
exec(s[:s.index('def goals_predict')])
def arr(z,k):return vec(z,k)
def score_logp(h,a,hg,ag):
 return xlogy(hg,h)-h-gammaln(hg+1)+xlogy(ag,a)-a-gammaln(ag+1)
def rho_effect(h,a,rho):
 # Bound each correction to the valid Dixon-Coles probability domain.
 return np.clip(rho,-.999/np.maximum(h,a),.999/np.maximum(1,h*a))
def dc_cell(h,a,hg,ag,rho):
 r=rho_effect(h,a,rho)
 return np.where((hg==0)&(ag==0),1-h*a*r,np.where((hg==0)&(ag==1),1+h*r,np.where((hg==1)&(ag==0),1+a*r,np.where((hg==1)&(ag==1),1-r,1.))))
def dc_fit(z):
 h,a,hg,ag=[arr(z,k) for k in ('mh','ma','hg','ag')]
 return float(minimize_scalar(lambda rho:-np.log(dc_cell(h,a,hg,ag,rho)).sum(),bounds=(-.5,.5),method='bounded').x)
def nb_fit(z):
 t=arr(z,'mh')+arr(z,'ma');n=arr(z,'hg')+arr(z,'ag')
 def loss(alpha):
  if alpha<1e-7:return -poisson.logpmf(n,t).sum()
  k=1/alpha;return -nbinom.logpmf(n,k,k/(k+t)).sum()
 opt=minimize_scalar(loss,bounds=(1e-6,1),method='bounded');return float(opt.x) if opt.fun<loss(0) else 0.
def bets(z,w,l,market):
 pa,pb,sa,sb=('ah','aa','home_U','away_U') if market=='AH' else ('oo','ou','over_U','under_U')
 ea=w*(arr(z,pa)-1)-l;eb=l*(arr(z,pb)-1)-w
 v=np.where(ea>=eb,arr(z,sa),arr(z,sb));return {'all':stat(v),'positive_EV_diagnostic':stat(v[np.maximum(ea,eb)>1e-9])}
def dc_wl(z,h,a,rho,market):
 t=h+a;f=h/t;line=arr(z,'al' if market=='AH' else 'ol')
 w,l=ah_wl(t,f,line) if market=='AH' else ou_wl(t,line)
 for hg,ag in ((0,0),(0,1),(1,0),(1,1)):
  delta=np.exp(score_logp(h,a,hg,ag))*(dc_cell(h,a,hg,ag,rho)-1)
  for q in halves(line):
   v=(hg-ag+q) if market=='AH' else (hg+ag-q)
   w+=delta*(v>0)/2;l+=delta*(v<0)/2
 return w,l
def nb_probs(z,h,a,alpha):
 t=h+a;f=h/t;al=arr(z,'al');ol=arr(z,'ol')
 # N=total; conditional home score Binomial(N,f). Fixed marginal means and shared rate variation.
 n=np.arange(151)[None,:]
 mass=nbinom.pmf(n,1/alpha,(1/alpha)/(1/alpha+t[:,None])) if alpha>1e-7 else poisson.pmf(n,t[:,None])
 assert np.max(1-mass.sum(1))<1e-6
 def bc(idx):
  ii=np.maximum(0,np.minimum(idx,n))
  return np.where(idx<0,0,np.where(idx>=n,1,bdtr(ii,n,f[:,None])))
 aw=np.zeros(len(z));aloss=aw.copy();ow=aw.copy();oloss=aw.copy()
 for q in halves(al):
  cut=(n-q[:,None])/2
  aw+=(mass*(1-bc(np.floor(cut)))).sum(1)/2
  aloss+=(mass*bc(np.ceil(cut)-1)).sum(1)/2
 for q in halves(ol):
  ow+=(mass*(n>q[:,None])).sum(1)/2;oloss+=(mass*(n<q[:,None])).sum(1)/2
 # exact draw, low totals, high totals
 matchdraw=(mass[:,::2]*np.exp(gammaln(n[:,::2]+1)-2*gammaln(n[:,::2]/2+1)+xlogy(n[:,::2]/2,f[:,None])+xlogy(n[:,::2]/2,1-f[:,None]))).sum(1)
 return aw,aloss,ow,oloss,matchdraw,mass[:,:2].sum(1),mass[:,5:].sum(1)
def eval_shape(z,typ,param):
 h,a,hg,ag=[arr(z,k) for k in ('mh','ma','hg','ag')];t=h+a
 p0=score_logp(h,a,hg,ag);draw=(pmf(h)*pmf(a)).sum(1);low=poisson.cdf(1,t);tail=poisson.sf(4,t)
 if typ=='base':
  nll=-p0;out={}
 elif typ=='DC':
  nll=-p0-np.log(dc_cell(h,a,hg,ag,param));r=rho_effect(h,a,param);delta=np.exp(-t)*h*a*r
  draw-=2*delta;low+=delta
  out={m:bets(z,*dc_wl(z,h,a,param,m),m) for m in ('AH','OU')}
 else:
  n=hg+ag;k=1/param if param>1e-7 else None
  nll=-p0+(poisson.logpmf(n,t)-nbinom.logpmf(n,k,k/(k+t))) if k else -p0
  aw,al,ow,ol,draw,low,tail=nb_probs(z,h,a,param)
  out={'AH':bets(z,aw,al,'AH'),'OU':bets(z,ow,ol,'OU')}
 out['NLL']=round(float(nll.mean()),7)
 out['distribution']={k:{'expected':round(float(p.mean()),6),'observed':round(float(o.mean()),6)} for k,p,o in [('draw',draw,hg==ag),('total_0_1',low,hg+ag<=1),('total_5plus',tail,hg+ag>=5)]}
 return out
out={}
for T in (24,12,6):
 z=[r for r in rows if r['T']==T];valid=[]
 for st in range(0,len(z),4000):
  v=z[st:st+4000];ol,al=arr(v,'ol'),arr(v,'al')
  op=arr(v,'ou')/(arr(v,'oo')+arr(v,'ou'));ap=arr(v,'aa')/(arr(v,'ah')+arr(v,'aa'))
  tot,ok1,er1=solve(op,.0001,20.,lambda x:ou_share(x,ol))
  fra,ok2,er2=solve(ap,.00001,.99999,lambda x:ah_share(tot,x,al))
  for i,r in enumerate(v):
   if ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5:
    r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]));valid.append(r)
 out[str(T)]={'valid':len(valid),'years':{}}
 for y in (2024,2025,2026):
  tr=[r for r in valid if r['year']<y];te=[r for r in valid if r['year']==y]
  rho,alpha=dc_fit(tr),nb_fit(tr)
  rec={'train_n':len(tr),'test_n':len(te),'rho':rho,'alpha':alpha,'base':eval_shape(te,'base',0),'DC':eval_shape(te,'DC',rho),'NB':eval_shape(te,'NB',alpha)}
  out[str(T)]['years'][str(y)]=rec
  print('RESULT',T,y,json.dumps(rec),flush=True)
(P/'m8_early_distribution_shape_20261115.json').write_text(json.dumps(out,indent=2))
