import json,collections,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
SOURCE=P/'m8_early_AH_same_line_water_movement_2019to2026_20261114.jsonl'
BASE={r['fid'] for r in map(json.loads,(P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()) if '2026-01'<=r['month']<='2026-11' and r['direction']=='deepen'}
C=collections.Counter()
STATS=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.,set()]))
def period(y):
 return '2019-2023' if y<=2023 else '2024-2025' if y<=2025 else '2026'
def fmt(t):return {'n':t[0],'net_U':round(t[1],3),'ROI_pct':round(t[1]*100/t[0],3) if t[0] else None}
for a in map(json.loads,SOURCE.open()):
 w=a['window'];p=period(a['year'])
 groups=[]
 if not a['line_same']:
  continue
 C['same_line_all']+=1
 if a['rise_side'] is None:continue
 C['same_line_moved_price']+=1
 hs=a['homechange'];az=a['awaychange']
 # Direct opponent odds move without any extra magnitude gate; explore distinct directions for both
 groups.append(('same_line_rising_price_side','rise_side_U'))
 groups.append(('same_line_falling_price_side','fall_side_U'))
 # Nonzero AH sides preserve marker without applying extra threshold.
 if not a['end_zero']:
  if a['dogchange'] is not None and a['dogchange']>0:
   groups.append(('same_line_dog_odds_rise','underdog_U'))
   groups.append(('same_line_dog_odds_rise_but_buy_fav','favorite_U'))
  if a['dogchange'] is not None and a['dogchange']<0:
   groups.append(('same_line_dog_odds_fall','underdog_U'))
  if a['favchange'] is not None and a['favchange']>0:
   groups.append(('same_line_favorite_odds_rise','favorite_U'))
   groups.append(('same_line_favorite_odds_rise_but_buy_dog','underdog_U'))
  if a['favchange'] is not None and a['favchange']<0:
   groups.append(('same_line_favorite_odds_fall','favorite_U'))
  if a['line_reverted']:
   groups.append(('same_line_reverted_rising_price_side','rise_side_U'))
 # Exploratory bins only, not official terms:
 delta=abs(hs-az)
 if delta<=.02:strength='weak_delta<=0.02'
 elif delta<=.05:strength='medium_delta_0.02_to_0.05'
 elif delta<=.1:strength='larger_delta_0.05_to_0.1'
 else:strength='strong_delta>0.1'
 groups.extend([('same_line_rising_price_side|'+strength,'rise_side_U'),('same_line_falling_price_side|'+strength,'fall_side_U')])
 for key,field in groups:
  if a[field] is None:continue
  t=STATS[(w,key)][p];t[0]+=1;t[1]+=a[field]
  if p=='2026':t[2].add(a['fid'])
def groupout(w,k):
 raw=STATS.get((w,k))
 if not raw:return None
 v={per:fmt(raw[per]) for per in ('2019-2023','2024-2025','2026')}
 if sum(x['n'] for x in v.values())<=0:return None
 xx=raw['2026'][2]
 v['2026_new_unique_vs_base_1182']={'n':len(xx-BASE),'overlap':len(xx&BASE)}
 return v
windows=['24->18','24->12','24->6','20->12','18->12','12->6','12->3','12->1','8->4','6->1']
keys=['same_line_rising_price_side','same_line_falling_price_side','same_line_dog_odds_rise','same_line_dog_odds_rise_but_buy_fav','same_line_dog_odds_fall','same_line_favorite_odds_rise','same_line_favorite_odds_rise_but_buy_dog','same_line_favorite_odds_fall','same_line_reverted_rising_price_side']
OUT={'source':'Crown original49 AH historical price at comparable pregame event-hour snapshots, 2019-2025 separate M7 original, 2026 M5 original; all price-changed same-line fixtures included and no rule changed. 2026 is in-sample exploratory despite distinct history.','coverage':dict(C),'baseline_size_2026':len(BASE),'studies':{}}
for w in windows:
 print('\nWINDOW',w,flush=True);row={}
 for k in keys:
  v=groupout(w,k)
  if v:row[k]=v;print(k,'older',v['2019-2023'],'2024-25',v['2024-2025'],'2026',v['2026'],'NEW',v['2026_new_unique_vs_base_1182'],flush=True)
 OUT['studies'][w]=row
# also preserve strength bins for result audit
OUT['exploratory_strength']={}
for w in windows:
 for k in list(STATS):
  if k[0]!=w or 'delta' not in k[1]:continue
  OUT['exploratory_strength'].setdefault(w,{})[k[1]]=groupout(*k)
(P/'m8_early_AH_water_signal_vintages_and_incremental_20261114.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2))
