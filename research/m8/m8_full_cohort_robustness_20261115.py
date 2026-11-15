import json,collections,datetime,statistics
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
old=[{**r,'pnl':prior[(r['year'],r['fid'])][1],'cohort':prior[(r['year'],r['fid'])][0],'vintage':'original'} for r in A if (r['year'],r['fid']) in prior]
old.extend({**r,'pnl':r['contra_U'],'cohort':'G','vintage':'original'} for r in G[('shape_relation','reverted','agree')])
extra=[{**r,'vintage':'added'} for r in map(json.loads,(P/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()) if r.get('cohort')]
new=[{**r,'vintage':'database_audit'} for r in map(json.loads,(P/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl').open()) if r.get('cohort')]
Z=old+extra+new
assert len(Z)==10294 and len({r['fid'] for r in Z})==len(Z)
assert abs(sum(r['pnl'] for r in Z)-236.015)<1e-6
def stat(z):
 n=len(z);u=sum(r['pnl'] for r in z)
 if not n:return {'n':0,'U':0,'ROI':None}
 byday=collections.defaultdict(float);w=collections.defaultdict(float);m=collections.defaultdict(float);l=collections.defaultdict(lambda:[0.,0])
 for r in z:
  byday[r['date']]+=r['pnl'];dt=datetime.date.fromisoformat(r['date']).isocalendar()
  w[f'{dt.year}-W{dt.week:02}']+=r['pnl'];m[r['month']]+=r['pnl'];l[r['league']][0]+=r['pnl'];l[r['league']][1]+=1
 equity=peak=dd=0.;peakdate=None;ddstart=ddend=None
 for day,x in sorted(byday.items()):
  equity+=x
  if equity>=peak:peak=equity;peakdate=day
  if peak-equity>dd:dd=peak-equity;ddstart=peakdate;ddend=day
 best=max(l,key=lambda k:l[k][0]);worst=min(l,key=lambda k:l[k][0])
 leave=[(100*(u-v[0])/(n-v[1]),k) for k,v in l.items() if n>v[1]]
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3),'daily_marked_max_drawdown_U':round(dd,3),'drawdown_peak_day':ddstart,'drawdown_trough_day':ddend,'positive_week_count':sum(x>1e-9 for x in w.values()),'active_week_count':len(w),'positive_month_count':sum(x>1e-9 for x in m.values()),'active_month_count':len(m),'best_league':{'id':best,'n':l[best][1],'U':round(l[best][0],3)},'worst_league':{'id':worst,'n':l[worst][1],'U':round(l[worst][0],3)},'leave_one_league_out_min_ROI':round(min(leave)[0],3) if leave else None,'leave_one_league_out_max_ROI':round(max(leave)[0],3) if leave else None}
out={}
for c in ('base','A','B','C','D','E','F','G','all'):
 a=[r for r in Z if r['cohort']==c or c=='all'];v=[r for r in a if r['year']==2026];q=[r for r in a if r['vintage']!='original']
 rec={'all':stat(a),'2026':stat(v),'additional_archive':stat(q),'annual':{str(y):stat([r for r in a if r['year']==y]) for y in range(2019,2027)}}
 out[c]=rec
 print('COHORT',c,'ALL',rec['all'],'2026',rec['2026'],'NEW',rec['additional_archive'],flush=True)
# No altered combination adopted; compare previous eight only, excluding single cohort for attribution, not rule.
out['leave_one_cohort_out']={c:{'all':stat([r for r in Z if r['cohort']!=c]),'2026':stat([r for r in Z if r['cohort']!=c and r['year']==2026])} for c in ('base','A','B','C','D','E','F','G')}
(P/'m8_full_cohort_robustness_20261115.json').write_text(json.dumps(out,indent=2))
