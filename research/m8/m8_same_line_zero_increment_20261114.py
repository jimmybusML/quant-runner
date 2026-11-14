import json,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
old=json.load((P/'m8_late_full_path_expansion_combos_20261114.json').open())
print('OLD_KEYS',list(old['base+A+B+C+D']),flush=True)
rows=[json.loads(l) for l in (P/'m8_same_line_probability_path_20261114.jsonl').open()]
def sign(x):return 1 if x>1e-9 else -1 if x<-1e-9 else 0
groups=collections.defaultdict(list)
for r in rows:
 if not r['end_zero']:continue
 a,b=sign(r['p3']-r['p0']),sign(r['p1']-r['p3']);net=sign(r['p1']-r['p0'])
 s=net or a or b or sign(r['last_move'])
 if not s or not r['n_price_moves']:continue
 if r['up_moves'] and r['down_moves'] and not net:
  side='away' if s>0 else 'home';g='E_return'
 elif (not r['up_moves'] or not r['down_moves']) and a==0 and b*s==1:
  side='home' if s>0 else 'away';g='F_late_monotonic'
 else:continue
 groups[g].append({**r,'pnl':r['end_'+side+'_U'],'side':side})
allrows=groups['E_return']+groups['F_late_monotonic']
def st(z):
 n=len(z);u=sum(r['pnl'] for r in z)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
era=lambda r:'2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
result={}
for k,z in {**groups,'E+F':allrows}.items():
 result[k]={e:st([r for r in z if era(r)==e]) for e in ('2019-23','2024-25','2026')}
 result[k].update({name:st([r for r in z if r['year']==2026 and (r['month']<='2026-06')==h]) for name,h in [('2026_H1',True),('2026_H2',False)]})
 result[k]['annual']={str(y):st([r for r in z if r['year']==y]) for y in range(2019,2027)}
 print('NEW',k,result[k],flush=True)
# verify actual fixture independence with former exact cohort rules
oldraw=[json.loads(l) for l in (P/'m8_late_full_path_water_features_20261114.jsonl').open()]
oldgroups=collections.defaultdict(list)
for r in oldraw:
 if r['base']:g='base';p=r['base_U']
 elif r.get('path_6_3_1')=='deepen_weaken':g='A';p=r['end_dog_U']
 elif r.get('path_6_3_1')=='weaken_same':g='B';p=r['end_dog_U']
 elif not r['end_zero'] and r['path_shape']=='oscillating':g='C';p=r['end_fav_U']
 elif r['end_zero'] and r['path_shape']=='reverted' and r['home_price_vs_timeavg'] is not None and r['home_price_vs_timeavg']-r['away_price_vs_timeavg']<-1e-9:g='D';p=r['end_away_U']
 else:continue
 oldgroups[g].append({**r,'pnl':p})
assert len({(r['year'],r['fid']) for r in allrows})==len(allrows)
assert not ({(r['year'],r['fid']) for r in allrows}&{(r['year'],r['fid']) for z in oldgroups.values() for r in z})
for label,gs in [('five_plus_EF',['base','A','B','C','D']),('four_plus_EF',['base','A','C','D'])]:
 z=[r for g in gs for r in oldgroups[g]]+allrows
 v=[r for r in z if r['year']==2026]
 weeks=collections.Counter()
 for r in v:
  w=datetime.date.fromisoformat(r['date']).isocalendar();weeks[f'{w.year}-W{w.week:02}']+=1
 result[label]={e:st([r for r in z if era(r)==e]) for e in ('2019-23','2024-25','2026')}
 result[label]['weekly']={'max':max(weeks.values()),'mean_44_weeks':round(len(v)/44,2)}
 print('COMBO',label,result[label],flush=True)
(P/'m8_same_line_zero_increment_20261114.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
