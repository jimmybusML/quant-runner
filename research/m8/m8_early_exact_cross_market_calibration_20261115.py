import json
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=list(map(json.loads,(P/'m8_early_exact_cross_market_consistency_20261115.jsonl').open()))
def feats(r,kind):
 l=r['line'];h=r['home_price'];a=r['away_price'];ah=np.log1p(r['age_AH_h']);x=np.log1p(r['age_1x2_h'])
 f=[1,l,abs(l),h,a,h-a,ah,l*(h-a)]
 if kind=='joint':f.extend([r['eh'],r['ea'],r['eh']-r['ea'],x,x-ah,(r['eh']-r['ea'])*(x-ah),l*(r['eh']-r['ea'])])
 return f
def stats(v):
 n=len(v);u=float(sum(v))
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
out={}
for t in (24,12,6):
 z=[r for r in rows if r['T']==t];out[str(t)]={}
 for y in (2024,2025,2026):
  tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y];out[str(t)][str(y)]={}
  for k in ('AH','joint'):
   X=np.array([feats(r,k) for r in tr]);Y=np.array([[r['home_U'],r['away_U']] for r in tr]);mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1;X=(X-mu)/sd
   reg=np.eye(X.shape[1])*100;reg[0,0]=0
   beta=np.linalg.solve(X.T@X+reg,X.T@Y)
   pred=((np.array([feats(r,k) for r in te])-mu)/sd)@beta
   v=np.where(pred[:,0]>=pred[:,1],[r['home_U'] for r in te],[r['away_U'] for r in te])
   out[str(t)][str(y)][k]={'all':stats(v),'positive_estimate_diagnostic':stats(v[pred.max(1)>0])}
  print(t,y,out[str(t)][str(y)],flush=True)
(P/'m8_early_exact_cross_market_calibration_20261115.json').write_text(json.dumps(out,indent=2))
