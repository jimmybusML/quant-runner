import json,hashlib,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_efficiency_league_training_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Alternate rolling history decay only; preserve identical verified fixtures.
src=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
seg=src[src.index('hist=sorted(ep.values()'):src.index('z=[target[f] for f in ep]')]
assert '/180' in seg
metric_fn=metrics
exec(seg.replace('/180','/90'))
metrics=metric_fn
shortfeat=feat
assert set(shortfeat)==set(esfeat)
F0=esfeat
# Recover core fixtures in case the helper changed local variable names.
z=[r for r in esvalid if r['league'] in ('1','14')]
def day(s):return datetime.date.fromisoformat(s)
def fit_new(tr,te,F,cut,half_life=None):
 X=np.array([base(r,F,'full_shot_efficiency') for r in tr]);Xt=np.array([base(r,F,'full_shot_efficiency') for r in te])
 a=np.ones(len(tr)) if half_life is None else np.array([2**(-((cut-day(r['date'])).days)/half_life) for r in tr])
 # normalize mean weight to keep existing regularization scale comparable
 a=a/a.mean();mu=np.average(X,axis=0,weights=a);sd=np.sqrt(np.average((X-mu)**2,axis=0,weights=a));mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;Xt=(Xt-mu)/sd
 pen=np.full(X.shape[1],100.);pen[0]=0;D=np.diag(pen);B=np.zeros(X.shape[1])
 y=vec(tr,'hg')+vec(tr,'ag');offset=np.log(vec(tr,'mh')+vec(tr,'ma'));ot=np.log(vec(te,'mh')+vec(te,'ma'))
 for _ in range(30):
  w=np.exp(np.clip(offset+X@B,-7,5));step=np.linalg.solve(X.T@((a*w)[:,None]*X)+D,X.T@(a*(y-w))-D@B);B+=step
  if np.max(np.abs(step))<1e-7:break
 total=np.exp(np.clip(ot+Xt@B,-7,3));w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 side=eo>=eu
 return total,side,np.where(side,vec(te,'over_U'),vec(te,'under_U'))
variants={'annual_lag':(12,None,180),'quarterly':(3,None,180),'monthly':(1,None,180),'annual_weighted':(12,365,180),'monthly_weighted':(1,365,180),'monthly_recent_form':(1,None,90)}
def predict(y,te,config):
 step,half,form=config;F=F0 if form==180 else shortfeat
 x=np.zeros(len(te));s=np.zeros(len(te),bool);p=np.zeros(len(te));used=np.zeros(len(te),bool);runs=[]
 for m in range(1,13,step):
  start=datetime.date(y,m,1);cut=start-datetime.timedelta(days=3)
  a=[r for r in z if day(r['date'])<=cut]
  mask=np.array([m<=int(r['date'][5:7])<m+step for r in te])
  if not mask.any():continue
  b=[r for r in te if m<=int(r['date'][5:7])<m+step]
  assert max(day(r['date']) for r in a)<=cut and min(day(r['date']) for r in b)>=start
  x[mask],s[mask],p[mask]=fit_new(a,b,F,cut,half);used|=mask
  runs.append({'start':start.isoformat(),'latest_allowed_train_date':cut.isoformat(),'latest_observed_train_date':max(r['date'] for r in a),'n_train':len(a),'n_test':len(b)})
 assert used.all()
 return (x,s,p),runs
def groups(te,p,ref):
 g=groupstats(te,p)
 h1=np.array([r['date'][5:7]<='06' for r in te]);g['H1']=metrics(te,p,h1)
 g['outside_H2']=metrics(te,p,np.array([r['fid'] not in ids and r['date'][5:7]>'06' for r in te]))
 g['switch_vs_annual']=int((p[1]!=ref[1]).sum())
 return g
out={'method':'Same explored T12 fixtures, prior-UTC-date lag on period start; expanding training, fixed experiments; 365-day training weight half-life normalized to mean 1 and 90-day alternative prior team form vs original 180-day. No new rules, no test-year ROI choice. Historical receipt proxy, not prospective. Annual legacy baseline has original calendar prior-year fit.','variants':variants,'years':{}}
for y in (2024,2025,2026):
 te=[r for r in z if r['year']==y];tr=[r for r in z if r['year']<y]
 ref=fit(tr,te,'shared')
 check=fit_new(tr,te,F0,datetime.date(y,1,1))
 assert np.allclose(ref[0],check[0]) and np.array_equal(ref[1],check[1]) and np.array_equal(ref[2],check[2])
 legacy_last=max(datetime.datetime.fromisoformat(ep[r['fid']]['ko']) for r in tr)
 earliest=min(datetime.datetime.fromisoformat(ep[r['fid']]['ko']) for r in te)-datetime.timedelta(hours=12)
 cut=datetime.date(y,1,1)-datetime.timedelta(days=3)
 rec={'n':len(te),'models':{'annual_legacy':groups(te,ref,ref)},'runs':{},'annual_boundary':{'legacy_train_n':len(tr),'lag_train_n':sum(day(r['date'])<=cut for r in tr),'legacy_last_train_kickoff':legacy_last.isoformat(),'first_test_T12_cutoff':earliest.isoformat(),'hours_between_kickoff_and_first_cutoff':(earliest-legacy_last).total_seconds()/3600,'same_training_unweighted_reproduction':True}}
 for k,c in variants.items():
  p,runs=predict(y,te,c);rec['models'][k]=groups(te,p,ref);rec['runs'][k]=runs
 out['years'][str(y)]=rec
 print('YEAR',y,{k:{'U':v['all']['U'],'ROI':v['all']['ROI'],'NLL':v['all']['NLL'],'H2':v['H2']['ROI'],'outside':v['outside']['U']} for k,v in rec['models'].items()},flush=True)
assert [out['years'][str(y)]['models']['annual_legacy']['all']['U'] for y in (2024,2025,2026)]==[19.115,9.89,31.555]
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_efficiency_rolling_training_20261115.json').write_text(json.dumps(out,indent=2))
print('FOUNDATION',out['foundation'],flush=True)
