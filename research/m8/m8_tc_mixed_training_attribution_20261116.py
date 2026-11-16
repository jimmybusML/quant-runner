import json,itertools,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_same_source_training_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Three disjoint changes relative to original ESPN training:
# replace common training fixture records; add new fixtures from original two leagues;
# add new fixtures from other leagues. Exact factorial, no result-dependent choice.
bits=list(itertools.product((0,1),repeat=3))
out={'method':'Retrospective fixed 2,951 historical and 308 receipt targets; 2^3 factorial of training changes. R=replace duplicate ESPN fixture representation with TC; S=add TC-only targets in original EPL/LaLiga; O=add TC-only targets in other leagues. All combinations, original parameters, prior-year training, no filters or deployment. Shapley is descriptive.' ,'models':{}}
for kind in ('baseline','shot_level_drift'):
 EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind)
 pools={}
 for y in (2024,2025,2026):
  e=[r for r in train if r['year']<y];c=[r for r in z if r['year']<y];ed={r['fid']:r for r in e};cd={r['fid']:r for r in c}
  overlap=set(ed)&set(cd);same=[r for r in c if r['fid'] not in ed and r['league'] in ('1','14')];other=[r for r in c if r['fid'] not in ed and r['league'] not in ('1','14')]
  pools[y]=(e,cd,overlap,same,other)
 results={};preds={}
 for bit in bits:
  key=''.join(map(str,bit));hp=np.empty(len(zz));rp=np.empty(len(rr))
  for y,(e,cd,overlap,same,other) in pools.items():
   tr=[];xx=[]
   for r in e:
    use=bit[0] and r['fid'] in overlap
    tr.append(cd[r['fid']] if use else r);xx.append((CA if use else EA)[r['fid']])
   add=(same if bit[1] else [])+(other if bit[2] else [])
   tr+=add;xx.extend(CA[r['fid']] for r in add)
   mask=np.array([r['year']==y for r in zz]);te=[r for r,m in zip(zz,mask) if m]
   assert len({r['fid'] for r in tr})==len(tr) and max(r['year'] for r in tr)<y
   xt=matrix(te,ZF,kind)
   if y==2026:xt=np.vstack([xt,matrix(rr,RF,kind)])
   p=fitmat(tr,np.asarray(xx),te+rr if y==2026 else te,xt)
   hp[mask]=p[:len(te)]
   if y==2026:rp[:]=p[len(te):]
  preds[key]=(hp,rp)
  def sub(m):return summarize([r for r,b in zip(zz,m) if b],hp[m],mz[m])
  results[key]={'history':summarize(zz,hp,mz),'receipt':summarize(rr,rp,mr),'disjoint':sub(unique),'year':{str(y):sub(np.array([r['year']==y for r in zz])) for y in (2024,2025,2026)}}
 def shapley(scope,metric):
  a={}
  for i,n in enumerate(('replace','same_league_add','other_league_add')):
   val=0.
   for b in bits:
    if b[i]:continue
    b1=list(b);b1[i]=1;s=sum(b);w=math.factorial(s)*math.factorial(2-s)/6
    x=results[''.join(map(str,b))][scope][metric];y=results[''.join(map(str,b1))][scope][metric];val+=w*(y-x)
   a[n]=round(val,6)
  return a
 league={}
 for l in sorted({r['league'] for r in zz}):
  h=np.array([r['league']==l for r in zz]);r=np.array([t['league']==l for t in rr]);league[l]={}
  for scope,mask,targets,market,kidx in [('history',h,zz,mz,0),('receipt',r,rr,mr,1)]:
   sel=[t for t,b in zip(targets,mask) if b]
   if not sel:continue
   league[l][scope]={k:summarize(sel,preds[k][kidx][mask],market[mask]) for k in ('000','111')}
 out['models'][kind]={'factorial':results,'attribution_U':{s:shapley(s,'U') for s in ('history','receipt')},'attribution_brier':{s:shapley(s,'brier') for s in ('history','receipt')},'league':league,'counts':{str(y):{'ESPN':len(e),'replace':len(o),'same_league_add':len(sa),'other_league_add':len(ot)} for y,(e,cd,o,sa,ot) in pools.items()}}
 print(kind,'counts',out['models'][kind]['counts'],flush=True)
 for k,v in results.items():print(k, v['history']['U'],v['history']['ROI'],v['history']['brier'], [v['year'][str(y)]['ROI'] for y in (2024,2025,2026)],v['receipt']['U'],v['receipt']['ROI'],v['receipt']['brier'],flush=True)
 print('attribution',out['models'][kind]['attribution_U'],out['models'][kind]['attribution_brier'],flush=True)
 print('leagues',[(l,[(scope,v['000']['n'],v['000']['ROI'],v['111']['ROI']) for scope,v in a.items()]) for l,a in league.items()],flush=True)
assert out['models']['baseline']['factorial']['000']['history']['U']==-4.23
assert out['models']['baseline']['factorial']['111']['history']['U']==24.205
assert out['models']['baseline']['factorial']['111']['receipt']['U']==9.83
assert out['models']['shot_level_drift']['factorial']['111']['history']['U']==54.21
(P/'m8_tc_mixed_training_attribution_20261116.json').write_text(json.dumps(out,indent=2))
