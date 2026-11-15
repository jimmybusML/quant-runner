import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_espn_ou_league_calibration_20261115.py').read_text()
exec(src[:src.index("out={'history_n'")])
def pos(z):
 return np.array([1. if r['league']=='1' else -1. if r['league']=='14' else 0. for r in z])
def fit(tr,te,kind,mode,variant):
 X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
 mu=X.mean(0);sd=X.std(0);mu[0]=0.;sd[0]=1.;sd[sd<1e-10]=1.
 X=(X-mu)/sd;Xt=(Xt-mu)/sd
 pen=np.full(X.shape[1],100.);pen[0]=0.
 if variant!='shared':
  # One contrast between the two leagues. Intercept or full deviation with shrinkage.
  p=100. if variant=='intercept' else float(variant.split('_')[1])
  I=X[:,:1] if variant=='intercept' else X
  It=Xt[:,:1] if variant=='intercept' else Xt
  X=np.column_stack([X,I*pos(tr)[:,None]]);Xt=np.column_stack([Xt,It*pos(te)[:,None]])
  pen=np.r_[pen,np.full(I.shape[1],p)]
 def reg(y,offset,offtest):
  b=np.zeros(X.shape[1]);D=np.diag(pen)
  for i in range(30):
   w=np.exp(np.clip(offset+X@b,-7,5))
   step=np.linalg.solve(X.T@(w[:,None]*X)+D,X.T@(y-w)-D@b)
   b+=step
   if np.max(np.abs(step))<1e-7:break
  return np.exp(np.clip(offtest+Xt@b,-7,3))
 if mode=='total':
  total=reg(vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),np.log(vec(te,'mh')+vec(te,'ma')))
 else:
  total=reg(vec(tr,'hg'),np.log(vec(tr,'mh')),np.log(vec(te,'mh')))+reg(vec(tr,'ag'),np.log(vec(tr,'ma')),np.log(vec(te,'ma')))
 w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 pnl=np.where(eo>=eu,vec(te,'over_U'),vec(te,'under_U'))
 return {'pnl':pnl,'ev':np.maximum(eo,eu),'total':total}
def nll(te,p):
 y=vec(te,'hg')+vec(te,'ag');x=p['total']
 return float(np.mean(x-y*np.log(x)))
variants=('shared','intercept','partial_100','partial_500','partial_2000')
out={'notes':'Nested chronological validation chooses shared/league intercept/full shrunken deviations by prior-year total goals Poisson NLL, not test ROI. Penalties are experimental, not formal trading rules. Each model tested on same two-league annual sample.','years':{}}
z=[r for r in valid if r['league'] in ('1','14')]
for y in (2024,2025,2026):
 train=[r for r in z if r['year']<y];test=[r for r in z if r['year']==y]
 dev=[r for r in z if r['year']<y-1];val=[r for r in z if r['year']==y-1]
 groups={'all':np.ones(len(test),bool),'1':pos(test)==1,'14':pos(test)==-1,'H1':np.array([int(r['date'][5:7])<=6 for r in test])};groups['H2']=~groups['H1']
 rec={'train_n':len(train),'test_n':len(test),'models':{}}
 for kind in ('market','market_performance'):
  for mode in ('total','separate'):
   scores={v:nll(val,fit(dev,val,kind,mode,v)) for v in variants}
   picked=min(scores,key=scores.get)
   r={'validation_n':len(val),'validation_NLL':scores,'picked':picked,'models':{}}
   for v in variants:
    p=fit(train,test,kind,mode,v)
    r['models'][v]={'NLL':nll(test,p),'groups':{g:assess(test,p,m) for g,m in groups.items()}}
   rec['models'][kind+'_'+mode]=r
   print('YEAR',y,kind,mode,'picked',picked,'results', {v:r['models'][v]['groups']['all']['all'] for v in variants},'picked_H2',r['models'][picked]['groups']['H2']['all'],flush=True)
 out['years'][str(y)]=rec
(P/'m8_espn_ou_partial_pooling_20261115.json').write_text(json.dumps(out,indent=2))
