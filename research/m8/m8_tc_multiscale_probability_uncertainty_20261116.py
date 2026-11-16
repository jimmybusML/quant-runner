import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_multiscale_research_20261116.py').read_text()
exec(s[:s.index("out={'method'")])
pg=g['probstats'].__globals__
def individual(z,t):
 y=vec(z,'hg')+vec(z,'ag');line=vec(z,'ol');c=pg['pmf'](t).cumsum(axis=1);out=[]
 for q in pg['halves'](line):
  w=1-pg['cdf_at'](c,np.floor(q)[:,None])[:,0];l=pg['cdf_at'](c,(np.ceil(q)-1)[:,None])[:,0];p=np.maximum(0,1-w-l)
  out.append(((np.column_stack([w,p,l])-np.column_stack([y>q,y==q,y<q]))**2).sum(1))
 return np.mean(out,axis=0)
def paired(z,p,q):
 a=individual(z,p)-individual(z,q)
 # Resample calendar weeks as blocks to retain within-week dependence; descriptive intervals, unadjusted for multiple variants.
 keys=[datetime.date.fromisoformat(r['date']).isocalendar()[:2] for r in z]
 b=sorted(set(keys)); where={k:i for i,k in enumerate(b)};j=np.array([where[k] for k in keys])
 sums=np.bincount(j,weights=a);sizes=np.bincount(j);rng=np.random.default_rng(20261116)
 k=rng.integers(0,len(b),size=(5000,len(b)))
 samples=sums[k].sum(1)/sizes[k].sum(1)
 return {'n':len(z),'weeks':len(b),'mean_delta':round(float(a.mean()),6),'interval95':[round(float(x),6) for x in np.quantile(samples,[.025,.975])]}
out={}
for name,zz,ff,market in [('historical',z,ZF,mz),('receipt',ex,RF,mr)]:
 base=run(zz,ff,'baseline');out[name]={}
 for kind in ('level_plus_drift','drift_only','shot_level_drift'):
  p=run(zz,ff,kind)
  out[name][kind]={'vs_180':paired(zz,p,base),'vs_market':paired(zz,p,market)}
(P/'m8_tc_multiscale_probability_uncertainty_20261116.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
