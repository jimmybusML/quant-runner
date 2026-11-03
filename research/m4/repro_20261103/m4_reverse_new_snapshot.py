import sys,json,collections,math
from pathlib import Path
sys.path.insert(0,str(Path.home()/'QuantAsiaDesk'))
import order_records as o

def settle(side,line,price,h,a):
 if side not in ('home','away') or price is None or line is None:return None
 line=float(line);price=float(price)
 if abs(line*2-round(line*2))<1e-8: parts=(line,line)
 else:parts=(math.floor(line*2)/2,math.floor(line*2)/2+0.5)
 return sum(((price-1) if (h-a if side=='home' else a-h)+z>1e-9 else (-1 if (h-a if side=='home' else a-h)+z < -1e-9 else 0))/2 for z in parts)
records=o.rows_for('mr1');by=collections.defaultdict(list);bad=[]
for r in records:
 if r['pnl'] is None:continue
 h,a=r['result']['home'],r['result']['away'];side='home' if r['direction']=='主队' else 'away'
 pos=settle(side,r['selection_line'],r['selection_price'],h,a)
 if abs(pos-r['pnl'])>1e-6:bad.append((r['id'],pos,r['pnl']))
 other='away' if side=='home' else 'home'
 opposite_line=-float(r['selection_line'])
 opposite_price=r['away_price'] if side=='home' else r['home_price']
 reverse=settle(other,opposite_line,opposite_price,h,a)
 if reverse is None:bad.append((r['id'],'reverse_missing'))
 else:by[r['league']].append((r,reverse))
print('VALIDATION',len(records),'SETTLED',sum(r['pnl'] is not None for r in records),'REVERSE_COMPUTED',sum(len(v) for v in by.values()),'BAD',len(bad),'EXAMPLES',bad[:4])
for league,group in sorted(by.items(),key=lambda kv:sum(x[0]['pnl'] for x in kv[1])):
 sides=collections.Counter(x[0]['direction'] for x in group)
 direct=sum(x[0]['pnl'] for x in group);rev=sum(x[1] for x in group)
 print(json.dumps({'league':league,'orders':len(group),'unique_matches':len({x[0]['fixture'] for x in group}),'original':round(direct,4),'reverse':round(rev,4),'gain':round(rev-direct,4),'side':dict(sides)},ensure_ascii=False))
