import json,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_espn_ou_league_calibration_20261115.py').read_text()
exec(s[:s.index("out={'history_n'")])
esfeat=feat
tcpaths=['m8_performance_batch_probe_20261115.jsonl','m8_performance_cross_year_20261115/verified_new.jsonl','m8_performance_contiguous_20261115/verified_new.jsonl','m8_performance_gap_recovery_20261115/verified_new.jsonl']
tc={r['fid']:r for path in tcpaths for r in map(json.loads,(P/path).open())}
assert len(tc)==409
T={}
for f,r in tc.items():
 if any(r[k] is None or len(r[k])!=2 or any(x is None or x<0 for x in r[k]) for k in ('shot_on','shot_off','possess')):continue
 if abs(sum(r['possess'])-100)>1:continue
 h,a=r['shot_on'];ho,ao=r['shot_off'];hp,ap=r['possess']
 T[f]={**r,'year':int(r['date'][:4]),'hshots':h+ho,'ashots':a+ao,'hsot':h,'asot':a,'hposs':hp,'aposs':ap}
# Reuse the exact historical rolling feature construction independently per source.
src=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
esvalid=valid
ep_saved=ep
ep=T
exec(src[src.index('hist=sorted(ep.values()'):src.index("out={'raw_verified'")])
tcfeat=feat;tcvalid=valid
ep=ep_saved
def base(r,F,kind):
 h,a=r['mh'],r['ma']
 v=[1,np.log(h),np.log(a),np.log(h+a),np.log1p(r['age_ah']),np.log1p(r['age_ou']),r['al'],r['ol']]
 raw=F[r['fid']];eff=[]
 for j in range(4):
  sh,so,po,g,conv=raw[5*j:5*j+5]
  eff.extend([50*sh/po,50*so/po,50*g/po,so/sh])
 if kind=='full':v+=raw
 if kind=='efficiency':v+=eff
 if kind=='full_efficiency':v+=raw+eff
 if kind=='full_shot_efficiency':v+=raw+[eff[j*4+k] for j in range(4) for k in (0,1)]
 return v
variants=('market','full','efficiency','full_efficiency','full_shot_efficiency')
def forecast(tr,te,F,kind):
 X=np.array([base(r,esfeat,kind) for r in tr]);Xt=np.array([base(r,F,kind) for r in te])
 total=goals_predict(X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
 w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 side=eo>=eu
 return total,side,np.where(side,vec(te,'over_U'),vec(te,'under_U'))
def metrics(te,p,mask):
 x,side,pnl=p;y=vec(te,'hg')+vec(te,'ag')
 return {**stat(pnl[mask]),'NLL':round(float(np.mean((x-y*np.log(x))[mask])),6),'MAE':round(float(np.mean(abs(x-y)[mask])),6)}
def evaluate_variants(tr,te,F):
 groups={'all':np.ones(len(te),bool)}
 for lid in sorted({r['league'] for r in te}):groups['league_'+lid]=np.array([r['league']==lid for r in te])
 for name,cond in [('H1',True),('H2',False)]:
  m=np.array([(r['date'][5:7]<='06')==cond for r in te])
  if m.any():groups[name]=m
 p={k:forecast(tr,te,F,k) for k in variants}
 return {'train_n':len(tr),'test_n':len(te),'models':{k:{'groups':{g:metrics(te,v,m) for g,m in groups.items()},'switch_vs_full':int((v[1]!=p['full'][1]).sum())} for k,v in p.items()}}
out={'method':'Historical T12 same-fixture comparison. Existing lag, decay, shrinkage and annual train-only model. Ratios: shots, SOT, goals per 50 possession percentage points, SOT/shots. No new selection rules. TC evaluated separately, no merged training. Previously inspected historical outcomes.','ESPN_n':len(esfeat),'TC_complete_n':len(T),'TC_valid_n':len(tcvalid),'ESPN':{},'TC_transfer':{}}
z=[r for r in esvalid if r['league'] in ('1','14')]
for y in (2024,2025,2026):
 tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y]
 out['ESPN'][str(y)]=evaluate_variants(tr,te,esfeat)
for y in sorted({r['year'] for r in tcvalid}):
 tr=[r for r in z if r['year']<y];te=[r for r in tcvalid if r['year']==y and r['league'] not in ('1','14')]
 if tr and te:out['TC_transfer'][str(y)]=evaluate_variants(tr,te,tcfeat)
for group in ('ESPN','TC_transfer'):
 for year,rec in out[group].items():print(group,year,rec['test_n'],{k:v['groups']['all'] for k,v in rec['models'].items()},flush=True)
assert [out['ESPN'][str(y)]['models']['full']['groups']['all']['U'] for y in (2024,2025,2026)]==[-6.61,-4.175,28.19]
# Fixture-level overlap is a diagnostic, not a trading deduplication rule.
frozen=list(map(json.loads,(P/'m8_foundation_20261115/historical_membership.jsonl').open()))
ids={r['fid'] for r in frozen}
out['fixture_overlap']={}
for y in (2024,2025,2026):
 tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y]
 overlap=np.array([r['fid'] in ids for r in te])
 rec={'overlap_n':int(overlap.sum()),'outside_n':int((~overlap).sum()),'models':{}}
 for k in variants:
  p=forecast(tr,te,esfeat,k)
  rec['models'][k]={name:metrics(te,p,mask) for name,mask in [('overlap',overlap),('outside',~overlap)] if mask.any()}
 out['fixture_overlap'][str(y)]=rec
 print('OVERLAP',y,rec,flush=True)
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_possession_efficiency_20261115.json').write_text(json.dumps(out,indent=2))
print('FOUNDATION',out['foundation'],flush=True)
