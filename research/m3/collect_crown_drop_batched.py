"""Resumable M3-only Crown history collector, encrypted at each stage/batch."""
from __future__ import annotations
import argparse,base64,csv,datetime as dt,hashlib,json,os,re,time,unicodedata,urllib.error,urllib.parse,urllib.request,zlib
from collections import Counter,defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[2]
PRED=ROOT/'research/m3/results/predictions/88cda93edc2bacc835ddea02e6d2c2140177e454cd336ab335cb2262a3f633bf.csv'
OUT=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'m3-crown-research'
BASE='https://api.totalcorner.com/v1'
TZ=ZoneInfo('Asia/Shanghai');UTC=dt.timezone.utc
GAP=2.12;TARGET_TEST=7000;TARGET_TRAIN=1200;BATCH_SIZE=1000
LEAGUES={
 'E0':{'name':'England Premier League','id':'1'},
 'D1':{'name':'Germany Bundesliga I','id':'16'},
 'F1':{'name':'France Ligue 1','id':'25'},
 'I1':{'name':'Italy Serie A','id':'12'},
 'SP1':{'name':'Spain La Liga','id':'14'},
 'B1':{'name':'Belgium First Division A','id':'31'},
}
MODELS={'poisson','dixon_coles','bivariate_poisson'}
last_start=0.0
diag=Counter()

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+','',s)

def day(s):return dt.date.fromisoformat(str(s)[:10])

def rate_wait(headers=None,default=0.0):
 if not headers:return default
 try:
  value=float(headers.get('X-Rate-Limit-Reset',''))
  if value>time.time()+1:return max(default,min(60.0,value-time.time()+.2))
  if value>0:return max(default,min(60.0,value+.2))
 except Exception:pass
 return default

def request(path,params):
 global last_start
 token=os.environ.get('TOTALCORNER_TOKEN')
 if not token:raise RuntimeError('TotalCorner API credential unavailable')
 q=dict(params);q['token']=token;url=BASE+path+'?'+urllib.parse.urlencode(q)
 for attempt in range(10):
  wait=GAP-(time.monotonic()-last_start)
  if wait>0:time.sleep(wait)
  last_start=time.monotonic()
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'M3-Crown-Research/2.0'})
   with urllib.request.urlopen(req,timeout=45) as response:
    headers=response.headers;payload=json.load(response)
  except urllib.error.HTTPError as e:
   try:body=json.loads(e.read().decode('utf-8','replace'))
   except Exception:body={}
   code=(body.get('error') or {}).get('code') if isinstance(body,dict) else None
   if (e.code==429 or code=='TOO_MANY_REQUEST') and attempt<9:
    time.sleep(rate_wait(e.headers,11.0));continue
   if code in {'TOKEN_ERROR','VIP_REQUIRED','VIP_ONLY','NO_PERMISSION'}:raise RuntimeError('TotalCorner API access was rejected') from None
   if e.code>=500 and attempt<4:time.sleep(min(2*(attempt+1),10));continue
   raise RuntimeError('TotalCorner request failed after bounded retries') from None
  except Exception:
   if attempt<4:time.sleep(min(2*(attempt+1),10));continue
   raise RuntimeError('TotalCorner transport failed after bounded retries') from None
  code=(payload.get('error') or {}).get('code') if isinstance(payload,dict) else None
  if code=='TOO_MANY_REQUEST' and attempt<9:
   time.sleep(rate_wait(headers,11.0));continue
  if code in {'TOKEN_ERROR','VIP_REQUIRED','VIP_ONLY','NO_PERMISSION'}:raise RuntimeError('TotalCorner API access was rejected')
  if isinstance(payload,dict):return payload
  raise RuntimeError('Unexpected TotalCorner response shape')
 raise RuntimeError('TotalCorner retry budget exhausted')

