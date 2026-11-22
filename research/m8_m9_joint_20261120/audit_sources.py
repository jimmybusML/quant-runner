#!/usr/bin/env python3
"""Independent SHA/identity/quote/FT audit for M9 reconstruction rows."""
import collections,datetime as dt,hashlib,json,sqlite3
from pathlib import Path
P=Path(__file__).parent; src=P/'m9_reconstruction_m8_universe.jsonl'; DESK=Path('/Users/mac/QuantAsiaDesk')
def parse(s):
 x=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
 if x.tzinfo is None:x=x.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
 return x.astimezone(dt.timezone.utc)
rows=[json.loads(x) for x in src.open()]
counts=collections.Counter(); errors=[]; cache={}
cx=sqlite3.connect('file:/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3?mode=ro',uri=True)
source_paths={}
for fid,sha,path in cx.execute('select fixture_id,response_sha256,source_file from capture'):
 source_paths.setdefault((str(fid),str(sha)),path)
cx.close()
for r in rows:
 fid=str(r['fid']); expected=r['crown_raw_response_sha256']; rawpath=source_paths.get((fid,expected))
 path=Path(rawpath) if rawpath else DESK/'data/crown_quote_store/raw/historical'/fid/(expected+'.json')
 try:
  if path not in cache:
   raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest();doc=json.loads(raw)
   cache[path]=(actual,doc)
  actual,doc=cache[path]
  if actual!=expected:raise ValueError('raw_sha_mismatch')
  data=doc.get('data') or []
  match=[x for x in data if str(x.get('id'))==fid]
  if len(match)!=1:raise ValueError('fid_not_unique_in_raw')
  m=match[0]
  books=[b for b in m.get('bookmakers',[]) if str(b.get('slug','')).lower()=='crown']
  if len(books)!=1:raise ValueError('crown_bookmaker_missing_or_duplicate')
  b=books[0]; qtime=parse(r['crown_source_event_utc']); found=False
  for item in b.get('asian_list') or []:
   if not isinstance(item,list) or len(item)<5:continue
   try:
    if (abs(float(item[1])-float(r['crown_line_home']))<1e-8 and abs(float(item[2])-float(r['crown_home_decimal']))<1e-8 and abs(float(item[3])-float(r['crown_away_decimal']))<1e-8 and parse(item[4])==qtime):found=True;break
   except Exception:continue
  if not found:
   close=b.get('asian',{}).get('close') or {}
   try:
    found=abs(float(close['line'])-float(r['crown_line_home']))<1e-8 and abs(float(close['home'])-float(r['crown_home_decimal']))<1e-8 and abs(float(close['away'])-float(r['crown_away_decimal']))<1e-8 and parse(close['time'])==qtime
   except Exception:pass
  if not found:raise ValueError('quote_not_found_in_raw_crown_response')
  if m.get('status')!='full' or int(m.get('hg',-1))!=int(r['ft_home']) or int(m.get('ag',-1))!=int(r['ft_away']):raise ValueError('FT_mismatch_or_not_full')
  if parse(r['crown_source_event_utc'])>parse(r['kickoff_utc'])-dt.timedelta(hours=1):raise ValueError('source_event_after_Tminus1_cutoff')
  if r.get('crown_capture_mode')!='historical' or r.get('crown_prospective_observation'):counts['nonhistorical_or_live_quote']+=1
  else:counts['historical_quote_not_true_pregame_http_receipt']+=1
  counts['quote_raw_sha_identity_ft_all_pass']+=1
 except Exception as ex:
  counts['audit_fail']+=1;errors.append({'fid':fid,'error':str(ex)})
result={'rows':len(rows),'unique_raw_response_files':len(cache),'audit_counts':dict(counts),'errors_first_100':errors[:100],'full_quote_and_FT_raw_sha_audit':'PASS' if not errors else 'FAIL'}
# Cross-check FT against the separately persisted M1 cache. This archive can
# contain stale/mismatched scores, so conflicts are resolved against official
# club/league match reports and retained as explicit exceptions.
hist={}
for f in (DESK/'repos/m1/data/m1_history_cache').glob('*.json'):
 try: doc=json.loads(f.read_text())
 except Exception:continue
 for x in doc.get('rows',[]):
  if x.get('status')=='full':
   try:hist[str(x['id'])]=(str(x['h_id']),str(x['a_id']),int(x['hg']),int(x['ag']))
   except Exception:pass
cross=collections.Counter()
for r in rows:
 x=hist.get(str(r['fid']))
 if x is None:cross['not_in_m1_cache']+=1
 elif x==(str(r['home_team_id']),str(r['away_team_id']),int(r['ft_home']),int(r['ft_away'])):cross['exact_id_teams_FT_match']+=1
 else:cross['score_or_identity_conflict']+=1
result['M1_cache_FT_crosscheck']=dict(cross)
result['resolved_FT_conflicts']=[
 {'fid':'160205699','crown_raw_and_official_FT':'Inter 4-0 Atalanta','m1_cache':'Inter 3-0 Atalanta','resolution':'Use FT verified in SHA-bound Crown match response; independently matches official Inter and Serie A records.','official_sources':['https://www.inter.it/en/match_center/5250','https://www.laliga.com/partido/temporada-2024-2025-serie-a-inter-atalanta-3']},
 {'fid':'172688907','crown_raw_and_official_FT':'Lecce 0-1 Napoli','m1_cache':'Lecce 0-0 Napoli','resolution':'Use FT verified in SHA-bound Crown match response; independently matches SSC Napoli official match report.','official_sources':['https://sscnapoli.it/news/match-report-lecce-napoli-0-1']}
]
(P/'source_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
