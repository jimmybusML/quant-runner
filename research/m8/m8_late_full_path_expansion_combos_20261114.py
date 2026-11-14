import json,collections,datetime,statistics
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_late_full_path_water_features_20261114.jsonl').open()]
groups=collections.defaultdict(list)
for r in rows:
 if r['base']:name='base';pnl=r['base_U']
 elif r.get('path_6_3_1')=='deepen_weaken':name='A';pnl=r['end_dog_U']
 elif r.get('path_6_3_1')=='weaken_same':name='B';pnl=r['end_dog_U']
 elif not r['end_zero'] and r['path_shape']=='oscillating':name='C';pnl=r['end_fav_U']
 elif r['end_zero'] and r['path_shape']=='reverted' and r['home_price_vs_timeavg'] is not None and r['home_price_vs_timeavg']-r['away_price_vs_timeavg']<-1e-9:
  name='D';pnl=r['end_away_U']
 else:continue
 groups[name].append({**r,'pnl':pnl})
def stat(z):
 n=len(z);u=sum(r['pnl'] for r in z)
 return {'n':n,'U':round(u,3),'ROI':round(u*100/n,3) if n else None}
def summary(z):
 d={k:stat([r for r in z if lo<=r['year']<=hi]) for k,lo,hi in [('2019-23',2019,2023),('2024-25',2024,2025),('2026',2026,2026)]}
 d['annual']={str(y):stat([r for r in z if r['year']==y]) for y in range(2019,2027)}
 a=[r for r in z if r['year']==2026]
 d['2026_H1']=stat([r for r in a if r['month']<='2026-06']);d['2026_H2']=stat([r for r in a if r['month']>='2026-07'])
 d['monthly']={m:stat([r for r in a if r['month']==m]) for m in (f'2026-{i:02}' for i in range(1,12))}
 wk=collections.Counter();days=collections.defaultdict(lambda:[0.,0])
 for r in a:
  w=datetime.date.fromisoformat(r['date']).isocalendar();wk[f'{w.year}-W{w.week:02}']+=1
  days[r['date']][0]+=r['pnl'];days[r['date']][1]+=1
 d['weekly']={'active_weeks':len(wk),'mean_per_original44_weeks':round(len(a)/44,2),'max':max(wk.values()) if wk else 0,'counts':dict(sorted(wk.items()))}
 if days:
  arr=np.array(list(days.values()));rng=np.random.default_rng(261114);boot=[]
  for i in range(3000):
   s=arr[rng.integers(len(arr),size=len(arr))].sum(axis=0);boot.append(s[0]*100/s[1])
  d['2026descriptive_day_bootstrap95']=[round(float(v),3) for v in np.percentile(boot,[2.5,97.5])]
 return d
result={}
for name,names in [('C',['C']),('D',['D']),('C+D',['C','D']),('base+A',['base','A']),('base+A+C+D',['base','A','C','D']),('base+A+B',['base','A','B']),('base+A+B+C+D',['base','A','B','C','D'])]:
 z=[r for n in names for r in groups[n]]
 assert len(z)==len({(r['year'],r['fid']) for r in z})
 s=summary(z);result[name]=s
 print(name,{k:s[k] for k in ('2019-23','2024-25','2026','2026_H1','2026_H2','2026descriptive_day_bootstrap95')}, {k:v for k,v in s['weekly'].items() if k!='counts'},flush=True)
(P/'m8_late_full_path_expansion_combos_20261114.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
