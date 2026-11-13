import json,hashlib,datetime,collections,statistics,os
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk')
BASE=P/'repos/mr1/data/prospective-market/shadow-v23'
SCOPE=P/'research-work/m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
scope={str(r['league_id']) for r in map(json.loads,SCOPE.open())}
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def quote_data(attempt):
 raw=attempt.get('raw_response')
 if not raw or not attempt.get('raw_sha256') or hashlib.sha256(raw.encode()).hexdigest()!=attempt['raw_sha256']:
  return None,'raw_sha_bad_or_missing'
 try:
  j=json.loads(raw)
  if not j.get('success') or not j.get('data'):return None,'no_quote_response'
  x=j['data'][0];b=next((t for t in x.get('bookmakers',[]) if t.get('slug')=='crown'),None)
  if not b:return None,'no_crown'
  return (x,b),None
 except:return None,'raw_parse_error'
index=[];bad=collections.Counter()
for line in (BASE/'snapshot-index.jsonl').open():
 try:
  x=json.loads(line)
  if x['classification']!='SNAPSHOT_OK' or x['committed_at']<'2026-11-11T00:00:00Z':continue
  index.append(x)
 except Exception:bad['index_bad_row']+=1
print('RECENT_SUCCESS_INDEX',len(index),flush=True)
rows=[];missing=collections.Counter()
for x in index:
 try:
  p=BASE/x['snapshot_path'];source=p.read_bytes()
  # snapshots index SHA is raw bytes, hash verification
  if hashlib.sha256(source).hexdigest()!=x['snapshot_sha256']:
   missing['snapshot_sha_mismatch']+=1;continue
  snap=json.loads(source)
  if snap['source_bookmaker']!='crown' or not snap['source_bookmaker_verified']:
   missing['non_Crown']+=1;continue
  fid=snap['match_id'];matchfolder=BASE/'snapshots'/fid/snap['target_horizon']/'odds'
  attempts=sorted(matchfolder.glob('attempt-*.json'))
  quote=None;used=None
  for path in attempts[::-1]:
   a=json.loads(path.read_text())
   if a.get('classification')!='SNAPSHOT_OK':continue
   info,error=quote_data(a)
   if error:missing[error]+=1;continue
   match,book=info
   if str(match.get('id'))!=fid:missing['match_id_disagrees']+=1;continue
   quote=(match,book,a);used=str(path);break
  if not quote:missing['no_verified_actual_raw']+=1;continue
  match,book,attempt=quote
  league=str(match.get('l_id'))
  if league not in scope:missing['outside_original49_leagues']+=1;continue
  ko=dt(snap['kickoff_at']);recv=dt(attempt['received_at'])
  if recv>=ko:missing['HTTP_recv_after_kickoff']+=1;continue
  if abs((recv-dt(snap['received_at'])).total_seconds())>.005:missing['snapshot_vs_HTTP_received_time_diff']+=1;continue
  m={}
  for market,key,sides in [('AH','asian',('home','away')),('OU','goal',('over','under'))]:
   q=book.get(key,{}).get('close')
   if not isinstance(q,dict) or not q.get('time'):missing['no_valid_'+market]+=1;continue
   stamp=dt(q['time'].replace(' ','T')+'+08:00').astimezone(datetime.timezone.utc)
   if stamp>recv:missing['future_market_source_event_'+market]+=1;continue
   if stamp>=ko:missing['bookmaker_event_not_pregame_'+market]+=1;continue
   m[market]={'line':float(q['line']),'odds':{s:float(q[s]) for s in sides},'source_event_utc':stamp.isoformat(),'source_age_minutes_at_actual_receipt':round((recv-stamp).total_seconds()/60,3)}
  if len(m)!=2:missing['missing_both_markets']+=1;continue
  rows.append({'fixture_id':fid,'league_id':league,'league':match.get('l'),'kickoff_utc':snap['kickoff_at'],'received_utc':attempt['received_at'],'snapshot_horizon':snap['target_horizon'],'snapshot_split':snap['split'],'raw_sha256':attempt['raw_sha256'],'snapshot_sha256':x['snapshot_sha256'],'markets':m,'source_file':used,'received_minutes_to_kickoff':round((ko-recv).total_seconds()/60,3)})
 except Exception as exc:
  missing['exception_'+type(exc).__name__]+=1
  if missing['exception_'+type(exc).__name__]<4:print('ERROR',str(exc)[:170],flush=True)
by=collections.defaultdict(list)
for r in rows:by[r['fixture_id']].append(r)
for v in by.values():v.sort(key=lambda z:z['received_utc'])
dates=collections.Counter(r['received_utc'][:10] for r in rows)
unique_new={d:len({r['fixture_id'] for r in rows if r['received_utc'][:10]==d}) for d in dates}
state=collections.Counter()
for fid,z in by.items():
 if len(z)>1:
  state['multiple_actual_Crown_receipts']+=1
  if len({(a['markets']['AH']['line'],*a['markets']['AH']['odds'].values(),a['markets']['AH']['source_event_utc']) for a in z})>1:
   state['multiple_distinct_AH_states']+=1
  if len({a['markets']['AH']['line'] for a in z})>1:state['AH_line_changes']+=1
def qtl(l):
 if not l:return None
 vals=sorted(l)
 return {'p10':round(vals[int((len(vals)-1)*.1)],2),'median':round(vals[len(vals)//2],2),'p90':round(vals[int((len(vals)-1)*.9)],2)}
out={'when_created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'MR1 shadow-v23 indexed archived actual HTTP odds responses Crown verified, 49 original provider league IDs, no impact on MR1 production','since_commit_utc':'2026-11-11T00:00:00Z','raw_SHA256_checked':True,'snapshot_SHA256_checked':True,'recent_success_index_entries_all_leagues':len(index),'valid_Crown_49market_receipts':len(rows),'valid_Crown_49market_fixtures':len(by),'received_dates':dict(dates),'distinct_fixtures_by_received_date':unique_new,'multiple_actual_receipts':dict(state),'AH_source_event_age_minutes':qtl([r['markets']['AH']['source_age_minutes_at_actual_receipt'] for r in rows]),'OU_source_event_age_minutes':qtl([r['markets']['OU']['source_age_minutes_at_actual_receipt'] for r in rows]),'received_minutes_before_kickoff':qtl([r['received_minutes_to_kickoff'] for r in rows]),'missing_reasons':dict(missing),'no_production_rules_changed':True}
print('SUMMARY',json.dumps(out,ensure_ascii=False),flush=True)
for fid,v in list(sorted(by.items()))[-8:]:print('RECENT',fid,len(v),v[-1]['received_utc'],v[-1]['league'],v[-1]['markets']['AH'],flush=True)
folder=P/'research-work'
(folder/'m8_MR1_recent_actual_Crown_receipt_bridge_20261113.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
(folder/'m8_MR1_recent_actual_Crown_receipt_bridge_20261113.jsonl').write_text(''.join(json.dumps(z,ensure_ascii=False)+'\n' for z in rows))
