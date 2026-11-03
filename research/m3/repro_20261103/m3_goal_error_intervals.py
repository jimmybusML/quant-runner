from pathlib import Path
import json,sys,numpy as np
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
raw=o.rows_for('m3');rows=[x for x in raw if x['market']=='OU' and x['pnl'] is not None and x['submodel']=='泊松']
ids={r['id'] for r in rows};order_to_forecast={};grids={}
p=Path.home()/'QuantAsiaDesk/repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl'
for line in p.open():
 x=json.loads(line)
 if x.get('protocol')=='M3_SHADOW_ORDER_V1' and x.get('event_id') in ids:
  order_to_forecast[x['event_id']]=x['forecast_id']
 elif x.get('protocol')=='M3_TOTALCORNER_FORWARD_FORECAST_V1':
  grids[x['forecast_id']]=x['score_probability_grid']
records=[]
for x in rows:
 g=grids[order_to_forecast[x['id']]];total=sum(map(sum,g));pred=sum((h+a)*v for h,row in enumerate(g) for a,v in enumerate(row))/total
 records.append((x['direction'],x['result']['home']+x['result']['away']-pred))
rng=np.random.default_rng(198964)
for label,s in [('all',[x[1] for x in records]),('under',[x[1] for x in records if x[0]=='小球']),('over',[x[1] for x in records if x[0]=='大球'])]:
 a=np.array(s);sample=rng.choice(a,size=(8000,len(a)),replace=True).mean(axis=1);print(label,'n',len(a),'mean',round(float(a.mean()),4),'CI95',list(map(lambda z:round(float(z),4),np.quantile(sample,[.025,.975]))))
