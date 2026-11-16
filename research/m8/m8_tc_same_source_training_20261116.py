import json,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_multiscale_research_20261116.py').read_text()
exec(s[:s.index("out={'method'")])
# Fixed test cohorts, same feature recipes. TC training targets are earlier historical Crown rows only.
CF=ZF
EF=fset(histories(z,ei))
EN=features_for(z,ei)[1]
paired=[r for r in z if min(EN[r['fid']])>0]
# build ESPN matrix for original training and TC training matrices independently to avoid fixture-key collision.
def mapmat(a,ff,k):return {r['fid']:v for r,v in zip(a,matrix(a,ff,k))}
def fitmat(tr,X,te,Xt):
 return g['goals_predict'](X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
def run_mode(kind,mode,te,FF):
 # Scope identical across variants. 2023 TC training unavailable; report 2024 onward only.
 EA=mapmat(train,TF,kind);CA=mapmat(z,CF,kind);PA=mapmat(paired,EF,kind)
 pred=np.empty(len(te));ns={}
 keys=[r['date'][:7] if mode=='tc_monthly' else str(r['year']) for r in te]
 for key in sorted(set(keys)):
  mask=np.array([v==key for v in keys]);tt=[r for r,m in zip(te,mask) if m]
  year=int(key[:4]);cut=(datetime.date.fromisoformat(key+'-01')-datetime.timedelta(days=3)).isoformat() if mode=='tc_monthly' else str(year)+'-01-01'
  c=[r for r in z if r['date']<cut]
  e=[r for r in train if r['year']<year]
  pair=[r for r in paired if r['date']<cut]
  if mode=='espn':tr=e;xx=[EA[r['fid']] for r in tr]
  elif mode in ('tc','tc_monthly'):tr=c;xx=[CA[r['fid']] for r in tr]
  elif mode=='mixed':
   seen={r['fid'] for r in c};ee=[r for r in e if r['fid'] not in seen]
   tr=c+ee;xx=[CA[r['fid']] for r in c]+[EA[r['fid']] for r in ee]
  elif mode in ('paired_espn','paired_tc'):
   tr=pair;aa=PA if mode=='paired_espn' else CA;xx=[aa[r['fid']] for r in tr]
  elif mode=='tc_league':
   tr=c;xx=[CA[r['fid']] for r in tr]
  else:raise ValueError(mode)
  assert tr and max(r['date'] for r in tr)<min(r['date'] for r in tt)
  assert len({r['fid'] for r in tr})==len(tr) and not ({r['fid'] for r in tr}&{r['fid'] for r in tt})
  X=np.asarray(xx);Xt=matrix(tt,FF,kind)
  if mode=='tc_league':
   leagues=sorted({r['league'] for r in tr})
   X=np.column_stack((X,[[r['league']==l for l in leagues] for r in tr]))
   Xt=np.column_stack((Xt,[[r['league']==l for l in leagues] for r in tt]))
  pred[mask]=fitmat(tr,X,tt,Xt);ns[key]=len(tr)
 return pred,ns
zz=[r for r in z if r['year']>=2024];rr=ex
mz=vec(zz,'mh')+vec(zz,'ma');mr=vec(rr,'mh')+vec(rr,'ma')
assert len(zz)==2951
rids={r['fid'] for r in rows}
unique=np.array([r['fid'] not in rids for r in zz])
out={'method':'Fixed R10 archive. Target years 2024–26 only (TC earlier-year training exists); same test IDs. Experimental prior-year TC training, mixed deduplicated prior-year TC/ESPN, matched training fixture identity with histories from each source, TC monthly training (strict preceding date), and regularized league indicator. Same historical feature lag, Poisson ridge and settlement. No change to original models, no ROI optimization. Retrospective data, not forward validation.','history_n':len(history),'paired_train_candidates':len(paired),'meta':{},'models':{}}
for kind in ('baseline','shot_level_drift','drift_only'):
 out['models'][kind]={}
 for mode in ('espn','tc','mixed','paired_espn','paired_tc','tc_monthly','tc_league'):
  # matched sample does not include 2023 if common ESPN history absent; no extrapolated training. report exactly available years.
  test=zz if mode not in ('paired_espn','paired_tc') else [r for r in zz if any(t['year']<r['year'] for t in paired)]
  if not test:continue
  p,ns=run_mode(kind,mode,test,ZF);q,nr=run_mode(kind,mode,rr,RF)
  m=vec(test,'mh')+vec(test,'ma')
  def group(mask):
   if not mask.any():return {'n':0}
   return summarize([r for r,b in zip(test,mask) if b],p[mask],m[mask])
  a={'history':summarize(test,p,m),'year':{str(y):group(np.array([r['year']==y for r in test])) for y in sorted({r['year'] for r in test})},'disjoint':group(np.array([r['fid'] not in rids for r in test])),'receipt':summarize(rr,q,mr),'train_counts':ns,'receipt_train_counts':nr}
  out['models'][kind][mode]=a
  print(kind,mode,'history',a['history'],'year',[(y,b['n'],b['ROI'],b['delta_brier_market']) for y,b in a['year'].items()],'receipt',a['receipt'],'train_counts',ns,flush=True)
assert out['models']['baseline']['espn']['history']['U']==-4.23
assert out['models']['baseline']['espn']['receipt']['U']==-8.54
(P/'m8_tc_same_source_training_20261116.json').write_text(json.dumps(out,indent=2))
