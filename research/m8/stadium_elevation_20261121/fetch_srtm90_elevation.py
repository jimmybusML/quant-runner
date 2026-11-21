#!/usr/bin/env python3
"""Batch-query Open Topo Data SRTM90m, max 100 points/request, cached and resumable."""
import datetime as dt,gzip,hashlib,json,pathlib,time,urllib.error,urllib.request

OUT=pathlib.Path(__file__).resolve().parent
COORDS=OUT/'venue_coordinates_20261121.jsonl';RAW=OUT/'srtm90m_raw';MANIFEST=OUT/'srtm90m_manifest_20261121.jsonl'
UA='M8AHElevationResearch/1.0 (+https://github.com/jimmybusML/quant-runner; one-time SRTM lookup)'
def main():
 RAW.mkdir(parents=True,exist_ok=True)
 locs=[json.loads(x) for x in COORDS.open(encoding='utf8') if x.strip()]
 dedup={}
 for r in locs:
  key=f"{r['latitude']:.6f},{r['longitude']:.6f}"
  d=dedup.setdefault(key,{'coordinate_id':key,'latitude':float(r['latitude']),'longitude':float(r['longitude']),'venues':[],'candidate_fids':0})
  d['venues'].append(r['venue']);d['candidate_fids']+=int(r.get('candidate_fids',0))
 unique=list(dedup.values());done=set()
 if MANIFEST.exists():
  for line in MANIFEST.open(encoding='utf8'):
   try:r=json.loads(line)
   except:continue
   if r.get('status')=='success':done.update(r.get('coordinate_ids',[]))
 pending=[x for x in unique if x['coordinate_id'] not in done]
 print(json.dumps({'unique_locations':len(unique),'cached_locations':len(done),'pending_locations':len(pending),'max_points_per_request':100,'request_interval_seconds':1.1},ensure_ascii=False),flush=True)
 if done and pending:time.sleep(1.2)
 for i in range(0,len(pending),100):
  batch=pending[i:i+100];locations='|'.join(f"{x['latitude']:.6f},{x['longitude']:.6f}" for x in batch)
  payload=json.dumps({'locations':locations},separators=(',',':')).encode()
  req=urllib.request.Request('https://api.opentopodata.org/v1/srtm90m',data=payload,headers={'User-Agent':UA,'Content-Type':'application/json','Accept':'application/json'},method='POST')
  row={'batch':i//100+1,'coordinate_ids':[x['coordinate_id'] for x in batch],'locations':batch,
       'dataset':'SRTM90m v3','request_started_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
  try:
   with urllib.request.urlopen(req,timeout=60) as resp:raw=resp.read();status=resp.status
   parsed=json.loads(raw)
   if status!=200 or parsed.get('status')!='OK' or len(parsed.get('results',[]))!=len(batch):raise ValueError(f'bad status/row count: {status} {parsed.get("status")} {len(parsed.get("results",[]))}')
   packed=gzip.compress(raw,compresslevel=6,mtime=0);rawsha=hashlib.sha256(raw).hexdigest();name=f'srtm90m_batch_{i//100+1:02d}_{rawsha[:12]}.json.gz';(RAW/name).write_bytes(packed)
   row.update({'status':'success','http_status':status,'response_sha256':rawsha,'compressed_sha256':hashlib.sha256(packed).hexdigest(),
     'compressed_file':f'srtm90m_raw/{name}','response_received_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
     'results':[{'coordinate_id':batch[j]['coordinate_id'],'elevation_m':x.get('elevation'),'dataset':x.get('dataset'),'returned_location':x.get('location')} for j,x in enumerate(parsed['results'])]})
   print(json.dumps({'status':'success','batch':row['batch'],'locations':len(batch),'null_elevations':sum(x['elevation_m'] is None for x in row['results']),'remaining':len(pending)-i-len(batch),'sha256':rawsha}),flush=True)
  except Exception as e:
   row.update({'status':'failure','error':type(e).__name__+': '+str(e),'failed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
   with MANIFEST.open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
   print(json.dumps({'status':'failure','batch':row['batch'],'error':row['error']},ensure_ascii=False),flush=True);break
  with MANIFEST.open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
  if i+100<len(pending):time.sleep(1.1)
 print(json.dumps({'manifest_rows':sum(1 for x in MANIFEST.open(encoding='utf8') if x.strip()) if MANIFEST.exists() else 0}),flush=True)
if __name__=='__main__':main()
