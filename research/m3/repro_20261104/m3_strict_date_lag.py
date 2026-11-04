"""M3 goal-mean bias correction with conservative prequential date lag.

Only use games from at least 2 UTC calendar dates earlier, avoiding
same-day and immediately prior-date kickoff/results ambiguity.
Offline methodology, not a trading threshold or production rule.
"""
from datetime import date,timedelta
from pathlib import Path
import json,sys,statistics
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
rows={r['id']:r for r in o.rows_for('m3') if r['market']=='OU' and r['submodel']=='泊松' and r['pnl'] is not None}
ids={};forecast={}
p=Path.home()/'QuantAsiaDesk/repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl'
for l in p.open():
 x=json.loads(l)
 if x.get('protocol')=='M3_SHADOW_ORDER_V1' and x.get('event_id') in rows:ids[x['event_id']]=x['forecast_id']
 elif x.get('protocol')=='M3_TOTALCORNER_FORWARD_FORECAST_V1':forecast[x['forecast_id']]=x
records=[]
for k,r in rows.items():
 f=forecast.get(ids.get(k))
 if not f:continue
 g=f['score_probability_grid']
 z=sum(float(v) for row in g for v in row)
 exp=sum((i+j)*float(v) for i,row in enumerate(g) for j,v in enumerate(row))/z
 records.append({'day':date.fromisoformat(r['kickoff'][:10]),'err':r['result']['home']+r['result']['away']-exp})
total=0;baseline=0;adj=0
for day in sorted(set(r['day'] for r in records)):
 prior=[r for r in records if r['day']<=day-timedelta(days=2)]
 cases=[r for r in records if r['day']==day]
 if not prior:continue
 offset=statistics.mean(r['err'] for r in prior)
 total+=len(cases)
 baseline+=sum(r['err']**2 for r in cases)
 adj+=sum((r['err']-offset)**2 for r in cases)
 print(day,'prior',len(prior),'eval',len(cases),'offset',round(offset,4))
print('STRICT_COMPLETE_DAY_BUFFER','eval',total,'baseline_mse',round(baseline/total,4),'adjusted_mse',round(adj/total,4))
