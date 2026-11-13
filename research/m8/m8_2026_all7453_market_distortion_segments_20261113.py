import json,collections,datetime,statistics,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(z) for z in (P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()]
rows=[r for r in rows if '2026-01'<=r['month']<='2026-11']
def performance(a,field):
 n=len(a);p=sum(x[field] for x in a)
 return {'matches':n,'net_U':round(p,3),'ROI_pct':round(100*p/n,3) if n else None}
def period(r):return 'Jan-Jun' if r['month']<='2026-06' else 'Jul-Nov'
def segment(r):
 ln=abs(r['AH_t1_line']);price=r['AH_t1_odds_home'] if r['dog_side']=='home' else r['AH_t1_odds_away']
 if ln<=.5:depth='0.25-0.5'
 elif ln<=1:depth='0.75-1'
 elif ln<=1.5:depth='1.25-1.5'
 else:depth='>=1.75'
 if price<1.85:odd='<1.85'
 elif price<2:odd='1.85-<2'
 else:odd='>=2'
 shift=abs(r['AH_t1_line']-r['AH_t6_line'])
 if shift==0:move='0'
 elif shift<=.25:move='0.25'
 elif shift<=.5:move='0.5'
 else:move='>=.75'
 age=r['AH_t1_event_age_hours']
 if age<=.25:fresh='within15m'
 elif age<=1:fresh='15-60m'
 else:fresh='over60m'
 return [('direction',r['direction']),('line_depth',depth),('dog_quote_decimal',odd),('line_movement_size',move),('T1_last_event_age',fresh),('league_id',r['league_id']),('direction_x_line_depth',r['direction']+'|'+depth),('direction_x_dog_quote',r['direction']+'|'+odd),('direction_x_line_movement',r['direction']+'|'+move),('direction_x_T1_event_age',r['direction']+'|'+fresh)]
groups=collections.defaultdict(list)
for r in rows:
 for k,v in segment(r):groups[(k,v)].append(r)
output={'source':'historical Crown asian_list full 49 leagues 2026, 7453 valid nonzero AH as-of T6 and T1, no new production filters. Grouping for research only.','all':performance(rows,'dog_U'),'groups':{}}
for (k,v),g in sorted(groups.items()):
 z={'all_dog':performance(g,'dog_U'),'all_fav':performance(g,'fav_U'),'period':{},'months':{}}
 for label in ('Jan-Jun','Jul-Nov'):
  sub=[r for r in g if period(r)==label]
  z['period'][label]={'dog':performance(sub,'dog_U'),'fav':performance(sub,'fav_U')}
 for m in sorted({r['month'] for r in g}):
  z['months'][m]=performance([r for r in g if r['month']==m],'dog_U')
 output['groups'].setdefault(k,{})[v]=z
print('ALL',performance(rows,'dog_U'),performance(rows,'fav_U'),flush=True)
for typ in ['direction','line_depth','dog_quote_decimal','direction_x_line_depth','direction_x_dog_quote','direction_x_line_movement','direction_x_T1_event_age']:
 print('\nSEGMENT',typ,flush=True)
 for k,z in output['groups'].get(typ,{}).items():
  print(k,'dog',z['all_dog'],'fav',z['all_fav'],'first',z['period']['Jan-Jun']['dog'],'later',z['period']['Jul-Nov']['dog'],flush=True)
P.joinpath('m8_2026_all7453_market_distortion_segments_20261113.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
