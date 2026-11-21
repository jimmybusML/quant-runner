#!/usr/bin/env python3
"""One-time sequential venue geocoding; cache every response and obey OSM limits."""
import datetime as dt,hashlib,json,pathlib,time,urllib.error,urllib.parse,urllib.request

OUT=pathlib.Path(__file__).resolve().parent
QUERIES=OUT/'venue_geocode_queries_20261121.jsonl'
CACHE=OUT/'nominatim_geocode_cache_20261121.jsonl'
UA='M8StadiumElevationResearch/1.0 (+https://github.com/jimmybusML/quant-runner; one-time cached geocoding)'
def main():
 done=set()
 if CACHE.exists():
  for line in CACHE.open(encoding='utf8'):
   try:
    r=json.loads(line)
    if r.get('http_status')==200 and isinstance(r.get('response'),list):done.add(r['query_key'])
   except Exception:continue
 rows=[json.loads(x) for x in QUERIES.open(encoding='utf8') if x.strip()]
 pending=[r for r in rows if r['query'] not in done]
 print(json.dumps({'already_cached':len(done),'pending':len(pending),'max_request_rate_per_second':1,'single_thread':True}),flush=True)
 if done and pending:time.sleep(1.2)
 for i,r in enumerate(pending):
  params=urllib.parse.urlencode({'q':r['query'],'format':'jsonv2','addressdetails':1,'extratags':1,'limit':5})
  url='https://nominatim.openstreetmap.org/search?'+params
  req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
  started=dt.datetime.now(dt.timezone.utc).isoformat()
  try:
   with urllib.request.urlopen(req,timeout=30) as resp:
    raw=resp.read();payload=json.loads(raw)
    result={'query_key':r['query'],'venue':r['venue'],'country':r['country'],'candidate_fids':r['candidate_fids'],
      'years':r['years'],'url':url,'http_status':resp.status,'response_sha256':hashlib.sha256(raw).hexdigest(),
      'response':payload,'received_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'policy_note':'single-machine single-thread; >=1.1 seconds between requests; cached once'}
   with CACHE.open('a',encoding='utf8') as f:f.write(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
   if (i+1)%20==0 or i+1==len(pending):print(json.dumps({'completed_this_run':i+1,'remaining':len(pending)-i-1,'last_query':r['query'],'results':len(payload)}),flush=True)
  except urllib.error.HTTPError as e:
   result={'query_key':r['query'],'venue':r['venue'],'country':r['country'],'url':url,'http_status':e.code,
     'error':'HTTPError; stopped without retry','received_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
   with CACHE.open('a',encoding='utf8') as f:f.write(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
   print(json.dumps(result,ensure_ascii=False),flush=True);break
  except Exception as e:
   result={'query_key':r['query'],'venue':r['venue'],'country':r['country'],'url':url,
     'error':type(e).__name__+': '+str(e),'received_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
   with CACHE.open('a',encoding='utf8') as f:f.write(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
   print(json.dumps(result,ensure_ascii=False),flush=True);break
  if i+1<len(pending):time.sleep(1.1)
 print(json.dumps({'cached_rows':sum(1 for x in CACHE.open(encoding='utf8') if x.strip()) if CACHE.exists() else 0}),flush=True)
if __name__=='__main__':main()
