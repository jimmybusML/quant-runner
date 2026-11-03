from pathlib import Path
from collections import defaultdict
import sys,json,statistics
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o
r=o.rows_for('mr1');r=[x for x in r if x['pnl'] is not None]
cut=datetime.fromisoformat('2026-10-29T00:00:00+00:00');good=['Sweden Allsvenskan','Denmark Division 1','South Korea K League 1'];bad=['Japan J-League','England Championship','Türkiye Super Lig','Poland Ekstraklasa','France Ligue 1']
def mins(a,b):
 try:return (datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()/60
 except Exception:return None
for l in bad+good:
 rows=[x for x in r if x['league']==l];groups=defaultdict(list)
 for x in rows:
  age=mins(x.get('quote_at'),x['posted_at']);lead=mins(x['posted_at'],x['kickoff']);hour=(datetime.fromisoformat(x['posted_at'].replace('Z','+00:00'))+timedelta(hours=8)).hour
  groups['side:'+x['direction']].append(x)
  groups['sent:' + ('before 10/29' if datetime.fromisoformat(x['posted_at'].replace('Z','+00:00'))<cut else 'on/after 10/29')].append(x)
  groups['quote_age:' + ('<60m' if age is not None and age<60 else '>=60m')].append(x)
  groups['sent_hour_cn:'+str(hour).zfill(2)].append(x)
  groups['lead:' + ('<120m' if lead is not None and lead<120 else '>=120m')].append(x)
 print('LEAGUE',l,'total',len(rows),'pnl',round(sum(x['pnl'] for x in rows),4),'distinct_match',len({x['fixture'] for x in rows}), 'mean_EV',round(statistics.mean(x['ev'] for x in rows if x['ev'] is not None),4))
 for label,v in sorted(groups.items()):
  print('  ',label,len(v),round(sum(x['pnl'] for x in v),4), 'matches',len({x['fixture'] for x in v}))
