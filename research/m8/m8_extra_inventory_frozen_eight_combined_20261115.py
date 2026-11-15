import json, collections, datetime, statistics
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Reconstruct the eight old cohorts exactly from the previously published code.
exec((P/'m8_score_market_divergence_full_AH_20261114.py').read_text().split('out={}\n')[0])
old=[{**r,'pnl':prior[(r['year'],r['fid'])][1],'cohort':prior[(r['year'],r['fid'])][0]} for r in A if (r['year'],r['fid']) in prior]
old.extend({**r,'pnl':r['contra_U'],'cohort':'G'} for r in G[('shape_relation','reverted','agree')])
extra=list(map(json.loads,(P/'m8_extra_inventory_frozen_eight_20261115.jsonl').open()))
new=[r for r in extra if r.get('cohort')]
assert len(old)==8956 and len(new)==1337
assert not {r['fid'] for r in old}&{r['fid'] for r in new}
def stat(rs):
 n=len(rs);u=sum(r['pnl'] for r in rs)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def yr(rs):return {str(y):stat([r for r in rs if r['year']==y]) for y in range(2019,2027)}
out={'old_all':stat(old),'new_all':stat(new),'combined_all':stat(old+new),'groups':{},'years':{'old':yr(old),'new':yr(new),'combined':yr(old+new)},'new_dates':{str(y):[min(r['date'] for r in extra if r['year']==y),max(r['date'] for r in extra if r['year']==y)] for y in sorted({r['year'] for r in extra})}}
for k in ['base','A','B','C','D','E','F','G']:
 a=[r for r in old if r['cohort']==k];b=[r for r in new if r['cohort']==k]
 out['groups'][k]={'old':stat(a),'new':stat(b),'combined':stat(a+b),'combined_2026':stat([r for r in a+b if r['year']==2026])}
for tag,rows in [('old',old),('combined',old+new)]:
 z=[r for r in rows if r['year']==2026];w=collections.Counter()
 for r in z:
  t=datetime.date.fromisoformat(r['date']).isocalendar();w[f'{t.year}-W{t.week:02}']+=1
 out[tag+'_2026_weekly']={'count':len(z),'weeks_with_signals':len(w),'mean_active_weeks':round(statistics.mean(w.values()),3),'max':max(w.values()),'weeks':dict(sorted(w.items()))}
 print(tag,'2026',stat(z),out[tag+'_2026_weekly'],flush=True)
print('ALL_GROUPS',json.dumps(out['groups'],ensure_ascii=False),flush=True)
print('ANNUAL',out['years'],'ALL',out['old_all'],out['new_all'],out['combined_all'],'DATES',out['new_dates'],flush=True)
(P/'m8_extra_inventory_frozen_eight_combined_20261115.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
