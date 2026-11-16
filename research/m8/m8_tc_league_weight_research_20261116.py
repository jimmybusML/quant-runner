import json,itertools,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_same_source_training_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Research experiment: prior ESPN records stay at unit weight; add unique TC
# records at different local/foreign relative weights, not a filtering rule.
specs=list(itertools.product((0.,1.,2.),(0.,.5,1.)))
def weighted(X,y,off,Xt,ot,w):
 keep=w>0;X=X[keep];y=y[keep];off=off[keep];w=w[keep]
 mu=np.average(X,axis=0,weights=w);sd=np.sqrt(np.average((X-mu)**2,axis=0,weights=w));mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;Xt=(Xt-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for i in range(20):
  u=np.exp(np.clip(off+X@b,-7,5));step=np.linalg.solve(X.T@((w*u)[:,None]*X)+pen,X.T@(w*(y-u))-pen@b);b+=step
  if np.max(np.abs(step))<1e-7:break
 return np.exp(np.clip(ot+Xt@b,-7,3))
def assess(a,p,m):
 x=summarize(a,p,m);sides=g['make_pred'](a,p);daily=collections.defaultdict(float)
 for r,v in zip(a,sides[2]):daily[r['date']]+=float(v)
 c=peak=dd=0.
 for d,u in sorted(daily.items()):c+=u;peak=max(peak,c);dd=max(dd,peak-c)
 x['daily_mdd']=round(dd,3);x['over_n']=int(sides[1].sum());return x
def sc(hp,rp):
 def hs(mask):
  return assess([r for r,b in zip(zz,mask) if b],hp[mask],mz[mask])
 return {'history':assess(zz,hp,mz),'receipt':assess(rr,rp,mr),'disjoint':hs(unique),'year':{str(y):hs(np.array([r['year']==y for r in zz])) for y in (2024,2025,2026)},'league_year':{str(y):{l:hs(np.array([r['year']==y and r['league']==l for r in zz])) for l in sorted({r['league'] for r in zz if r['year']==y})} for y in (2024,2025,2026)}}
out={'method':'Retrospective research; fixed R10 cohort. Full ESPN unit weights; 9 local/foreign relative weight combinations for additional deduplicated TC rows, retain all results, original ridge and features. Prior-year training only. Equal probability-rate ensemble and earlier-year Brier choice purely diagnostic, not approved trade rules. Daily kickoff date MDD not live ledger.','models':{}}
for kind in ('baseline','shot_level_drift'):
 EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind)
 predictions={};result={}
 for a,b in specs:
  hp=np.zeros(len(zz));rp=np.zeros(len(rr))
  for y in (2024,2025,2026):
   e=[r for r in train if r['year']<y];seen={r['fid'] for r in e};c=[r for r in z if r['year']<y and r['fid'] not in seen];tr=e+c
   X=np.asarray([EA[r['fid']] for r in e]+[CA[r['fid']] for r in c]);Y=vec(tr,'hg')+vec(tr,'ag');off=np.log(vec(tr,'mh')+vec(tr,'ma'))
   assert max(r['year'] for r in tr)<y and len({r['fid'] for r in tr})==len(tr)
   for l in sorted({r['league'] for r in zz if r['year']==y}):
    w=np.asarray([1.]*len(e)+[a if r['league']==l else b for r in c])
    mh=np.array([r['year']==y and r['league']==l for r in zz]);mr0=np.array([r['year']==y and r['league']==l for r in rr])
    te=[r for r,m in zip(zz,mh) if m];rt=[r for r,m in zip(rr,mr0) if m]
    xt=matrix(te,ZF,kind)
    if rt:xt=np.vstack([xt,matrix(rt,RF,kind)])
    t=te+rt;p=weighted(X,Y,off,xt,np.log(vec(t,'mh')+vec(t,'ma')),w)
    hp[mh]=p[:len(te)];rp[mr0]=p[len(te):]
  key=f'{a:g}:{b:g}';predictions[key]=(hp,rp);result[key]=sc(hp,rp)
 # no selected seeds or result-weighted blend
 result['equal_rate_ensemble']=sc(np.mean([p[0] for p in predictions.values()],axis=0),np.mean([p[1] for p in predictions.values()],axis=0))
 trans={}
 for y in (2025,2026):
  prior_years=[k for k in (2024,2025) if k<y]
  vals={k:sum(v['year'][str(j)]['brier']*v['year'][str(j)]['n'] for j in prior_years)/sum(v['year'][str(j)]['n'] for j in prior_years) for k,v in result.items() if k!='equal_rate_ensemble'}
  k=min(vals,key=vals.get);trans[str(y)]={'selected':k,'prior_brier':vals[k],'year':result[k]['year'][str(y)],'receipt':result[k]['receipt'] if y==2026 else None}
 out['models'][kind]={'results':result,'calendar_brier_transfer':trans}
 for k,v in result.items():
  print(kind,k,'H',v['history']['U'],v['history']['ROI'],v['history']['brier'],v['history']['daily_mdd'],'years',[v['year'][str(y)]['ROI'] for y in (2024,2025,2026)],'disjoint',v['disjoint']['ROI'],'R',v['receipt']['U'],v['receipt']['ROI'],v['receipt']['daily_mdd'],v['receipt']['brier'],flush=True)
 print('transfer',kind,json.dumps(trans),flush=True)
assert out['models']['baseline']['results']['0:0']['history']['U']==-4.23
assert out['models']['baseline']['results']['1:1']['history']['U']==20.04
assert out['models']['shot_level_drift']['results']['1:0']['history']['U']==64.425
assert out['models']['shot_level_drift']['results']['1:0']['receipt']['U']==-15.61
(P/'m8_tc_league_weight_research_20261116.json').write_text(json.dumps(out,indent=2))
