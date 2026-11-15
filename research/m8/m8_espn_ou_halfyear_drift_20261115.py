import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Reuse exact prior historical population, score-only lag logic and frozen model features.
s=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
exec(s[:s.index("out={'raw_verified'")])
coverage={}
for y in (2024,2025,2026):
 for half in (1,2):
  for league in ('1','14'):
   key=f'{y}H{half}|{league}'
   zz=[r for r in target.values() if r['league']==league and r['year']==y and (int(r['date'][5:7])<=6)==(half==1)]
   coverage[key]={'market_n':len(zz),'performance_n':sum(r['fid'] in ep for r in zz)}
def predict(tr,te,kind):
 X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
 h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
 a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
 total=h+a
 w,l=ou_wl(total,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 side=np.where(eo>=eu,1,-1);pl=np.where(side==1,vec(te,'over_U'),vec(te,'under_U'))
 return dict(total=total,side=side,pnl=pl,ev=np.maximum(eo,eu))
def summarize(te,p,mask):
 o=np.array([r['hg']+r['ag'] for r in te]);market=vec(te,'mh')+vec(te,'ma');line=vec(te,'ol')
 n=int(mask.sum())
 if not n:return {'n':0}
 return {'n':n,'U':round(float(p['pnl'][mask].sum()),3),'ROI':round(float(p['pnl'][mask].mean()*100),3),
 'mean_goal_actual':round(float(o[mask].mean()),4),'mean_goal_market':round(float(market[mask].mean()),4),'mean_goal_forecast':round(float(p['total'][mask].mean()),4),
 'total_goal_MAE':round(float(np.abs(p['total'][mask]-o[mask]).mean()),4),
 'forecast_poisson_NLL_without_factorial':round(float(np.mean(p['total'][mask]-o[mask]*np.log(p['total'][mask]))),6),
 'over_n':int((p['side'][mask]==1).sum()),'mean_line':round(float(line[mask].mean()),4),
 'mean_selected_price':round(float(np.where(p['side']==1,vec(te,'oo'),vec(te,'ou'))[mask].mean()),4)}
out={'coverage':coverage,'years':{}}
for y in (2024,2025,2026):
 tr=[r for r in valid if r['year']<y];te=[r for r in valid if r['year']==y]
 p={k:predict(tr,te,k) for k in ('market','market_performance')}
 # Same model, same matches, split by time, league and agreement; no new selection rule.
 groups={'all':np.ones(len(te),bool)}
 for half in (1,2):
  mask=np.array([(int(r['date'][5:7])<=6)==(half==1) for r in te])
  groups[f'H{half}']=mask
  for league in ('1','14'):groups[f'H{half}|{league}']=mask&np.array([r['league']==league for r in te])
  groups[f'H{half}|agree']=mask&(p['market']['side']==p['market_performance']['side'])
  groups[f'H{half}|differ']=mask&(p['market']['side']!=p['market_performance']['side'])
 rec={'groups':{g:{k:summarize(te,v,mask) for k,v in p.items()} for g,mask in groups.items()}}
 # Study-only refitting at the start of H2, does not use future results.
 cut=datetime.date(y,7,1)-datetime.timedelta(days=3)
 tr2=[r for r in valid if datetime.date.fromisoformat(r['date'])<=cut]
 te2=[r for r in te if int(r['date'][5:7])>6]
 rec['H2_refit']={'train_n':len(tr2),**{k:summarize(te2,predict(tr2,te2,k),np.ones(len(te2),bool)) for k in p}}
 out['years'][str(y)]=rec
 print('YEAR',y,json.dumps({g:rec['groups'][g] for g in ('H1','H2','H2|1','H2|14','H2|agree','H2|differ')}),flush=True)
 print('REFIT',y,json.dumps(rec['H2_refit']),flush=True)
(P/'m8_espn_ou_halfyear_drift_20261115.json').write_text(json.dumps(out,indent=2))
print('COVERAGE',json.dumps(coverage),flush=True)
