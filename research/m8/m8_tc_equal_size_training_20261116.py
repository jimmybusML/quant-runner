import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_same_source_training_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
out={'method':'Diagnostic equal-size subsampling: draw 12 seeded subsets from the deduplicated mixed annual training pool, each the exact size of full ESPN training. Same earlier-year data availability and test features; sample size controlled but league and source composition differ. No tuning or selection of winning seeds.','seeds':list(range(12)),'models':{}}
for kind in ('baseline','shot_level_drift'):
 EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind)
 results=[]
 for seed in out['seeds']:
  hp=np.empty(len(zz));rp=np.empty(len(rr));counts={}
  for y in (2024,2025,2026):
   e=[r for r in train if r['year']<y];c=[r for r in z if r['year']<y];seen={r['fid'] for r in c}
   ee=[r for r in e if r['fid'] not in seen];pool=c+ee
   X=np.asarray([CA[r['fid']] for r in c]+[EA[r['fid']] for r in ee])
   ix=np.sort(np.random.default_rng(seed+100*y).choice(len(pool),len(e),replace=False))
   tr=[pool[i] for i in ix];mask=np.array([r['year']==y for r in zz]);te=[r for r,m in zip(zz,mask) if m]
   xt=matrix(te,ZF,kind)
   if y==2026:xt=np.vstack([xt,matrix(rr,RF,kind)])
   p=fitmat(tr,X[ix],te+rr if y==2026 else te,xt);hp[mask]=p[:len(te)]
   if y==2026:rp[:]=p[len(te):]
   counts[str(y)]={'n':len(tr),'TC_n':int((ix<len(c)).sum())}
  yr={}
  for y in (2024,2025,2026):
   m=np.array([r['year']==y for r in zz]);yr[str(y)]=summarize([r for r,b in zip(zz,m) if b],hp[m],mz[m])
  results.append({'seed':seed,'history':summarize(zz,hp,mz),'receipt':summarize(rr,rp,mr),'year':yr,'train_counts':counts})
 def stat(a):
  return {k:{'mean':round(float(np.mean([b[k] for b in a])),6),'min':round(float(min(b[k] for b in a)),6),'max':round(float(max(b[k] for b in a)),6)} for k in ('ROI','brier','U')}
 out['models'][kind]={'results':results,'history':stat([r['history'] for r in results]),'receipt':stat([r['receipt'] for r in results]),'year':{str(y):stat([r['year'][str(y)] for r in results]) for y in (2024,2025,2026)}}
 print(kind,json.dumps({k:v for k,v in out['models'][kind].items() if k!='results'}),flush=True)
(P/'m8_tc_equal_size_training_20261116.json').write_text(json.dumps(out,indent=2))
