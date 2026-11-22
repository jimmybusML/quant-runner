#!/usr/bin/env python3
"""Normalize existing Crown OU raw responses into the shared Crown SQLite store.

This script makes no network requests. It preserves raw responses and HTTP
receive times, reuses existing capture keys where possible, and stores OU
quotes beside the existing AH tables in the same SQLite database.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, gzip, hashlib, json, math, os, shutil, sqlite3, sys
from pathlib import Path
from typing import Any

BASE=Path('/Users/mac/QuantAsiaDesk')
WORK=BASE/'research-work/full_history_backfill_20261121'
DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3'
INVENTORY=WORK/'fixture_inventory_2019_2026.jsonl.gz'
M5=BASE/'data/m5-crown-authorized/crown-responses'
M5_INDEX=BASE/'data/m5-crown-authorized/crown-response-index.jsonl'
EPL=BASE/'data/epl_laliga_crown_5seasons/raw_crown'
NETWORK_LOG=WORK/'ou_2019_2026_network_collection.jsonl'
NETWORK_RAW=WORK/'crown_ou_raw'
SOURCE_RECOVERY=WORK/'ou_2019_2026_source_recovery.jsonl'
STORE_RAW=BASE/'data/crown_quote_store/raw/historical'
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'scripts'))
import crown_capture_store as crown

UTC=dt.timezone.utc

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def finite(x):
 try:
  v=float(x)
  return v if math.isfinite(v) else None
 except (TypeError,ValueError,OverflowError):return None
def parse_ts(s):return crown.parse_timestamp(s)
def load_jsonl(p:Path):
 if not p.exists():return
 with p.open(encoding='utf-8') as f:
  for line in f:
   try:
    if line.strip():yield json.loads(line)
   except Exception:continue

def load_inventory():
 years={}
 with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
  for line in f:
   try:
    x=json.loads(line);fid=str(x.get('fid') or '')
    if fid:
     years[fid]=str(x.get('year') or '')
   except Exception:continue
 return set(years),years

def load_target_schedule(path:Path):
 """Load the explicitly approved 64-league fixture set; never infer scope from models."""
 allowed={1,10,12,14,16,25,29,31,33,35,37,40,43,45,46,47,48,51,52,55,60,61,62,66,68,70,73,75,85,88,109,116,129,141,145,152,177,262,290,297,298,299,303,314,319,328,330,332,345,378,670,779,979,1439,8172,8293,10480,10714,11498,19290,26540,27388,27389,27390}
 fids=set();seen=set()
 with path.open(encoding='utf-8') as f:
  for line in f:
   x=json.loads(line);lid=int(x['league_id']);year=int(x.get('season_year') or 0);fid=str(x.get('match_id') or '')
   if lid not in allowed:continue
   seen.add(lid)
   if not 2023<=year<=2026:continue
   if fid:fids.add(fid)
 if seen!=allowed:raise ValueError(f'TARGET_LEAGUE_ID_SET_MISMATCH missing={sorted(allowed-seen)} extra={sorted(seen-allowed)}')
 return fids

def load_receipt_index():
 out=collections.defaultdict(set)
 for x in load_jsonl(M5_INDEX) or []:
  fid=str(x.get('match_id') or '');sha=str(x.get('response_sha256') or '')
  rec=parse_ts(x.get('captured_at_utc'))
  if fid and sha and rec:out[(fid,sha)].add(rec)
 return out

def extract_fixture(body:dict,fid:str):
 data=body.get('data') if isinstance(body,dict) else None
 items=data if isinstance(data,list) else [data] if isinstance(data,dict) else []
 return next((x for x in items if isinstance(x,dict) and str(x.get('id'))==str(fid)),None)

def crown_book(match):
 return next((x for x in (match or {}).get('bookmakers',[]) if str(x.get('slug','')).lower()=='crown'),None)

def ou_rows(book):
 rows=[];g=(book or {}).get('goal') or {}
 for kind in ('open','close'):
  x=g.get(kind)
  if isinstance(x,dict):
   vals=(finite(x.get('line')),finite(x.get('over')),finite(x.get('under')))
   if any(v is not None for v in vals):rows.append((kind,*vals,parse_ts(x.get('time'))))
 for item in (book or {}).get('goal_list') or []:
  if isinstance(item,(list,tuple)) and len(item)>=5:
   vals=(finite(item[1]),finite(item[2]),finite(item[3]))
   if any(v is not None for v in vals):rows.append(('movement',*vals,parse_ts(item[4])))
 return rows

def ah_layers(book):
 layers=[]
 if crown.rows_for_layer(book,'summary'):layers.append('summary')
 if crown.rows_for_layer(book,'movement'):layers.append('movement')
 return layers

def cap_key(layer,mode,fid,sha,received):
 return hashlib.sha256(f"{layer}|{mode}|{fid}|{sha}|{received if mode=='live' else ''}".encode()).hexdigest()

def ensure_schema(cx):
 cx.execute('PRAGMA busy_timeout=15000')
 cx.execute('PRAGMA foreign_keys=ON')
 cx.executescript('''
 CREATE TABLE IF NOT EXISTS crown_ou_source (
   source_key TEXT PRIMARY KEY,
   fixture_id TEXT NOT NULL,
   capture_key TEXT,
   source_type TEXT NOT NULL,
   capture_mode TEXT NOT NULL,
   response_received_at_utc TEXT,
   kickoff_at_utc TEXT,
   source_file TEXT,
   response_sha256 TEXT,
   response_status TEXT NOT NULL,
   raw_sha_verified INTEGER NOT NULL DEFAULT 0,
   has_goal_summary INTEGER NOT NULL DEFAULT 0,
   goal_list_count INTEGER NOT NULL DEFAULT 0,
   imported_at_utc TEXT NOT NULL,
   FOREIGN KEY(capture_key) REFERENCES capture(capture_key)
 );
 CREATE INDEX IF NOT EXISTS idx_crown_ou_source_fixture ON crown_ou_source(fixture_id,capture_mode);
 CREATE INDEX IF NOT EXISTS idx_crown_ou_source_sha ON crown_ou_source(fixture_id,response_sha256);
 CREATE TABLE IF NOT EXISTS crown_ou_quote (
   source_key TEXT NOT NULL,
   sequence_index INTEGER NOT NULL,
   fixture_id TEXT NOT NULL,
   quote_kind TEXT NOT NULL CHECK(quote_kind IN ('open','close','movement')),
   total_line REAL,
   over_decimal REAL,
   under_decimal REAL,
   quote_source_at_utc TEXT,
   response_received_at_utc TEXT,
   prospective_observation INTEGER NOT NULL DEFAULT 0,
   quote_before_kickoff INTEGER,
   PRIMARY KEY(source_key,sequence_index),
   FOREIGN KEY(source_key) REFERENCES crown_ou_source(source_key)
 );
 CREATE INDEX IF NOT EXISTS idx_crown_ou_quote_fixture ON crown_ou_quote(fixture_id,quote_kind,quote_source_at_utc);
 CREATE VIEW IF NOT EXISTS crown_market_quote AS
   SELECT 'AH' AS market,q.fixture_id,q.capture_key AS source_key,c.data_layer,c.capture_mode,
     q.quote_kind,q.handicap_home AS line,q.home_decimal,q.away_decimal,
     NULL AS over_decimal,NULL AS under_decimal,q.quote_source_at_utc,q.response_received_at_utc,
     q.prospective_observation,q.quote_before_kickoff,c.response_sha256,c.source_file
   FROM asian_quote q JOIN capture c ON c.capture_key=q.capture_key
   UNION ALL
   SELECT 'OU' AS market,q.fixture_id,q.source_key,s.source_type AS data_layer,s.capture_mode,
     q.quote_kind,q.total_line AS line,NULL AS home_decimal,NULL AS away_decimal,
     q.over_decimal,q.under_decimal,q.quote_source_at_utc,q.response_received_at_utc,
     q.prospective_observation,q.quote_before_kickoff,s.response_sha256,s.source_file
   FROM crown_ou_quote q JOIN crown_ou_source s ON s.source_key=q.source_key;
 ''')
 cx.commit()

def source_candidates(cx, inventory_ids, inventory_years, receipt_index):
 """Yield metadata rows. Raw bodies are parsed later, one at a time."""
 # Existing canonical-store response records, including summary/movement layers.
 cur=cx.execute('''SELECT capture_key,fixture_id,data_layer,capture_mode,response_received_at_utc,
   source_file,response_sha256,kickoff_at_utc,status FROM capture''')
 for row in cur:
  ck,fid,layer,mode,received,path,sha,kickoff,status=row;fid=str(fid)
  y=(str(kickoff)[:4] if kickoff else inventory_years.get(fid,''))
  if y and not ('2019'<=y<='2026'):continue
  if not y and fid not in inventory_ids:continue
  yield {'fid':fid,'source_type':'sqlite_capture','layer':str(layer),'mode':str(mode),
    'received':parse_ts(received),'path':Path(path),'sha':str(sha),'kickoff':parse_ts(kickoff),
    'existing_capture_key':str(ck),'response_status':str(status)}
 # Existing legacy Crown raw caches: open/close and full lists are both parsed.
 for src_type,root in (('m5_response_cache',M5),('epl_laliga_response_cache',EPL)):
  if not root.exists():continue
  for p in root.glob('*.json'):
   fid=p.stem
   if not fid.isdigit():continue
   try:
    b=p.read_bytes();sha=sha_bytes(b);body=json.loads(b);m=extract_fixture(body,fid)
    if not m:continue
    ko=parse_ts(m.get('start'));y=ko[:4] if ko else inventory_years.get(fid,'')
    if y and not ('2019'<=y<='2026'):continue
    receives=sorted(receipt_index.get((fid,sha),()))
    if receives:
     for rec in receives:
      mode='live' if ko and rec<ko else 'historical'
      yield {'fid':fid,'source_type':src_type,'layer':'summary','mode':mode,'received':rec,'path':p,'sha':sha,'kickoff':ko,'existing_capture_key':None,'response_status':'RAW_AVAILABLE'}
    else:
     yield {'fid':fid,'source_type':src_type,'layer':'summary','mode':'historical','received':None,'path':p,'sha':sha,'kickoff':ko,'existing_capture_key':None,'response_status':'RAW_AVAILABLE'}
   except Exception:continue
 # Independent OU network collection; log is append-only and any torn last line is ignored.
 for rec in load_jsonl(NETWORK_LOG) or []:
  fid=str(rec.get('fid') or '')
  if not fid:continue
  path=Path(rec['raw_file']) if rec.get('raw_file') else None
  yield {'fid':fid,'source_type':'ou_network_collection','layer':'summary','mode':'historical',
   'received':parse_ts(rec.get('response_received_at_utc')),'path':path,'sha':str(rec.get('sha256') or ''),
   'kickoff':None,'existing_capture_key':None,'response_status':str(rec.get('status') or 'UNKNOWN'),
   'log_record':rec}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--mode',choices=('audit','import'),default='audit')
 ap.add_argument('--database',default=str(DB))
 ap.add_argument('--target-schedule',help='Optional JSONL schedule; restrict import to exact approved 64-league FIDs')
 ap.add_argument('--output',default=str(OUT/'ou_unification_audit_latest.json'))
 args=ap.parse_args()
 db=Path(args.database);out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 inventory_ids,inventory_years=load_inventory();receipt_index=load_receipt_index()
 cx=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=30);cx.execute('PRAGMA busy_timeout=30000')
 candidates=list(source_candidates(cx,inventory_ids,inventory_years,receipt_index))
 target_fids=load_target_schedule(Path(args.target_schedule)) if args.target_schedule else None
 if target_fids is not None:candidates=[r for r in candidates if r['fid'] in target_fids]
 # Every source row keeps its own receipt provenance; parse each raw body only once.
 groups=collections.defaultdict(list);failures=[]
 for r in candidates:
  if r.get('path') and r.get('sha'):groups[(r['fid'],r['sha'])].append(r)
  else:failures.append(r)
 table_counts={name:int(cx.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]) for name in ('capture','asian_quote')}
 try:ou_before=int(cx.execute('SELECT COUNT(*) FROM crown_ou_quote').fetchone()[0])
 except sqlite3.OperationalError:ou_before=0
 cx.close()
 counts=collections.Counter();by_year=collections.defaultdict(collections.Counter);by_source=collections.defaultdict(collections.Counter)
 quote_kinds=collections.Counter();by_year_kind=collections.defaultdict(collections.Counter);hash_mismatches=[];identity_mismatches=[];processed=[]
 unique_fids_by_year=collections.defaultdict(lambda:collections.defaultdict(set))
 writer=None
 if args.mode=='import':
  writer=sqlite3.connect(db,timeout=15);writer.execute('PRAGMA busy_timeout=15000');ensure_schema(writer)
  # Reuse same extraction function as the approved Crown archive utility; no API calls.
 for (fid,expected_sha),metas in groups.items():
  p=next((m['path'] for m in metas if m.get('path') and m['path'].is_file()),None)
  if p is None:
   counts['raw_file_missing']+=1;continue
  try:b=p.read_bytes()
  except Exception:counts['raw_read_error']+=1;continue
  got=sha_bytes(b)
  # A supplied SHA must match its raw response. Cache sources without an externally
  # supplied SHA compute their identity from the immutable bytes above.
  if got!=expected_sha:
   hash_mismatches.append({'fid':fid,'expected_sha256':expected_sha,'actual_sha256':got,'source_types':sorted({m['source_type'] for m in metas})});counts['raw_sha_mismatch']+=1;continue
  try:body=json.loads(b)
  except Exception:counts['invalid_json']+=1;continue
  match=extract_fixture(body,fid)
  if not match:
   identity_mismatches.append({'fid':fid,'sha256':got,'reason':'fixture_id_not_in_response'});counts['fixture_id_mismatch']+=1;continue
  ko=parse_ts(match.get('start')) or next((m.get('kickoff') for m in metas if m.get('kickoff')),None)
  book=crown_book(match);quotes=ou_rows(book);layers=ah_layers(book)
  has_summary=any(q[0] in ('open','close') for q in quotes);nlist=sum(q[0]=='movement' for q in quotes)
  counts['unique_fid_sha_responses']+=1;counts['responses_with_crown_book']+=int(book is not None)
  counts['responses_with_ou_open_close']+=int(has_summary);counts['responses_with_goal_list']+=int(nlist>0)
  if has_summary and nlist:counts['responses_with_both_summary_and_path']+=1
  if book is None:counts['responses_without_crown_book']+=1
  if not quotes:counts['responses_without_ou_values']+=1
  year=(ko[:4] if ko else inventory_years.get(fid,'unknown'))
  by_year[year]['response_bodies']+=1;by_year[year]['open_close_responses']+=int(has_summary);by_year[year]['goal_list_responses']+=int(nlist>0)
  by_source[','.join(sorted({m['source_type'] for m in metas}))]['response_bodies']+=1
  # Keep unique fixture counts distinct from response-body/SHA counts. A fixture
  # may legitimately have multiple historical captures with different SHAs.
  unique_fids_by_year[year]['any_crown_response'].add(fid)
  if book is not None:unique_fids_by_year[year]['with_crown_book'].add(fid)
  if has_summary:unique_fids_by_year[year]['with_ou_open_close'].add(fid)
  if nlist>0:unique_fids_by_year[year]['with_ou_goal_list'].add(fid)
  for q in quotes:quote_kinds[q[0]]+=1;by_year_kind[year][q[0]]+=1
  if args.mode!='import':continue
  assert writer is not None
  # Reuse an existing unified capture for identical FID/SHA evidence. Only raw
  # files absent from the shared store create capture rows, so this integration
  # does not expand or alter the active AH collection queue.
  is_network=any(m['source_type']=='ou_network_collection' for m in metas)
  source_path=p
  if is_network:
   source_path=STORE_RAW/fid/(got+'.json')
   if not source_path.exists():crown.archive_file(source_path,b)
  capture_keys=sorted({m['existing_capture_key'] for m in metas if m.get('existing_capture_key')})
  if not capture_keys:
   capture_keys=[r[0] for r in writer.execute('SELECT capture_key FROM capture WHERE fixture_id=? AND response_sha256=?',(fid,got)).fetchall()]
  # Reuse all market layers already present in this immutable raw response.
  # A summary capture must not block materializing asian_list from the same SHA.
  existing_layers={r[0] for r in writer.execute('SELECT DISTINCT data_layer FROM capture WHERE fixture_id=? AND response_sha256=?',(fid,got)).fetchall()}
  layers_to_store=layers or ['summary']
  modes=sorted({(m.get('mode') or 'historical',m.get('received')) for m in metas},key=lambda z:(z[0],z[1] or ''))
  for layer in layers_to_store:
   if layer in existing_layers:continue
   for mode0,received0 in modes:
    key=cap_key(layer,mode0,fid,got,received0)
    if writer.execute('SELECT 1 FROM capture WHERE capture_key=?',(key,)).fetchone() is None:
     crown.store_response(writer,fid,layer,mode0,source_path,received0,match.get('start'))
    if key not in capture_keys:capture_keys.append(key)
   existing_layers.add(layer)
  layers_to_store=layers or ['summary']
  if not capture_keys:
   counts['capture_link_missing']+=1;continue
  primary_key=next((k for k in capture_keys if writer.execute('SELECT data_layer FROM capture WHERE capture_key=?',(k,)).fetchone() and writer.execute('SELECT data_layer FROM capture WHERE capture_key=?',(k,)).fetchone()[0]=='summary'),capture_keys[0])
  for m in metas:
   receipt=m.get('received');m_mode=m.get('mode') or 'historical'
   sk=hashlib.sha256('|'.join((m['source_type'],fid,got,str(receipt or ''),str(m.get('existing_capture_key') or ''),str(m.get('path') or ''))).encode()).hexdigest()
   linked=m.get('existing_capture_key') or primary_key
   status=m.get('response_status') or 'RAW_AVAILABLE'
   writer.execute('''INSERT OR IGNORE INTO crown_ou_source
      (source_key,fixture_id,capture_key,source_type,capture_mode,response_received_at_utc,kickoff_at_utc,source_file,response_sha256,response_status,raw_sha_verified,has_goal_summary,goal_list_count,imported_at_utc)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sk,fid,linked,m['source_type'],m_mode,receipt,ko,str(m.get('path') or p),got,status,1,int(has_summary),nlist,dt.datetime.now(UTC).isoformat()))
   for i,q in enumerate(quotes):
    kind,line,over,under,source_time=q
    before=int(source_time<ko) if source_time and ko else None
    prospective=int(m_mode=='live' and bool(receipt and ko and receipt<ko))
    writer.execute('''INSERT OR IGNORE INTO crown_ou_quote
       (source_key,sequence_index,fixture_id,quote_kind,total_line,over_decimal,under_decimal,quote_source_at_utc,response_received_at_utc,prospective_observation,quote_before_kickoff)
       VALUES (?,?,?,?,?,?,?,?,?,?,?)''',(sk,i,fid,kind,line,over,under,source_time,receipt,prospective,before))
   if quotes:counts['source_receipts_with_ou']+=1
   counts['source_receipt_rows']+=1
   if counts['source_receipt_rows']%100==0:writer.commit()
  processed.append((fid,got))
 # Include request failures without pretending a response/quote exists.
 if args.mode=='import' and writer:
  for m in failures:
   rec=m.get('log_record') or {};fid=m['fid'];status=m.get('response_status') or 'UNKNOWN'
   sk=hashlib.sha256('|'.join((m['source_type'],fid,status,str(rec.get('error') or ''))).encode()).hexdigest()
   writer.execute('''INSERT OR IGNORE INTO crown_ou_source
      (source_key,fixture_id,capture_key,source_type,capture_mode,response_received_at_utc,kickoff_at_utc,source_file,response_sha256,response_status,raw_sha_verified,has_goal_summary,goal_list_count,imported_at_utc)
      VALUES (?,?,NULL,?,?,?,?,NULL,NULL,?,0,0,0,?)''',(sk,fid,m['source_type'],'historical',None,None,status,dt.datetime.now(UTC).isoformat()))
   counts['failed_or_bodyless_request_rows']+=1
  writer.commit()
  writer.close()
 result={'study':'CROWN_AH_OU_SHARED_STORE_INTEGRATION','mode':args.mode,'generated_at_utc':dt.datetime.now(UTC).isoformat(),
  'scope':('exact 64-league target schedule' if target_fids is not None else 'all existing 2019-2026 sources')+'; local normalization/import only; no network requests',
  'sources':{'fixture_inventory_path':str(INVENTORY),'fixture_inventory_unique_fids':len(inventory_ids),'target_schedule_fids':len(target_fids) if target_fids is not None else None,'m5_raw_dir':str(M5),'m5_raw_json_count':sum(1 for _ in M5.glob('*.json')) if M5.exists() else 0,'legacy_epl_raw_dir':str(EPL),'network_log':str(NETWORK_LOG),'network_log_records_seen':sum(1 for _ in load_jsonl(NETWORK_LOG) or []),'sqlite_path':str(db),'sqlite_counts_before':table_counts},
  'counts':dict(counts),'quote_rows_by_kind':dict(quote_kinds),'by_year_response_bodies':{k:dict(v) for k,v in sorted(by_year.items())},
  'unique_fids_by_year':{y:{k:len(v) for k,v in kinds.items()} for y,kinds in sorted(unique_fids_by_year.items())},
  'quote_rows_by_year_and_kind':{k:dict(v) for k,v in sorted(by_year_kind.items())},
  'by_source_type':{k:dict(v) for k,v in by_source.items()},'sha_mismatches':hash_mismatches[:100],'sha_mismatch_n':len(hash_mismatches),'identity_mismatches':identity_mismatches[:100],'identity_mismatch_n':len(identity_mismatches),
  'existing_ou_source_rows_before':ou_before,'new_source_rows_or_imported_responses':len(processed),'database_after':None}
 if args.mode=='import':
  cx=sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=30);cx.execute('PRAGMA busy_timeout=30000')
  result['database_after']={t:int(cx.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ('capture','asian_quote','crown_ou_source','crown_ou_quote')}
  result['database_after']['unique_ou_fids']=int(cx.execute('SELECT COUNT(DISTINCT fixture_id) FROM crown_ou_quote').fetchone()[0])
  result['database_after']['ou_by_kind']={k:int(v) for k,v in cx.execute('SELECT quote_kind,COUNT(*) FROM crown_ou_quote GROUP BY quote_kind')}
  result['database_after']['pregame_actual_receipt_quotes']=int(cx.execute('SELECT COUNT(*) FROM crown_ou_quote WHERE prospective_observation=1').fetchone()[0])
  result['database_after']['target_inventory_ou_fids']=int(cx.execute('SELECT COUNT(DISTINCT q.fixture_id) FROM crown_ou_quote q JOIN (SELECT DISTINCT fixture_id FROM capture WHERE kickoff_at_utc >= \'2019-01-01\' AND kickoff_at_utc < \'2027-01-01\') t ON t.fixture_id=q.fixture_id').fetchone()[0])
  cx.close()
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
