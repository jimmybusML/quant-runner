#!/usr/bin/env python3
"""Read-only cross-check of existing raw Crown AH responses vs SQLite indexing.

No API requests and no database writes. Historical source-event evidence and
real HTTP receipts remain distinct; this audit scans historical caches only.
"""
from __future__ import annotations
import collections, gzip, hashlib, json, pathlib, sqlite3

BASE=pathlib.Path('/Users/mac/QuantAsiaDesk')
OUT=pathlib.Path(__file__).resolve().parent
INVENTORY=OUT/'fixture_inventory_2019_2026.jsonl.gz'
DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3'
RAW_HIST=BASE/'data/crown_quote_store/raw/historical'
LEGACY=[BASE/'data/m5-crown-authorized/crown-responses',BASE/'data/epl_laliga_crown_5seasons/raw_crown']
LEGACY_INDEX=BASE/'data/m5-crown-authorized/crown-response-index.jsonl'

def sha(p:pathlib.Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def main():
 rows=[]
 with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line);rows.append(r)
 byfid={str(r['fid']):r for r in rows}
 legacy_sha=set()
 if LEGACY_INDEX.exists():
  with LEGACY_INDEX.open(encoding='utf-8') as f:
   for line in f:
    try:
     x=json.loads(line);legacy_sha.add((str(x.get('match_id') or ''),str(x.get('response_sha256') or '')))
    except Exception:pass
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=20);cx.row_factory=sqlite3.Row
 cx.execute('BEGIN')
 indexed=collections.defaultdict(set);quote_fids=collections.defaultdict(set);quote_rows=collections.Counter()
 for r in cx.execute('select fixture_id,data_layer,response_sha256,status,quote_count from capture where capture_mode=\'historical\''):
  indexed[str(r['fixture_id'])].add((str(r['data_layer']),str(r['response_sha256'])))
  if r['status']=='QUOTES_SAVED':quote_fids[str(r['data_layer'])].add(str(r['fixture_id']))
  quote_rows[str(r['data_layer'])]+=int(r['quote_count'] or 0)
 cx.commit();cx.close()
 by_year=collections.defaultdict(collections.Counter);ledger=[];parse_errors=collections.Counter();fids_with=[]
 duplicate_files=0;total_files=0;identity_checked=0;content_addressed=0;legacy_index_anchored=0;db_index_anchored=0;unanchored=0
 for fid,r in byfid.items():
  candidates=[]
  for p in (RAW_HIST/fid).glob('*.json') if (RAW_HIST/fid).exists() else ():
   candidates.append(('historical_store',p))
  for root in LEGACY:
   p=root/(fid+'.json')
   if p.exists():candidates.append((root.name,p))
  distinct={p.resolve():source for source,p in candidates}
  total_files+=len(distinct)
  if len(distinct)>1:duplicate_files+=1
  dims=(str(r.get('provider_league_id') or 'UNKNOWN'),str(r.get('year') or 'UNKNOWN'))
  agg=by_year[dims];agg['schedule_fids']+=1
  found=False
  for p,source in [(p,s) for p,s in distinct.items()]:
   try:
    body=p.read_bytes();digest=hashlib.sha256(body).hexdigest();obj=json.loads(body)
    data=obj.get('data');match=data[0] if isinstance(data,list) and len(data)==1 else data
    if not isinstance(match,dict) or str(match.get('id'))!=fid:
     parse_errors['identity_or_shape']+=1;continue
    books=match.get('bookmakers') or []
    crown=next((b for b in books if str(b.get('slug','')).lower()=='crown'),None)
    if not crown:
     parse_errors['no_crown_bookmaker']+=1;continue
    alist=crown.get('asian_list') or []
    asian=crown.get('asian') or {}
    movement_rows=sum(1 for q in alist if isinstance(q,list) and len(q)>=5)
    summary_rows=sum(1 for k in ('open','close') if isinstance(asian.get(k),dict))
    found=True;identity_checked+=1
    indexed_movement=('movement',digest) in indexed[fid]
    indexed_summary=('summary',digest) in indexed[fid]
    db_indexed=any(x[1]==digest for x in indexed[fid])
    path_addressed=(source=='historical_store' and p.stem==digest)
    legacy_indexed=(fid,digest) in legacy_sha
    content_addressed+=int(path_addressed);legacy_index_anchored+=int(legacy_indexed);db_index_anchored+=int(db_indexed)
    if not(path_addressed or legacy_indexed or db_indexed):unanchored+=1
    agg['raw_response_files']+=1;agg['raw_response_with_Asian_list']+=int(movement_rows>0)
    agg['raw_response_with_summary']+=int(summary_rows>0)
    agg['movement_quote_rows_available']+=movement_rows;agg['summary_quote_rows_available']+=summary_rows
    agg['movement_response_not_indexed']+=int(movement_rows>0 and not indexed_movement)
    agg['summary_response_not_indexed']+=int(summary_rows>0 and not indexed_summary)
    ledger.append({'fid':fid,'provider_league_id':dims[0],'year':int(dims[1]) if dims[1].isdigit() else None,
      'cache_source':source,'cache_file_basename':p.name,'response_sha256':digest,
      'raw_movement_rows':movement_rows,'raw_summary_rows':summary_rows,
      'movement_sha_indexed':indexed_movement,'summary_sha_indexed':indexed_summary,
      'db_sha_indexed_any_layer':db_indexed,'content_addressed_filename_matches':path_addressed,
      'legacy_response_index_sha_matches':legacy_indexed})
   except Exception as e:parse_errors[type(e).__name__]+=1
  if found:fids_with.append(fid);agg['fids_with_valid_raw_response']+=1
 # deterministic JSONL/GZIP ledger (digests and counts only; no quote bodies or values)
 with (OUT/'offline_raw_Crown_response_index_audit_2019_2026.jsonl.gz').open('wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for x in sorted(ledger,key=lambda z:(z['provider_league_id'],z['year'] or 0,z['fid'],z['response_sha256'])):
    gz.write((json.dumps(x,separators=(',',':'))+'\n').encode())
 summary={'study':'Read-only audit of existing historical raw Crown response caches; no collection requests and no SQLite writes',
  'source_inventory_sha256':sha(INVENTORY),'inventory_fids':len(byfid),'sqlite_historical_indexed_fids':{k:len(v) for k,v in quote_fids.items()},
  'sqlite_historical_quote_rows':dict(quote_rows),'raw_cache_response_files':total_files,'raw_cache_fids_with_valid_response':len(set(fids_with)),
  'raw_cache_files_identity_checked':identity_checked,'raw_sha_content_addressed_paths':content_addressed,
  'raw_sha_matched_legacy_response_index':legacy_index_anchored,'raw_sha_matched_existing_sqlite_index':db_index_anchored,
  'raw_files_without_external_sha_anchor':unanchored,'schedule_fids_with_multiple_raw_cache_files':duplicate_files,
  'raw_parse_or_identity_issues':dict(parse_errors),'by_league_year':{f'{k[0]}|{k[1]}':dict(v) for k,v in sorted(by_year.items(),key=lambda x:(x[0][0],x[0][1]))},
  'per_fixture_digest_ledger':'offline_raw_Crown_response_index_audit_2019_2026.jsonl.gz',
  'per_fixture_ledger_sha256':sha(OUT/'offline_raw_Crown_response_index_audit_2019_2026.jsonl.gz'),
  'interpretation':'A raw response can contain an empty Crown AH list or already be indexed under a different capture layer. Not-indexed means the exact raw SHA was not normalized into the matching historical layer; it is eligible for offline reuse only if the layer-specific parser produces rows.'}
 (OUT/'offline_raw_Crown_response_inventory_audit_2019_2026.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'inventory_fids':len(byfid),'raw_files':total_files,'valid_raw_fids':len(set(fids_with)),
   'identity_checked_raw_files':identity_checked,'sha_anchors':{'content_addressed':content_addressed,'legacy_index':legacy_index_anchored,'sqlite_index':db_index_anchored,'none':unanchored},
   'duplicate_file_fids':duplicate_files,'parse_issues':dict(parse_errors),
   'sqlite_quote_fids':summary['sqlite_historical_indexed_fids'],'sqlite_quote_rows':dict(quote_rows),
   'summary_out':str(OUT/'offline_raw_Crown_response_inventory_audit_2019_2026.json')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
