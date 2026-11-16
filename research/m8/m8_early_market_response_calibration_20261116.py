import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_latent_path_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
from scipy.special import expit
# Outcome calibration: model final market total and home share, then estimate
# incremental correction from observed pre-T12 market movement. No selection.
assert hv.all() and rv.all()
def state(x):
 t0,t1,d0,d1=x[:,:4].T
 f0=(1+d0/t0)/2;f1=(1+d1/t1)/2
 return np.log(t0),np.log(t1),np.log(f0/(1-f0)),np.log(f1/(1-f1))
def make_x(x,mode):
 a,b,c,d=state(x)
 if mode=='static':return np.column_stack([np.ones(len(x)),b,d])
 if mode=='response':return np.column_stack([np.ones(len(x)),b,d,b-a,d-c])
 raise ValueError(mode)
def fit_share(X,h,n,off,Xt,ot):
 mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 x=(X-mu)/sd;xt=(Xt-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for _ in range(30):
  f=expit(off+x@b);w=n*f*(1-f)
  step=np.linalg.solve(x.T@(w[:,None]*x)+pen,x.T@(h-n*f)-pen@b);b+=step
  if np.max(abs(step))<1e-8:break
 return expit(ot+xt@b),b/sd
def fit_total(X,y,off,Xt,ot):
 mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 x=(X-mu)/sd;xt=(Xt-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for _ in range(30):
  u=np.exp(np.clip(off+x@b,-7,5));step=np.linalg.solve(x.T@(u[:,None]*x)+pen,x.T@(y-u)-pen@b);b+=step
  if np.max(abs(step))<1e-8:break
 return np.exp(np.clip(ot+xt@b,-7,5)),b/sd
def rates(x):
 a,b,c,d=state(x)
 return np.exp(b),expit(d)
def evaluate(q,t,f,k):
 q=[a for a,b in zip(q,k) if b];t=t[k];f=f[k]
 h=vec(q,'hg');a=vec(q,'ag');tot=h+a
 ph=t*f;pa=t*(1-f)
 return {'n':len(q),'poisson_score':round(float(np.mean(ph-h*np.log(ph)+pa-a*np.log(pa))),6),'total_MAE':round(float(np.mean(abs(t-tot))),6),'margin_MAE':round(float(np.mean(abs(t*(2*f-1)-(h-a)))),6),'mean_total_bias':round(float(np.mean(t-tot)),6),'mean_margin_bias':round(float(np.mean(t*(2*f-1)-(h-a))),6)}
def pay(q,t,f,market):
 if market=='AH':
  w,l=g['ah_wl'](t,f,vec(q,'al'));o1,o2,u1,u2=map(lambda k:vec(q,k),('ah','aa','home_U','away_U'))
 else:
  w,l=g['ou_wl'](t,vec(q,'ol'));o1,o2,u1,u2=map(lambda k:vec(q,k),('oo','ou','over_U','under_U'))
 return np.where(w*(o1-1)-l>=l*(o2-1)-w,u1,u2)
def movement_stats(q,x,k):
 y=vec(q,'hg')+vec(q,'ag');d=vec(q,'hg')-vec(q,'ag')
 res={}
 for name,real,j,m in [('total',y,1,4),('margin',d,3,5)]:
  z={}
  for side,mask in [('down',x[:,m]<-1e-7),('flat',abs(x[:,m])<=1e-7),('up',x[:,m]>1e-7)]:
   mask=mask&k;err=real[mask]-x[mask,j]
   z[side]={'n':int(mask.sum()),'mean_change':round(float(x[mask,m].mean()),6),'actual_minus_T12':round(float(err.mean()),6),'T24_MAE':round(float(np.mean(abs(real[mask]-x[mask,j-1]))),6),'T12_MAE':round(float(np.mean(abs(err))),6)}
  res[name]=z
 return res
hyh=vec(H,'hg');hyn=hyh+vec(H,'ag')
hm=hm0&hv;rm=rm0&rv
out={'method':'R25 fixed R24 data, prior-year outcome calibration of market-implied total (Poisson) and home goal share (conditional binomial), static level vs static plus log-total/logit-share market changes. Same ridge100 experimental penalty, no tuning to returns. Market-implied uncalibrated reference is scored on outcomes only; its near-tied EV does not determine a trading side. All matched fixtures included, no outcome filtering; history and receipt separate, previously explored, not independent prospective.','motion':{'history':movement_stats(H,hx,hm),'receipt':movement_stats(R,rx,rm)},'models':{}}
print('MOTION',out['motion'],flush=True)
for mode in ('market_reference','static','response'):
 ht,hf=rates(hx);rt0,rf0=rates(rx);fits={}
 if mode!='market_reference':
  X=make_x(hx,mode);Z=make_x(rx,mode);a,b,c,d=state(hx);ra,rb0,rc,rd0=state(rx)
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
   assert HY[tr].max()<yr
   ht[te],bt=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te])
   hf[te],bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
   if re.any():
    rt0[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb0[re]);rf0[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd0[re])
   fits[str(yr)]={'train_n':int(tr.sum()),'total_coefficients':bt.tolist(),'share_coefficients':bf.tolist(),'update_multiplier_total':round(float(1+bt[-2]),6) if mode=='response' else None,'update_multiplier_share':round(float(1+bf[-1]),6) if mode=='response' else None}
 a={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt0,rf0,rm),'fit':fits,'markets':{}}
 if mode!='market_reference':
  for market in ('AH','OU'):
   p=pay(H,ht,hf,market);r=pay(R,rt0,rf0,market)
   a['markets'][market]={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'years':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)}}
 out['models'][mode]=a
 print(mode,'Hprob',a['history_probability'],'Rprob',a['receipt_probability'],'fit',fits,'markets',{k:{'H':slim(v['history']),'R':slim(v['receipt']),'Y':{y:slim(j) for y,j in v['years'].items()}} for k,v in a['markets'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_early_market_response_calibration_20261116.json').write_text(json.dumps(out,indent=2))
