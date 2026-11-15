import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
exec(src[:src.index('# Index only already')])
target={r['fid']:r for r in rows if r['T']==12}
ep={r['fid']:r for r in map(json.loads,(P/'m8_espn_performance_confirmed_18leagues_20261115.jsonl').open())}
assert len(ep)==4122
exec(src[src.index('hist=sorted(ep.values()'):src.index("out={'raw_verified'")])
def pred(tr,te,kind,goalmode='separate'):
 X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
 if goalmode=='separate':
  h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
  a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
  total=h+a
 else:
  total=goals_predict(X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
 w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 return {'pnl':np.where(eo>=eu,vec(te,'over_U'),vec(te,'under_U')),'ev':np.maximum(eo,eu),'total':total}
def assess(te,p,mask):
 pnl=p['pnl'];actual=vec(te,'hg')+vec(te,'ag')
 if not mask.sum():return {'all':stat(pnl[mask]),'positive_EV_diagnostic':stat(pnl[mask])}
 return {'all':stat(pnl[mask]),'positive_EV_diagnostic':stat(pnl[mask&(p['ev']>1e-9)]),'goal_MAE':round(float(np.abs(p['total'][mask]-actual[mask]).mean()),6)}
out={'history_n':len(valid),'years':{},'transfer_new_leagues':{},'notes':'annual prior-year fit with same research features; no strategy adopted. New leagues lack earlier-year performance training, pooled transfer only.'}
for y in (2024,2025,2026):
 tr=[r for r in valid if r['year']<y and r['league'] in ('1','14')];te=[r for r in valid if r['year']==y and r['league'] in ('1','14')]
 variants={}
 for k in ('market','market_performance'):
  for mode in ('separate','total'):
   variants['pooled_'+k+'_'+mode]=pred(tr,te,k,mode)
   result={f:np.zeros(len(te)) for f in ('pnl','ev','total')}
   for lid in ('1','14'):
    mask=np.array([r['league']==lid for r in te]);one=pred([r for r in tr if r['league']==lid],[r for r in te if r['league']==lid],k,mode)
    for f in result:result[f][mask]=one[f]
   variants['league_'+k+'_'+mode]=result
 groups={'all':np.ones(len(te),bool)}
 for lid in ('1','14'):groups[lid]=np.array([r['league']==lid for r in te])
 for half in (1,2):
  mask=np.array([(int(r['date'][5:7])<=6)==(half==1) for r in te]);groups['H'+str(half)]=mask
  for lid in ('1','14'):groups['H'+str(half)+'|'+lid]=mask&groups[lid]
 rec={'train_n':len(tr),'test_n':len(te),'groups':{g:{k:assess(te,p,m) for k,p in variants.items()} for g,m in groups.items()}}
 out['years'][str(y)]=rec
 print('YEAR',y, {k:{g:rec['groups'][g][k]['all'] for g in ('all','1','14','H1','H2')} for k in variants},flush=True)
tr=[r for r in valid if r['year']<2026 and r['league'] in ('1','14')]
te=[r for r in valid if r['league'] not in ('1','14')]
for kind in ('market','market_performance'):
 p=pred(tr,te,kind)
 out['transfer_new_leagues'][kind]=assess(te,p,np.ones(len(te),bool))
print('TRANSFER',out['transfer_new_leagues'],flush=True)
(P/'m8_espn_ou_league_calibration_20261115.json').write_text(json.dumps(out,indent=2))
