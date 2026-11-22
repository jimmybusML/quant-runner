#!/usr/bin/env python3
"""Audit and collect combined Crown AH/OU history for the approved 64 leagues only (2023-2026).

No model inputs are used. One Crown request per FID can populate AH summary,
AH movement, OU summary and OU movement from the same SHA-addressed response.
Historical retrieval is always marked historical (never prospective/live).
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, http.client, json, math, signal, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE=Path('/Users/mac/QuantAsiaDesk')
DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3'
SCHEDULE=BASE/'research-work/crown-drop-expanded-62/schedule_universe.jsonl'
STORE=BASE/'data/crown_quote_store'
OUT=Path(__file__).resolve().parent
IDS={1,10,12,14,16,25,29,31,33,35,37,40,43,45,46,47,48,51,52,55,60,61,62,66,68,70,73,75,85,88,109,116,129,141,145,152,177,262,290,297,298,299,303,314,319,328,330,332,345,378,670,779,979,1439,8172,8293,10480,10714,11498,19290,26540,27388,27389,27390}
YEAR_MIN=2023;YEAR_MAX=2026
UTC=dt.timezone.utc
STOP=False

class RequestFailure(RuntimeError):
 def __init__(self,message,attempts):super().__init__(message);self.attempts=attempts

def on_signal(_sig,_frame):
 global STOP
 STOP=True
signal.signal(signal.SIGINT,on_signal); signal.signal(signal.SIGTERM,on_signal)

sys.path.insert(0,str(BASE/'scripts'))
import crown_capture_store as crown
sys.path.insert(0,str(OUT))
from integrate_crown_ou_history import ensure_schema, finite, ou_rows

def load_schedule():
 rows={}; seen=set()
 with SCHEDULE.open(encoding='utf-8') as f:
  for line in f:
   x=json.loads(line);league=int(x['league_id']);year=int(x.get('season_year') or 0);fid=str(x.get('match_id') or '')
   if league not in IDS:continue
   seen.add(league)
   if not YEAR_MIN<=year<=YEAR_MAX:continue
   if fid:rows[fid]=x
 if seen!=IDS:raise RuntimeError(f'64_LEAGUE_ID_SCOPE_MISMATCH missing={sorted(IDS-seen)} extra={sorted(seen-IDS)}')
 return rows

def coverage(db,fixtures):
 cx=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=60);cx.execute('PRAGMA busy_timeout=60000')
 ah=collections.defaultdict(collections.Counter);ou=collections.defaultdict(collections.Counter)
 for fid,kind,n in cx.execute('''SELECT fixture_id,quote_kind,COUNT(*) FROM asian_quote GROUP BY fixture_id,quote_kind'''):
  if str(fid) in fixtures:ah[str(fid)][kind]=n
 for fid,kind,n in cx.execute('''SELECT fixture_id,quote_kind,COUNT(*) FROM crown_ou_quote GROUP BY fixture_id,quote_kind'''):
  if str(fid) in fixtures:ou[str(fid)][kind]=n
 cx.close()
 def state(fid):
  a=ah[fid];o=ou[fid]
  return {'ah_open_close':a['open']>0 and a['close']>0,'ah_movement':a['movement']>0,
          'ou_open_close':o['open']>0 and o['close']>0,'ou_movement':o['movement']>0,
          'ah_open_n':a['open'],'ah_close_n':a['close'],'ah_movement_n':a['movement'],
          'ou_open_n':o['open'],'ou_close_n':o['close'],'ou_movement_n':o['movement']}
 return state

def audit(db,fixtures):
 state=coverage(db,fixtures);cnt=collections.Counter();by_year=collections.defaultdict(collections.Counter);by_league=collections.defaultdict(collections.Counter);queue=[]
 for fid,x in fixtures.items():
  s=state(fid);year=int(x['season_year']);league=int(x['league_id'])
  for k in ('ah_open_close','ah_movement','ou_open_close','ou_movement'):cnt[k]+=int(s[k]);by_year[year][k]+=int(s[k]);by_league[league][k]+=int(s[k])
  if not all(s[k] for k in ('ah_open_close','ah_movement','ou_open_close','ou_movement')):
   queue.append({'match_id':fid,'league_id':league,'year':year,'kickoff_source_local':x.get('kickoff_source_local'),'home':x.get('home'),'away':x.get('away'),**s})
 return {'schedule_fids':len(fixtures),'approved_league_ids':sorted(IDS),'covered':dict(cnt),'missing_requests':len(queue),'queue':queue,'by_year':{str(k):dict(v) for k,v in sorted(by_year.items())},'by_league':{str(k):dict(v) for k,v in sorted(by_league.items())}}

def write_queue(report,path):
 with Path(path).open('w',encoding='utf-8') as f:
  for row in report['queue']:f.write(json.dumps(row,ensure_ascii=False)+'\n')

def terminal_attempts(path):
 done=set()
 p=Path(path)
 if not p.exists():return done
 for line in p.read_text(encoding='utf-8').splitlines():
  try:r=json.loads(line)
  except Exception:continue
  if r.get('status') not in ('FETCH_FAILED',):done.add(str(r.get('match_id') or ''))
 return done

def combined_request(fid,token):
 query={'token':token,'bookmaker':'crown','columns':'asianList,goalList'}
 url=crown.API+fid+'?'+urllib.parse.urlencode(query)
 last='UNKNOWN';attempts=[]
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'QuantAsiaDesk-CrownLocalArchive/2'})
   started=time.monotonic();started_at=dt.datetime.now(UTC).isoformat()
   with urllib.request.urlopen(req,timeout=40) as rsp:
    raw=rsp.read();status=rsp.status
   obj=json.loads(raw)
   if obj.get('success') not in (1,True,'1'):
    code=str((obj.get('error') or {}).get('code') or 'API_REPORTED_ERROR');last=code;attempts.append({'attempt':attempt+1,'started_at_utc':started_at,'elapsed_seconds':round(time.monotonic()-started,4),'outcome':'api_error','error':code,'http_status':status})
    if code=='TOO_MANY_REQUEST' and attempt<3:
     for _ in range((10+attempt*5)*10):
      if STOP:raise RequestFailure('PAUSED_FOR_SCHEDULED_JOB',attempts)
      time.sleep(.1)
     continue
    raise RequestFailure(code,attempts)
   match,book=crown.extract_match(obj,fid)
   elapsed=time.monotonic()-started;received=dt.datetime.now(UTC).isoformat();attempts.append({'attempt':attempt+1,'started_at_utc':started_at,'response_received_at_utc':received,'elapsed_seconds':round(elapsed,4),'outcome':'success','http_status':status,'response_bytes':len(raw)})
   return raw,received,status,obj,match,book,elapsed,attempts
  except (urllib.error.HTTPError,urllib.error.URLError,http.client.IncompleteRead,TimeoutError,ConnectionError,ValueError,TypeError) as e:
   last=('HTTP_'+str(e.code)) if isinstance(e,urllib.error.HTTPError) else type(e).__name__
   attempt_row={'attempt':attempt+1,'started_at_utc':started_at,'elapsed_seconds':round(time.monotonic()-started,4),'outcome':'transport_error','error':last}
   if isinstance(e,urllib.error.HTTPError):attempt_row['http_status']=e.code
   attempts.append(attempt_row)
   if STOP:raise RequestFailure('PAUSED_FOR_SCHEDULED_JOB',attempts)
   if attempt<3:
    for _ in range((6+attempt*5)*10):
     if STOP:raise RequestFailure('PAUSED_FOR_SCHEDULED_JOB',attempts)
     time.sleep(.1)
 raise RequestFailure(last,attempts)

def save_combined(cx,fid,raw,received,match,book):
 sha=hashlib.sha256(raw).hexdigest();path=STORE/'raw'/'historical'/fid/(sha+'.json');crown.archive_file(path,raw)
 # Both AH layers and OU rows are written from the same response in one transaction.
 started=time.monotonic()
 sha=hashlib.sha256(raw).hexdigest();kickoff=crown.parse_timestamp(match.get('start'));now=dt.datetime.now(UTC).isoformat()
 ah_counts={}
 for layer in ('summary','movement'):
  rows=crown.rows_for_layer(book,layer);key=hashlib.sha256(f"{layer}|historical|{fid}|{sha}|".encode()).hexdigest();ah_counts[layer]=len(rows)
  prev=cx.execute('SELECT quote_count FROM capture WHERE capture_key=?',(key,)).fetchone()
  if prev is None:
   cx.execute('''INSERT INTO capture(capture_key,fixture_id,data_layer,capture_mode,response_received_at_utc,processed_at_utc,source_file,response_sha256,kickoff_at_utc,prospective_observation,quote_count,status)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(key,fid,layer,'historical',received,now,str(path),sha,kickoff,0,len(rows),'QUOTES_SAVED' if rows else 'NO_CROWN_AH_QUOTES'))
  for i,(kind,line,home,away,source_time) in enumerate(rows):
   source_utc=crown.parse_timestamp(source_time);before=int(source_utc<kickoff) if source_utc and kickoff else None
   cx.execute('''INSERT OR IGNORE INTO asian_quote(capture_key,sequence_index,fixture_id,quote_kind,handicap_home,home_decimal,away_decimal,quote_source_at_utc,response_received_at_utc,prospective_observation,quote_before_kickoff)
    VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(key,i,fid,kind,crown.valid_number(line),crown.valid_number(home),crown.valid_number(away),source_utc,received,0,before))
 # Store OU against the same response and linked AH movement capture.
 capkey=hashlib.sha256(f"movement|historical|{fid}|{sha}|".encode()).hexdigest()
 source_key=hashlib.sha256('|'.join(('combined_crown_collection',fid,sha,received,capkey)).encode()).hexdigest()
 qs=ou_rows(book);goal=book.get('goal') or {};has_summary=any(isinstance(goal.get(k),dict) for k in ('open','close'))
 ko=crown.parse_timestamp(match.get('start'));now=dt.datetime.now(UTC).isoformat()
 with cx:
  cx.execute('''INSERT OR IGNORE INTO crown_ou_source
   (source_key,fixture_id,capture_key,source_type,capture_mode,response_received_at_utc,kickoff_at_utc,source_file,response_sha256,response_status,raw_sha_verified,has_goal_summary,goal_list_count,imported_at_utc)
   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(source_key,fid,capkey,'combined_crown_collection','historical',received,ko,str(path),sha,'HTTP_200_CROWN_RESPONSE',1,int(has_summary),sum(q[0]=='movement' for q in qs),now))
  for i,(kind,line,over,under,source_time) in enumerate(qs):
   before=int(source_time<ko) if source_time and ko else None
   cx.execute('''INSERT OR IGNORE INTO crown_ou_quote
    (source_key,sequence_index,fixture_id,quote_kind,total_line,over_decimal,under_decimal,quote_source_at_utc,response_received_at_utc,prospective_observation,quote_before_kickoff)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',(source_key,i,fid,kind,line,over,under,source_time,received,0,before))
 return {'sha256':sha,'raw_file':str(path),'ah_summary_n':sum(q[0] in ('open','close') for q in crown.rows_for_layer(book,'summary')),'ah_movement_n':sum(q[0]=='movement' for q in crown.rows_for_layer(book,'movement')),'ou_summary_n':sum(q[0] in ('open','close') for q in qs),'ou_movement_n':sum(q[0]=='movement' for q in qs),'db_write_seconds':round(time.monotonic()-started,4)}

def collect(db,fixtures,queue_path,log_path,interval,limit=0):
 state=coverage(db,fixtures);token=crown.api_token();last_start=None;counts=collections.Counter();log=Path(log_path);already=terminal_attempts(log)
 rows=[json.loads(x) for x in Path(queue_path).read_text().splitlines() if x.strip()]
 if limit>0:rows=rows[:limit]
 writer=sqlite3.connect(db,timeout=30);writer.execute('PRAGMA busy_timeout=30000');ensure_schema(writer)
 with log.open('a',encoding='utf-8') as f:
  for i,row in enumerate(rows,1):
   if STOP:break
   fid=str(row['match_id']);s=state(fid)
   if fid in already:
    counts['already_attempted_skipped']+=1;continue
   if all(s[k] for k in ('ah_open_close','ah_movement','ou_open_close','ou_movement')):
    counts['became_complete_before_request']+=1;continue
   if last_start is not None:
    wait=max(0,interval-(time.monotonic()-last_start))
    if wait:time.sleep(wait)
   last_start=time.monotonic();started=time.monotonic()
   try:
    raw,received,http,obj,match,book,request_seconds,attempts=combined_request(fid,token)
    saved=save_combined(writer,fid,raw,received,match,book)
    status='BOTH_MARKETS' if all(saved[k] for k in ('ah_summary_n','ah_movement_n','ou_summary_n','ou_movement_n')) else 'PARTIAL_MARKETS' if any(saved[k] for k in ('ah_summary_n','ah_movement_n','ou_summary_n','ou_movement_n')) else 'NO_CROWN_MARKET_DATA'
    rec={'match_id':fid,'league_id':row['league_id'],'year':row['year'],'status':status,'http_status':http,'api_success':obj.get('success'),'response_received_at_utc':received,'request_seconds':round(request_seconds,4),'request_attempts':attempts,'attempt_count':len(attempts),'elapsed_seconds':round(time.monotonic()-started,3),**saved}
   except Exception as e:
    writer.rollback()
    with writer:writer.execute('INSERT INTO failed_attempt VALUES (?,?,?,?,?)',(dt.datetime.now(UTC).isoformat(),fid,'movement+OU','historical',str(e)[:160]))
    attempts=getattr(e,'attempts',[]);rec={'match_id':fid,'league_id':row['league_id'],'year':row['year'],'status':'FETCH_FAILED','error':str(e)[:160],'request_attempts':attempts,'attempt_count':len(attempts),'elapsed_seconds':round(time.monotonic()-started,3)}
   f.write(json.dumps(rec,ensure_ascii=False)+'\n');f.flush();counts[rec['status']]+=1
   if i%25==0:print(json.dumps({'processed_from_queue':i,'total_queue':len(rows),'counts':dict(counts),'last':rec},ensure_ascii=False),flush=True)
 writer.close()
 print(json.dumps({'status':'STOPPED' if STOP else 'QUEUE_COMPLETE','queue_count':len(rows),'counts':dict(counts),'log':str(log)},ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=('audit','build-queue','collect'),default='audit');p.add_argument('--database',default=str(DB));p.add_argument('--schedule',default=str(SCHEDULE));p.add_argument('--queue',default=str(OUT/'crown_64_combined_missing_queue.jsonl'));p.add_argument('--log',default=str(OUT/'crown_64_combined_collection.jsonl'));p.add_argument('--interval-seconds',type=float,default=5.2);p.add_argument('--limit',type=int,default=0,help='Optional request count cap for a controlled pilot; 0 processes queue')
 a=p.parse_args();fixtures=load_schedule();report=audit(Path(a.database),fixtures);report['schedule_path']=a.schedule;report['schedule_sha256']=hashlib.sha256(Path(a.schedule).read_bytes()).hexdigest();report['year_range']=[YEAR_MIN,YEAR_MAX]
 if a.mode=='audit':
  report.pop('queue',None);out=OUT/'crown_64_coverage_latest.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
 elif a.mode=='build-queue':
  attempted=terminal_attempts(a.log);report['attempted_nonretryable_fids']=len(attempted);report['queue']=[r for r in report['queue'] if r['match_id'] not in attempted];report['missing_requests']=len(report['queue']);write_queue(report,a.queue);print(json.dumps({k:v for k,v in report.items() if k not in ('queue','by_league')}|{'queue_path':a.queue,'attempted_nonretryable_fids':len(attempted)},ensure_ascii=False,indent=2))
 else:collect(Path(a.database),fixtures,a.queue,a.log,a.interval_seconds,a.limit)
if __name__=='__main__':main()
