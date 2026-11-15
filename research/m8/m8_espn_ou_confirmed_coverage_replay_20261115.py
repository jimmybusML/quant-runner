import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=(P/'m8_espn_cached_performance_verified_20261115.py').read_text()
exec(src[:src.index('# Index only already')])
target={r['fid']:r for r in rows if r['T']==12}
ep={r['fid']:r for r in map(json.loads,(P/'m8_espn_cached_performance_verified_20261115.jsonl').open())}
prior_ids=set(ep);additional=[v['record'] for v in map(json.loads,(P/'m8_espn_additional_cache_candidates_20261115.jsonl').open()) if v['league_explicit']]
assert not prior_ids&{v['fid'] for v in additional}
ep.update((r['fid'],r) for r in additional)
exec(src[src.index('hist=sorted(ep.values()'):src.index("out={'raw_verified'")])
tr=[r for r in valid if r['year']<2026];te=[r for r in valid if r['year']==2026]
out={'confirmed_n':len(ep),'added_n':len(additional),'train_n':len(tr),'groups':{}}
for kind in ('market','market_performance'):
 X=np.array([features(r,kind) for r in tr]);Xt=np.array([features(r,kind) for r in te])
 h=goals_predict(X,vec(tr,'hg'),np.log(vec(tr,'mh')),Xt,np.log(vec(te,'mh')))
 a=goals_predict(X,vec(tr,'ag'),np.log(vec(tr,'ma')),Xt,np.log(vec(te,'ma')))
 w,l=ou_wl(h+a,vec(te,'ol'));eo=w*(vec(te,'oo')-1)-l;eu=l*(vec(te,'ou')-1)-w
 pnl=np.where(eo>=eu,vec(te,'over_U'),vec(te,'under_U'));ev=np.maximum(eo,eu)
 masks={'all':np.ones(len(te),bool),'H1':np.array([r['date'][5:7]<='06' for r in te]),'H2':np.array([r['date'][5:7]>'06' for r in te]),'newly_matched':np.array([r['fid'] not in prior_ids for r in te]),'original_H2':np.array([r['fid'] in prior_ids and r['date'][5:7]>'06' for r in te])}
 for l in ('1','14'):masks['H2|'+l]=np.array([r['league']==l and r['date'][5:7]>'06' for r in te])
 for name,m in masks.items():out['groups'].setdefault(name,{})[kind]={'all':stat(pnl[m]),'positive_EV_diagnostic':stat(pnl[m&(ev>1e-9)])}
(P/'m8_espn_ou_confirmed_coverage_replay_20261115.json').write_text(json.dumps(out,indent=2))
(P/'m8_espn_performance_confirmed_expanded_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in ep.values()))
print(json.dumps(out),flush=True)
