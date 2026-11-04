#!/usr/bin/env python3
from pathlib import Path
import json,sys,collections,statistics,math
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
rows={r['id']:r for r in o.rows_for('m3') if r['market']=='OU' and r['submodel']=='泊松' and r['pnl'] is not None}
book=Path.home()/'QuantAsiaDesk/repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl'
ids={};forecast={}
for line in book.open():
 x=json.loads(line);t=x.get('protocol')
 if t=='M3_SHADOW_ORDER_V1' and x.get('event_id') in rows:ids[x['event_id']]=x['forecast_id']
 elif t=='M3_TOTALCORNER_FORWARD_FORECAST_V1':forecast[x['forecast_id']]=x
d=[]
for key,r in rows.items():
 f=forecast.get(ids.get(key))
 if not f:continue
 grid=f['score_probability_grid'];s=sum(float(v) for row in grid for v in row)
 actual=r['result']['home']+r['result']['away']
 preds={k:sum(float(v) for i,row in enumerate(grid) for j,v in enumerate(row) if i+j>=k)/s for k in (4,5,6,7)}
 d.append((r,actual,preds,len(grid),len(grid[0])))
print('GRID_SHAPES',collections.Counter((x[3],x[4]) for x in d))
for k in (4,5,6,7):
 exp=sum(x[2][k] for x in d)
 act=sum(x[1]>=k for x in d)
 print('TOTAL_GOALS_TAIL',k,'games',len(d),'forecast_events',round(exp,3),'observed_events',act,'obs_minus_forecast',round(act-exp,3),
       'observed_pct',round(act*100/len(d),1),'predicted_pct',round(exp*100/len(d),1))
for x in (5,6,7):
 g=[q[0] for q in d if q[1]>=x];other=[q[0] for q in d if q[1]<x]
 print('M3_OVER_GOAL_RESULT_BUCKET',x,'matches',len(g),'pnl',round(sum(r['pnl'] for r in g),4),'other_pnl',round(sum(r['pnl'] for r in other),4),
       'under_orders',sum(r['direction']=='小球' for r in g))
#  M4 actual profitability - predicted EV positive mismatch, league-specific and group records; EV not a hard gate
r=[x for x in o.rows_for('mr1') if x['pnl'] is not None]
for league in ['Japan J-League','Poland Ekstraklasa','Türkiye Super Lig','England Championship','France Ligue 1',
               'Sweden Allsvenskan','Denmark Division 1','South Korea K League 1','Colombia Primera A']:
 a=[x for x in r if x['league']==league and x['ev'] is not None]
 print('M4_EV_EXPECTATION_VS_REALIZED',json.dumps({'league':league,'orders':len(a),'matches':len({x['fixture'] for x in a}),
  'mean_forecast_ev_pct':round(statistics.mean(x['ev'] for x in a)*100,2),
  'expected_profit_u':round(sum(x['ev'] for x in a),3),
  'realized_profit_u':round(sum(x['pnl'] for x in a),3),
  'gap_u':round(sum(x['pnl']-x['ev'] for x in a),3),
  'ev_min':round(min(x['ev'] for x in a),5),'ev_max':round(max(x['ev'] for x in a),5)},ensure_ascii=False))
print('M4_GLOBAL_EV_GAP',json.dumps({'forecast_units':round(sum(x['ev'] for x in r if x['ev'] is not None),3),
'realized_units':round(sum(x['pnl'] for x in r),3),'coverage':sum(x['ev'] is not None for x in r),'matches':len({x['fixture'] for x in r})}))
