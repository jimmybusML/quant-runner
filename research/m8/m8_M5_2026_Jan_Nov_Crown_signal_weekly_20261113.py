import json,collections,datetime,statistics
import numpy as np
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
raw=[json.loads(z) for z in (P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()]
a=[r for r in raw if r['month'].startswith('2026') and r['month']<='2026-11']
signal=[r for r in a if r['direction']=='deepen']
def s(x,field='dog_U'):
 n=len(x);p=sum(z[field] for z in x)
 return {'n':n,'net_U':round(p,3),'ROI_pct':round(p/n*100,3) if n else None}
rng=np.random.default_rng(20261113)
days=collections.defaultdict(float)
for r in signal:days[r['date']]+=r['dog_U']
arr=np.asarray(list(days.values()));d=len(arr);n=len(signal)
rep=np.array([arr[rng.integers(d,size=d)].sum()*100/n for _ in range(6000)])
print('COMBINED Jan-Nov historically',s(signal),'day_bootstrap95',[round(float(x),3) for x in np.percentile(rep,[2.5,97.5])],'all',len(a),'future_2025_dec',len(raw)-len(a),flush=True)
weeks=collections.defaultdict(list)
for r in a:
 dt=datetime.date.fromisoformat(r['date']);w=dt.isocalendar();k=f'{w.year}-W{w.week:02}'
 weeks[k].append(r)
weekly=[]
for w,x in sorted(weeks.items()):
 cand=[r for r in x if r['direction']=='deepen']
 weekly.append({'week':w,'all_valid_nonzero':len(x),'deepen':len(cand),'deepen_net_U':s(cand)['net_U'],'deepen_roi_pct':s(cand)['ROI_pct']})
print('WEEKS',len(weekly),'max',max(x['deepen'] for x in weekly),'median',statistics.median(x['deepen'] for x in weekly),'avg',round(statistics.mean(x['deepen'] for x in weekly),2))
print('TOP',sorted(weekly,key=lambda x:-x['deepen'])[:12])
print('YEAR month 2026-01..11 weekly',weekly[:7],weekly[-6:])
(P/'m8_M5_2026_Jan_Nov_Crown_signal_weekly_20261113.json').write_text(json.dumps({'historical_retrieval_not_realtime':True,'historical_deepen_year':s(signal),'observed_data_day_bootstrap95_roi_pct':[round(float(x),3) for x in np.percentile(rep,[2.5,97.5])],'valid_nonzero_year':len(a),'full_weeks_and_partial_weeks':weekly,'highest_week_candidate_count':max(x['deepen'] for x in weekly),'median_week_candidate_count':statistics.median(x['deepen'] for x in weekly),'no_new_production_filters':True},ensure_ascii=False,indent=2))
