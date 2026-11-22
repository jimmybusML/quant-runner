#!/usr/bin/env python3
"""Independent settlement and raw Crown source audit for rate-consensus ledger."""
import collections, gzip, hashlib, json, math, sqlite3, datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent
WORK=Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=Path('/Users/mac/QuantAsiaDesk/data')
LEDGER=OUT/'score_rate_consensus_per_fixture.jsonl.gz'
PATHS=WORK/'m8_late_full_path_water_features_20261114.jsonl'
OLD=WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
SCHEDULE=WORK/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
INDEX=DATA/'m5-crown-authorized/crown-response-index.jsonl'
DB=DATA/'crown_quote_store/crown_quotes.sqlite3'

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def settle(line,side,hg,ag,odds):
 margin=(hg-ag) if side=='home' else (ag-hg)
 handicap=line if side=='home' else -line
 q=round(handicap*4)
 if abs(handicap*4-q)>1e-8: raise ValueError('unsupported line')
 legs=(math.floor(handicap*2)/2, math.floor(handicap*2)/2+.5) if q%2 else (handicap,)
 vals=[]; states=[]
 for leg in legs:
  x=margin+leg
  if x>1e-9: vals.append(odds-1); states.append('W')
  elif x < -1e-9: vals.append(-1.); states.append('L')
  else: vals.append(0.); states.append('P')
 u=sum(vals)/len(vals)
 state=('full_'+('win' if u>0 else 'loss') if 'P' not in states else 'push' if u==0 else 'half_'+('win' if u>0 else 'loss'))
 return state,u

def parse_time(s):
 d=dt.datetime.fromisoformat(str(s).replace(' ','T'))
 return d.replace(tzinfo=ZoneInfo('Asia/Shanghai')) if d.tzinfo is None else d

def main():
 rows=[json.loads(x) for x in gzip.open(LEDGER,'rt')]
 bad=[]; metrics=collections.defaultdict(lambda:[0,0.,collections.Counter()])
 for r in rows:
  if len(r['fid'])==0 or r['frozen_eight_overlap'] and r['year']>=2024 and r['year']<=2026: pass
  for name,m in r['methods'].items():
   side=m['side']
   if side is None:
    state,u='no_bet',0.
   else:
    state,u=settle(float(r['line_home']),side,int(r['hg']),int(r['ag']),float(r['home_odds'] if side=='home' else r['away_odds']))
   if state!=m['settlement'] or abs(u-float(m['net_u']))>1e-8: bad.append((r['fid'],name,state,u,m))
   if side is not None:
    q=metrics[name]; q[0]+=1; q[1]+=u; q[2][state]+=1
 # Verify target IDs are disjoint from frozen set; one row per FID.
 frozen={str(json.loads(l)['fid']) for l in open(WORK/'m8_foundation_20261115/historical_membership.jsonl') if l.strip()}
 ids=[r['fid'] for r in rows]
 dup=len(ids)-len(set(ids)); overlap=sum(1 for r in rows if r['year']>=2024 and r['year']<=2026 and not r['frozen_eight_overlap'] and r['fid'] in frozen)
 candidate_rows=[r for r in rows if r['year']>=2024 and r['year']<=2026 and not r['frozen_eight_overlap']]
 candidate_overlaps=sorted({r['fid'] for r in candidate_rows if r['fid'] in frozen})
 # Raw Crown historical source audit: inspect original per-FID response and select latest AH event at or before T-1h.
 old_index={str(x['fixture_id']):x for x in map(json.loads,open(OLD))}
 sched={str(x['fid']):x for x in map(json.loads,open(SCHEDULE))}
 idx={str(x['match_id']):x for x in map(json.loads,open(INDEX))}
 fullpath={str(x['fid']):x for x in map(json.loads,open(PATHS))}
 ledger_by_fid={r['fid']:r for r in rows}
 raw_counts=collections.Counter(); examples=[]
 for fid,p in fullpath.items():
  if fid in old_index:
   meta=old_index[fid]; source=Path(meta['source_file']); expected_sha=None; kind='archive'
  elif fid in sched:
   source=DATA/f'm5-crown-authorized/crown-responses/{fid}.json'; expected_sha=idx.get(fid,{}).get('response_sha256'); kind='2026'
  else:
   raw_counts['no_source_mapping']+=1; continue
  if not source.exists(): raw_counts['missing_raw']+=1; continue
  b=source.read_bytes()
  if expected_sha and hashlib.sha256(b).hexdigest()!=expected_sha: raw_counts['raw_sha_mismatch']+=1; continue
  try: body=json.loads(b)
  except Exception: raw_counts['raw_json_invalid']+=1; continue
  f=next((x for x in body.get('data',[]) if str(x.get('id'))==fid),None)
  if not f: raw_counts['fid_missing']+=1; continue
  ko=parse_time(f['start'])
  expected=ledger_by_fid[fid]
  if int(f.get('hg',-999))!=int(expected['hg']) or int(f.get('ag',-999))!=int(expected['ag']): raw_counts['ft_mismatch']+=1; continue
  crown=next((x for x in f.get('bookmakers',[]) if x.get('slug')=='crown'),None)
  if not crown: raw_counts['crown_missing']+=1; continue
  cutoff=ko-dt.timedelta(hours=1); qs=[]
  for q in crown.get('asian_list') or []:
   try:
    t=parse_time(q[4]); line=float(q[1]); ho=float(q[2]); ao=float(q[3])
    if t<=cutoff and ho>1 and ao>1: qs.append((t,line,ho,ao))
   except (ValueError,TypeError,IndexError): continue
  if not qs: raw_counts['no_t1_quote']+=1; continue
  q=max(qs,key=lambda z:z[0]); raw_counts['t1_found']+=1
  ok=(abs(q[1]-float(p['end_line']))<1e-8 and abs(q[2]-float(p['home_price']))<1e-8 and abs(q[3]-float(p['away_price']))<1e-8)
  if ok: raw_counts['t1_exact_match']+=1
  else:
   raw_counts['t1_price_mismatch']+=1
   if len(examples)<12: examples.append({'fid':fid,'from_path':[p['end_line'],p['home_price'],p['away_price']],'raw_t1':[q[1],q[2],q[3]],'raw_time':q[0].isoformat()})
 summary={'ledger_rows':len(rows),'method_rows':len(rows)*4,'settlement_mismatches':len(bad),'duplicate_fids':dup,'candidate_overlap_frozen_2024_2026':overlap,'candidate_unique_fids_2024_2026':len({r['fid'] for r in candidate_rows}),'metrics':{k:{'orders':v[0],'net_u':round(v[1],6),'roi_pct':round(100*v[1]/v[0],6) if v[0] else None,'settlements':dict(v[2])} for k,v in metrics.items()},'raw_crown_t1_audit':dict(raw_counts),'raw_quote_mismatch_examples':examples,'input_sha256':{str(p):digest(p) for p in (LEDGER,PATHS,OLD,SCHEDULE,INDEX,WORK/'m8_foundation_20261115/historical_membership.jsonl') if p.exists()},'crown_sqlite_sha256':digest(DB) if DB.exists() else None}
 summary['pass_settlement']=not bad
 summary['pass_fid_unique']=dup==0
 summary['pass_incremental_disjoint']=overlap==0
 (OUT/'independent_verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in summary.items() if k not in ('input_sha256','raw_quote_mismatch_examples')},ensure_ascii=False,indent=2))
 if bad: raise SystemExit('settlement mismatch')
if __name__=='__main__': main()
