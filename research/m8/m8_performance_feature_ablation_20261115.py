import json,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
source=(P/'m8_espn_ou_league_calibration_20261115.py').read_text()
exec(source[:source.index("out={'history_n'")])
names=('shots','sot','poss','goals','conversion')
variants={'market':(), 'full':names}
for name in names:
 variants['only_'+name]=(name,)
 variants['without_'+name]=tuple(k for k in names if k!=name)
def custom(r,cols):
 v=features(r,'market')
 f=feat[r['fid']]
 return v+[f[j*5+k] for j in range(4) for k,name in enumerate(names) if name in cols]
def forecast(train,test,cols):
 X=np.array([custom(r,cols) for r in train]);Xt=np.array([custom(r,cols) for r in test])
 y=vec(train,'hg')+vec(train,'ag');actual=vec(test,'hg')+vec(test,'ag')
 total=goals_predict(X,y,np.log(vec(train,'mh')+vec(train,'ma')),Xt,np.log(vec(test,'mh')+vec(test,'ma')))
 w,l=ou_wl(total,vec(test,'ol'));eo=w*(vec(test,'oo')-1)-l;eu=l*(vec(test,'ou')-1)-w
 side=eo>=eu;pnl=np.where(side,vec(test,'over_U'),vec(test,'under_U'))
 return total,side,pnl
def metrics(test,p,m):
 total,side,pnl=p; y=vec(test,'hg')+vec(test,'ag')
 return {**stat(pnl[m]),'NLL':round(float(np.mean((total-y*np.log(total))[m])),6),'MAE':round(float(np.mean(abs(total-y)[m])),6),'over_n':int(side[m].sum())}
z=[r for r in valid if r['league'] in ('1','14')]
out={'variants':variants,'method':'Crown T12 same fixtures, prior annual fit, prior performance >=3 UTC dates, fixed existing model and features. No new formal rule. All variants historical exploratory, not unseen prospective validation.','years':{}}
for yr in (2024,2025,2026):
 tr=[r for r in z if r['year']<yr];te=[r for r in z if r['year']==yr]
 groups={'all':np.ones(len(te),bool),'EPL':np.array([r['league']=='1' for r in te]),'LaLiga':np.array([r['league']=='14' for r in te]),'H1':np.array([r['date'][5:7]<='06' for r in te]),'H2':np.array([r['date'][5:7]>'06' for r in te])}
 ps={k:forecast(tr,te,v) for k,v in variants.items()}
 ref=ps['market'];full=ps['full']
 rec={'train_n':len(tr),'test_n':len(te),'models':{}}
 for k,p in ps.items():
  rec['models'][k]={'groups':{g:metrics(te,p,m) for g,m in groups.items()},'switch_vs_market':int((p[1]!=ref[1]).sum()),'switch_vs_full':int((p[1]!=full[1]).sum())}
 print(yr,{k:(v['groups']['all']['U'],v['groups']['all']['ROI'],v['groups']['all']['NLL']) for k,v in rec['models'].items()},flush=True)
 out['years'][str(yr)]=rec
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
assert [out['years'][str(y)]['models']['full']['groups']['all']['U'] for y in (2024,2025,2026)]==[-6.61,-4.175,28.19]
(P/'m8_performance_feature_ablation_20261115.json').write_text(json.dumps(out,indent=2))
print('FOUNDATION',out['foundation'],flush=True)
