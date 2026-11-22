#!/usr/bin/env python3
"""Read-only benchmark: full quote-table scan vs approved-FID indexed lookups."""
from __future__ import annotations
import argparse, collections, datetime as dt, json, sqlite3, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import collect_crown_ah_ou_64 as collector

def flatten(d):
 return {(fid,kind):n for fid,kinds in d.items() for kind,n in kinds.items()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--database',default=str(collector.DB));p.add_argument('--output');a=p.parse_args()
 fixtures=collector.load_schedule();fids=list(fixtures);allowed=set(fids)
 cx=sqlite3.connect(f'file:{a.database}?mode=ro',uri=True,timeout=60);cx.execute('PRAGMA busy_timeout=60000');cx.execute('BEGIN')
 old={};new={};
 t=time.monotonic()
 for table in ('asian_quote','crown_ou_quote'):
  counts=collections.defaultdict(collections.Counter)
  for fid,kind,n in cx.execute(f'SELECT fixture_id,quote_kind,COUNT(*) FROM {table} GROUP BY fixture_id,quote_kind'):
   if str(fid) in allowed:counts[str(fid)][kind]=n
  old[table]=counts
 old_seconds=time.monotonic()-t
 t=time.monotonic()
 for table in ('asian_quote','crown_ou_quote'):
  counts=collections.defaultdict(collections.Counter)
  for offset in range(0,len(fids),800):
   batch=fids[offset:offset+800];marks=','.join('?' for _ in batch)
   sql=f'SELECT fixture_id,quote_kind,COUNT(*) FROM {table} WHERE fixture_id IN ({marks}) GROUP BY fixture_id,quote_kind'
   for fid,kind,n in cx.execute(sql,batch):counts[str(fid)][kind]=n
  new[table]=counts
 new_seconds=time.monotonic()-t
 plans={}
 for table in ('asian_quote','crown_ou_quote'):
  plans[table]=cx.execute(f'EXPLAIN QUERY PLAN SELECT fixture_id,quote_kind,COUNT(*) FROM {table} WHERE fixture_id IN (?,?,?) GROUP BY fixture_id,quote_kind',fids[:3]).fetchall()
 result={'measured_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'scope_fids':len(fids),'same_fixture_kind_counts':all(flatten(old[t])==flatten(new[t]) for t in old),'old_full_group_seconds':round(old_seconds,6),'indexed_scope_seconds':round(new_seconds,6),'speedup':round(old_seconds/new_seconds,3) if new_seconds else None,'quote_rows_by_table':{t:sum(flatten(new[t]).values()) for t in new},'fixture_kind_groups_by_table':{t:len(flatten(new[t])) for t in new},'query_plans':{t:[x[3] for x in plans[t]] for t in plans},'chunk_fids':800,'readonly_snapshot':True}
 cx.rollback();cx.close()
 out=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if a.output:Path(a.output).write_text(out,encoding='utf-8')
 print(out,end='')
if __name__=='__main__':main()
