#!/usr/bin/env python3
"""Import verified forward-shadow Crown HTTP receipts into the local archive as live data."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, sys
from pathlib import Path

BASE=Path('/Users/mac/QuantAsiaDesk')
ROOT=BASE/'data/m5-crown-authorized/forward-shadow'
INDEX=ROOT/'crown-capture-index.jsonl'
OUT=Path('/Users/mac/QuantAsiaDesk/research-work/full_history_backfill_20261121')
sys.path.insert(0,str(BASE/'scripts'))
import crown_capture_store as store

def main():
    cx=store.init_db();counts=collections.Counter();written=[];skipped=0
    for line_no,line in enumerate(INDEX.open(encoding='utf-8'),1):
        row=json.loads(line)
        if row.get('status')!='verified_fixture_response':skipped+=1;continue
        fid=str(row.get('match_id') or '')
        path=(ROOT/str(row['raw_response_relative_path'])).resolve()
        if ROOT.resolve() not in path.parents or not path.is_file():raise RuntimeError(f'RAW_PATH_INVALID:{line_no}')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=row.get('response_sha256'):raise RuntimeError(f'RAW_SHA_MISMATCH:{line_no}:{fid}')
        received=row.get('captured_at_utc');kickoff=row.get('kickoff_utc')
        result=store.store_response(cx,fid,'movement','live',path,received,kickoff)
        counts[result['status']]+=1
        received_utc=store.parse_timestamp(received,assumed_zone=dt.timezone.utc)
        key=hashlib.sha256(f"movement|live|{fid}|{digest}|{received_utc}".encode()).hexdigest()
        rec=cx.execute('select status,quote_count,prospective_observation,kickoff_at_utc from capture where capture_key=?',(key,)).fetchone()
        if rec is None:raise RuntimeError(f'IMPORT_NOT_PERSISTED:{line_no}:{fid}')
        written.append({'index_line':line_no,'match_id':fid,'source_path':str(path.relative_to(BASE)),
          'response_sha256':digest,'response_received_at_utc':received_utc,'kickoff_at_utc':rec[3],
          'capture_status':rec[0],'quote_count':rec[1],'prospective_observation':bool(rec[2]),
          'database_result':result['status']})
    output=OUT/'forward_shadow_live_import_audit.jsonl'
    with output.open('w',encoding='utf-8') as f:
        for row in written:f.write(json.dumps(row,separators=(',',':'))+'\n')
    summary={'imported_or_reused_rows':len(written),'index_rows_skipped_nonverified':skipped,
      'database_result_counts':dict(counts),'unique_fids':len({x['match_id'] for x in written}),
      'prospective_capture_rows':sum(x['prospective_observation'] for x in written),
      'capture_rows_with_AH_quotes':sum(x['quote_count']>0 for x in written),
      'AH_quote_rows':sum(x['quote_count'] for x in written),'output':str(output),
      'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    p=OUT/'forward_shadow_live_import_summary.json';p.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))
    cx.close()

if __name__=='__main__':main()
