import json
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_same_source_training_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Always retain the full original ESPN training set. Vary only nonduplicate TC additions.
# Diagnostic target-league additions vs other-league additions, no learned rule.
out={'method':'Fixed historical and receipt targets; original ESPN training preserved in every arm. For each target year/league add only new TC records of the same league, only other leagues, or all leagues. No target-year outcomes used in training. No league selection or trading gate; historical retrospective.', 'models':{}}
for kind in ('baseline','shot_level_drift'):
 EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind)
 result={};counts={}
 for mode in ('espn','local_add','foreign_add','all_add'):
  hp=np.zeros(len(zz));rp=np.zeros(len(rr));counts[mode]={}
  for y in (2024,2025,2026):
   e=[r for r in train if r['year']<y];seen={r['fid'] for r in e};c=[r for r in z if r['year']<y and r['fid'] not in seen]
   for l in sorted({r['league'] for r in zz if r['year']==y}):
    add=[r for r in c if (mode=='all_add' or mode=='local_add' and r['league']==l or mode=='foreign_add' and r['league']!=l)]
    tr=e+add; X=np.asarray([EA[r['fid']] for r in e]+[CA[r['fid']] for r in add])
    mh=np.array([r['year']==y and r['league']==l for r in zz]);mr0=np.array([r['year']==y and r['league']==l for r in rr])
    te=[r for r,m in zip(zz,mh) if m];rt=[r for r,m in zip(rr,mr0) if m]
    assert max(r['year'] for r in tr)<y and len({r['fid'] for r in tr})==len(tr)
    xt=matrix(te,ZF,kind)
    if rt:xt=np.vstack([xt,matrix(rt,RF,kind)])
    p=fitmat(tr,X,te+rt,xt);hp[mh]=p[:len(te)];rp[mr0]=p[len(te):]
    counts[mode][str(y)+':'+l]=len(add)
  def hs(m):return summarize([r for r,b in zip(zz,m) if b],hp[m],mz[m])
  result[mode]={'history':summarize(zz,hp,mz),'receipt':summarize(rr,rp,mr),'disjoint':hs(unique),'year':{str(y):hs(np.array([r['year']==y for r in zz])) for y in (2024,2025,2026)}}
  print(kind,mode,'history',result[mode]['history'],'year',[(y,a['ROI']) for y,a in result[mode]['year'].items()],'receipt',result[mode]['receipt'],flush=True)
 out['models'][kind]={'results':result,'addition_counts':counts}
assert out['models']['baseline']['results']['espn']['history']['U']==-4.23
assert out['models']['baseline']['results']['all_add']['history']['U']==20.04
assert out['models']['shot_level_drift']['results']['all_add']['history']['U']==50.69
(P/'m8_tc_cross_league_transfer_20261116.json').write_text(json.dumps(out,indent=2))
