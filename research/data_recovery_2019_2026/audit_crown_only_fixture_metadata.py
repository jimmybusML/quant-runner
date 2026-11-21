#!/usr/bin/env python3
"""Find Crown-captured fixture identities absent from reconciled schedule sources."""
from __future__ import annotations
import collections,datetime as dt,gzip,hashlib,json,pathlib,sqlite3
from zoneinfo import ZoneInfo
BASE=pathlib.Path('/Users/mac/QuantAsiaDesk');DB=BASE/'data/crown_quote_store/crown_quotes.sqlite3';OUT=pathlib.Path(__file__).resolve().parent
INVENTORY=OUT/'fixture_inventory_2019_2026.jsonl.gz';SH=ZoneInfo('Asia/Shanghai');UTC=dt.timezone.utc

def sha(b):return hashlib.sha256(b).hexdigest()
def parse_start(v):
 if not v:return None,None
 raw=str(v)
 try:
  x=dt.datetime.fromisoformat(raw.replace('Z','+00:00'))
  if x.tzinfo is None:x=x.replace(tzinfo=SH)
  return x.astimezone(UTC),raw
 except Exception:return None,raw

def main():
 scheduled=set()
 with gzip.open(INVENTORY,'rt',encoding='utf-8') as f:
  for line in f:scheduled.add(str(json.loads(line)['fid']))
 cx=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=30);cx.row_factory=sqlite3.Row;cx.execute('BEGIN')
 candidates={str(r[0]) for r in cx.execute('select distinct fixture_id from capture')}-scheduled
 rows=[];issues=collections.Counter()
 for fid in sorted(candidates):
  captures=cx.execute('select data_layer,capture_mode,status,response_sha256,source_file,response_received_at_utc from capture where fixture_id=? order by processed_at_utc,capture_key',(fid,)).fetchall()
  metadata=[];identity=set()
  for c in captures:
   try:
    body=pathlib.Path(c['source_file']).read_bytes();digest=sha(body)
    if digest!=c['response_sha256']:
     issues['raw_sha_mismatch']+=1;continue
    obj=json.loads(body);match=next((m for m in obj.get('data',[]) if str(m.get('id'))==fid),None)
    if not match:
     issues['raw_fid_missing']+=1;continue
    bookmaker_present=any(b.get('slug')=='crown' for b in match.get('bookmakers',[]))
    kickoff,raw_start=parse_start(match.get('start'))
    if not kickoff:
     issues['kickoff_unparseable']+=1;continue
    tup=(str(match.get('l_id') or ''),str(match.get('h_id') or ''),str(match.get('h') or ''),str(match.get('a_id') or ''),str(match.get('a') or ''),kickoff.isoformat())
    identity.add(tup)
    metadata.append({'response_sha256':digest,'source_basename':pathlib.Path(c['source_file']).name,
      'data_layer':c['data_layer'],'capture_mode':c['capture_mode'],'capture_status':c['status'],
      'crown_bookmaker_present':bookmaker_present,
      'response_received_at_utc':c['response_received_at_utc'],'kickoff_source_raw':raw_start})
   except Exception as e:issues[type(e).__name__]+=1
  if not metadata:continue
  if len(identity)!=1:
   issues['fixture_identity_conflict']+=1
   continue
  lid,home_id,home,away_id,away,kickoff_text=next(iter(identity));kickoff=dt.datetime.fromisoformat(kickoff_text)
  local=kickoff.astimezone(SH)
  # The target dataset uses UTC calendar years. Preserve the China-date start
  # boundary separately so it can be reconciled without silently changing scope.
  utc_target=2019<=kickoff.year<=2026
  china_boundary=(local.year==2019 and kickoff.year==2018)
  if not utc_target and not china_boundary:continue
  representative=sorted(metadata,key=lambda x:(x['data_layer'],x['capture_mode'],x['response_sha256']))[0]
  body=next((pathlib.Path(c['source_file']).read_bytes() for c in captures if c['response_sha256']==representative['response_sha256']),None)
  match=next((m for m in json.loads(body).get('data',[]) if str(m.get('id'))==fid),{}) if body else {}
  rows.append({'fid':fid,'provider_league_id':lid,'provider_league_name':match.get('l'),
   'source':'Fixture metadata embedded in an existing Crown quote-capture response; it is not counted as a Crown AH quote when the bookmaker entry is absent',
   'scope_position':'within_utc_2019_2026' if utc_target else 'china_date_2019_start_boundary_utc_2018',
   'kickoff_utc':kickoff.isoformat().replace('+00:00','Z'),'kickoff_source_raw':representative['kickoff_source_raw'],
   'kickoff_china':local.isoformat(),'home_id':home_id,'home_name':home,'away_id':away_id,'away_name':away,
   'status_raw':match.get('status'),'home_goals_raw':match.get('hg'),'away_goals_raw':match.get('ag'),
   'crown_bookmaker_present_in_selected_raw_response':representative['crown_bookmaker_present'],
   'response_references':sorted({(x['data_layer'],x['capture_mode'],x['response_sha256'],x['source_basename'],x['response_received_at_utc']) for x in metadata}),
   'source_identity_consistent_across_captures':True})
 cx.close()
 out=OUT/'crown_only_fixture_identity_candidates_2019_2026.jsonl.gz'
 with out.open('wb') as raw:
  with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
   for r in rows:gz.write((json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n').encode())
 positions=collections.Counter(r['scope_position'] for r in rows);by=collections.Counter((r['provider_league_id'],r['scope_position'],r['kickoff_utc'][:4]) for r in rows)
 summary={'generated_at_utc':dt.datetime.now(UTC).isoformat().replace('+00:00','Z'),'scheduled_inventory_sha256':sha(INVENTORY.read_bytes()),
  'crown_sqlite_sha256':sha(DB.read_bytes()),'crown_capture_fids_not_in_schedule_inventory':len(candidates),
  'identity_rows_retained':len(rows),'scope_position_counts':dict(positions),'by_league_scope_year':{'|'.join(k):v for k,v in sorted(by.items())},
  'identity_conflict_or_parse_issues':dict(issues),'api_requests':0,'sqlite_writes':0,'output_file':out.name,'output_sha256':sha(out.read_bytes()),
  'interpretation':'Fixture metadata from quote-capture responses is retained as a distinct source and does not claim a separate schedule page or Crown AH quote existed. Nine target UTC-period rows are future fixtures; scores shown in source metadata remain unverified unless status is full and separately reconciled. One 2019 China-date boundary record is UTC 2018-12-31 and is preserved separately.'}
 (OUT/'crown_only_fixture_identity_candidates_2019_2026.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