def prediction_candidates():
 if not PRED.exists():raise RuntimeError('M3 OOS prediction artifact missing')
 grouped={}
 with PRED.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if r.get('prediction_status')!='predicted' or r.get('league') not in LEAGUES:continue
   try:
    match_day=day(r.get('match_date_utc'));train_end=dt.datetime.fromisoformat(str(r.get('train_end_utc')).replace('Z','+00:00'))
    if train_end.tzinfo is None or train_end.date()>=match_day:continue
    model=r.get('model')
    if model not in MODELS:continue
    score=[int(float(r['actual_home_goals'])),int(float(r['actual_away_goals']))]
   except Exception:continue
   key=(r['league'],match_day.isoformat(),norm(r.get('home_team')),norm(r.get('away_team')))
   item=grouped.setdefault(key,{'league':r['league'],'season':r.get('season'),'date':match_day.isoformat(),
     'home':r['home_team'],'away':r['away_team'],'score':score,'models':{}})
   if item['score']!=score:diag['m3_outcome_conflict']+=1;grouped.pop(key,None);continue
   if model in item['models']:diag['duplicate_model_rows']+=1;continue
   item['models'][model]={k:r.get(k) for k in ('train_end_utc','ah_home_0_p_win','ah_home_0_p_push','ah_home_0_p_lose','ou_p_over_2_5')}
 for key in list(grouped):
  if set(grouped[key]['models'])!=MODELS:del grouped[key];diag['incomplete_model_group']+=1
 items=sorted(grouped.values(),key=lambda x:(x['date'],x['league'],norm(x['home']),norm(x['away'])))
 if len(items)<TARGET_TEST+TARGET_TRAIN:raise RuntimeError('Insufficient unique strict-OOS M3 fixtures')
 test_start=day(items[max(0,len(items)-TARGET_TEST)]['date'])
 test=[x for x in items if day(x['date'])>=test_start]
 prior=[x for x in items if day(x['date'])<test_start]
 train=prior[-TARGET_TRAIN:]
 if len(train)<TARGET_TRAIN:raise RuntimeError('Insufficient pre-test training fixtures')
 return train,test

