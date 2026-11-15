import json,datetime,collections,hashlib,time
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
import os
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
source=R/'m8_new_receipt_frozen_eight_20261115.jsonl'
rows=list(map(json.loads,source.open()));signals={r['fid']:r for r in rows if r['cohort']}
assert len(rows)==306 and len(signals)==50
before=hashlib.sha256(source.read_bytes()).hexdigest()
now=datetime.datetime.now(datetime.timezone.utc)
def dt(s):
 x=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return x.astimezone(datetime.timezone.utc) if x.tzinfo else x.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def norm(s):return ' '.join(str(s or '').casefold().split())
quality=collections.Counter()
def verify(row,x,observed):
 assert str(x['id'])==row['fid'] and str(x['l_id'])==row['league']
 assert dt(x['start'])==dt(row['kickoff_utc']) and x['status']=='full'
 assert norm(x['h'])==norm(row['home']) and norm(x['a'])==norm(row['away'])
 assert dt(row['kickoff_utc'])<observed<=datetime.datetime.now(datetime.timezone.utc)
 h,a=int(x['hg']),int(x['ag']);assert h>=0 and a>=0
 return h,a
def settle(row,x,observed,sha,tag):
 h,a=verify(row,x,observed)
 row['score']=f'{h}-{a}';row['pnl']=settle_score('AH',row['line'],row['side'],h,a,row['odds'])[1]
 row['FT_observed_utc']=observed.isoformat();row['FT_raw_sha256']=sha;row['FT_source']=tag
for e in map(json.loads,(R/'m7/m7_schedule_verified_FT_receipt_events_20261111.jsonl').open()):
 row=signals.get(str(e['fixture_id']))
 if not row or row['pnl'] is not None:continue
 try:
  raw=Path(e['raw_path']).read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==e['raw_sha256']
  body=json.loads(raw);x=next(x for x in body['data']['matches'] if str(x['id'])==row['fid'])
  assert int(x['hg'])==int(e['home_goals']) and int(x['ag'])==int(e['away_goals'])
  settle(row,x,dt(e['observed_at_utc']),sha,'verified_M7_schedule_FT_raw_20261111')
  quality['verified_archived_FT']+=1
 except Exception as ex:quality['archived_FT_error_'+type(ex).__name__]+=1
pending=[r for r in signals.values() if r['pnl'] is None]
print('ARCHIVED',dict(quality),'pending',len(pending),flush=True)
# Existing authorized score-only endpoint; do not print secrets, odds or URLs including the token.
dest=R/'m8_new_receipt_FT_raw_20261115';dest.mkdir(exist_ok=True)
attempts=[]
# 48 archived score records expected; if more are unavailable, don't assume they are new query targets.
for row in pending:
 if row['fid'] not in ('203961660','203961688'):continue
 try:
  token=os.environ['TOTALCORNER_TOKEN'].strip()
  response=requests.get('https://api.totalcorner.com/v1/match/view/'+row['fid'],params={'token':token},headers={'Accept':'application/json','User-Agent':'M8-FT-Evidence/1.0'},timeout=10)
  observed=datetime.datetime.now(datetime.timezone.utc);raw=response.content;sha=hashlib.sha256(raw).hexdigest()
  path=dest/f"{row['fid']}-{sha}.json";path.write_bytes(raw)
  e={'fid':row['fid'],'http_status':response.status_code,'sha256':sha,'observed_at_utc':observed.isoformat()}
  attempts.append(e)
  if response.status_code!=200:e['status']='unavailable';continue
  b=json.loads(raw)
  if not b.get('success') or not b.get('data'):e['status']='provider_error';continue
  x=next(x for x in b['data'] if str(x['id'])==row['fid']);e['provider_status']=x.get('status')
  if x.get('status')!='full':e['status']='not_FT';continue
  settle(row,x,observed,sha,'TotalCorner_match_view_FT_only')
  e['status']='verified_FT';quality['verified_new_FT']+=1
 except Exception as ex:
  quality['new_FT_error_'+type(ex).__name__]+=1
 time.sleep(2.6)
def stat(z):
 a=[r for r in z if r['pnl'] is not None];u=sum(r['pnl'] for r in a)
 return {'signals':len(z),'settled':len(a),'unsettled':len(z)-len(a),'net_U':round(u,3),'ROI':round(100*u/len(a),3) if a else None,'win':sum(r['pnl']>0 for r in a),'lose':sum(r['pnl']<0 for r in a),'push':sum(r['pnl']==0 for r in a)}
out={'source_pre_result_SHA256':before,'asof_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'quality':dict(quality),'score_attempts':attempts,'all':stat(list(signals.values())),'cohorts':{c:stat([r for r in signals.values() if r['cohort']==c]) for c in ('base','A','B','C','D','E','F','G')},'pending':[r['fid'] for r in signals.values() if r['pnl'] is None]}
(R/'m8_new_receipt_frozen_eight_FT_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_new_receipt_frozen_eight_FT_20261115.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
print('RESULT',json.dumps(out,ensure_ascii=False),flush=True)
