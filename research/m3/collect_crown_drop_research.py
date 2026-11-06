"""Bounded M3-only Crown history collector. Output is encrypted before upload."""
from __future__ import annotations
import base64, csv, datetime as dt, hashlib, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, zlib
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[2]
PRED=ROOT/'research/m3/results/predictions/88cda93edc2bacc835ddea02e6d2c2140177e454cd336ab335cb2262a3f633bf.csv'
OUT=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'m3-crown-research'
BASE='https://api.totalcorner.com/v1'
TZ=ZoneInfo('Asia/Shanghai')
GAP=2.05
TARGET_TEST=7000
TARGET_TRAIN=1200
LEAGUE={
 'E0':'England Premier League','D1':'Germany Bundesliga I','F1':'France Ligue 1',
 'I1':'Italy Serie A','SP1':'Spain La Liga','B1':'Belgium First Division A'}
MODELS={'poisson','dixon_coles','bivariate_poisson'}
last_start=0.0
diag=Counter()

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+','',s)

def day(s): return dt.date.fromisoformat(str(s)[:10])

def request(path,params):
 global last_start
 wait=GAP-(time.monotonic()-last_start)
 if wait>0: time.sleep(wait)
 last_start=time.monotonic()
 q=dict(params);q['token']=os.environ['TOTALCORNER_TOKEN']
 url=BASE+path+'?'+urllib.parse.urlencode(q)
 for attempt in range(8):
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'M3-Crown-Research/1.0'})
   with urllib.request.urlopen(req,timeout=45) as r: payload=json.load(r)
  except Exception as e:
   if attempt==7: raise RuntimeError('TotalCorner transport failed after bounded retries') from None
   time.sleep(min(2*(attempt+1),12));continue
  err=payload.get('error') if isinstance(payload,dict) else None
  if isinstance(err,dict) and err.get('code')=='TOO_MANY_REQUEST' and attempt<7:
   time.sleep(11);continue
  return payload
 raise RuntimeError('TotalCorner retry budget exhausted')

def schedule(date):
 rows=[];page=1
 while True:
  p=request('/match/schedule',{'date':date.strftime('%Y%m%d'),'page':page})
  if p.get('success')!=1 or not isinstance(p.get('data'),list):
   code=(p.get('error') or {}).get('code') if isinstance(p.get('error'),dict) else None
   if code in {'TOKEN_ERROR','VIP_REQUIRED','VIP_ONLY'}:raise RuntimeError('TotalCorner API access was rejected')
   diag['schedule_api_error']+=1;return []
  rows.extend(x for x in p['data'] if isinstance(x,dict))
  pag=p.get('pagination') or {}
  pages=max(1,int(pag.get('pages') or 1))
  if page>=pages:break
  page+=1
 return rows

def kickoff_utc(m):
 try:
  x=dt.datetime.strptime(str(m['start']),'%Y-%m-%d %H:%M:%S').replace(tzinfo=TZ)
  return x.astimezone(dt.timezone.utc)
 except Exception:return None

