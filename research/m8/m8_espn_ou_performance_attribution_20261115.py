import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
# Re-execute same data joining and model features, no changes or post-hoc model selection.
exec(s[:s.index("out={'raw_verified'")])
out={}
for y in (2024,2025,2026):
 tr=[r for r in valid if r['year']<y];te=[r for r in valid if r['year']==y]
 pred={}
 for kind in ('market','market_performance'):
  X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
  h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
  a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
  w,l=ou_wl(h+a,vec(te,'ol'))
  eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
  pred[kind]={'pnl':np.where(eo>=eu,vec(te,'over_U'),vec(te,'under_U')),'ev':np.maximum(eo,eu),'side':np.where(eo>=eu,'over','under')}
 leagues=sorted({r['league'] for r in te});groups={'all':np.ones(len(te),bool)}
 for g in leagues:groups['league_'+g]=np.array([r['league']==g for r in te])
 for h1 in (True,False):groups['H1' if h1 else 'H2']=np.array([(r['date'][5:7]<='06')==h1 for r in te])
 for side in ('over','under'):groups['performance_'+side]=pred['market_performance']['side']==side
 rec={'date_min':min(r['date'] for r in te),'date_max':max(r['date'] for r in te),'groups':{}}
 for k,mask in groups.items():
  rec['groups'][k]={kind:{'all':stat(v['pnl'][mask]),'positive_EV':stat(v['pnl'][mask&(v['ev']>1e-9)])} for kind,v in pred.items()}
 rec['directions_differ']=int((pred['market']['side']!=pred['market_performance']['side']).sum())
 out[str(y)]=rec;print('ATTR',y,json.dumps(rec),flush=True)
(P/'m8_espn_ou_performance_attribution_20261115.json').write_text(json.dumps(out,indent=2))
