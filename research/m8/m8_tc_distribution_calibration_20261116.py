import json,datetime,collections,math,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_league_residual_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Compare mean-preserving dispersion changes to the existing Poisson model.
# Fit Conway-Maxwell-Poisson dispersion by previous-period likelihood.
# Finite numerical support 0..60 and bounds on optimizer are research numerics.
from scipy.optimize import minimize_scalar
K=np.arange(61,dtype=float);LF=np.array([math.lgamma(k+1) for k in K])
def cmp(mu,nu):
 mu=np.asarray(mu,dtype=float);lo=np.full(len(mu),-20.);hi=np.full(len(mu),20.)
 def mass(theta):
  a=theta[:,None]*K[None,:]-nu*LF[None,:]
  a-=a.max(axis=1)[:,None];a=np.exp(a);return a/a.sum(axis=1)[:,None]
 for i in range(32):
  mid=(lo+hi)/2;v=mass(mid)@K;lo=np.where(v<mu,mid,lo);hi=np.where(v>=mu,mid,hi)
 a=mass((lo+hi)/2)
 assert np.max(abs(a@K-mu))<1e-5
 return a
def fit_disp(yy,mu):
 yy=yy.astype(int)
 assert yy.max()<len(K)
 def loss(nu):
  a=cmp(mu,nu);return -np.log(np.maximum(a[np.arange(len(yy)),yy],1e-15)).sum()
 v=minimize_scalar(loss,bounds=(.4,2.5),method='bounded',options={'xatol':.002})
 return float(v.x)
def evalmass(q,pm,market):
 yy=vec(q,'hg')+vec(q,'ag');line=vec(q,'ol');c=pm.cumsum(axis=1)
 w=np.zeros(len(q));l=w.copy();bs=[];ll=[]
 for a in g['probstats'].__globals__['halves'](line):
  wi=1-c[np.arange(len(q)),np.floor(a).astype(int)]
  li=c[np.arange(len(q)),np.ceil(a).astype(int)-1];pi=np.maximum(0,1-wi-li)
  obs=np.column_stack([yy>a,yy==a,yy<a]);pr=np.column_stack([wi,pi,li])
  bs.append(((obs-pr)**2).sum(axis=1));ll.append(-np.log(np.maximum((pr*obs).sum(axis=1),1e-15)))
  w+=wi/2;l+=li/2
 eo=w*(vec(q,'oo')-1)-l;eu=l*(vec(q,'ou')-1)-w
 side=eo>=eu;pnl=np.where(side,vec(q,'over_U'),vec(q,'under_U'))
 d=collections.defaultdict(float)
 for r,u in zip(q,pnl):d[r['date']]+=float(u)
 a=b=dd=0.
 for _,u in sorted(d.items()):a+=u;b=max(a,b);dd=max(dd,b-a)
 return {**g['stat'](pnl),'daily_mdd':round(dd,3),'brier':round(float(np.mean(bs)),6),'logloss':round(float(np.mean(ll)),6),'over_n':int(side.sum()),'under_roi':g['stat'](pnl[~side])['ROI'],'over_roi':g['stat'](pnl[side])['ROI']}
def run(q,pr,market,h,meanmode,cache):
 mat=cmp(pr,1.);meta=[]
 keys=[r['date'][:7] if h=='month' else str(r['year']) for r in q]
 for key in sorted(set(keys)):
  cut=(datetime.date.fromisoformat(key+'-01')-datetime.timedelta(days=3)).isoformat() if h=='month' else key+'-01-01'
  for l in sorted(negative):
   mask=np.array([k==key and r['league']==l for k,r in zip(keys,q)])
   if not mask.any():continue
   tr=valid&(dates<cut)&(ls==l)
   if not tr.any():continue
   assert max(dates[tr])<min(r['date'] for r,b in zip(q,mask) if b)
   ck=(h,meanmode,key,l)
   if ck not in cache:
    mult=float(y[tr].sum()/p[tr].sum()) if meanmode=='both' else 1.
    nu=fit_disp(y[tr],p[tr]*mult);cache[ck]=(mult,nu,int(tr.sum()))
   mult,nu,n=cache[ck]
   mat[mask]=cmp(pr[mask]*mult,nu);meta.append({'period':key,'league':l,'n':n,'mean_multiplier':mult,'nu':nu})
 return mat,meta
def suite(q,pm,market):
 def sub(mask):
  return evalmass([r for r,b in zip(q,mask) if b],pm[mask],market[mask])
 return {'all':evalmass(q,pm,market),'year':{str(yr):sub(np.array([r['year']==yr for r in q])) for yr in sorted({r['year'] for r in q})},'league':{l:sub(np.array([r['league']==l for r in q])) for l in sorted({r['league'] for r in q})}}
out={'method':'R18 frozen B predictions, same outside-eight cohorts 4059 historical and 240 receipt. Mean-preserving CMP dispersion fit by likelihood on strictly earlier same-league historical outcomes, excluding 1393 receipt ids. Prior-year and prior-month; dispersion alone and joint mean correction; untouched four profitable R16 leagues. Numerical bounds .4..2.5, 0..60 support; research only. Results retrospective, no trading gates.', 'diagnostics':{},'models':{}}
for l in sorted(leagues):
 mask=ls==l;mu=p[mask];yy=y[mask]
 out['diagnostics'][l]={'n':int(mask.sum()),'mean_actual':float(yy.mean()),'mean_predict':float(mu.mean()),'pearson_dispersion':float(np.mean((yy-mu)**2/mu)),'variance_actual':float(yy.var()),'variance_expected':float(mu.mean()+mu.var()),'year':{str(yr):{'n':int(k.sum()),'pearson_dispersion':float(np.mean((y[k]-p[k])**2/p[k])),'bias':float(np.mean(p[k]-y[k]))} for yr in (2024,2025,2026) for k in [mask&np.array([r['year']==yr for r in t])]}}
 print('diag',l,out['diagnostics'][l],flush=True)
bp=cmp(p,1);br=cmp(rp,1)
out['models']['B']={'history':suite(t,bp,m),'receipt':suite(rt,br,rm)}
assert out['models']['B']['history']['all']['U']==4.465 and out['models']['B']['receipt']['all']['U']==-8.745
for h in ('year','month'):
 for mode in ('dispersion','both'):
  cache={};a,ah=run(t,p,m,h,mode,cache);b,bh=run(rt,rp,rm,h,mode,cache)
  v={'history':suite(t,a,m),'receipt':suite(rt,b,rm),'fits_history':ah,'fits_receipt':bh}
  out['models'][h+'_'+mode]=v
  print(h,mode,'H',v['history']['all'],'Y',[(k,x['ROI']) for k,x in v['history']['year'].items()],'L',[(k,x['ROI']) for k,x in v['history']['league'].items()],'R',v['receipt']['all'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_distribution_calibration_20261116.json').write_text(json.dumps(out,indent=2))
