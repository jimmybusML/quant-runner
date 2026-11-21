#!/usr/bin/env python3
"""Summarize crown_capture_store stdout without reading or changing its SQLite DB."""
from __future__ import annotations
import argparse, collections, gzip, json
from pathlib import Path


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('jsonl',type=Path)
    p.add_argument('--candidate-manifest',type=Path)
    p.add_argument('--inventory',type=Path)
    p.add_argument('--list-remaining',action='store_true')
    args=p.parse_args()
    counts=collections.Counter();failures=collections.Counter();saved_quotes=0;rows=[];latest_by_fixture={}
    first_received=last_received=None;processed=[]
    for line in args.jsonl.open(encoding='utf-8'):
        try: row=json.loads(line)
        except json.JSONDecodeError: continue
        if not isinstance(row,dict) or 'fixture_id' not in row or 'status' not in row: continue
        status=str(row['status']);counts[status]+=1;processed.append(str(row['fixture_id']))
        rows.append(row)
        latest_by_fixture[str(row['fixture_id'])]=row
        if status=='FETCH_FAILED':failures[str(row.get('error') or 'UNKNOWN')]+=1
        saved_quotes+=int(row.get('quote_count') or 0)
        stamp=row.get('response_received_at_utc')
        if stamp:
            first_received=min(first_received,stamp) if first_received else stamp
            last_received=max(last_received,stamp) if last_received else stamp
    out={'log':str(args.jsonl),'attempted_fixture_rows':sum(counts.values()),'status_counts':dict(counts),
      'fetch_failure_codes':dict(failures),'saved_quote_rows_reported':saved_quotes,
      'first_http_receive_utc':first_received,'last_http_receive_utc':last_received,
      'unique_fixture_ids_in_log':len(set(processed))}
    latest_counts=collections.Counter(str(x['status']) for x in latest_by_fixture.values())
    out['latest_status_counts_by_unique_fixture']=dict(latest_counts)
    out['unique_fixtures_with_response_received_timestamp']=sum(bool(x.get('response_received_at_utc')) for x in latest_by_fixture.values())
    if args.candidate_manifest:
        candidates={json.loads(x)['match_id'] for x in args.candidate_manifest.open(encoding='utf-8') if x.strip()}
        done=set(processed);out.update({'candidate_fixture_count':len(candidates),
          'remaining_not_logged':len(candidates-done)})
        if args.list_remaining:out['remaining_fixture_ids']=sorted(candidates-done)
    if args.inventory:
        opener=gzip.open if args.inventory.suffix=='.gz' else open
        dims={}
        with opener(args.inventory,'rt',encoding='utf-8') as f:
            for line in f:
                row=json.loads(line);dims[str(row['fid'])]=(str(row['provider_league_id']),str(row['year']))
        per=collections.defaultdict(collections.Counter)
        for row in rows:
            if row.get('fixture_id') not in dims:continue
            league,year=dims[row['fixture_id']];per[(league,year)][str(row.get('status'))]+=1
        out['processed_by_league_year']=[{'provider_league_id':k[0],'calendar_year_utc':k[1],'statuses':dict(v)} for k,v in sorted(per.items())]
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
