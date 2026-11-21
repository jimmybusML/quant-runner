#!/usr/bin/env python3
"""Audit, without importing, forward-shadow Crown responses and their receipt index."""
from __future__ import annotations
import collections, datetime as dt, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/Users/mac/QuantAsiaDesk')
ROOT=BASE/'data/m5-crown-authorized/forward-shadow'
INDEX=ROOT/'crown-capture-index.jsonl'
OUT=Path(__file__).resolve().parent
SH=ZoneInfo('Asia/Shanghai')

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def utc(value):
    if not value:return None
    try:
        x=dt.datetime.fromisoformat(str(value).replace('Z','+00:00').replace(' ','T'))
        if x.tzinfo is None:x=x.replace(tzinfo=SH)
        return x.astimezone(dt.timezone.utc)
    except (TypeError,ValueError):return None

def main():
    status=collections.Counter();rows=[];missing=bad_sha=identity_bad=0;quote_rows=0;quoted_fids=set();prospective=pre_kickoff_quotes=0
    league=collections.Counter();receive_dates=collections.Counter()
    for line_no,line in enumerate(INDEX.open(encoding='utf-8'),1):
        r=json.loads(line);st=str(r.get('status') or 'MISSING_STATUS');status[st]+=1
        if st!='verified_fixture_response':continue
        rel=Path(str(r.get('raw_response_relative_path') or ''))
        path=(ROOT/rel).resolve()
        if ROOT.resolve() not in path.parents:
            missing+=1;continue
        if not path.is_file():missing+=1;continue
        actual=sha(path);expected=str(r.get('response_sha256') or '')
        if actual!=expected:bad_sha+=1;continue
        try:body=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError):identity_bad+=1;continue
        data=body.get('data');match=data[0] if isinstance(data,list) and len(data)==1 else data
        fid=str(r.get('match_id') or '')
        if body.get('success') not in (1,True,'1') or not isinstance(match,dict) or str(match.get('id'))!=fid:
            identity_bad+=1;continue
        book=next((b for b in match.get('bookmakers',[]) if str(b.get('slug','')).lower()=='crown'),None)
        if book is None:identity_bad+=1;continue
        q=[x for x in book.get('asian_list') or [] if isinstance(x,list) and len(x)>=5]
        received=utc(r.get('captured_at_utc'));kickoff=utc(r.get('kickoff_utc'))
        is_pre=bool(received and kickoff and received<kickoff)
        source_times=[utc(x[4]) for x in q];source_times=[x for x in source_times if x]
        source_pre=sum(bool(kickoff and t<kickoff) for t in source_times)
        quote_rows+=len(q)
        if q:quoted_fids.add(fid)
        if is_pre:prospective+=1
        if source_pre:pre_kickoff_quotes+=source_pre
        league[str(r.get('league_id') or r.get('league') or match.get('l_id') or 'UNKNOWN')]+=1
        if received:receive_dates[str(received.date())[:4]]+=1
        rows.append({'index_line':line_no,'match_id':fid,'league_id':str(r.get('league_id') or match.get('l_id') or ''),
          'league':r.get('league') or match.get('l'),'home':match.get('h'),'away':match.get('a'),
          'kickoff_utc':kickoff.isoformat().replace('+00:00','Z') if kickoff else None,
          'response_received_at_utc':received.isoformat().replace('+00:00','Z') if received else None,
          'prospective_observation':is_pre,'response_sha256':expected,'response_path':path.relative_to(BASE).as_posix(),
          'asian_movement_quote_rows':len(q),
          'quote_source_min_utc':min(source_times).isoformat().replace('+00:00','Z') if source_times else None,
          'quote_source_max_utc':max(source_times).isoformat().replace('+00:00','Z') if source_times else None,
          'source_quotes_before_kickoff':source_pre})
    rows.sort(key=lambda x:(x['response_received_at_utc'] or '',x['match_id'],x['index_line']))
    out_rows=OUT/'forward_shadow_Crown_receipt_inventory.jsonl'
    with out_rows.open('w',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    receipt_files=[]
    for p in sorted(ROOT.glob('crown-capture-receipt-*.json'))+[ROOT/'m5_forward_pairs_20261107T0549Z_refresh.jsonl.receipt.json']:
        if p.exists():receipt_files.append({'path':str(p.relative_to(BASE)),'sha256':sha(p),'bytes':p.stat().st_size})
    index_sha=sha(INDEX)
    summary={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_index':str(INDEX.relative_to(BASE)),
      'source_index_sha256':index_sha,'verified_response_rows':len(rows),'index_rows':sum(status.values()),'index_status_counts':dict(status),
      'verified_raw_files_missing':missing,'verified_raw_sha256_mismatch':bad_sha,'verified_fixture_or_bookmaker_identity_errors':identity_bad,
      'unique_verified_fids':len({x['match_id'] for x in rows}),'distinct_AH_quote_fids':len(quoted_fids),
      'asian_movement_quote_rows':quote_rows,'actual_receive_before_kickoff_response_rows':prospective,
      'source_quote_rows_before_kickoff':pre_kickoff_quotes,'receive_year_counts':dict(receive_dates),'league_counts':dict(league),
      'raw_responses_sha256_manifest_sha256':hashlib.sha256(out_rows.read_bytes()).hexdigest(),
      'receipt_evidence_files':receipt_files,'output':str(out_rows)}
    p=OUT/'forward_shadow_Crown_receipt_audit.json';p.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
