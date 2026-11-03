from pathlib import Path
import json,sys,collections,statistics,math
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
rows=[x for x in o.rows_for('m3') if x['market']=='OU' and x['pnl'] is not None]
ids={r['id']:r for r in rows};selected={r['id']:r for r in rows}
# The displayed order id is event id; source forecast_id mapping requires original order events.
ledger=Path.home()/'QuantAsiaDesk/repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl'
keys=set(r['fixture'] for r in rows)
early={};forecasts={};read=0
for line in ledger.open():
 if not line.strip():continue
 x=json.loads(line);kind=x.get('protocol')
 if kind=='M3_SHADOW_ORDER_V1' and x.get('market')=='OU' and x.get('event_id') in ids:
  early[x['event_id']]=x['forecast_id']
 elif kind=='M3_TOTALCORNER_FORWARD_FORECAST_V1':
  forecasts[x['forecast_id']]=x
res=collections.defaultdict(list);bad=collections.Counter()
for eid,oid in ids.items():
 fid=early.get(eid)
 f=forecasts.get(fid)
 if not f:bad['no forecast']+=1;continue
 grid=f['score_probability_grid']
 try:
  z=sum(float(p) for row in grid for p in row)
  mean=sum((h+a)*float(p) for h,row in enumerate(grid) for a,p in enumerate(row))/z
  if not math.isfinite(mean) or abs(z-1)>.01:bad['invalid grid']+=1;continue
 except Exception:bad['error']+=1;continue
 actual=oid['result']['home']+oid['result']['away']
 res[oid['submodel']].append((oid,mean,actual))
print('GRID_COVERAGE',dict(bad),{k:len(v) for k,v in res.items()})
for model,records in res.items():
 print('MODEL',model,'n',len(records),'mean_grid_total',round(statistics.mean(x[1] for x in records),4),'mean_actual_goals',round(statistics.mean(x[2] for x in records),4),'mean_error_actual_minus_pred',round(statistics.mean(x[2]-x[1] for x in records),4))
 for side in ('小球','大球'):
  group=[x for x in records if x[0]['direction']==side]
  if group:print(' SIDE',side,'n',len(group),'pred_total',round(statistics.mean(x[1] for x in group),4),'actual_total',round(statistics.mean(x[2] for x in group),4),'difference',round(statistics.mean(x[2]-x[1] for x in group),4))
 # by kickoff day: assess whether actual exceeds model expected systematic or weekend spikes
 for day in sorted(set(x[0]['kickoff'][:10] for x in records)):
  g=[x for x in records if x[0]['kickoff'].startswith(day)]
  print(' DATE',day,'n',len(g),'goal_diff_actual_minus_pred',round(statistics.mean(x[2]-x[1] for x in g),4))
