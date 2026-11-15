import json,collections,datetime,hashlib,time,os
from pathlib import Path
import requests
P=Path('/Users/mac/QuantAsiaDesk/research-work')
rows={r['fid']:r for r in map(json.loads,(P/'m8_early_joint_market_inventory_20261115.jsonl').open()) if r['T']==12}
league_counts=collections.Counter(r['league'] for r in rows.values() if r['year']==2026)
# Six different high-coverage leagues, one historical page each, a coverage probe rather than a population estimate.
leagues=[l for l,n in league_counts.most_common(6)]
token=os.environ['TOTALCORNER_TOKEN']
dest=P/'m8_performance_batch_20261115';dest.mkdir(exist_ok=True)
result=[];matched={}
fields=('shot_on','shot_off','attacks','dang_attacks','possess','xg')
def pair(v):
 try:return isinstance(v,list) and len(v)==2 and all(x is not None and float(x)>=0 for x in v)
 except:return False
for lid in leagues:
 rec={'league':lid,'page':5,'received_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  response=requests.get('https://api.totalcorner.com/v1/league/schedule/'+lid,params={'token':token,'page':5,'columns':'shotOn,shotOff,attacks,dangerousAttacks,possession,xg'},timeout=10)
  rec['http_status']=response.status_code;rec['rate_remaining']=response.headers.get('X-Rate-Limit-Remaining');raw=response.content;sha=hashlib.sha256(raw).hexdigest();rec['sha256']=sha
  (dest/(lid+'-5-'+sha+'.json')).write_bytes(raw)
  b=response.json();rec['provider_error']=(b.get('error') or {}).get('code')
  if response.status_code==429 or rec['provider_error']=='TOO_MANY_REQUEST':
   result.append(rec);print('RATE_LIMIT',rec,flush=True);break
  a=b.get('data',{});matches=a.get('matches',[]) if isinstance(a,dict) else []
  rec['page_matches']=len(matches);rec['full']=0;rec['matched']=0;rec['mismatch']=0;rec['nonzero']={k:0 for k in fields}
  for x in matches:
   if x.get('status')!='full':continue
   rec['full']+=1;fid=str(x['id']);r=rows.get(fid)
   if not r:continue
   # Verify exact UTC kickoff date against matched historical inventory; API account uses Asia/Shanghai.
   from zoneinfo import ZoneInfo
   k=datetime.datetime.fromisoformat(x['start']).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
   if str(x['l_id'])!=lid or r['league']!=lid or str(x['h_id'])!=r['home_id'] or str(x['a_id'])!=r['away_id'] or (int(x['hg']),int(x['ag']))!=(r['hg'],r['ag']) or k.date().isoformat()!=r['date']:
    rec['mismatch']+=1;continue
   rec['matched']+=1
   record={'fid':fid,'league':lid,'date':r['date'],'kickoff_utc':k.isoformat(),'home':r['home_id'],'away':r['away_id'],'hg':r['hg'],'ag':r['ag'],'received_utc':rec['received_utc'],'raw_sha256':sha}
   for field in fields:
    v=x.get(field);record[field]=list(map(float,v)) if pair(v) else None
    if pair(v) and sum(map(float,v))>0:rec['nonzero'][field]+=1
   matched[fid]=record
 except Exception as e:rec['error']=type(e).__name__
 result.append(rec);print('PAGE',rec,flush=True)
 time.sleep(4)
out={'probe':'one page per six leagues with largest 2026 T12 archive counts, page 5; descriptive coverage sample, not representative','pages':result,'unique_matched':len(matched),'fields_nonzero':{k:sum(r[k] is not None and sum(r[k])>0 for r in matched.values()) for k in fields}}
(P/'m8_performance_batch_probe_20261115.json').write_text(json.dumps(out,indent=2))
(P/'m8_performance_batch_probe_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in matched.values()))
print('SUMMARY',out['unique_matched'],out['fields_nonzero'],flush=True)
