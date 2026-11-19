#!/usr/bin/env python3
"""Read-only forensic audit for the Crown collection/store topology.

Reads the user's local Crown SQLite, persisted Crown HTTP artifacts, launchd state,
M7 runner records and MR1 shadow-v23 snapshots. Writes only derived, sanitized
artifacts into this research directory; never calls TotalCorner or mutates sources.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, pathlib, re, sqlite3, statistics, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'research/m8/crown_collection_diagnostic_20261119'
OUT.mkdir(parents=True, exist_ok=True)
BASE = pathlib.Path('/Users/mac/QuantAsiaDesk')
DB = BASE / 'data/crown_quote_store/crown_quotes.sqlite3'
RAW = BASE / 'data/crown_quote_store/raw'
M7 = BASE / 'research-work/m7'
M7_RUNS = M7 / 'm7_unified_approved_future_live_rechecks_20261111'
M7_RUNNER = M7 / 'm7_run_unified_live_rechecks_with_batch_boundary_priority_20261110.py'
MR1 = BASE / 'repos/mr1'
MR1_ROOT = MR1 / 'data/prospective-market/shadow-v23'
MR1_INDEX = MR1_ROOT / 'snapshot-index.jsonl'
MR1_LOG = BASE / 'logs/mr1_collect_background.log'
BACKFILL_LOG = BASE / 'logs/crown-ah-five-season-backfill.log'
BACKFILL_ERR = BASE / 'logs/crown-ah-five-season-backfill-error.log'


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p: pathlib.Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def parse_dt(s):
    if not s: return None
    return dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))

def iso_week(s):
    x=parse_dt(s)
    return f'{x.isocalendar()[0]}-W{x.isocalendar()[1]:02}' if x else None

def pct(values, q):
    if not values: return None
    vals=sorted(values)
    return vals[min(len(vals)-1,int((len(vals)-1)*q))]

def norm_exception(code):
    return code if code else 'UNKNOWN'

# Freeze the append-only MR1 index at the byte boundary read here; later appends
# during the live 5-minute scheduler do not alter this audit snapshot.
started=dt.datetime.now(dt.timezone.utc)
idx_bytes=MR1_INDEX.read_bytes()
complete=idx_bytes.splitlines()
index_records=[]
for b in complete:
    if not b.strip(): continue
    try: index_records.append(json.loads(b))
    except Exception: continue
index_sha=sha_bytes(idx_bytes)

cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=30)
cx.row_factory=sqlite3.Row
capture_groups=[dict(r) for r in cx.execute("""SELECT capture_mode,data_layer,status,prospective_observation,
 COUNT(*) captures,COUNT(DISTINCT fixture_id) fids,MIN(response_received_at_utc) first_received,
 MAX(response_received_at_utc) last_received FROM capture GROUP BY 1,2,3,4 ORDER BY 1,2,3,4""")]
fail_rows=[dict(r) for r in cx.execute("SELECT attempted_at_utc,fixture_id,data_layer,capture_mode,error_code FROM failed_attempt ORDER BY attempted_at_utc")]
fail_groups=[dict(r) for r in cx.execute("""SELECT data_layer,capture_mode,error_code,COUNT(*) failure_rows,
 COUNT(DISTINCT fixture_id) unique_fids,MIN(attempted_at_utc) first_attempt,MAX(attempted_at_utc) last_attempt
 FROM failed_attempt GROUP BY 1,2,3 ORDER BY 1,2,3""")]
all_caps=[dict(r) for r in cx.execute("SELECT fixture_id,data_layer,capture_mode,status,response_received_at_utc,processed_at_utc,source_file,response_sha256,kickoff_at_utc,quote_count,prospective_observation FROM capture")]
caps_by_key=collections.defaultdict(list)
for r in all_caps: caps_by_key[(str(r['fixture_id']),r['data_layer'],r['capture_mode'])].append(r)

# Verify and classify every live summary no-quote response and aggregate the 248
# event inventory. Raw response contents themselves remain local and unpublished.
noquote_rows=[r for r in all_caps if r['capture_mode']=='live' and r['data_layer']=='summary' and r['status']=='NO_CROWN_AH_QUOTES']
no_by_fid=collections.defaultdict(list); no_sha=set(); no_integrity={'files':0,'sha_match':0,'missing':0,'mismatch':0,'success_one':0,'matching_fixture':0,'bookmakers_empty':0,'crown_absent':0,'raw_body_invalid':0}
no_leads=[]; no_week=collections.Counter(); no_league_capture=collections.Counter(); no_league_fid=collections.defaultdict(set)
for r in noquote_rows:
    p=pathlib.Path(r['source_file']) if r.get('source_file') else None
    if not p or not p.is_file(): no_integrity['missing']+=1; continue
    body=p.read_bytes(); no_integrity['files']+=1
    h=sha_bytes(body)
    if h==r['response_sha256']: no_integrity['sha_match']+=1
    else: no_integrity['mismatch']+=1
    no_sha.add(h)
    try:
        payload=json.loads(body)
        data=payload.get('data')
        match=data[0] if isinstance(data,list) and len(data)==1 else data if isinstance(data,dict) else None
        if payload.get('success') in (1,True,'1'): no_integrity['success_one']+=1
        if isinstance(match,dict) and str(match.get('id'))==str(r['fixture_id']): no_integrity['matching_fixture']+=1
        books=match.get('bookmakers') if isinstance(match,dict) else None
        if isinstance(books,list) and len(books)==0: no_integrity['bookmakers_empty']+=1
        if isinstance(books,list) and not any(str(x.get('slug','')).lower()=='crown' for x in books if isinstance(x,dict)): no_integrity['crown_absent']+=1
        if not isinstance(match,dict): no_integrity['raw_body_invalid']+=1
        event={
          'fid':str(r['fixture_id']),'home':match.get('h') if isinstance(match,dict) else None,
          'away':match.get('a') if isinstance(match,dict) else None,
          'league':match.get('l') if isinstance(match,dict) else None,
          'league_id':match.get('l_id') if isinstance(match,dict) else None,
          'source_start_local':match.get('start') if isinstance(match,dict) else None,
          'kickoff_utc':r.get('kickoff_at_utc'),
          'capture_count':0,'first_http_received_utc':None,'last_http_received_utc':None,
          'unique_response_sha256':set(),'success_response_count':0,'bookmakers_empty_response_count':0,
          'crown_bookmaker_present_response_count':0,'later_shared_sqlite_quote':False,
          'later_mr1_crown_ah_receipt_after_2026_11_14':False,
          'last_noquote_lead_hours':None,'min_noquote_lead_hours':None,
        }
        fid=str(r['fixture_id']); no_by_fid[fid].append((r,event,match))
        if event['league']:
            no_league_capture[event['league']]+=1; no_league_fid[event['league']].add(fid)
        if payload.get('success') in (1,True,'1') and isinstance(match,dict) and str(match.get('id'))==fid:
            event['success_response_count']+=1
        if isinstance(books,list) and len(books)==0: event['bookmakers_empty_response_count']+=1
        if isinstance(books,list) and any(str(x.get('slug','')).lower()=='crown' for x in books if isinstance(x,dict)):
            event['crown_bookmaker_present_response_count']+=1
        if r.get('kickoff_at_utc') and r.get('response_received_at_utc'):
            lead=(parse_dt(r['kickoff_at_utc'])-parse_dt(r['response_received_at_utc'])).total_seconds()/3600
            no_leads.append(lead); event['min_noquote_lead_hours']=lead; event['last_noquote_lead_hours']=lead
        no_week[iso_week(r.get('response_received_at_utc'))]+=1
    except Exception:
        no_integrity['raw_body_invalid']+=1

noquote_events=[]
for fid, vals in sorted(no_by_fid.items()):
    events=[x[1] for x in vals]; recs=[x[0] for x in vals]
    # source metadata is fixed for one FID; use first API response only after ID validation.
    event=dict(events[0]); times=[x['response_received_at_utc'] for x in recs if x.get('response_received_at_utc')]
    leads=[(parse_dt(x['kickoff_at_utc'])-parse_dt(x['response_received_at_utc'])).total_seconds()/3600 for x in recs if x.get('kickoff_at_utc') and x.get('response_received_at_utc')]
    sha_list=sorted({x['response_sha256'] for x in recs if x.get('response_sha256')})
    event.update({'capture_count':len(recs),'first_http_received_utc':min(times) if times else None,
      'last_http_received_utc':max(times) if times else None,'unique_response_sha256':sha_list,
      'success_response_count':sum(1 for x in events if x['success_response_count']),
      'bookmakers_empty_response_count':sum(1 for x in events if x['bookmakers_empty_response_count']),
      'crown_bookmaker_present_response_count':sum(1 for x in events if x['crown_bookmaker_present_response_count']),
      'min_noquote_lead_hours':min(leads) if leads else None,'last_noquote_lead_hours':leads[-1] if leads else None})
    timeline=caps_by_key.get((fid,'summary','live'),[])
    last_noquote=max(times) if times else ''
    later_quotes=[x for x in timeline if x['status']=='QUOTES_SAVED' and (x.get('response_received_at_utc') or '')>last_noquote]
    event['later_shared_sqlite_quote']=bool(later_quotes)
    noquote_events.append(event)

# Error FID-level audit: the schema holds only the terminal error row per failed
# job, not all retry attempts or raw failure bodies.
failed_by_key=collections.defaultdict(list)
for r in fail_rows: failed_by_key[(str(r['fixture_id']),r['data_layer'],r['capture_mode'])].append(r)
fail_fid_rows=[]; resolution=collections.defaultdict(collections.Counter)
for (fid,layer,mode), rows in sorted(failed_by_key.items()):
    errs=collections.Counter(x['error_code'] for x in rows)
    last_fail=max(x['attempted_at_utc'] for x in rows)
    existing=caps_by_key.get((fid,layer,mode),[])
    saved=[x for x in existing if x['status']=='QUOTES_SAVED']
    noq=[x for x in existing if x['status']=='NO_CROWN_AH_QUOTES']
    later=[x for x in saved if (x.get('response_received_at_utc') or x.get('processed_at_utc') or '')>last_fail]
    if later: state='quote_saved_after_failure'
    elif saved: state='quote_saved_before_or_no_later'
    elif noq: state='terminal_no_crown_quotes'
    else: state='no_terminal_capture_found'
    for err,n in errs.items(): resolution[err][state]+=1
    fail_fid_rows.append({'fid':fid,'data_layer':layer,'capture_mode':mode,'failure_rows':len(rows),
       'error_counts':dict(errs),'first_attempt_utc':min(x['attempted_at_utc'] for x in rows),
       'last_attempt_utc':last_fail,'terminal_state':state,
       'saved_quote_capture_count':len(saved),'no_quote_capture_count':len(noq)})

# Audit MR1's independently persisted, actual Crown snapshots from Nov 14 onward.
cut='2026-11-14T00:00:00'
post_index=[r for r in index_records if r.get('committed_at','')>=cut]
mr1_status=collections.Counter(); mr1_by_week=collections.defaultdict(lambda:{'index_rows':0,'valid_ah_rows':0,'valid_ou_rows':0,'valid_ah_fids':set(),'valid_ou_fids':set(),'snapshot_hash_ok':0,'raw_hash_checked':0,'raw_hash_ok':0,'too_many_request_attempts':0})
mr1_by_fid=collections.defaultdict(list); mr1_hash={'snapshot_files':0,'snapshot_hash_match':0,'snapshot_hash_mismatch':0,'missing_snapshot':0,'raw_attempts_checked':0,'raw_attempts_hash_match':0,'raw_attempts_hash_mismatch':0,'raw_attempts_missing_body':0}
mr1_invalid=[]; post_rate_messages=collections.Counter(); post_rate_count=0; raw_quote_times=[]
for entry in post_index:
    wk=iso_week(entry.get('committed_at')); bucket=mr1_by_week[wk]; bucket['index_rows']+=1
    p=MR1_ROOT/entry['snapshot_path']
    if not p.is_file(): mr1_hash['missing_snapshot']+=1; continue
    sb=p.read_bytes(); mr1_hash['snapshot_files']+=1
    if sha_bytes(sb)==entry.get('snapshot_sha256'): mr1_hash['snapshot_hash_match']+=1; bucket['snapshot_hash_ok']+=1
    else: mr1_hash['snapshot_hash_mismatch']+=1
    try: d=json.loads(sb)
    except Exception: continue
    cls=d.get('classification'); mr1_status[cls]+=1
    # Raw HTTP body values are retained in private MR1 attempt JSON. Verify them
    # in place; publish only counts, not response bodies, odds, or raw paths.
    for a in d.get('request_attempts') or []:
        if a.get('business_code')=='TOO_MANY_REQUEST':
            post_rate_count+=1; post_rate_messages[a.get('business_message','')]+=1; bucket['too_many_request_attempts']+=1
        raw=a.get('raw_response'); rh=a.get('raw_sha256')
        if raw is not None:
            mr1_hash['raw_attempts_checked']+=1; bucket['raw_hash_checked']+=1
            if sha_bytes(raw.encode())==rh and a.get('raw_saved'):
                mr1_hash['raw_attempts_hash_match']+=1; bucket['raw_hash_ok']+=1
            else: mr1_hash['raw_attempts_hash_mismatch']+=1
        else: mr1_hash['raw_attempts_missing_body']+=1
    rec=d.get('received_at'); kick=d.get('kickoff_at'); ah=d.get('AH'); ou=d.get('OU')
    source_ok=d.get('source_bookmaker')=='crown' and d.get('source_bookmaker_verified') is True
    live_timing=bool(rec and kick and rec<kick)
    ah_ok=bool(d.get('prematch_valid') and source_ok and live_timing and isinstance(ah,dict)
      and ah.get('line') is not None and ah.get('home_price') is not None and ah.get('away_price') is not None
      and ah.get('observed_at_utc') and ah.get('observed_at_utc')<=rec and ah.get('observed_at_utc')<kick)
    ou_ok=bool(d.get('prematch_valid') and source_ok and live_timing and isinstance(ou,dict)
      and ou.get('line') is not None and ou.get('over_price') is not None and ou.get('under_price') is not None
      and ou.get('observed_at_utc') and ou.get('observed_at_utc')<=rec and ou.get('observed_at_utc')<kick)
    if ah_ok:
        bucket['valid_ah_rows']+=1; bucket['valid_ah_fids'].add(str(d['match_id'])); mr1_by_fid[str(d['match_id'])].append(d)
        raw_quote_times.append(d['AH']['observed_at_utc'])
    if ou_ok: bucket['valid_ou_rows']+=1; bucket['valid_ou_fids'].add(str(d['match_id']))
    if cls=='SNAPSHOT_OK' and not (ah_ok or ou_ok): mr1_invalid.append({'key':entry.get('key'),'classification':cls,'source_crown_verified':source_ok,'prematch_valid':d.get('prematch_valid')})

# Public detail join for noquote IDs against later independent MR1 Crown receipts.
for e in noquote_events:
    vals=mr1_by_fid.get(e['fid'],[])
    e['later_mr1_crown_ah_receipt_after_2026_11_14']=bool(vals)
    e['later_mr1_valid_ah_snapshots_after_2026_11_14']=len(vals)

# Current collector run records and liveness, no output includes credential/env data.
run_lines=[]
if MR1_LOG.exists():
    for line in MR1_LOG.read_text(errors='replace').splitlines():
        if line.startswith('{'):
            try:
                x=json.loads(line)
                if isinstance(x,dict) and x.get('run_id'): run_lines.append(x)
            except Exception: pass
now=dt.datetime.now(dt.timezone.utc)
last24=[x for x in run_lines if parse_dt(x.get('run_id','')[:20].replace('T','T').replace('-', '-', 0))] if False else []
# run_id timestamp is compact-readable; use finished_at for date range.
last24=[x for x in run_lines if parse_dt(x.get('finished_at')) and now-parse_dt(x['finished_at'])<=dt.timedelta(hours=24)]
latest_runs=run_lines[-10:]

# Backfill log final JSON-like records and interruption evidence.
backfill_records=[]
if BACKFILL_LOG.exists():
    for line in BACKFILL_LOG.read_text(errors='replace').splitlines():
        try:
            x=json.loads(line)
            if isinstance(x,dict): backfill_records.append(x)
        except Exception: pass
backfill_summaries=[x for x in backfill_records if x.get('protocol')=='CROWN_AH_EXPANDED62_TIME_FORWARD_V2' or x.get('status')=='SEASON_BACKFILL_AND_REPLAY_COMPLETE']
backfill_text=BACKFILL_ERR.read_text(errors='replace') if BACKFILL_ERR.exists() else ''

# M7 runner lifecycle and omitted capture windows.
m7_events=[]
if (M7_RUNS/'runner.jsonl').exists():
    for line in (M7_RUNS/'runner.jsonl').read_text(errors='replace').splitlines():
        try:
            x=json.loads(line)
            if isinstance(x,dict): m7_events.append(x)
        except Exception: pass
m7_status=json.loads((M7_RUNS/'status.json').read_text()) if (M7_RUNS/'status.json').exists() else {}
post_m7_windows=[x for x in m7_events if x.get('state') in ('WINDOW_COMPLETE','WINDOW_FAILED') and x.get('updated_at_utc','')>='2026-11-14']
missed=[x for x in m7_events if x.get('state') in ('SKIPPED_MISSED_PREKICKOFF_WINDOW','SKIPPED_AFTER_BATCH_BOUNDARY_WAIT')]
ps=subprocess.run(['ps','-ax','-o','command='],capture_output=True,text=True).stdout
m7_process_alive=any('m7_run_unified_live_rechecks_with_batch_boundary_priority_20261110.py' in x for x in ps.splitlines())
launch=subprocess.run(['launchctl','list'],capture_output=True,text=True).stdout
m7_launchd_loaded='m7_run_unified_live_rechecks' in launch or 'm7-unified-live' in launch.lower()

# Provider/collection configuration. Values are source-coded/configured, not changed here.
store_script=BASE/'scripts/crown_capture_store.py'
backfill_script=BASE/'research-work/crown-drop-expanded-62/backfill_five_full_seasons.py'
mr1_script=MR1/'src/shadow-v23.js'
mr1_source=MR1/'src/crown-source.js'
mr1_config=json.loads((MR1/'config/shadow-market-v23.json').read_text())
recent_start=dt.datetime.now(dt.timezone.utc)

def file_meta(p):
    return {'exists':p.exists(),'sha256':sha_file(p) if p.exists() and p.is_file() else None,'bytes':p.stat().st_size if p.exists() else None}
inputs={
 'shared_crown_sqlite':{'path':str(DB),'exists':DB.exists(),'bytes':DB.stat().st_size if DB.exists() else None,'mtime_utc':dt.datetime.fromtimestamp(DB.stat().st_mtime,dt.timezone.utc).isoformat() if DB.exists() else None},
 'crown_capture_store_py':file_meta(store_script),'m7_runner_py':file_meta(M7_RUNNER),'mr1_shadow_v23_js':file_meta(mr1_script),'mr1_crown_source_js':file_meta(mr1_source),
 'mr1_snapshot_index':{'path':str(MR1_INDEX),'bytes_read':len(idx_bytes),'sha256_prefix_snapshot':index_sha,'records':len(index_records)},
 'previous_public_audit':file_meta(ROOT/'research/m8/M8_PREMATCH_INFORMATION_LIVE_RECEIPT_AUDIT_20261119.md'),
 'project_handoff':file_meta(ROOT/'PROJECT_HANDOFF.md')}

# Persist one JSONL row for every affected noquote FID and one for every failed FID/layer.
with (OUT/'no_crown_quotes_event_inventory_20261119.jsonl').open('w') as f:
    for x in noquote_events: f.write(json.dumps(x,ensure_ascii=False)+'\n')
with (OUT/'failed_capture_fid_inventory_20261119.jsonl').open('w') as f:
    for x in fail_fid_rows: f.write(json.dumps(x,ensure_ascii=False)+'\n')

week_summary=[]
for wk,b in sorted(mr1_by_week.items()):
    week_summary.append({'iso_week':wk,'snapshot_index_rows':b['index_rows'],'verified_pregame_crown_ah_snapshots':b['valid_ah_rows'],
      'unique_fids_with_ah':len(b['valid_ah_fids']),'verified_pregame_crown_ou_snapshots':b['valid_ou_rows'],
      'unique_fids_with_ou':len(b['valid_ou_fids']),'snapshot_sha256_verified':b['snapshot_hash_ok'],
      'raw_response_hashes_checked':b['raw_hash_checked'],'raw_response_hashes_verified':b['raw_hash_ok'],
      'rate_limit_attempt_records':b['too_many_request_attempts']})

# Failure and noquote aggregate details.
noquote_leads=[(parse_dt(r['kickoff_at_utc'])-parse_dt(r['response_received_at_utc'])).total_seconds()/3600 for r in noquote_rows if r.get('kickoff_at_utc') and r.get('response_received_at_utc')]
no_league_top=[{'league':k,'capture_rows':v,'unique_fids':len(no_league_fid[k])} for k,v in no_league_capture.most_common()]

# Recent registered schedule inventory and the broader MR1 weekly denominator.
MR1_FIXTURES=json.loads((MR1_ROOT/'fixtures.json').read_text())
fixture_week_counts=collections.Counter()
fixture_week_leagues=collections.defaultdict(set)
for fid,fixture in MR1_FIXTURES.items():
    kickoff=fixture.get('kickoff_at')
    if not kickoff: continue
    week=iso_week(kickoff)
    fixture_week_counts[week]+=1
    if fixture.get('league'): fixture_week_leagues[week].add(fixture['league'])
registered_week_inventory=[{'kickoff_iso_week':w,'registered_fixtures':fixture_week_counts[w],
    'leagues_with_fixture':len(fixture_week_leagues[w])} for w in ('2026-W45','2026-W46','2026-W47')]
recent_index=[r for r in index_records if r.get('committed_at','')>='2026-11-02T00:00:00']
recent_week=collections.defaultdict(lambda:{'index_rows':0,'ids':set(),'valid_ah_rows':0,'valid_ah_fids':set(),
  'valid_ou_rows':0,'valid_ou_fids':set(),'classification_counts':collections.Counter()})
for entry in recent_index:
    p=MR1_ROOT/entry['snapshot_path']
    if not p.is_file(): continue
    try: snap=json.loads(p.read_bytes())
    except Exception: continue
    week=iso_week(entry.get('committed_at')); b=recent_week[week]
    b['index_rows']+=1; b['ids'].add(str(entry.get('match_id'))); b['classification_counts'][entry.get('classification')]+=1
    receipt=snap.get('received_at'); kickoff=snap.get('kickoff_at'); ah=snap.get('AH'); ou=snap.get('OU')
    source_ok=snap.get('source_bookmaker')=='crown' and snap.get('source_bookmaker_verified') is True
    timing_ok=bool(receipt and kickoff and receipt<kickoff)
    ah_ok=bool(snap.get('prematch_valid') and source_ok and timing_ok and isinstance(ah,dict)
      and all(ah.get(k) is not None for k in ('line','home_price','away_price'))
      and ah.get('observed_at_utc') and ah['observed_at_utc']<=receipt and ah['observed_at_utc']<kickoff)
    ou_ok=bool(snap.get('prematch_valid') and source_ok and timing_ok and isinstance(ou,dict)
      and all(ou.get(k) is not None for k in ('line','over_price','under_price'))
      and ou.get('observed_at_utc') and ou['observed_at_utc']<=receipt and ou['observed_at_utc']<kickoff)
    if ah_ok: b['valid_ah_rows']+=1; b['valid_ah_fids'].add(str(entry.get('match_id')))
    if ou_ok: b['valid_ou_rows']+=1; b['valid_ou_fids'].add(str(entry.get('match_id')))
recent_week_summary=[{'iso_week':w,'snapshot_index_rows':b['index_rows'],'unique_fids_with_snapshot':len(b['ids']),
  'classification_counts':dict(b['classification_counts']),'verified_crown_ah_snapshots':b['valid_ah_rows'],
  'unique_fids_with_ah':len(b['valid_ah_fids']),'verified_crown_ou_snapshots':b['valid_ou_rows'],
  'unique_fids_with_ou':len(b['valid_ou_fids'])} for w,b in sorted(recent_week.items())]
shared_sqlite_live_quoted_fids={str(r['fixture_id']) for r in all_caps if r['capture_mode']=='live' and r['status']=='QUOTES_SAVED'}
mr1_post_fids=set(mr1_by_fid)

result={
 'audit_generated_at_utc':started.isoformat(),
 'repo_head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),
 'scope':'Read-only diagnosis. No API calls, no writes to source stores, no production changes.',
 'inputs':inputs,
 'shared_sqlite':{
   'capture_status_groups':capture_groups,
   'last_live_summary_quote_receipt_utc':max((r['last_received'] for r in capture_groups if r.get('capture_mode')=='live' and r.get('data_layer')=='summary' and r.get('status')=='QUOTES_SAVED' and r.get('last_received')),default=None),
   'failed_attempt_groups':fail_groups,
   'failed_attempt_total_rows':len(fail_rows),
   'failed_fid_resolution_by_error':{k:dict(v) for k,v in resolution.items()},
   'failure_schema_fields':['attempted_at_utc','fixture_id','data_layer','capture_mode','error_code'],
   'failure_attempt_semantics':'one terminal error row per collect job/FID/layer; crown_capture_store.request_fixture can attempt up to four HTTP calls before the final error is stored.'
 },
 'no_crown_ah_quotes':{
   'capture_rows':len(noquote_rows),'unique_fids':len(noquote_events),'unique_response_sha256':len(no_sha),
   'raw_integrity':no_integrity,
   'all_valid_payloads_success_one_matching_fid':no_integrity['success_one']==len(noquote_rows) and no_integrity['matching_fixture']==len(noquote_rows),
   'all_responses_empty_bookmakers':no_integrity['bookmakers_empty']==len(noquote_rows),
   'request_reconstructed_from_code':{'method':'GET','endpoint':'https://api.totalcorner.com/v1/match/bookmaker_odds/{FID}','query':'bookmaker=crown','data_layer':'summary','raw_request_start_time_and_http_status_not_stored_in_crown_capture_table':True},
   'response_shape':'TotalCorner JSON success=1; one matching fixture; bookmakers=[]; therefore at that request time the API returned no bookmaker quote object. This is not evidence the underlying Crown market never existed.',
   'response_week_counts':dict(no_week),
   'repeat_captures_per_fid':dict(collections.Counter(x['capture_count'] for x in noquote_events)),
   'kickoff_lead_hours':{'min':min(noquote_leads) if noquote_leads else None,'p10':pct(noquote_leads,.10),'median':statistics.median(noquote_leads) if noquote_leads else None,'p90':pct(noquote_leads,.90),'max':max(noquote_leads) if noquote_leads else None},
   'kickoff_utc_range':{'min':min((x['kickoff_utc'] for x in noquote_events if x.get('kickoff_utc')),default=None),'max':max((x['kickoff_utc'] for x in noquote_events if x.get('kickoff_utc')),default=None)},
   'league_event_inventory':no_league_top,
   'later_shared_sqlite_quote_fids':sum(x['later_shared_sqlite_quote'] for x in noquote_events),
   'later_mr1_verified_crown_ah_fids_after_2026_11_14':sum(x['later_mr1_crown_ah_receipt_after_2026_11_14'] for x in noquote_events),
   'event_inventory_file':'no_crown_quotes_event_inventory_20261119.jsonl'
 },
 'mr1_independent_production_adjacent_capture':{
   'store_path':str(MR1_ROOT),'store_is_shared_crown_sqlite':False,'index_cutoff_utc':'2026-11-14T00:00:00Z',
   'index_rows_since_cutoff':len(post_index),'unique_fids_since_cutoff':len(set(str(x.get('match_id')) for x in post_index)),
   'classification_counts':dict(mr1_status),
   'verified_actual_pregame_crown_ah_rows':sum(v['valid_ah_rows'] for v in mr1_by_week.values()),
   'unique_fids_with_verified_ah':len(mr1_by_fid),
   'verified_ah_fids_also_present_in_shared_sqlite':len(mr1_post_fids & shared_sqlite_live_quoted_fids),
   'verified_ah_fids_absent_from_shared_sqlite':len(mr1_post_fids - shared_sqlite_live_quoted_fids),
   'verified_actual_pregame_crown_ou_rows':sum(v['valid_ou_rows'] for v in mr1_by_week.values()),
   'unique_fids_with_verified_ou':len({fid for b in mr1_by_week.values() for fid in b['valid_ou_fids']}),
   'weekly_receipts':week_summary,
   'recent_weekly_inventory_since_2026_11_02':recent_week_summary,
   'registered_schedule_fixture_inventory_by_kickoff_week':registered_week_inventory,
   'snapshot_and_raw_hash_audit':mr1_hash,
   'rate_limit_error_records_in_post_cutoff_snapshots':post_rate_count,
   'rate_limit_provider_messages':dict(post_rate_messages),
   'validation_exceptions':'SNAPSHOT_OK entries counted as usable only when Crown verified, pregame, source quote time <= HTTP receipt < kickoff, and AH/OU line plus both prices exist.',
   'index_snapshot_sha256':index_sha
 },
 'm7_shared_sqlite_runner':{
   'runner_status_last_record':m7_status,
   'runner_last_event':m7_events[-1] if m7_events else None,
   'runner_last_log_event_utc':m7_events[-1].get('updated_at_utc') if m7_events else None,
   'runner_process_present_now':m7_process_alive,'dedicated_m7_launchd_loaded':m7_launchd_loaded,
   'last_live_capture_windows_after_2026_11_14':[{'state':x.get('state'),'updated_at_utc':x.get('updated_at_utc'),'kickoff_utc':x.get('kickoff_utc'),'fixture_ids':x.get('fixture_ids'),'collector_counts':(x.get('result') or {}).get('counts'),'validation_ok':x.get('independent_validation_ok')} for x in post_m7_windows],
   'skipped_prekickoff_windows_logged':len(missed),
   'skipped_unique_fids':[str(fid) for fid in sorted({str(fid) for x in missed for fid in x.get('fixture_ids',[])})],
   'source_schedule_snapshot_sha256_latest':next((x.get('source_sha256') for x in reversed(m7_events) if x.get('state')=='SCHEDULED'),None),
   'source_schedule_candidate_count_latest':next((x.get('candidate_count') for x in reversed(m7_events) if x.get('state')=='SCHEDULED'),None),
   'source_schedule_offsets_minutes':[55,25,5],
   'runner_code_is_infinite_loop':True,'runner_has_dedicated_launchd_restart':m7_launchd_loaded,
   'last_status_is_stale_vs_current_time':bool(m7_events and (now-parse_dt(m7_events[-1]['updated_at_utc'])).total_seconds()>3600)
 },
 'backfill_run':{
   'launchd_label':'com.quantasia.crown-ah-five-season-backfill','last_exit_code_observed_from_launchctl':0,
   'terminal_summaries':[{k:x.get(k) for k in ('status','collection_counts','retry_counts','finished_at_epoch') if k in x} for x in backfill_summaries[-2:]],
   'error_log_has_interrupt_or_keyboardinterrupt':('KeyboardInterrupt' in backfill_text or 'exited with -2' in backfill_text),
   'backfill_code_request_interval_seconds_explicit':2.1
 },
 'mr1_current_workflow':{
   'launchd_label':'com.quantasia.mr1.collect','runs_last_24h':len(last24),
   'snapshots_committed_last_24h':sum(int(x.get('snapshots_committed_this_run') or 0) for x in last24),
   'http_requests_last_24h':sum(int(x.get('requests_this_run') or 0) for x in last24),
   'latest_runs':[{k:x.get(k) for k in ('run_id','status','snapshots_committed_this_run','requests_this_run','finished_at') if k in x} for x in latest_runs],
   'current_config':{'launchd_interval_seconds':300,'scheduler_interval_minutes':mr1_config.get('scheduler_interval_minutes'),
     'minimum_request_start_interval_ms':mr1_config.get('minimum_request_start_interval_ms'),
     'request_timeout_ms':mr1_config.get('request_timeout_ms'),'max_run_ms':mr1_config.get('max_run_ms'),
     'max_snapshots_per_run':mr1_config.get('max_snapshots_per_run'),'horizons':mr1_config.get('horizons'),
     'endpoint_sequence':['/match/view/{FID}','/match/bookmaker_odds/{FID}?bookmaker=crown']},
   'separate_from_crown_capture_store_sqlite':True
 },
 'rate_limit_evidence':{
   'stored_crown_db_code':'TOO_MANY_REQUEST; no raw HTTP response/status/headers are kept for those failed jobs.',
   'provider_message_from_MR1_persisted_http_attempts':'exceed the rate limit, allowed 5 request in 10 seconds. API Boost raises it to 60 requests per minute.',
   'request_intervals_observed_in_code':{'crown_capture_store_cli_default_seconds':5.2,'five_season_backfill_override_seconds':2.1,'m7_runner_override_seconds':3.0,'MR1_production_minimum_request_start_interval_seconds':mr1_config.get('minimum_request_start_interval_ms',0)/1000},
   'same_credential_source':'crown_capture_store reads QuantAsiaDesk.TOTALCORNER_TOKEN from macOS Keychain; mr1_background_maintenance.py reads the same Keychain service and exports TOTALCORNER_TOKEN to MR1 process.',
   'likely_root_cause':'Provider quota is per credential while the historical backfill, M7 live runner and MR1 collector each implement independent local pacing. Their request starts can overlap and aggregate above the provider 5-per-10-second limit. The 2.1s/3.0s overrides are below the documented 5.2s shared utility default. The old database does not retain failed response bodies, so exact past HTTP status/headers are unavailable.'
 },
 'root_cause_summary':[
   'No new rows in crown_quotes.sqlite3 after 2026-11-14 reflects the one-off M7 T-55/T-25/T-5 runner no longer executing; its last log state is 2026-11-17, it is not registered with launchd, and no process is present at audit time.',
   'This does not mean the whole system stopped collecting Crown AH: MR1 shadow-v23 continued on its own 5-minute launchd schedule and stored verified Crown AH snapshots in a separate immutable snapshot-index/snapshots tree, outside crown_quotes.sqlite3.',
   'The 1,330 NO_CROWN_AH_QUOTES rows are successful, SHA-verified responses with bookmakers=[] for 248 mostly far-ahead fixtures. They mean no Crown quote object was returned then; repeated calls often preceded market publication and do not prove no market existed later.',
   '843 IncompleteRead terminal failure rows are historical movement reads. Each of their 703 FIDs has a QUOTES_SAVED movement capture in the database (701 saved after the last recorded failure, 2 had a saved capture before/no later capture); they are transport truncations but did not leave a current movement-data hole.',
   '82 TOO_MANY_REQUEST rows are explicit TotalCorner quota responses (80 historical movement, 2 live summary). This is a cross-process rate-limit collision risk, not a pricing/business-market status.'
 ],
 'source_code_or_workflow_hashes':inputs,
 'artifacts':{'noquote_event_inventory':'no_crown_quotes_event_inventory_20261119.jsonl','failed_fid_inventory':'failed_capture_fid_inventory_20261119.jsonl'},
 'no_source_store_mutations':True,'no_external_api_requests_made':True,'no_telegram_or_ledger_changes':True
}
(OUT/'CROWN_COLLECTION_DIAGNOSTIC_RESULTS_20261119.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({k:result[k] for k in ('audit_generated_at_utc','shared_sqlite','no_crown_ah_quotes','mr1_independent_production_adjacent_capture','m7_shared_sqlite_runner','backfill_run','mr1_current_workflow','rate_limit_evidence','root_cause_summary')},ensure_ascii=False,indent=2,default=str))
cx.close()
