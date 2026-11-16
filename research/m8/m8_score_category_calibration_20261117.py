import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
from scipy.optimize import minimize
from scipy.special import logsumexp
# Natural score categories. Signed goal difference: -2 or fewer,-1,0,+1,+2 or more;
# total goals: 0,1,2,3,4,5 or more. Prior-year frequency likelihood, not ROI tuning.
gg=np.arange(40);dif=gg[:,None]-gg[None,:];tot=gg[:,None]+gg[None,:]
mg=np.clip(dif,-2,2)+2;tg=np.minimum(tot,5)
cell=(mg*6+tg).ravel()
C=np.eye(30)[cell]
D=np.column_stack((np.eye(5)[np.arange(30)//6][:,1:],np.eye(6)[np.arange(30)%6][:,1:]))
def build(q,t,f):
 M=np.zeros((len(q),30));W=np.zeros((len(q),30,4))
 for lo in range(0,len(q),400):
  hi=min(lo+400,len(q));a=t[lo:hi];b=f[lo:hi];z=q[lo:hi];n=len(z)
  h=g['pmf'](a*b);aw=g['pmf'](a*(1-b));p=h[:,:,None]*aw[:,None,:]
  p=p.reshape(n,-1);M[lo:hi]=p@C
  for j,(fkey,sign) in enumerate((('al',1),('ol',-1))):
   l=vec(z,fkey);val=(dif if j==0 else tot)[None,:,:];w=np.zeros((n,40,40));loss=w.copy()
   for ln in (np.floor(l*2+1e-8)/2,np.ceil(l*2-1e-8)/2):
    m0=val+sign*ln[:,None,None];w+=(m0>0)/2;loss+=(m0<0)/2
   W[lo:hi,:,2*j]=(p*w.reshape(n,-1))@C;W[lo:hi,:,2*j+1]=(p*loss.reshape(n,-1))@C
 assert np.max(abs(M.sum(1)-1))<1e-7
 obs=(np.clip(vec(q,'hg')-vec(q,'ag'),-2,2).astype(int)+2)*6+np.minimum(vec(q,'hg')+vec(q,'ag'),5).astype(int)
 assert np.all(M[np.arange(len(q)),obs]>0)
 return M,W,obs
def fit(M,obs,d):
 # Multinomial exponential tilt on grouped probability, fixed mild L2 regularization
 # inherited 100; category effects fitted to outcomes, not returns.
 lm=np.log(np.maximum(M,1e-300));target=d[obs].sum(0)
 def fn(b):
  a=lm+d@b;p=np.exp(a-logsumexp(a,axis=1,keepdims=True))
  return float(logsumexp(a,axis=1).sum()-(lm[np.arange(len(obs)),obs]).sum()-target@b+50*(b@b)),(p.sum(0)@d-target+100*b)
 opt=minimize(fn,np.zeros(d.shape[1]),jac=True,method='L-BFGS-B',options={'maxiter':300,'ftol':1e-12})
 assert opt.success,opt.message
 return opt.x
def stats(q,M,obs,mask):
 m=M[mask];o=obs[mask]
 result={'n':int(mask.sum()),'category_NLL':round(float(-np.log(m[np.arange(len(o)),o]).mean()),7),'categories':{}}
 for k,ind in [('draw',np.arange(30)//6==2),('one_goal_margin',np.isin(np.arange(30)//6,[1,3])),('two_plus_margin',np.isin(np.arange(30)//6,[0,4])),('total_0_1',np.arange(30)%6<=1),('total_2_3',np.isin(np.arange(30)%6,[2,3])),('total_4plus',np.arange(30)%6>=4)]:
  result['categories'][k]={'estimated_pct':round(float(m[:,ind].sum(1).mean()*100),3),'observed_pct':round(float(ind[o].mean()*100),3)}
 return result
ht,hf=rates(hx);rt,rf0=rates(rx)
HM,HW,ho=build(H,ht,hf);RM,RW,robs=build(R,rt,rf0)
hm=hm0&hv;rm=rm0&rv
out={'method':'R38 separate natural signed score-margin and total-goals categorical calibration, exponential tilt of full market-implied Poisson grid, prior-calendar-year likelihood only, ridge100 experimental regularization; same R25 T12 paired cohort, exclude all receipt FIDs from fit; both markets separate, every matched fixture for learned models, no new formal threshold. Uncalibrated near-tied market reference probability only. Historical and actual receipt replay distinct, previously explored not independent forward.','coverage':{'historical_full':len(H),'receipt_full':len(R),'historical_incremental':int(hm.sum()),'receipt_incremental':int(rm.sum())},'models':{}}
out['models']['reference']={'history':stats(H,HM,ho,hm),'receipt':stats(R,RM,robs,rm)}
print('REF',out['models']['reference'],flush=True)
for kind,d in [('margin',D[:,:4]),('total',D[:,4:]),('joint',D)]:
 hp=HM.copy();rp=RM.copy();hwl=np.zeros((len(H),4));rwl=np.zeros((len(R),4));fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
  b=fit(HM[tr],ho[tr],d);w=np.exp(d@b)
  for M,W,mask,pred,wl in ((HM,HW,te,hp,hwl),(RM,RW,re,rp,rwl)):
   den=M[mask]@w;pred[mask]=M[mask]*w/den[:,None];wl[mask]=np.einsum('nck,c->nk',W[mask],w)/den[:,None]
  fits[str(yr)]={'train_n':int(tr.sum()),'coefficients':b.tolist()}
 a={'history':stats(H,hp,ho,hm),'receipt':stats(R,rp,robs,rm),'fits':fits,'markets':{}}
 for j,(market,o1,o2,u1,u2) in enumerate((('AH','ah','aa','home_U','away_U'),('OU','oo','ou','over_U','under_U'))):
  def payout(q,wl):
   w,l=wl[:,2*j:2*j+2].T
   return np.where(w*(vec(q,o1)-1)-l>=l*(vec(q,o2)-1)-w,vec(q,u1),vec(q,u2))
  p=payout(H,hwl);r=payout(R,rwl)
  a['markets'][market]={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)}}
 out['models'][kind]=a
 print('RESULT',kind,'H',a['history'],'R',a['receipt'],'markets',{k:{'H':slim(v['history']),'R':slim(v['receipt']),'years':{y:slim(x) for y,x in v['years'].items()}} for k,v in a['markets'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_score_category_calibration_20261117.json').write_text(json.dumps(out,indent=2))