def prediction_candidates():
 if not PRED.exists(): raise RuntimeError('M3 OOS prediction artifact missing')
 grouped={}
 with PRED.open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   if r.get('prediction_status')!='predicted' or r.get('league') not in LEAGUE:continue
   try:
    match_day=day(r.get('match_date_utc'));train_end=dt.datetime.fromisoformat(str(r.get('train_end_utc')).replace('Z','+00:00'))
    if train_end.tzinfo is None or train_end.date()>=match_day:continue
    model=r.get('model')
    if model not in MODELS:continue
    score=[int(float(r['actual_home_goals'])),int(float(r['actual_away_goals']))]
   except Exception:continue
   key=(r['league'],match_day.isoformat(),norm(r.get('home_team')),norm(r.get('away_team')))
   item=grouped.setdefault(key,{'league':r['league'],'season':r.get('season'),'date':match_day.isoformat(),'home':r['home_team'],'away':r['away_team'],'score':score,'models':{}})
   if item['score']!=score:diag['m3_outcome_conflict']+=1;grouped.pop(key,None);continue
   if model in item['models']:diag['duplicate_model_rows']+=1;continue
   # Keep only ex-ante predictors and target settlement probabilities.
   item['models'][model]={k:r.get(k) for k in ('train_end_utc','ah_home_0_p_win','ah_home_0_p_push','ah_home_0_p_lose','ou_p_over_2_5')}
 for key in list(grouped):
  if set(grouped[key]['models'])!=MODELS:del grouped[key];diag['incomplete_model_group']+=1
 items=sorted(grouped.values(),key=lambda x:(x['date'],x['league'],norm(x['home']),norm(x['away'])))
 if len(items)<TARGET_TEST+TARGET_TRAIN:raise RuntimeError('Insufficient unique strict-OOS M3 fixtures')
 start_index=max(0,len(items)-TARGET_TEST)
 test_start=day(items[start_index]['date'])
 test=[x for x in items if day(x['date'])>=test_start]
 prior=[x for x in items if day(x['date'])<test_start]
 train=prior[-TARGET_TRAIN:]
 if len(train)<TARGET_TRAIN:raise RuntimeError('Insufficient pre-test training fixtures')
 return train,test

def fixture_key(m):
 ko=kickoff_utc(m)
 if not ko:return None
 lg=str(m.get('l') or '')
 code=next((c for c,v in LEAGUE.items() if norm(v)==norm(lg)),None)
 if not code:return None
 try:score=[int(float(m['hg'])),int(float(m['ag']))]
 except Exception:return None
 return (code,ko.date().isoformat(),norm(m.get('h')),norm(m.get('a'))),ko,score

