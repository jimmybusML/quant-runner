import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
src=P/'m8_early_AH_same_line_water_movement_2019to2026_20261114.jsonl'
TRIPLES=[('24->18','18->12','24/18/12'),('24->12','12->6','24/12/6'),('20->12','12->6','20/12/6'),('18->12','12->6','18/12/6')]
needed={r for a,b,c in TRIPLES for r in (a,b)}
idx=collections.defaultdict(dict)
for r in map(json.loads,src.open()):
 if r['window'] in needed:idx[(r['source'],r['fid'])][r['window']]=r
base={r['fid'] for r in map(json.loads,(P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()) if r['direction']=='deepen' and '2026-01'<=r['month']<='2026-11'}
G=collections.defaultdict(lambda:collections.defaultdict(list))
picked=collections.defaultdict(list)
def s(a,b,final):
 d=b-a
 return 'deepen' if d*final>0 else 'weaken' if d*final<0 else 'unchanged'
for (src_name,fid),segments in idx.items():
 for w1,w2,triple in TRIPLES:
  if w1 not in segments or w2 not in segments:continue
  a=segments[w1];b=segments[w2]
  if b['end_zero']:continue
  # same middle-point from separate window's T-end and T-start
  if abs(a['end_line']-b['start_line'])>1e-8:continue
  first=s(a['start_line'],a['end_line'],b['end_line'])
  second=s(b['start_line'],b['end_line'],b['end_line'])
  v='2019-2023' if a['year']<=2023 else '2024-2025' if a['year']<=2025 else '2026'
  record={'fid':fid,'month':a['month'],'date':a['date'],'vintage':v,'path':first+'→'+second,'triple':triple,'first':a['start_line'],'middle':a['end_line'],'last':b['end_line'],'dog_U':b['underdog_U'],'fav_U':b['favorite_U'],'new_unique_in_2026':v=='2026' and fid not in base}
  G[(triple,record['path'])][v].append(record)
  if triple=='24/12/6' and record['path']=='weaken→deepen':picked[v].append(record)
def st(rows,side):
 n=len(rows);v=sum(x[side] for x in rows)
 return {'n':n,'net_U':round(v,3),'ROI_pct':round(v*100/n,3) if n else None}
out={'triples':{},'recommended_status':'All paths research comparisons only, not production','base_2026':len(base)}
for (triple,pat),v in sorted(G.items()):
 a={}
 for vint in ('2019-2023','2024-2025','2026'):
  r=v[vint]
  a[vint]={'dog':st(r,'dog_U'),'fav':st(r,'fav_U')}
  if vint=='2026':
   extra=[x for x in r if x['new_unique_in_2026']]
   a[vint]['distinct_2026_extra']={'dog':st(extra,'dog_U'),'fav':st(extra,'fav_U')}
 out['triples'].setdefault(triple,{})[pat]=a
 print('TRIPLE',triple,pat,'2019-23',a['2019-2023'],'2024-25',a['2024-2025'],'2026',a['2026'],flush=True)
# Composition example: candidate from 24/12/6, no overlap with 6->1 2026 base
x=picked['2026'];extra=[r for r in x if r['new_unique_in_2026']]
old={r['fid']:r['dog_U'] for r in map(json.loads,(P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()) if r['direction']=='deepen' and '2026-01'<=r['month']<='2026-11'}
result=[*old.values(),*(r['fav_U'] for r in extra)]
out['specific_weaken_then_deepen_at_T6']={'all_year2026':st(x,'fav_U'),'extra_vs_base':st(extra,'fav_U'),'combined_with_original_2026':{'n':len(result),'net_U':round(sum(result),3),'ROI_pct':round(100*sum(result)/len(result),3)},'2026_early':st([r for r in extra if r['month']<='2026-06'],'fav_U'),'2026_later':st([r for r in extra if r['month']>='2026-07'],'fav_U'),'months':{}}
for m in sorted(set(r['month'] for r in extra)):
 out['specific_weaken_then_deepen_at_T6']['months'][m]=st([r for r in extra if r['month']==m],'fav_U')
print('COMPOSITION',out['specific_weaken_then_deepen_at_T6'],flush=True)
(P/'m8_early_AH_three_point_12h_and_6h_pattern_vintages_20261114.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
