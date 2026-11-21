#!/usr/bin/env python3
"""Use SHA-anchored saved Crown fixture responses for exact league-name IDs.

This is a read-only scope/mapping audit. It makes no network request, makes no
SQLite write, and never fuzzy-matches a league name.
"""
from __future__ import annotations
import collections, datetime as dt, hashlib, json, pathlib, sqlite3

OUT = pathlib.Path(__file__).resolve().parent
DB = pathlib.Path('/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3')
SCOPE = OUT / 'league_scope_union_2019_2026.json'
RESULT = OUT / 'crown_raw_exact_league_name_mapping_2019_2026.json'
MR1_RESULT_CHECKS = pathlib.Path('/Users/mac/QuantAsiaDesk/repos/mr1/data/strategy-shadow-ledger/result-checks')

def sha(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    scope=json.loads(SCOPE.read_text(encoding='utf-8'))
    names={x['competition_name_exact'] for x in scope['sources']['m7_research_universe_named_competitions']['unmapped_exact_names']}
    evidence=collections.defaultdict(lambda:{'response_shas':set(),'fids':set(),'received':[],'layers':set(),'capture_modes':set()})
    errors=collections.Counter();checked_files=0;checked_rows=0;matched_rows=0
    cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=30);cx.execute('BEGIN')
    captures=cx.execute('''SELECT fixture_id,data_layer,capture_mode,response_received_at_utc,response_sha256,source_file
      FROM capture WHERE source_file IS NOT NULL AND response_sha256 IS NOT NULL
      ORDER BY source_file,response_sha256,fixture_id''')
    seen=set()
    for fid,layer,mode,received,expected,path_raw in captures:
        key=(str(path_raw),str(expected))
        if key in seen:continue
        seen.add(key);path=pathlib.Path(path_raw);checked_files+=1
        try:
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=str(expected):
                errors['sha_mismatch']+=1;continue
            doc=json.loads(raw);data=doc.get('data') if isinstance(doc,dict) else None
            if isinstance(data,list):rows=data
            elif isinstance(data,dict):rows=data.get('matches') or ([data] if data.get('id') is not None else [])
            else:rows=[]
            for row in rows:
                if not isinstance(row,dict):continue
                checked_rows+=1
                name=row.get('l');lid=row.get('l_id')
                if name in names and lid is not None and str(row.get('id') or ''):
                    e=evidence[(str(name),str(lid))];e['response_shas'].add(str(expected));e['fids'].add(str(row['id']))
                    e['layers'].add(str(layer));e['capture_modes'].add(str(mode))
                    if received:e['received'].append(str(received))
                    matched_rows+=1
        except FileNotFoundError:errors['raw_missing']+=1
        except (json.JSONDecodeError,UnicodeDecodeError):errors['raw_parse_error']+=1
        except OSError as ex:errors['read_'+type(ex).__name__]+=1
    db_sha=sha(DB);cx.close()
    # Existing TotalCorner match-view response archives are a separate exact-ID
    # source. Require their own saved raw-response hash, successful HTTP/business
    # status, and a response FID identical to the containing fixture directory.
    for path in MR1_RESULT_CHECKS.rglob('attempt-*.json'):
        checked_files+=1
        try:
            attempt=json.loads(path.read_text(encoding='utf-8'))
            raw=attempt.get('raw_response')
            if not isinstance(raw,str):continue
            raw_bytes=raw.encode('utf-8');digest=hashlib.sha256(raw_bytes).hexdigest()
            if (attempt.get('http_status')!=200 or attempt.get('business_status')!=1
                    or not attempt.get('raw_saved') or digest!=attempt.get('raw_sha256')):
                continue
            doc=json.loads(raw);data=doc.get('data') or []
            rows=data if isinstance(data,list) else ([data] if isinstance(data,dict) else [])
            for row in rows:
                if not isinstance(row,dict):continue
                checked_rows+=1
                fid=str(row.get('id') or '')
                name=row.get('l');lid=row.get('l_id')
                if (fid!=path.parent.parent.name or name not in names or lid is None):continue
                e=evidence[(str(name),str(lid))];e['response_shas'].add(digest);e['fids'].add(fid)
                e['layers'].add('TotalCorner_match_view');e['capture_modes'].add('archived_HTTP_response')
                if attempt.get('received_at'):e['received'].append(str(attempt['received_at']))
                matched_rows+=1
        except FileNotFoundError:errors['result_check_raw_missing']+=1
        except (json.JSONDecodeError,UnicodeDecodeError):errors['result_check_parse_error']+=1
        except OSError as ex:errors['result_check_read_'+type(ex).__name__]+=1
    mapped=[];unmapped=[];ambiguous=[]
    for name in sorted(names):
        ids=sorted({lid for n,lid in evidence if n==name},key=int)
        if not ids:
            unmapped.append({'competition_name_exact':name,'provider_league_ids':[]})
            continue
        rows=[]
        for lid in ids:
            e=evidence[(name,lid)]
            rows.append({'provider_league_id':lid,'distinct_fids':len(e['fids']),
              'response_sha256_count':len(e['response_shas']),'response_sha256_sample':sorted(e['response_shas'])[:20],
              'capture_layers':sorted(e['layers']),'capture_modes':sorted(e['capture_modes']),
              'response_received_min_utc':min(e['received']) if e['received'] else None,
              'response_received_max_utc':max(e['received']) if e['received'] else None,
              'evidence_basis':'exact raw TotalCorner l/l_id pair in Crown fixture response; response SHA matched SQLite capture row'})
        mapped.append({'competition_name_exact':name,'provider_league_ids':ids,'evidence_by_id':rows})
        if len(ids)>1:ambiguous.append({'competition_name_exact':name,'provider_league_ids':ids})
    result={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),
      'scope':'Only the exact unresolved M7 competition labels; no fuzzy or translated name matching.',
      'source_crown_sqlite_sha256':db_sha,'raw_responses_checked':checked_files,
      'response_rows_checked':checked_rows,'responses_with_exact_unresolved_name':matched_rows,
      'mapping_count':len(mapped),'unmapped_count':len(unmapped),'ambiguous_count':len(ambiguous),
      'mapped_exact_names':mapped,'unmapped_exact_names':unmapped,'multiply_mapped_exact_names':ambiguous,
      'response_issues':dict(errors),'network_requests':0,'sqlite_writes':0}
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('raw_responses_checked','response_rows_checked','responses_with_exact_unresolved_name','mapping_count','unmapped_count','ambiguous_count','response_issues','network_requests','sqlite_writes')},ensure_ascii=False))

if __name__=='__main__':main()
