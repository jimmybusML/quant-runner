import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_recency_research_20261116.py').read_text()
exec(s[:s.index('specs=')])
# Test separate recent deviations from long-term level; no outcome-based trade filter.
# Matched effective mass keeps strength of shrinkage equal across horizons.
def matrix(z,FF,kind):
 base=np.array([g['base'](r,FF['180'],'full_shot_efficiency') for r in z])
 if kind=='baseline':return base
 if kind=='market_only':return base[:,:8]
 short=np.array([g['base'](r,FF['30'],'full_shot_efficiency') for r in z])[:,8:]
 long=base[:,8:]
 drift=short-long
 if kind=='drift_only':return np.column_stack((base[:,:8],drift))
 if kind=='level_plus_drift':return np.column_stack((base,drift))
 # Market-centered level + recent-vs-long difference for shot volume and shot accuracy only.
 if kind=='shot_level_drift':
  # four role blocks 5 columns each, followed by 8 efficiency columns
  js=[i*5+j for i in range(4) for j in (0,1)]+list(range(20,28))
  return np.column_stack((base[:,:8],long[:,js],drift[:,js]))
 raise ValueError(kind)
def fset(h):return {k:features(h,v,True)[0] for k,v in [('180',180),('30',30)]}
TF=fset(trh);ZF=fset(zh);RF=fset(rh)
def run(z,FF,kind):
 a=np.zeros(len(z))
 for y in sorted({r['year'] for r in z}):
  mask=np.array([r['year']==y for r in z]);te=[r for r,m in zip(z,mask) if m];tr=[r for r in train if r['year']<y]
  X=matrix(tr,TF,kind);Xt=matrix(te,FF,kind)
  a[mask]=g['goals_predict'](X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
 return a
mz=vec(z,'mh')+vec(z,'ma');mr=vec(ex,'mh')+vec(ex,'ma')
unique=np.array([r['fid'] not in {q['fid'] for q in rows} for r in z])
out={'method':'Experimental level/short-term drift decomposition; 30/180 day weights, equal mass, prior-year ESPN training, same fixed TC test targets and settlement. No production change or trading filter. Historical and receipt results separate.','models':{}}
for k in ('baseline','market_only','level_plus_drift','drift_only','shot_level_drift'):
 p=run(z,ZF,k);q=run(ex,RF,k)
 def sub(m):return summarize([r for r,b in zip(z,m) if b],p[m],mz[m])
 out['models'][k]={'historical_all':summarize(z,p,mz),'historical_disjoint':sub(unique),'year':{str(y):sub(np.array([r['year']==y for r in z])) for y in sorted({r['year'] for r in z})},'receipt':summarize(ex,q,mr)}
 print(k,json.dumps(out['models'][k]),flush=True)
assert out['models']['baseline']['historical_all']['U']==-13.82
assert out['models']['baseline']['receipt']['U']==-8.54
(P/'m8_tc_multiscale_research_20261116.json').write_text(json.dumps(out,indent=2))