def main():
 token=os.environ.get('TOTALCORNER_TOKEN')
 key=os.environ.get('M3_CROWN_RESEARCH_KEY')
 if not token:raise RuntimeError('TotalCorner credential unavailable')
 if not key:raise RuntimeError('Encryption key unavailable')
 train,test=prediction_candidates(); all_candidates=train+test
 wanted={ (x['league'],x['date'],norm(x['home']),norm(x['away'])):x for x in all_candidates }
 dates=sorted({day(x['date']) for x in all_candidates})
 schedule_days=sorted({d+dt.timedelta(days=offset) for d in dates for offset in (-1,0,1)})
 found=defaultdict(list)
 OUT.mkdir(parents=True,exist_ok=True)
 schedule_count=0
 for i,d in enumerate(schedule_days,1):
  rows=schedule(d);schedule_count+=1
  for m in rows:
   parsed=fixture_key(m)
   if not parsed:continue
   (code,utcday,home,away),ko,score=parsed
   k=(code,utcday,home,away)
   if k in wanted:found[k].append((m,ko,score))
  if i%100==0:print(json.dumps({'phase':'schedule','completed_days':i,'total_days':len(schedule_days),'matches_found':len(found)}),flush=True)
 matched={}; ambiguous=0; score_mismatch=0
 for k,rows in found.items():
  unique={str(r[0].get('id')):r for r in rows if r[0].get('id')}
  if len(unique)!=1:ambiguous+=1;continue
  row=next(iter(unique.values())); pred=wanted[k]
  if row[2]!=pred['score']:score_mismatch+=1;continue
  matched[k]=(pred,row[0],row[1],row[2])
 diag['schedule_ambiguous_fixture_keys']=ambiguous;diag['schedule_score_mismatch']=score_mismatch
 diag['schedule_exact_fixture_matches']=len(matched);diag['schedule_unmatched_m3_fixtures']=len(wanted)-len(matched)
 train_keys={(x['league'],x['date'],norm(x['home']),norm(x['away'])) for x in train}
 test_keys={(x['league'],x['date'],norm(x['home']),norm(x['away'])) for x in test}
 ids=[]
 for k,(pred,m,ko,score) in matched.items():
  ids.append((k,pred,m,ko,score,'TRAIN' if k in train_keys else 'TEST'))
 ids.sort(key=lambda z:(z[3],z[0]))
 records=[];market_rows=Counter();crown_ok=0
 for n,(k,pred,sched,ko,score,split) in enumerate(ids,1):
  mid=str(sched['id'])
  payload=request('/match/bookmaker_odds/'+urllib.parse.quote(mid,safe=''),{'bookmaker':'crown','columns':'asianList,goalList'})
  data=payload.get('data') if isinstance(payload,dict) else None
  matches=[x for x in data if isinstance(x,dict) and str(x.get('id'))==mid] if isinstance(data,list) else []
  if payload.get('success')!=1:
   code=(payload.get('error') or {}).get('code') if isinstance(payload.get('error'),dict) else None
   if code in {'TOKEN_ERROR','VIP_REQUIRED','VIP_ONLY'}:raise RuntimeError('TotalCorner API access was rejected')
   diag['odds_api_or_identity_failure']+=1;continue
  if len(matches)!=1:
   diag['odds_api_or_identity_failure']+=1;continue
  fixture=matches[0];books=fixture.get('bookmakers')
  crowns=[b for b in books if isinstance(b,dict) and b.get('slug')=='crown'] if isinstance(books,list) else []
  if len(crowns)!=1:diag['crown_missing_or_ambiguous']+=1;continue
  book=crowns[0]
  ah=book.get('asian_list') or [];ou=book.get('goal_list') or []
  # Retain only documented movement rows; downstream validation applies strict timestamps.
  record={'split':split,'league':pred['league'],'season':pred.get('season'),'m3_date':pred['date'],
    'home':pred['home'],'away':pred['away'],'m3_score':pred['score'],'models':pred['models'],
    'source':{'match_id':mid,'league':fixture.get('l'),'home':fixture.get('h'),'away':fixture.get('a'),
      'start_local':fixture.get('start'),'kickoff_utc':ko.isoformat(),'status':fixture.get('status'),
      'score':[fixture.get('hg'),fixture.get('ag')],'canonical_payload_sha256':hashlib.sha256(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()},
    'crown':{'asian_list':ah,'goal_list':ou}}
  records.append(record);crown_ok+=1
  market_rows['AH_raw']+=len(ah);market_rows['OU_raw']+=len(ou)
  if n%100==0:print(json.dumps({'phase':'crown','completed_matches':n,'total_matches':len(ids),'crown_responses':crown_ok,'ah_raw_rows':market_rows['AH_raw'],'ou_raw_rows':market_rows['OU_raw']}),flush=True)
 summary={'protocol':'M3_CROWN_DROP_RESEARCH_FETCH_V1','sample_design':{'train_candidate_fixtures':len(train),'test_candidate_fixtures':len(test),'train_start':train[0]['date'],'train_end':train[-1]['date'],'test_start':test[0]['date'],'test_end':test[-1]['date'],'scoped_leagues':list(LEAGUE)},'schedule_dates_queried':schedule_count,'matched_schedule_fixtures':len(matched),'crown_responses':crown_ok,'raw_market_rows':dict(market_rows),'diagnostics':dict(diag),'api_calls_excluded_tokens':True}
 bundle=json.dumps({'summary':summary,'records':records},ensure_ascii=False,separators=(',',':')).encode()
 compressed=zlib.compress(bundle,9)
 aeskey=base64.b64decode(key,validate=True)
 if len(aeskey)!=32:raise RuntimeError('Encryption key must decode to 32 bytes')
 nonce=os.urandom(12);cipher=AESGCM(aeskey).encrypt(nonce,compressed,b'M3_CROWN_RESEARCH_V1')
 (OUT/'m3_crown_research.bin').write_bytes(nonce+cipher)
 (OUT/'public_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