def kickoff_utc(m):
 try:
  x=dt.datetime.strptime(str(m['start']),'%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ)
  return x.astimezone(UTC)
 except Exception:return None

def get_matches(payload):
 data=payload.get('data') if isinstance(payload,dict) else None
 if isinstance(data,list):return [x for x in data if isinstance(x,dict)]
 if isinstance(data,dict):
  for k in ('matches','list','items','data'):
   if isinstance(data.get(k),list):return [x for x in data[k] if isinstance(x,dict)]
 return []

def next_page(payload,page):
 p=payload.get('pagination') or {}
 if 'next' in p:return bool(p.get('next'))
 try:return page<int(p.get('pages') or 1)
 except Exception:return False

def candidate_key(code,m):
 ko=kickoff_utc(m)
 if not ko:return None
 league_id=str(m.get('l_id') or '')
 league_name=norm(m.get('l') or '')
 if league_id and league_id!=LEAGUES[code]['id']:return None
 if not league_id and league_name!=norm(LEAGUES[code]['name']):return None
 try:score=[int(float(m['hg'])),int(float(m['ag']))]
 except Exception:return None
 return (code,ko.date().isoformat(),norm(m.get('h')),norm(m.get('a'))),ko,score

def key_for_prediction(x):return (x['league'],x['date'],norm(x['home']),norm(x['away']))

def encrypt_doc(doc,key_text,kind,path):
 key=base64.b64decode(key_text,validate=True)
 if len(key)!=32:raise RuntimeError('Research encryption key has invalid length')
 raw=json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode();packed=zlib.compress(raw,9)
 nonce=os.urandom(12);aad=('M3_CROWN_RESEARCH_V2:'+kind).encode()
 Path(path).write_bytes(nonce+AESGCM(key).encrypt(nonce,packed,aad))

def decrypt_doc(path,key_text,kind):
 key=base64.b64decode(key_text,validate=True);blob=Path(path).read_bytes()
 raw=zlib.decompress(AESGCM(key).decrypt(blob[:12],blob[12:],('M3_CROWN_RESEARCH_V2:'+kind).encode()))
 return json.loads(raw)

def write_public(name,summary):
 (OUT/name).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def stage_manifest():
 key_text=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not key_text:raise RuntimeError('Research encryption key unavailable')
 train,test=prediction_candidates();wanted={};
 for split,items in (('TRAIN',train),('TEST',test)):
  for item in items:wanted[key_for_prediction(item)]={'prediction':item,'split':split}
 found=defaultdict(dict);ambiguous_keys=set();pages_by_league={};
 for code,info in LEAGUES.items():
  page=1;seen_ids=set();league_pages=0
  while True:
   payload=request('/league/schedule/'+info['id'],{'page':page})
   if payload.get('success')!=1:raise RuntimeError('TotalCorner league schedule returned unsuccessful response')
   rows=get_matches(payload);league_pages+=1
   if not rows:
    diag['empty_schedule_page']+=1;break
   for m in rows:
    parsed=candidate_key(code,m)
    if not parsed:continue
    k,ko,score=parsed
    if k not in wanted:continue
    mid=str(m.get('id') or '')
    if not mid:diag['schedule_missing_match_id']+=1;continue
    pred=wanted[k]['prediction']
    if score!=pred['score']:
     diag['schedule_score_mismatch']+=1;continue
    if mid in seen_ids:continue
    seen_ids.add(mid)
    record={'split':wanted[k]['split'],'league':pred['league'],'season':pred.get('season'),
      'm3_date':pred['date'],'home':pred['home'],'away':pred['away'],'m3_score':pred['score'],'models':pred['models'],
      'source':{'match_id':mid,'league':m.get('l'),'league_id':str(m.get('l_id') or info['id']),
        'home':m.get('h'),'away':m.get('a'),'start_local':m.get('start'),'kickoff_utc':ko.isoformat(),
        'status':m.get('status'),'score':[m.get('hg'),m.get('ag')]}}
    if k in found and found[k] and mid not in found[k]:ambiguous_keys.add(k)
    found[k][mid]=record
    if not next_page(payload,page):break
   page+=1
  pages_by_league[code]=league_pages
  matched_now=sum(1 for k,v in found.items() if k[0]==code and len(v)==1 and k not in ambiguous_keys)
  print(json.dumps({'phase':'league_schedule','league':code,'pages':league_pages,'candidate_fixtures_matched':matched_now}),flush=True)
 matched=[]
 for k,variants in found.items():
  if k in ambiguous_keys or len(variants)!=1:diag['schedule_ambiguous_fixture_key']+=1;continue
  matched.append(next(iter(variants.values())))
 matched.sort(key=lambda r:(r['source']['kickoff_utc'],r['league'],norm(r['home']),norm(r['away'])))
 train_keys={key_for_prediction(x) for x in train};test_keys={key_for_prediction(x) for x in test}
 matched_keys={(r['league'],r['m3_date'],norm(r['home']),norm(r['away'])) for r in matched}
 summary={'protocol':'M3_CROWN_DROP_MANIFEST_V2','sample_design':{
   'train_candidate_fixtures':len(train),'test_candidate_fixtures':len(test),
   'train_start':train[0]['date'],'train_end':train[-1]['date'],'test_start':test[0]['date'],'test_end':test[-1]['date'],
   'scoped_leagues':list(LEAGUES)},'league_schedule_pages':pages_by_league,
   'matched_train_fixtures':len(train_keys&matched_keys),'matched_test_fixtures':len(test_keys&matched_keys),
   'matched_total_fixtures':len(matched),'diagnostics':dict(diag),'quote_batches':(len(matched)+BATCH_SIZE-1)//BATCH_SIZE}
 OUT.mkdir(parents=True,exist_ok=True)
 encrypt_doc({'summary':summary,'records':matched},key_text,'MANIFEST',OUT/'m3_crown_manifest.bin')
 write_public('manifest_summary.json',summary)
 print(json.dumps({'status':'MANIFEST_READY','summary':summary},ensure_ascii=False),flush=True)

def stage_manifest_window(start_text,end_text):
 key_text=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not key_text:raise RuntimeError('Research encryption key unavailable')
 start=day(start_text);end=day(end_text)
 if end<start:raise RuntimeError('Invalid manifest date window')
 train,test=prediction_candidates()
 wanted={}
 for split,items in (('TRAIN',train),('TEST',test)):
  for item in items:
   d=day(item['date'])
   if start<=d<=end:wanted[key_for_prediction(item)]={'prediction':item,'split':split}
 found={};ambiguous=set();pages_by_league={}
 for code,info in LEAGUES.items():
  page=1;league_pages=0
  while True:
   payload=request('/league/schedule/'+info['id'],{'page':page})
   if payload.get('success')!=1:raise RuntimeError('TotalCorner league schedule returned unsuccessful response')
   rows=get_matches(payload);league_pages+=1
   if not rows:break
   for m in rows:
    parsed=candidate_key(code,m)
    if not parsed:continue
    k,ko,score=parsed
    if k not in wanted:continue
    pred=wanted[k]['prediction']
    if pred['score']!=score:diag['schedule_score_mismatch']+=1;continue
    mid=str(m.get('id') or '')
    if not mid:diag['schedule_missing_match_id']+=1;continue
    record={'split':wanted[k]['split'],'league':pred['league'],'season':pred.get('season'),
      'm3_date':pred['date'],'home':pred['home'],'away':pred['away'],'m3_score':pred['score'],'models':pred['models'],
      'source':{'match_id':mid,'league':m.get('l'),'league_id':str(m.get('l_id') or info['id']),
        'home':m.get('h'),'away':m.get('a'),'start_local':m.get('start'),'kickoff_utc':ko.isoformat(),
        'status':m.get('status'),'score':[m.get('hg'),m.get('ag')]}}
    if k in found and found[k]['source']['match_id']!=mid:ambiguous.add(k)
    else:found[k]=record
   if not next_page(payload,page):break
   page+=1
  pages_by_league[code]=league_pages
  print(json.dumps({'phase':'league_schedule_window','window':f'{start}_{end}','league':code,'pages':league_pages,
    'matched':sum(1 for k in found if k[0]==code and k not in ambiguous)}),flush=True)
 matched=[v for k,v in found.items() if k not in ambiguous]
 matched.sort(key=lambda r:(r['source']['kickoff_utc'],r['league'],norm(r['home']),norm(r['away'])))
 summary={'protocol':'M3_CROWN_DROP_MANIFEST_WINDOW_V2','window':{'start':str(start),'end':str(end)},
  'train_candidate_fixtures':sum(1 for v in wanted.values() if v['split']=='TRAIN'),
  'test_candidate_fixtures':sum(1 for v in wanted.values() if v['split']=='TEST'),
  'matched_fixtures':len(matched),'ambiguous_fixtures':len(ambiguous),'schedule_pages':pages_by_league,
  'diagnostics':dict(diag),'records_digest':hashlib.sha256(json.dumps([x['source']['match_id'] for x in matched]).encode()).hexdigest()}
 OUT.mkdir(parents=True,exist_ok=True);tag=f'{start}_{end}'
 encrypt_doc({'summary':summary,'records':matched},key_text,'MANIFEST_WINDOW',OUT/f'm3_crown_manifest_{tag}.bin')
 write_public(f'manifest_{tag}_summary.json',summary)
 print(json.dumps({'status':'MANIFEST_WINDOW_READY','summary':summary},ensure_ascii=False),flush=True)

def stage_merge_manifests(input_dir):
 key_text=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not key_text:raise RuntimeError('Research encryption key unavailable')
 folder=Path(input_dir);files=sorted(folder.glob('m3_crown_manifest_*.bin'))
 if not files:raise RuntimeError('No encrypted date-window manifests found')
 by_id={};summaries=[];conflicts=0
 for path in files:
  doc=decrypt_doc(path,key_text,'MANIFEST_WINDOW');summaries.append(doc['summary'])
  for record in doc['records']:
   mid=str(record['source']['match_id'])
   if mid in by_id and by_id[mid]!=record:conflicts+=1;continue
   by_id[mid]=record
 records=sorted(by_id.values(),key=lambda r:(r['source']['kickoff_utc'],r['league'],norm(r['home']),norm(r['away'])))
 split_counts=Counter(r['split'] for r in records)
 summary={'protocol':'M3_CROWN_DROP_MANIFEST_V2','sample_design':{
  'scoped_leagues':list(LEAGUES),'train_candidate_fixtures':sum(x['train_candidate_fixtures'] for x in summaries),
  'test_candidate_fixtures':sum(x['test_candidate_fixtures'] for x in summaries),
  'train_start':min(x['window']['start'] for x in summaries),'train_end':max(x['window']['end'] for x in summaries),
  'test_start':min(x['window']['start'] for x in summaries),'test_end':max(x['window']['end'] for x in summaries)},
  'matched_train_fixtures':split_counts['TRAIN'],'matched_test_fixtures':split_counts['TEST'],
  'matched_total_fixtures':len(records),'window_manifests':len(files),'match_id_conflicts':conflicts,
  'quote_batches':(len(records)+BATCH_SIZE-1)//BATCH_SIZE,'window_summaries':summaries}
 OUT.mkdir(parents=True,exist_ok=True);encrypt_doc({'summary':summary,'records':records},key_text,'MANIFEST',OUT/'m3_crown_manifest.bin')
 write_public('manifest_summary.json',summary)
 print(json.dumps({'status':'MANIFEST_MERGED','summary':summary},ensure_ascii=False),flush=True)

def stage_quotes(batch):
 key_text=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not key_text:raise RuntimeError('Research encryption key unavailable')
 manifest_path=Path(os.environ.get('M3_CROWN_MANIFEST',''))
 if not manifest_path.exists():raise RuntimeError('Encrypted M3 Crown manifest artifact missing')
 manifest=decrypt_doc(manifest_path,key_text,'MANIFEST');records=manifest['records']
 start=batch*BATCH_SIZE;selected=records[start:start+BATCH_SIZE]
 results=[];counts=Counter();raw=Counter()
 for n,source_record in enumerate(selected,1):
  mid=str(source_record['source']['match_id'])
  payload=request('/match/bookmaker_odds/'+urllib.parse.quote(mid,safe=''),
    {'bookmaker':'crown','columns':'asianList,goalList'})
  data=payload.get('data') if isinstance(payload,dict) else None
  matches=[x for x in data if isinstance(x,dict) and str(x.get('id'))==mid] if isinstance(data,list) else []
  if payload.get('success')!=1 or len(matches)!=1:
   counts['odds_api_or_identity_failure']+=1
   record=dict(source_record);record['crown']={'asian_list':[],'goal_list':[]};results.append(record);continue
  fixture=matches[0];books=fixture.get('bookmakers')
  crowns=[b for b in books if isinstance(b,dict) and b.get('slug')=='crown'] if isinstance(books,list) else []
  record=dict(source_record)
  if len(crowns)!=1:
   counts['crown_missing_or_ambiguous']+=1;record['crown']={'asian_list':[],'goal_list':[]}
  else:
   book=crowns[0];ah=book.get('asian_list') or [];ou=book.get('goal_list') or []
   record['crown']={'asian_list':ah,'goal_list':ou};counts['crown_responses']+=1
   raw['AH_raw_rows']+=len(ah);raw['OU_raw_rows']+=len(ou)
  results.append(record)
  if n%100==0:print(json.dumps({'phase':'crown_quotes','batch':batch,'completed_matches':n,'total_matches':len(selected),'crown_responses':counts['crown_responses'],'ah_raw_rows':raw['AH_raw_rows'],'ou_raw_rows':raw['OU_raw_rows']}),flush=True)
 summary={'protocol':'M3_CROWN_DROP_QUOTE_BATCH_V2','batch_index':batch,'batch_size':BATCH_SIZE,
   'manifest_match_count':len(records),'batch_start_index':start,'batch_expected_matches':len(selected),
   'quote_responses':len(results),'counts':dict(counts),'raw_market_rows':dict(raw),
   'manifest_digest':hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
 OUT.mkdir(parents=True,exist_ok=True);dest=OUT/f'm3_crown_batch_{batch:02d}.bin'
 encrypt_doc({'summary':summary,'records':results},key_text,'BATCH',dest)
 write_public(f'batch_{batch:02d}_summary.json',summary)
 print(json.dumps({'status':'BATCH_READY','summary':summary},ensure_ascii=False),flush=True)

def stage_quotes_window(start_text,end_text):
 key_text=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not key_text:raise RuntimeError('Research encryption key unavailable')
 start=day(start_text);end=day(end_text)
 if end<start:raise RuntimeError('Invalid quote date window')
 train,test=prediction_candidates();wanted={}
 for split,items in (('TRAIN',train),('TEST',test)):
  for item in items:
   if start<=day(item['date'])<=end:wanted[key_for_prediction(item)]={'prediction':item,'split':split}
 matches_by_id={};counts=Counter();raw=Counter();page_counts={}
 for code,info in LEAGUES.items():
  page=1;pages=0
  while True:
   payload=request('/league/schedule/'+info['id'],{'page':page});pages+=1
   if payload.get('success')!=1:raise RuntimeError('TotalCorner league schedule returned unsuccessful response')
   rows=get_matches(payload)
   if not rows:break
   for m in rows:
    parsed=candidate_key(code,m)
    if not parsed:continue
    k,ko,score=parsed
    if k not in wanted or score!=wanted[k]['prediction']['score']:continue
    mid=str(m.get('id') or '')
    if mid:matches_by_id[mid]=(k,ko,m)
   if not next_page(payload,page):break
   page+=1
  page_counts[code]=pages
 print(json.dumps({'phase':'quote_window_schedule_ready','window':f'{start}_{end}','matched_ids':len(matches_by_id),'pages':page_counts}),flush=True)
 results=[];seen_keys=set()
 for n,(mid,(k,ko,sched)) in enumerate(sorted(matches_by_id.items(),key=lambda q:(q[1][1],q[0])),1):
  if k in seen_keys:continue
  seen_keys.add(k);predinfo=wanted[k];pred=predinfo['prediction']
  payload=request('/match/bookmaker_odds/'+urllib.parse.quote(mid,safe=''),{'bookmaker':'crown','columns':'asianList,goalList'})
  data=payload.get('data') if isinstance(payload,dict) else None
  fixtures=[x for x in data if isinstance(x,dict) and str(x.get('id'))==mid] if isinstance(data,list) else []
  if payload.get('success')!=1 or len(fixtures)!=1:
   counts['odds_api_or_identity_failure']+=1;continue
  fixture=fixtures[0];books=fixture.get('bookmakers')
  crowns=[b for b in books if isinstance(b,dict) and b.get('slug')=='crown'] if isinstance(books,list) else []
  if len(crowns)!=1:counts['crown_missing_or_ambiguous']+=1;continue
  book=crowns[0];ah=book.get('asian_list') or [];ou=book.get('goal_list') or []
  results.append({'split':predinfo['split'],'league':pred['league'],'season':pred.get('season'),'m3_date':pred['date'],
   'home':pred['home'],'away':pred['away'],'m3_score':pred['score'],'models':pred['models'],
   'source':{'match_id':mid,'league':fixture.get('l'),'league_id':str(fixture.get('l_id') or LEAGUES[k[0]]['id']),
    'home':fixture.get('h'),'away':fixture.get('a'),'start_local':fixture.get('start'),'kickoff_utc':ko.isoformat(),
    'status':fixture.get('status'),'score':[fixture.get('hg'),fixture.get('ag')],
    'canonical_payload_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()},
   'crown':{'asian_list':ah,'goal_list':ou}})
  counts['crown_responses']+=1;raw['AH_raw_rows']+=len(ah);raw['OU_raw_rows']+=len(ou)
  if n%100==0:print(json.dumps({'phase':'crown_quote_window','window':f'{start}_{end}','completed':n,'crown_responses':counts['crown_responses']}),flush=True)
 summary={'protocol':'M3_CROWN_DROP_WINDOW_QUOTES_V2','window':{'start':str(start),'end':str(end)},
  'matched_fixtures':len(matches_by_id),'crown_responses':counts['crown_responses'],'counts':dict(counts),
  'raw_market_rows':dict(raw),'schedule_pages':page_counts}
 OUT.mkdir(parents=True,exist_ok=True);tag=f'{start}_{end}'
 encrypt_doc({'summary':summary,'records':results},key_text,'QUOTE_WINDOW',OUT/f'm3_crown_quotes_{tag}.bin')
 write_public(f'quotes_{tag}_summary.json',summary)
 print(json.dumps({'status':'QUOTE_WINDOW_READY','summary':summary},ensure_ascii=False),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=('manifest','manifest-window','merge-manifests','quotes','quotes-window'),required=True);p.add_argument('--batch',type=int,default=0);p.add_argument('--start');p.add_argument('--end');p.add_argument('--input-dir');a=p.parse_args()
 if a.stage=='manifest':stage_manifest()
 elif a.stage=='manifest-window':
  if not a.start or not a.end:raise RuntimeError('manifest-window requires --start and --end')
  stage_manifest_window(a.start,a.end)
 elif a.stage=='merge-manifests':
  if not a.input_dir:raise RuntimeError('merge-manifests requires --input-dir')
  stage_merge_manifests(a.input_dir)
 elif a.stage=='quotes-window':
  if not a.start or not a.end:raise RuntimeError('quotes-window requires --start and --end')
  stage_quotes_window(a.start,a.end)
 else:stage_quotes(a.batch)

if __name__=='__main__':main()
