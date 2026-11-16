import json,datetime,hashlib,collections,time,os
from pathlib import Path
import requests
P=Path('/Users/mac/QuantAsiaDesk/research-work')
# Existing Crown historical raw identity inventory.
ns={};s=(P/'m8_early_exact_cross_market_consistency_20261115.py').read_text();exec(s[:s.index('C=collections.Counter();rows=[]')],ns)
jobs=ns['jobs'];dt=ns['dt']
target={r['fid']:r for r in map(json.loads,(P/'m8_early_joint_market_inventory_20261115.jsonl').open()) if r['T']==12}
priorpaths=['m8_performance_batch_probe_20261115.jsonl','m8_performance_cross_year_20261115/verified_new.jsonl','m8_performance_contiguous_20261115/verified_new.jsonl','m8_performance_gap_recovery_20261115/verified_new.jsonl','m8_tc_continuous_20261116/verified_new.jsonl','m8_tc_continuous_round2_20261116/verified_new.jsonl','m8_tc_crossyear_round3_20261116/verified_new.jsonl','m8_tc_crossyear_round4_20261116/verified_new.jsonl','m8_tc_crossyear_round5_20261116/verified_new.jsonl','m8_tc_crossyear_round6_20261116/verified_new.jsonl','m8_tc_crossyear_round7_20261116/verified_new.jsonl','m8_tc_crossyear_round8_20261116/verified_new.jsonl']
seen={r['fid'] for p in priorpaths for r in map(json.loads,(P/p).open())}
seen.update(r['fid'] for r in json.loads((P/'m8_tc_local_probe_bridge_20261115.json').read_text())['added'])
dest=P/'m8_tc_crossyear_round9_20261116';dest.mkdir(exist_ok=True);(dest/'pages').mkdir(exist_ok=True)
events=dest/'requests.jsonl';recfile=dest/'verified_new.jsonl'
old=list(map(json.loads,events.open())) if events.exists() else []
if recfile.exists():seen.update(r['fid'] for r in map(json.loads,recfile.open()))
done={(r['league'],r['page']) for r in old if r.get('success')}
# Extend around the 2024/25 boundary, using archived schedule page dates; Italy page is an estimate.
# This is the acquisition order for this run only, not a trading restriction.
# The page numbers are acquisition targets, not a match selection rule.
basepages=[('290',22),('16',21),('25',21),('1',24),('14',26),('12',25),('73',25),('145',31)]
todo=[(l,6) for l,p in basepages if l not in ('290','16','25')]+[(l,p-5) for l,p in basepages]
token=os.environ.get('TOTALCORNER_TOKEN') or Path('/Users/mac/Desktop/totalcorner_token.txt').read_text().strip()
def save(path,obj):
 with path.open('a') as f:f.write(json.dumps(obj,ensure_ascii=False)+'\n')
for l,page in todo:
 if (l,page) in done:continue
 e={'league':l,'page':page,'new':0,'matched':0,'mismatch':0,'complete':0}
 try:
  resp=requests.get('https://api.totalcorner.com/v1/league/schedule/'+l,params={'token':token,'page':page,'columns':'shotOn,shotOff,attacks,dangerousAttacks,possession,xg'},timeout=10)
  e.update(received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),http_status=resp.status_code,remaining=resp.headers.get('X-Rate-Limit-Remaining'),reset=resp.headers.get('X-Rate-Limit-Reset'))
  raw=resp.content;sha=hashlib.sha256(raw).hexdigest();e['sha256']=sha;(dest/'pages'/f'{l}-{page}-{sha}.json').write_bytes(raw)
  b=resp.json();e['provider_error']=(b.get('error') or {}).get('code')
  if resp.status_code!=200 or e['provider_error'] or not b.get('success'):
   e['success']=False;save(events,e);print('STOP',e,flush=True);break
  a=b.get('data',{}).get('matches',[]);e['rows']=len(a);e['success']=True
  for x in a:
   f=str(x.get('id'));r=target.get(f)
   if x.get('status')!='full' or not r:continue
   try:
    file,oldsha,lid=jobs[f];rr=file.read_bytes()
    assert not oldsha or hashlib.sha256(rr).hexdigest()==oldsha
    q=next(v for v in json.loads(rr)['data'] if str(v['id'])==f);k=dt(x['start'])
    assert str(x['l_id'])==str(lid)==l==r['league'] and str(x['h_id'])==str(q['h_id'])==r['home_id'] and str(x['a_id'])==str(q['a_id'])==r['away_id'] and dt(q['start'])==k and q['status']=='full'
    assert (int(x['hg']),int(x['ag']))==(int(q['hg']),int(q['ag']))==(r['hg'],r['ag'])
   except Exception:e['mismatch']+=1;continue
   e['matched']+=1
   def pair(key):
    v=x.get(key)
    try:return list(map(float,v)) if isinstance(v,list) and len(v)==2 and all(t is not None and float(t)>=0 for t in v) else None
    except:return None
   so,sf,po=[pair(key) for key in ('shot_on','shot_off','possess')]
   if so is None or sf is None or po is None or abs(sum(po)-100)>1:continue
   e['complete']+=1
   if f in seen:continue
   rec={'fid':f,'league':l,'year':k.year,'date':k.date().isoformat(),'kickoff_utc':k.isoformat(),'home':r['home_id'],'away':r['away_id'],'hg':r['hg'],'ag':r['ag'],'hshots':so[0]+sf[0],'ashots':so[1]+sf[1],'hsot':so[0],'asot':so[1],'hposs':po[0],'aposs':po[1],'raw_sha256':sha,'received_utc':e['received_utc']}
   save(recfile,rec);seen.add(f);e['new']+=1
  save(events,e);print('PAGE',e,flush=True)
  if e['remaining']=='0':print('STOP_PROVIDER_QUOTA',flush=True);break
  # Complete this bounded eight-league acquisition pass first, then assess continuity and cost.
 except Exception as ex:
  e['success']=False;e['error']=type(ex).__name__;save(events,e);print('STOP',e,flush=True);break
 time.sleep(4)
