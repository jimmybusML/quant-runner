from pathlib import Path
import sys,collections,random,statistics,json
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
rows=[x for x in o.rows_for('mr1') if x['pnl'] is not None and x['ev'] is not None]
by=collections.defaultdict(list)
for r in rows:by[r['fixture']].append(r)
fixtures=list(by.values())
rng=random.Random(41024)
values=[]
for _ in range(4000):
 batch=[fixtures[rng.randrange(len(fixtures))] for i in fixtures]
 n=sum(len(x) for x in batch)
 profit=sum(sum(r['pnl'] for r in x) for x in batch)
 expectation=sum(sum(r['ev'] for r in x) for x in batch)
 values.append(((profit-expectation)/n,profit/n,expectation/n))
for i,label in [(0,'GAP'),(1,'REALIZED'),(2,'PREDICTED')]:
 vals=sorted(row[i] for row in values)
 print('M4_MATCH_CLUSTER_BOOTSTRAP',label,'median_pct',round(vals[2000]*100,2),'95_pct',[round(vals[100]*100,2),round(vals[3900]*100,2)])
print('M4_MONTHLY_CORRELATION_BY_DAY')
for day in sorted(set(x['posted_at'][:10] for x in rows)):
 a=[x for x in rows if x['posted_at'].startswith(day)]
 print('DAY',day,'bets',len(a),'matches',len({x['fixture'] for x in a}),'EV_PRED',round(sum(x['ev'] for x in a),3),'PNL',round(sum(x['pnl'] for x in a),3))
