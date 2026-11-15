import json,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_efficiency_rolling_training_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
names=('annual_lag','quarterly','monthly')
def make_pred(te,total,side=None):
 if side is None:
  w,l=ou_wl(total,vec(te,'ol'));side=w*(vec(te,'oo')-1)-l>=l*(vec(te,'ou')-1)-w
 return total,side,np.where(side,vec(te,'over_U'),vec(te,'under_U'))
def calc(te,p,mask):
 if not mask.any():return {'n':0,'U':0.,'ROI':None,'NLL':None,'MAE':None}
 return metrics(te,p,mask)
def annual_stats(te,ps):
 sides=np.array([ps[k][1] for k in names]);votes=sides.sum(axis=0)
 total=np.mean([ps[k][0] for k in names],axis=0)
 ps['majority']=make_pred(te,total,votes>=2)
 ps['mean_goals']=make_pred(te,total)
 unanimous=(votes==0)|(votes==3);disagree=~unanimous
 outside=np.array([r['fid'] not in ids for r in te]);h2=np.array([r['date'][5:7]>'06' for r in te])
 groups={'all':np.ones(len(te),bool),'unanimous':unanimous,'disagree':disagree,'unanimous_over':votes==3,'unanimous_under':votes==0,'annual_vs_both':(sides[0]!=sides[1])&(sides[1]==sides[2]),'quarter_vs_both':(sides[1]!=sides[0])&(sides[0]==sides[2]),'month_vs_both':(sides[2]!=sides[0])&(sides[0]==sides[1])}
 for label,mask in list(groups.items()):
  groups[label+'_outside']=mask&outside
  groups[label+'_H2']=mask&h2
  groups[label+'_outside_H2']=mask&outside&h2
 rec={g:{k:calc(te,p,m) for k,p in ps.items()} for g,m in groups.items()}
 assert sum(rec[g]['majority']['n'] for g in ('unanimous','annual_vs_both','quarter_vs_both','month_vs_both'))==len(te)
 for k in ps:
  assert abs(rec['all'][k]['U']-rec['unanimous'][k]['U']-rec['disagree'][k]['U'])<.0011
 return rec
out={'method':'Same T12 historical fixtures. Original calendar annual as reference; three models share prior-period 3 UTC day boundary, 180 day team features, common training. Majority and equal mean prediction only descriptive comparisons; agreement diagnostic not a new gate. Historical outcomes already explored, no forward receipt verification.','years':{}}
for y in (2024,2025,2026):
 te=[r for r in z if r['year']==y];tr=[r for r in z if r['year']<y]
 ps={'annual_legacy':fit(tr,te,'shared')}
 for k in names:ps[k]=predict(y,te,variants[k])[0]
 rec=annual_stats(te,ps)
 out['years'][str(y)]=rec
 print('YEAR',y,flush=True)
 for g in ('all','unanimous','disagree','annual_vs_both','quarter_vs_both','month_vs_both','unanimous_outside','disagree_outside','unanimous_H2','disagree_H2'):
  print(g,{k:(v['n'],v['U'],v['ROI']) for k,v in rec[g].items()},flush=True)
old=json.loads((P/'m8_efficiency_rolling_training_20261115.json').read_text())
for y,rec in out['years'].items():
 for k in ('annual_legacy',*names):
  assert rec['all'][k]['U']==old['years'][y]['models'][k]['all']['U']
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':hashlib.sha256((P/m['historical_membership']['local_file']).read_bytes()).hexdigest()==m['historical_membership']['sha256'],'inputs':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['input_sha256'].items()),'scripts':all(hashlib.sha256((P/k).read_bytes()).hexdigest()==v for k,v in m['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_efficiency_model_agreement_20261115.json').write_text(json.dumps(out,indent=2))
print('FOUNDATION',out['foundation'],flush=True)
