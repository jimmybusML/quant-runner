import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_same_source_training_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Two candidates preserved from R13/R14, fixed recipes; no return-optimized blend.
A,an=run_mode('baseline','mixed',zz,ZF);AR,_=run_mode('baseline','mixed',rr,RF)
kind='shot_level_drift';EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind)
B=np.zeros(len(zz));BR=np.zeros(len(rr))
for y in (2024,2025,2026):
 e=[r for r in train if r['year']<y];seen={r['fid'] for r in e};c=[r for r in z if r['year']<y and r['fid'] not in seen]
 for l in sorted({r['league'] for r in zz if r['year']==y}):
  a=[r for r in c if r['league']==l];tr=e+a;X=np.asarray([EA[r['fid']] for r in e]+[CA[r['fid']] for r in a])
  mh=np.array([r['year']==y and r['league']==l for r in zz]);mr0=np.array([r['year']==y and r['league']==l for r in rr])
  te=[r for r,m in zip(zz,mh) if m];rt=[r for r,m in zip(rr,mr0) if m];xt=matrix(te,ZF,kind)
  if rt:xt=np.vstack([xt,matrix(rt,RF,kind)])
  p=fitmat(tr,X,te+rt,xt);B[mh]=p[:len(te)];BR[mr0]=p[len(te):]
def assess(z,t,m):
 x=summarize(z,t,m);p=g['make_pred'](z,t);daily=collections.defaultdict(float)
 for r,v in zip(z,p[2]):daily[r['date']]+=float(v)
 c=peak=dd=0.
 for d,u in sorted(daily.items()):c+=u;peak=max(peak,c);dd=max(dd,peak-c)
 x['daily_mdd']=round(dd,3);return x
def suite(h,r):
 def hs(m):return assess([r for r,b in zip(zz,m) if b],h[m],mz[m])
 return {'history':assess(zz,h,mz),'receipt':assess(rr,r,mr),'disjoint':hs(unique),'year':{str(y):hs(np.array([t['year']==y for t in zz])) for y in (2024,2025,2026)}}
out={'method':'Two preexisting candidates, mixed baseline R13 and local-add shot R14, fixed equal arithmetic mean of predicted total rates. No tuning, no order filter. Same historical samples already explored and actual receipt archive; not independently validated. Agreement breakdown descriptive only.','models':{'A_mixed_baseline':suite(A,AR),'B_local_shot':suite(B,BR),'equal_rate':suite((A+B)/2,(AR+BR)/2)},'agreement':{}}
for name,te,a,b,m in [('historical',zz,A,B,mz),('receipt',rr,AR,BR,mr)]:
 ap=g['make_pred'](te,a);bp=g['make_pred'](te,b);same=ap[1]==bp[1]
 out['agreement'][name]={'rate_correlation':float(np.corrcoef(a,b)[0,1]),'correction_correlation':float(np.corrcoef(a-m,b-m)[0,1]),'same':{'n':int(same.sum()),'A':g['stat'](ap[2][same]),'B':g['stat'](bp[2][same])},'different':{'n':int((~same).sum()),'A':g['stat'](ap[2][~same]),'B':g['stat'](bp[2][~same])}}
assert out['models']['A_mixed_baseline']['history']['U']==24.205
assert out['models']['A_mixed_baseline']['receipt']['U']==9.83
assert out['models']['B_local_shot']['history']['U']==64.425
assert out['models']['B_local_shot']['receipt']['U']==-15.61
(P/'m8_tc_candidate_complementarity_20261116.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
