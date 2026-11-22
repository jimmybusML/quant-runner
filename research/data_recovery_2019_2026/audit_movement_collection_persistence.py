#!/usr/bin/env python3
"""Independently reconcile an append-only Crown collector log to SQLite and raw SHA files.

This audit is read-only against the Crown database. It makes no HTTP requests and
writes only its optional aggregate JSON report.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, json, pathlib, sqlite3

TERMINAL={'SAVED','NO_CROWN_AH_QUOTES'}

def sha256(path:pathlib.Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--log',type=pathlib.Path,required=True)
    p.add_argument('--database',type=pathlib.Path,required=True)
    p.add_argument('--candidate-count',type=int)
    p.add_argument('--output',type=pathlib.Path)
    a=p.parse_args()
    attempts=[];latest={};candidate_errors=collections.Counter();first_receive=last_receive=None
    with a.log.open(encoding='utf-8') as f:
        for line in f:
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if not isinstance(r,dict) or r.get('fixture_id') is None or not r.get('status'):continue
            fid=str(r['fixture_id']);attempts.append(r)
            if r['status']=='FETCH_FAILED':candidate_errors[str(r.get('error') or 'UNKNOWN')]+=1
            if r.get('response_received_at_utc'):
                t=str(r['response_received_at_utc'])
                first_receive=min(first_receive,t) if first_receive else t
                last_receive=max(last_receive,t) if last_receive else t
            latest[fid]=r
    terminal={fid:r for fid,r in latest.items() if r.get('status') in TERMINAL}
    c=sqlite3.connect(f'file:{a.database}?mode=ro',uri=True);c.row_factory=sqlite3.Row
    matched=collections.Counter();raw_missing=raw_mismatch=receipt_mismatch=quote_count_mismatch=0
    quote_rows=0;capture_keys=[]
    ids=list(terminal)
    for start in range(0,len(ids),700):
        chunk=ids[start:start+700];marks=','.join('?' for _ in chunk)
        rows=c.execute(f"""SELECT capture_key,fixture_id,status,quote_count,response_received_at_utc,
            response_sha256,source_file FROM capture
            WHERE data_layer='movement' AND capture_mode='historical' AND fixture_id IN ({marks})""",chunk).fetchall()
        by_fid=collections.defaultdict(list)
        for row in rows:by_fid[str(row['fixture_id'])].append(row)
        for fid in chunk:
            expected=terminal[fid]
            row=next((x for x in by_fid[fid] if x['response_received_at_utc']==expected.get('response_received_at_utc')),None)
            if row is None:
                receipt_mismatch+=1;continue
            status={'SAVED':'QUOTES_SAVED','NO_CROWN_AH_QUOTES':'NO_CROWN_AH_QUOTES'}[expected['status']]
            if row['status']!=status:matched['status_mismatch']+=1
            matched[expected['status']]+=1
            path=pathlib.Path(row['source_file'])
            if not path.is_file():raw_missing+=1
            elif sha256(path)!=row['response_sha256']:raw_mismatch+=1
            actual=c.execute('SELECT count(*) FROM asian_quote WHERE capture_key=?',(row['capture_key'],)).fetchone()[0]
            reported=int(expected.get('quote_count') or 0)
            if actual!=reported:quote_count_mismatch+=1
            quote_rows+=actual;capture_keys.append(row['capture_key'])
    c.close()
    result={
      'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
      'log_source':'LOCAL_CROWN_MOVEMENT_COLLECTOR_LOG','database_source':'LOCAL_CROWN_SQLITE','read_only_database':True,
      'network_requests':0,'database_writes':0,
      'candidate_fids':a.candidate_count,
      'attempt_rows':len(attempts),'unique_logged_fids':len(latest),
      'latest_status_counts':dict(collections.Counter(str(x.get('status')) for x in latest.values())),
      'latest_terminal_fids':len(terminal),'latest_retryable_fids':sum(x.get('status') not in TERMINAL for x in latest.values()),
      'attempt_failure_codes':dict(candidate_errors),
      'first_http_response_received_at_utc':first_receive,'last_http_response_received_at_utc':last_receive,
      'terminal_fids_matched_to_sqlite':sum(v for k,v in matched.items() if k in TERMINAL),
      'sqlite_capture_status_counts':{k:v for k,v in matched.items() if k in TERMINAL},
      'raw_files_missing':raw_missing,'raw_response_sha_mismatches':raw_mismatch,
      'response_received_timestamp_mismatches':receipt_mismatch,
      'asian_quote_row_count_mismatches':quote_count_mismatch,
      'persisted_asian_quote_rows_for_matched_terminal_fids':quote_rows,
      'pass':(len(terminal)==sum(v for k,v in matched.items() if k in TERMINAL)
              and not raw_missing and not raw_mismatch and not receipt_mismatch
              and not quote_count_mismatch and not matched['status_mismatch'])}
    out=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(out,encoding='utf-8')
    print(out,end='')
    return 0 if result['pass'] else 1

if __name__=='__main__':raise SystemExit(main())
