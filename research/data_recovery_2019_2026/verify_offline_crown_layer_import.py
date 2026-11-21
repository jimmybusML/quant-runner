#!/usr/bin/env python3
"""Independent read-only audit of the offline Crown layer import pass."""
from __future__ import annotations
import collections,gzip,hashlib,json,pathlib,sqlite3,sys
from datetime import timezone
BASE=pathlib.Path('/Users/mac/QuantAsiaDesk')
OUT=pathlib.Path(__file__).resolve().parent
DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3'
INVENTORY=OUT/'fixture_inventory_2019_2026.jsonl.gz'
CUTOFF='2026-11-21T11:08:00Z'
sys.path.insert(0,str(BASE/'scripts'))
import crown_capture_store as store

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def same_num(a,b):
 if a is None or b is None:return a is None and b is None
 try:return abs(float(a)-float(b))<1e-9
 except (TypeError,ValueError):return False

def main():
 fixtures={}
 with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
  for line in f:
   x=json.loads(line);fixtures[str(x['fid'])]=x
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=30);cx.row_factory=sqlite3.Row;cx.execute('BEGIN')
 receipt=store.source_received_index();groups=collections.Counter();errors=collections.Counter();ledger=[];netfiles=0;quote_rows=0;quote_fids=collections.defaultdict(set)
 captures=cx.execute("select * from capture where capture_mode='historical' and status='QUOTES_SAVED' and processed_at_utc>=? order by processed_at_utc,capture_key",(CUTOFF,)).fetchall()
 for c in captures:
  fid=str(c['fixture_id']);layer=str(c['data_layer']);path=pathlib.Path(c['source_file']);netfiles+=1
  try:
   body=path.read_bytes();digest=sha_bytes(body)
   if digest!=c['response_sha256']:errors['raw_sha_mismatch']+=1;continue
   if fid not in fixtures:errors['FID_not_in_inventory']+=1;continue
   obj=json.loads(body);match,book=store.extract_match(obj,fid)
   if not book:errors['missing_Crown_bookmaker']+=1;continue
   expected=store.rows_for_layer(book,layer)
   actual=cx.execute('select sequence_index,quote_kind,handicap_home,home_decimal,away_decimal,quote_source_at_utc,response_received_at_utc,prospective_observation,quote_before_kickoff from asian_quote where capture_key=? order by sequence_index',(c['capture_key'],)).fetchall()
   if len(actual)!=len(expected) or len(actual)!=int(c['quote_count']):errors['quote_row_count_mismatch']+=1;continue
   kickoff=store.parse_timestamp(fixtures[fid].get('totalcorner_kickoff_utc'))
   expected_receive=store.parse_timestamp(receipt.get((fid,digest)),assumed_zone=timezone.utc)
   for i,(e,a) in enumerate(zip(expected,actual)):
    kind,line,home,away,source=e
    et=store.parse_timestamp(source)
    before=int(et<kickoff) if et and kickoff else None
    if int(a['sequence_index'])!=i or a['quote_kind']!=kind or not same_num(a['handicap_home'],store.valid_number(line)) or not same_num(a['home_decimal'],store.valid_number(home)) or not same_num(a['away_decimal'],store.valid_number(away)):
     errors['contract_values_mismatch']+=1;break
    if a['quote_source_at_utc']!=et or a['response_received_at_utc']!=expected_receive:
     errors['timestamp_mismatch']+=1;break
    if int(a['prospective_observation'])!=0 or int(a['quote_before_kickoff'] if a['quote_before_kickoff'] is not None else -1)!=(before if before is not None else -1):
     errors['time_provenance_flag_mismatch']+=1;break
   else:
    groups[(layer,c['status'])]+=1;quote_rows+=len(actual);quote_fids[layer].add(fid)
    ledger.append({'fid':fid,'provider_league_id':str(fixtures[fid].get('provider_league_id')),'year':fixtures[fid].get('year'),
      'layer':layer,'capture_key':c['capture_key'],'response_sha256':digest,'source_file_basename':path.name,
      'response_received_at_utc':c['response_received_at_utc'],'quote_count':len(actual),'prospective_observation':0,'verified':True})
  except Exception as e:errors[type(e).__name__]+=1
 # This cutoff includes the exact import run; outputs are deterministic to inspect/reproduce.
 ledger.sort(key=lambda x:(x['layer'],x['provider_league_id'],x['year'] or 0,x['fid'],x['response_sha256']))
 ledger_path=OUT/'offline_Crown_layer_import_verified_rows_2019_2026.jsonl.gz'
 with ledger_path.open('wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for x in ledger:gz.write((json.dumps(x,separators=(',',':'))+'\n').encode())
 result={'study':'Independent read-only verification of offline historical Crown layer normalization',
  'source_inventory_sha256':sha_bytes(INVENTORY.read_bytes()),'capture_processed_at_utc_cutoff':CUTOFF,
  'candidate_capture_rows':len(captures),'verified_capture_rows':len(ledger),'verified_quote_rows':quote_rows,
  'unique_fids_by_layer':{k:len(v) for k,v in quote_fids.items()},'capture_rows_by_layer_and_status':{f'{k[0]}|{k[1]}':v for k,v in groups.items()},
  'errors':dict(errors),'pass':not errors and len(ledger)==len(captures),
  'checks':['raw response SHA matches capture','response FID and Crown bookmaker','layer-specific parser output and row count','Asian handicap line and both raw decimal prices','source event timestamp','indexed HTTP receive timestamp only when exact legacy SHA mapping exists','historical capture remains non-prospective','quote-before-kickoff provenance flag'],
  'verified_capture_ledger':'offline_Crown_layer_import_verified_rows_2019_2026.jsonl.gz',
  'verified_capture_ledger_sha256':sha_bytes(ledger_path.read_bytes()),
  'note':'This verifies persisted local normalization of already-existing raw responses; it does not assert a historical HTTP response was received pre-kickoff or that absent quotes never existed.'}
 (OUT/'offline_Crown_layer_import_independent_verification_2019_2026.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False),flush=True)
 cx.close()

if __name__=='__main__':main()
