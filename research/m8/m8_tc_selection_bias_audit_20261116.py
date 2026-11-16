import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_complementary_league_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# In-scope retrospective robustness check, not a genuinely untouched test.
def week(q):return np.array([datetime.date.fromisoformat(a['date']).strftime('%G-W%V') for a in q])
def audit(q,val,k):
 if not k.any():return {'n':0}
 w=week(q);pnl=val[3];wk=sorted(set(w[k]))
 z=np.asarray([[int((k&(w==j)).sum()),float(pnl[k&(w==j)].sum())] for j in wk])
 rng=np.random.default_rng(20261116)
 ix=rng.integers(0,len(z),size=(10000,len(z)));draw=z[ix].sum(1);qtl=np.quantile(100*draw[:,1]/draw[:,0],[.025,.975])
 n,u=z.sum(0);best=z[:,1].argmax();worst=z[:,1].argmin()
 return {**g['stat'](pnl[k]),'weeks':len(z),'positive_weeks':int((z[:,1]>0).sum()),'weekly_bootstrap_95pct_descriptive':[round(float(i),3) for i in qtl],'without_best_week_roi':round(100*(u-z[best,1])/(n-z[best,0]),3) if n>z[best,0] else None,'best_week':wk[best],'best_week_U':round(float(z[best,1]),3),'worst_week':wk[worst],'worst_week_U':round(float(z[worst,1]),3)}
h,log=annual(t,'previous_year');rh,_=annual(rt,'previous_year')
masks={'all_B':np.ones(len(t),bool),'R19':band,'R20_static':band|static(t),'R20_annual':band|h}
rmasks={'all_B':np.ones(len(rt),bool),'R19':rb,'R20_static':rb|static(rt),'R20_annual':rb|rh}
out={'method':'Selection-bias audit: same previously explored data. Weekly block bootstrap conditional on selected arms, 10000 draws; nominal descriptive intervals, NOT adjusted for model/interval search, not independent validation. Exclude receipt archive FIDs in historical estimates. Prior-year interval choice over all five existing bins is a retrospective nested-style falsification, not a confirmed rule.','arms':{},'prior_year_band_selection':{}}
for name,k in masks.items():
 a={'history_disjoint':audit(t,v,k&ind),'2026_disjoint':audit(t,v,k&ind&(years==2026)),'receipt':audit(rt,r,rmasks[name])}
 out['arms'][name]=a
 print(name,a,flush=True)
ed=[-np.inf,0,.02,.05,.10,np.inf];labels=['negative','0_2','2_5','5_10','10_plus']
for y0 in (2025,2026):
 tr=ind&(years<y0);te=ind&(years==y0)
 stats={}
 for label,a,b in zip(labels,ed[:-1],ed[1:]):
  k=(v[0]>=a)&(v[0]<b)
  stats[label]={'prior':g['stat'](v[3][tr&k]),'later':g['stat'](v[3][te&k])}
 chosen=max(labels,key=lambda i:stats[i]['prior']['ROI'])
 i=labels.index(chosen);a,b=ed[i:i+2]
 out['prior_year_band_selection'][str(y0)]={'all_bins':stats,'prior_best_by_roi':chosen,'later':stats[chosen]['later'],'receipt':g['stat'](r[3][(r[0]>=a)&(r[0]<b)]) if y0==2026 else None}
 print('prior band selection',y0,out['prior_year_band_selection'][str(y0)],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_selection_bias_audit_20261116.json').write_text(json.dumps(out,indent=2))
