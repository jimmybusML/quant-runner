import json,collections,datetime,hashlib,time,os,sys
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
# Use the same exact archived sources as prior M8 historical research for identity.
s=(R/'m8_early_exact_cross_market_consistency_20261115.py').read_text()
exec(s[:s.index('C=collections.Counter();rows=[]')])
targets={r['fid']:r for r in map(json.loads,(R/'m8_early_joint_market_inventory_20261115.jsonl').open()) if r['T']==12}
scope=sorted({str(r['league']) for r in targets.values()});assert len(scope)==49
before=list(map(json.loads,(R/'m8_performance_batch_probe_20261115.jsonl').open()))
prior=json.load((R/'m8_performance_batch_probe_20261115.json').open())
base=R/'m8_performance_expanded_20261115';base.mkdir(exist_ok=True)
pages=base/'pages';pages.mkdir(exist_ok=True)
fields=('shot_on','shot_off','attacks','dang_attacks','possess','xg')
def pair(v):
 try:return isinstance(v,list) and len(v)==2 and all(x is not None and float(x)>=0 for x in v)
 except:return False
# Local schedule index estimates remaining target pages; provider page order may drift. Not proof of completeness.
q=[];cached_ids=set()
for l in scope:
 for f in (P/'data/m5-crown-authorized/schedules'/l).glob('page-*.raw.json'):
  try:
   b=json.load(f.open());page=int(f.name.split('-')[1].split('.')[0]);ids={str(x['id']) for x in b['data']['matches'] if x.get('status')=='full'}&targets.keys()
   if ids:
    cached_ids.update(ids);q.append({'league':l,'page':page,'cached_T12_matches':len(ids),'cached_2026_matches':sum(targets[f]['year']==2026 for f in ids)})
  except:continue
(base/'cached_page_inventory.json').write_text(json.dumps({'scope':scope,'n_pages':len(q),'n_distinct_target_ids':len(cached_ids),'target_n':len(targets),'pages':q},indent=2))
print('QUEUE',len(scope),len(q),len(cached_ids),len(targets),flush=True)
# This turn extends the already verified six nearby historical page ranges, so teams have consecutive records.
# Page count is only this finite request's work batch, not a future cap or model condition.
leagues=[v['league'] for v in prior['pages'] if v.get('matched')]
todo=[(l,p) for p in (4,6,7) for l in leagues]
token=os.environ['TOTALCORNER_TOKEN']
events=base/'requests.jsonl';records=base/'verified_new.jsonl'
seen={r['fid'] for r in before}
if records.exists():seen.update(r['fid'] for r in map(json.loads,records.open()))
done={(r['league'],r['page']) for r in map(json.loads,events.open()) if r.get('success')} if events.exists() else set()
for l,p in todo:
 if (l,p) in done:continue
 e={'league':l,'page':p,'received_utc':None,'matched':0,'new':0,'mismatch':0,'nonzero':collections.Counter()}
 try:
  resp=requests.get('https://api.totalcorner.com/v1/league/schedule/'+l,params={'token':token,'page':p,'columns':'shotOn,shotOff,attacks,dangerousAttacks,possession,xg'},timeout=10)
  e['received_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();e['http_status']=resp.status_code;e['remaining']=resp.headers.get('X-Rate-Limit-Remaining')
  raw=resp.content;sha=hashlib.sha256(raw).hexdigest();e['sha256']=sha;(pages/f'{l}-{p}-{sha}.json').write_bytes(raw)
  b=resp.json();e['provider_error']=(b.get('error') or {}).get('code')
  if resp.status_code!=200 or e['provider_error']:
   e['success']=False
   with events.open('a') as f:f.write(json.dumps(e)+'\n')
   print('ERROR',e,flush=True);break
  a=b.get('data',{}).get('matches',[]);e['rows']=len(a);e['full']=sum(x.get('status')=='full' for x in a);e['success']=True
  for x in a:
   fid=str(x.get('id'));r=targets.get(fid)
   if not r or x.get('status')!='full':continue
   try:
    file,old_sha,lid=jobs[fid];rr=file.read_bytes()
    if old_sha and hashlib.sha256(rr).hexdigest()!=old_sha: raise ValueError('hash')
    old=next(y for y in json.loads(rr)['data'] if str(y['id'])==fid)
    k=dt(x['start'])
    assert str(x['l_id'])==l==str(lid)==r['league']
    assert str(x['h_id'])==r['home_id']==str(old['h_id']) and str(x['a_id'])==r['away_id']==str(old['a_id'])
    assert k==dt(old['start']) and (int(x['hg']),int(x['ag']))==(r['hg'],r['ag'])==(int(old['hg']),int(old['ag']))
    assert old['status']=='full'
   except Exception:e['mismatch']+=1;continue
   e['matched']+=1
   rec={'fid':fid,'league':l,'date':k.date().isoformat(),'kickoff_utc':k.isoformat(),'home':r['home_id'],'away':r['away_id'],'hg':r['hg'],'ag':r['ag'],'received_utc':e['received_utc'],'raw_sha256':sha}
   for field in fields:
    v=x.get(field);rec[field]=list(map(float,v)) if pair(v) else None
    if rec[field] is not None and sum(rec[field])>0:e['nonzero'][field]+=1
   if fid not in seen:
    with records.open('a') as f:f.write(json.dumps(rec)+'\n')
    e['new']+=1;seen.add(fid)
  with events.open('a') as f:f.write(json.dumps(e)+'\n')
  print('PAGE',json.dumps(e),flush=True)
  # Respect observed rate limiting rather than attempting to bypass.
  if e['remaining']=='0':print('STOP_RATE_LIMIT',flush=True);break
 except Exception as ex:
  e['error']=type(ex).__name__;e['success']=False
  with events.open('a') as f:f.write(json.dumps(e)+'\n')
  print('ERROR',e,flush=True);break
 time.sleep(4)
print('COMPLETE_BATCH',len(seen),flush=True)
