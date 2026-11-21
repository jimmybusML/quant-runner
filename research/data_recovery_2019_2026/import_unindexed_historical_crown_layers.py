#!/usr/bin/env python3
"""Import already-saved historical raw Crown AH rows missing from layer index.

This is an offline, append-only normalization pass. It makes no API requests,
does not overwrite raw files, never touches live receipts, and uses the existing
collector's exact parser/storage helpers so source and receive times stay intact.
"""
from __future__ import annotations
import collections,gzip,hashlib,json,pathlib,sqlite3,sys

BASE=pathlib.Path('/Users/mac/QuantAsiaDesk')
OUT=pathlib.Path(__file__).resolve().parent
INVENTORY=OUT/'fixture_inventory_2019_2026.jsonl.gz'
DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3'
RAW_HIST=BASE/'data/crown_quote_store/raw/historical'
LEGACY=[BASE/'data/m5-crown-authorized/crown-responses',BASE/'data/epl_laliga_crown_5seasons/raw_crown']
sys.path.insert(0,str(BASE/'scripts'))
import crown_capture_store as store

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def main():
 fixtures={}
 with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
  for line in f:
   r=json.loads(line);fixtures[str(r['fid'])]=r
 cx=sqlite3.connect(DB,timeout=40);cx.execute('PRAGMA busy_timeout=40000')
 indexed=collections.defaultdict(set)
 for r in cx.execute("select fixture_id,data_layer,response_sha256 from capture where capture_mode='historical'"):
  indexed[str(r[0])].add((str(r[1]),str(r[2])))
 receipt_index=store.source_received_index()
 files_seen=set();results=collections.Counter();imported_rows=collections.Counter();
 available_rows=collections.Counter();already_indexed=collections.Counter();errors=collections.Counter();
 per_fixture=collections.defaultdict(lambda:collections.Counter());new_capture_refs=[]
 for fid,fixture in fixtures.items():
  cand=[]
  pdir=RAW_HIST/fid
  if pdir.exists():cand.extend(pdir.glob('*.json'))
  for root in LEGACY:
   p=root/(fid+'.json')
   if p.exists():cand.append(p)
  unique={p.resolve() for p in cand}
  for path in sorted(unique):
   key=(fid,str(path))
   if key in files_seen:continue
   files_seen.add(key)
   try:
    body=path.read_bytes();digest=sha_bytes(body);obj=json.loads(body)
    match,book=store.extract_match(obj,fid)
    if not book:continue
    kickoff=fixture.get('totalcorner_kickoff_utc')
    if not kickoff:
     pages=fixture.get('totalcorner_page_records') or []
     kickoff=next((x.get('kickoff_utc') for x in pages if x.get('kickoff_utc')),None)
    for layer in ('movement','summary'):
     rows=store.rows_for_layer(book,layer)
     valid=[x for x in rows if x[1] is not None and x[2] is not None and x[3] is not None and x[4] is not None]
     if not valid:continue
     available_rows[layer]+=len(valid)
     if (layer,digest) in indexed[fid]:
      already_indexed[layer]+=len(valid);continue
     outcome=store.store_response(cx,fid,layer,'historical',path,None,kickoff,receipt_index)
     results[f"{layer}:{outcome['status']}"]+=1
     if outcome['status'] in ('SAVED','REUSED_DB'):
      per_fixture[fid][layer]+=int(outcome.get('quote_count') or 0)
      if outcome['status']=='SAVED':
       imported_rows[layer]+=int(outcome.get('quote_count') or 0)
       new_capture_refs.append({'fid':fid,'layer':layer,'response_sha256':digest,'source_basename':path.name,'quote_count':outcome.get('quote_count')})
       indexed[fid].add((layer,digest))
   except Exception as e:
    errors[type(e).__name__]+=1
 cx.commit()
 final={}
 for layer in ('movement','summary'):
  final[layer]={'indexed_quote_fids':cx.execute("select count(distinct q.fixture_id) from asian_quote q join capture c using(capture_key) where c.capture_mode='historical' and c.data_layer=?",(layer,)).fetchone()[0],
   'indexed_quote_rows':cx.execute("select count(*) from asian_quote q join capture c using(capture_key) where c.capture_mode='historical' and c.data_layer=?",(layer,)).fetchone()[0]}
 cx.close()
 out={'run_type':'offline_append_only_normalization','api_requests':0,'live_capture_rows_touched':0,
  'source_inventory_sha256':sha_bytes(INVENTORY.read_bytes()),'raw_cache_files_scanned':len(files_seen),
  'available_rows_by_layer':dict(available_rows),'already_indexed_rows_by_layer':dict(already_indexed),
  'outcomes_by_layer_and_status':dict(results),'newly_imported_quote_rows_by_layer':dict(imported_rows),
  'errors':dict(errors),'final_historical_sqlite_counts':final,'new_capture_refs':len(new_capture_refs),
  'note':'Each response is keyed by original FID and SHA, parsed with crown_capture_store.py. The mode remains historical; response receive time is populated only by an exact legacy-index SHA match, and prospective_observation remains false.'}
 (OUT/'offline_Crown_layer_import_results_2019_2026.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'offline_Crown_layer_imported_responses_2019_2026.jsonl.gz').open('wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for x in sorted(new_capture_refs,key=lambda z:(z['layer'],z['fid'],z['response_sha256'])):
    gz.write((json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 print(json.dumps(out,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
