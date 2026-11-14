import json,collections,datetime,statistics,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_late_full_path_water_features_20261114.jsonl').open()]
assert len(rows)==39101
def group(r):
 if r['base']:return 'original'
 if r.get('path_6_3_1')=='deepen_weaken':return 'A'
 if r.get('path_6_3_1')=='weaken_same':return 'B'
 return 'remaining'
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
def sign(v):
 if v is None:return 'unknown'
 return 'above' if v>1e-9 else 'below' if v<-1e-9 else 'equal'
def st(z,k):
 v=[r[k] for r in z if r.get(k) is not None];n=len(v);u=sum(v)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def report(z,k):
 return {e:st([r for r in z if era(r)==e],k) for e in ('2019-23','2024-25','2026')}|{'2026_H1':st([r for r in z if r['year']==2026 and r['month']<='2026-06'],k),'2026_H2':st([r for r in z if r['year']==2026 and r['month']>='2026-07'],k)}
G=collections.defaultdict(list)
for r in rows:
 r['cohort']=group(r)
 if r['end_zero']:
  r['market']='zero'
  r['price_relative']=sign(None if r['home_price_vs_timeavg'] is None else r['home_price_vs_timeavg']-r['away_price_vs_timeavg'])
  r['p1']=r['end_home_U'];r['p2']=r['end_away_U']
 else:
  r['market']='nonzero';r['price_relative']=sign(r['dog_price_vs_timeavg'])
  r['p1']=r['end_dog_U'];r['p2']=r['end_fav_U']
 if r['cohort']!='remaining':continue
 # Three independently reported research decompositions, never a production filter.
 G[('shape',r['market'],r['path_shape'])].append(r)
 G[('shape_price',r['market'],r['path_shape'],r['price_relative'])].append(r)
 if r['market']=='nonzero':
  G[('shape_lastmove',r['market'],r['path_shape'],sign(r['fav_last_move']))].append(r)
  G[('phase_price',r['market'],r['path_6_3_1'],r['price_relative'])].append(r)
result={'source':'same 39101 complete historical Crown paths T6-T1, all results computed at T1, previous original/A/B retained, remaining studied separately, no production rules','groups':{},'cohort_2026':dict(collections.Counter(r['cohort'] for r in rows if r['year']==2026))}
for key,z in sorted(G.items()):
 field='|'.join(key);s={k:report(z,k) for k in ('p1','p2')}
 result['groups'][field]=s
 if key[0]=='shape':print('SHAPE',field,s,flush=True)
 # show broad historical positive leads but preserve all groups in result.
 for k,t in s.items():
  if all(t[e]['ROI'] is not None and t[e]['ROI']>0 for e in ('2019-23','2024-25','2026')):
   print('ALL3_POS',field,k,t,flush=True)
# One disjoint full partition using path shape and final-price relative to same-line time-weighted mean.
# Fit research-only group mean on older years, choose side with higher empirical mean. Evaluate even negative expected groups;
# second counterfactual adds only positive training estimates, clearly a tested research method, not an approved restriction.
partition=[(key,z) for key,z in G.items() if key[0]=='shape_price']
def train_test(selected_mode):
 pred=[];learned={}
 for key,z in partition:
  training=[r for r in z if r['year']<=2023]
  if not training:continue
  a,b=st(training,'p1'),st(training,'p2')
  side=max(('p1','p2'),key=lambda k:st(training,k)['ROI'])
  value=st(training,side)['ROI'];learned['|'.join(key)]={'side':side,'train_ROI':value,'train_n':len(training)}
  for r in z:
   if selected_mode=='all' or value>0:
    pred.append({**r,'pnl':r[side]})
 return {'study':selected_mode,'results':report(pred,'pnl'),'learned':learned}
for mode in ('all','positive_training_estimate'):
 v=train_test(mode);result['fit_'+mode]=v
 print('TRAIN_TEST',mode,v['results'],flush=True)
print('COVERAGE',result['cohort_2026'],flush=True)
(P/'m8_late_full_path_water_structure_20261114.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
