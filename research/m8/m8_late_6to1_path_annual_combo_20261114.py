import json,collections,datetime,statistics
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows=[json.loads(l) for l in (P/'m8_late_6to1_dynamic_path_recovery_20261114.jsonl').open()]
baseline=[r for r in rows if r['base']]
a=[r for r in rows if not r['base'] and r.get('path_6_3_1')=='deepen_weaken']
b=[r for r in rows if not r['base'] and r.get('path_6_3_1')=='weaken_same']
def pnl(r):return r['base_U'] if r['base'] else r['end_dog_U']
def st(z):
 n=len(z);u=sum(pnl(r) for r in z)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
assert len({(r['year'],r['fid']) for r in rows})==len(rows)
groups={'base':baseline,'A':a,'B':b,'base+A':baseline+a,'base+B':baseline+b,'base+A+B':baseline+a+b}
result={}
for name,l in groups.items():
 sm={}
 for y in sorted({r['year'] for r in rows}):sm[str(y)]=st([r for r in l if r['year']==y])
 for k,lo,hi in [('2019-2023',2019,2023),('2024-2025',2024,2025),('2026',2026,2026)]:sm[k]=st([r for r in l if lo<=r['year']<=hi])
 z=[r for r in l if r['year']==2026]
 sm['monthly_2026']={m:st([r for r in z if r['month']==m]) for m in sorted({r['month'] for r in z})}
 weeks=collections.Counter()
 for r in z:
  d=datetime.date.fromisoformat(r['date']).isocalendar();weeks[f'{d.year}-W{d.week:02}']+=1
 sm['weekly_2026']={'active_weeks':len(weeks),'max':max(weeks.values()),'median':statistics.median(weeks.values()),'mean_active_week':round(statistics.mean(weeks.values()),2),'weeks':dict(sorted(weeks.items()))}
 # cluster bootstrap days, resample net and count jointly (not fixed-denominator)
 daily=collections.defaultdict(lambda:[0.,0])
 for r in z:daily[r['date']][0]+=pnl(r);daily[r['date']][1]+=1
 ar=np.array(list(daily.values()));rng=np.random.default_rng(20261114)
 boot=[]
 for _ in range(4000):
  rs=ar[rng.integers(len(ar),size=len(ar))].sum(axis=0);boot.append(rs[0]*100/rs[1])
 sm['2026_day_bootstrap95_descriptive']=[round(float(x),3) for x in np.percentile(boot,[2.5,97.5])]
 result[name]=sm
 print('GROUP',name,{p:sm[p] for p in ('2019-2023','2024-2025','2026')},'weeks',{k:v for k,v in sm['weekly_2026'].items() if k!='weeks'},'CI',sm['2026_day_bootstrap95_descriptive'],flush=True)
# league regimes for B: report all leagues with sample counts; difference within common old/new leagues, not a selection rule
leagues=sorted({r['league'] for r in b})
result['B_all_leagues']={}
for league in leagues:
 q=[r for r in b if r['league']==league]
 result['B_all_leagues'][league]={era:st([r for r in q if lo<=r['year']<=hi]) for era,lo,hi in [('2019-2023',2019,2023),('2024-2025',2024,2025),('2026',2026,2026)]}
print('B annual', {str(y):result['B'][str(y)] for y in range(2019,2027)},flush=True)
# 164 prior 2026 candidate is evaluated at same T1 and same underdog side; pairwise overlap exactly.
original2026=[r for r in map(json.loads,(P/'m8_M5_2026_Jan_Nov_full_Crown_AH_T6T1_replay_20261113.jsonl').open()) if '2026-01'<=r['month']<='2026-11']
prior={r['fid']:r for r in original2026 if r['direction']=='weaken' and .75<=abs(r['AH_t1_line'])<=1}
b0={r['fid']:r for r in baseline if r['year']==2026};a0={r['fid']:r for r in a if r['year']==2026};b1={r['fid']:r for r in b if r['year']==2026}
union={r['fid']:pnl(r) for r in baseline+a+b if r['year']==2026}
for fid,r in prior.items():
 if fid in union:assert abs(union[fid]-r['dog_U'])<1e-7
 else:union[fid]=r['dog_U']
result['prior_164_overlap']={'prior':len(prior),'overlap_A':len(set(prior)&set(a0)),'overlap_B':len(set(prior)&set(b1)),'overlap_base':len(set(prior)&set(b0)),'additional_distinct':len(set(prior)-set(a0)-set(b1)-set(b0)),'union_n':len(union),'union_net_U':round(sum(union.values()),3),'union_ROI':round(100*sum(union.values())/len(union),3)}
print('PRIOR',result['prior_164_overlap'],flush=True)
(P/'m8_late_6to1_path_annual_combo_20261114.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
