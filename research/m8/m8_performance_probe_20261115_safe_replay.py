import json,datetime,collections,hashlib,time
from pathlib import Path
import requests
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Representative date-stratified spot check only, no claim of complete historical coverage.
z=list(map(json.loads,(P/'m8_early_joint_market_inventory_20261115.jsonl').open()))
pool={r['fid']:r for r in z if r['T']==12}
samples=[]
for y in range(2019,2027):
 q=sorted((r for r in pool.values() if r['year']==y),key=lambda r:(r['date'],r['fid']))
 if q:samples.append(q[len(q)//2])
# Include late 2026 to probe recent xG availability. No selected results or odds used in sampling.
q=sorted((r for r in pool.values() if r['year']==2026),key=lambda r:(r['date'],r['fid']))
samples.extend([q[-1]])
import os
token=os.environ['TOTALCORNER_TOKEN']
rawdir=P/'m8_performance_probe_20261115';rawdir.mkdir(exist_ok=True)
results=[]
for r in samples:
 e={'fid':r['fid'],'year':r['year'],'league':r['league'],'date':r['date'],'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  resp=requests.get('https://api.totalcorner.com/v1/match/view/'+r['fid'],params={'token':token,'columns':'shotOn,shotOff,xg,attacks,dangerousAttacks,possession'},headers={'Accept':'application/json','User-Agent':'M8-Performance-Data-Coverage/1.0'},timeout=8)
  e['http_status']=resp.status_code
  raw=resp.content;sha=hashlib.sha256(raw).hexdigest();e['sha256']=sha
  # Keep original provider payload local.
  (rawdir/(r['fid']+'-'+sha+'.json')).write_bytes(raw)
  if resp.status_code==429:results.append(e);print(e,flush=True);break
  body=resp.json()
  e['provider_error_code']=(body.get('error') or {}).get('code')
  if e['provider_error_code']=='TOO_MANY_REQUEST':
   results.append(e);print(e,flush=True);break
  x=next((x for x in body.get('data',[]) if str(x['id'])==r['fid']),None) if isinstance(body.get('data'),list) else None
  if x and str(x['l_id'])==str(r['league']) and str(x.get('h_id'))==r['home_id'] and str(x.get('a_id'))==r['away_id'] and x.get('status')=='full' and int(x['hg'])==r['hg'] and int(x['ag'])==r['ag']:
   e['identity_and_FT']=True;e['fields']={}
   for field in ('shot_on','shot_off','xg','attacks','dangerous_attacks','possess'):
    v=x.get('dang_attacks' if field=='dangerous_attacks' else field)
    try:
     valid=isinstance(v,list) and len(v)==2 and all(t is not None and float(t)>=0 for t in v)
     e['fields'][field]={'non_null_pair':valid,'nonzero_pair':bool(valid and sum(map(float,v))>0)}
    except (ValueError,TypeError):e['fields'][field]={'non_null_pair':False,'nonzero_pair':False}
  else:e['identity_and_FT']=False
 except Exception as exc:e['error']=type(exc).__name__
 results.append(e);print(e,flush=True)
 time.sleep(2.6)
out={'sample_selection':'one time-median T12 historical fixture per year plus latest 2026 fixture; illustrative only','requested':len(results),'results':results,'fields_nonzero':{k:sum(x.get('fields',{}).get(k,{}).get('nonzero_pair',False) for x in results) for k in ('shot_on','shot_off','xg','attacks','dangerous_attacks','possess')}}
(P/'m8_performance_probe_20261115.json').write_text(json.dumps(out,indent=2))
print('SUMMARY',out['requested'],out['fields_nonzero'],flush=True)
