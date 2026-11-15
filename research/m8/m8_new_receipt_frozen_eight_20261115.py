import json,datetime,math,bisect,collections,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work';B=P/'repos/mr1/data/prospective-market/shadow-v23'
now=datetime.datetime.now(datetime.timezone.utc)
def dt(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
known={r['fid'] for f in ('m8_late_full_path_water_features_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl') for r in map(json.loads,(R/f).open())}
scope={r['league'] for r in map(json.loads,(R/'m8_late_full_path_water_features_20261114.jsonl').open())}
assert len(known)==44956 and len(scope)==49
fixtures=json.load((B/'fixtures.json').open());C=collections.Counter();groups=collections.defaultdict(list)
# New match IDs only; select latest actual verified snapshot received before that fixture's T1.
for ix in map(json.loads,(B/'snapshot-index.jsonl').open()):
 if ix['committed_at']<'2026-11-06':continue
 fid=ix['match_id'];f=fixtures.get(fid)
 if not f or str(f['league_id']) not in scope or fid in known:continue
 k=dt(f['kickoff_at'])
 if k<dt('2026-11-06T00:00:00Z'):continue
 groups[fid].append(ix)
print('NEW_FIXTURES',len(groups),flush=True)
def sg(x):return 1 if x>1e-9 else -1 if x<-1e-9 else 0
def opp(s):return 'home' if s=='away' else 'away'
# Reuse previous frozen score model's implementation, with original score-only history and no new match outcomes.
src=(R/'m8_extra_inventory_frozen_eight_20261115.py').read_text()
exec(src[src.index('scorelist=list('):src.index('\nq=0\n')])
exec(src[src.index('K=40'):src.index('selected=[]')])
q=0
def calc_rates(z):
 global q
 date=datetime.date.fromisoformat(z['date'])
 while q<len(scorelist) and (date-datetime.date.fromisoformat(scorelist[q]['date'])).days>=2:
  update(scorelist[q]);q+=1
 if z['home'] and z['away']:return list(predict(z))
 return None
scores=P/'repos/mr1/data/strategy-shadow-ledger/results'
out=[]
for fid,ixs in sorted(groups.items(),key=lambda item:fixtures[item[0]]['kickoff_at']):
 f=fixtures[fid];k=dt(f['kickoff_at']);t6=k-datetime.timedelta(hours=6);t3=k-datetime.timedelta(hours=3);t1=k-datetime.timedelta(hours=1)
 if t1>now:C['T1_not_reached']+=1;continue
 valid=[]
 for ix in ixs:
  if ix['classification']!='SNAPSHOT_OK':continue
  try:
   source=(B/ix['snapshot_path']).read_bytes()
   if hashlib.sha256(source).hexdigest()!=ix['snapshot_sha256']:C['snapshot_sha_error']+=1;continue
   s=json.loads(source)
   if dt(s['kickoff_at'])!=k:C['kickoff_mismatch_snapshots']+=1;continue
   recv=dt(s['received_at'])
   if recv>t1 or dt(ix['committed_at'])>t1:continue
   for ap in sorted((B/'snapshots'/fid/s['target_horizon']/'odds').glob('attempt-*.json'),reverse=True):
    a=json.load(ap.open());raw=a.get('raw_response','')
    if a.get('classification')!='SNAPSHOT_OK' or not raw or hashlib.sha256(raw.encode()).hexdigest()!=a.get('raw_sha256'):continue
    if abs((dt(a['received_at'])-recv).total_seconds())>.005:continue
    x=next((z for z in json.loads(raw).get('data',[]) if str(z.get('id'))==fid),None)
    if not x or dt(x['start'])!=k or str(x['l_id'])!=str(f['league_id']):continue
    b=next((z for z in x.get('bookmakers',[]) if z.get('slug')=='crown'),None)
    if not b:continue
    path=[]
    for quote in b.get('asian_list') or []:
     try:
      t=dt(quote[4]);l,h,a1=map(float,quote[1:4])
      if t<=recv and t<k and h>1 and a1>1 and all(math.isfinite(v) for v in (l,h,a1)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,h,a1))
     except:continue
    path.sort(key=lambda v:v[0])
    if not path or path[0][0]>t6:continue
    valid.append((recv,path,x,a['raw_sha256'],ix['snapshot_sha256']))
    break
  except Exception as e:C['error_'+type(e).__name__]+=1
 if not valid:C['missing_asof_T1_complete_AH_path']+=1;continue
 recv,path,x,rawsha,snapsha=max(valid,key=lambda q:q[0]);ts=[v[0] for v in path];i=bisect.bisect_right(ts,t6)-1;j=bisect.bisect_right(ts,t1)-1;mid=path[bisect.bisect_right(ts,t3)-1]
 start,end=path[i],path[j];seq=path[i:j+1];steps=[(u,v) for u,v in zip(seq,seq[1:]) if u[1]!=v[1]]
 shape='never_changed' if not steps else 'reverted' if start[1]==end[1] else 'one_way' if all((v[1]-u[1])*(end[1]-start[1])>0 for u,v in steps) else 'oscillating'
 g=side=None;l=end[1];dog='home' if l>0 else 'away';fav=opp(dog)
 def state(a,b):return 'deepen' if (b-a)*l>0 else 'weaken' if (b-a)*l<0 else 'same'
 if (l-start[1])*l>0:g='base';side=dog
 elif l and state(start[1],mid[1])+'_'+state(mid[1],l)=='deepen_weaken':g='A';side=dog
 elif l and state(start[1],mid[1])+'_'+state(mid[1],l)=='weaken_same':g='B';side=dog
 elif l and shape=='oscillating':g='C';side=fav
 elif not l and shape=='reverted':
  durations=0.;hp=ap=0.
  for n,v in enumerate(seq):
   if v[1]!=l:continue
   dur=max(0.,((seq[n+1][0] if n+1<len(seq) else t1)-max(v[0],t6)).total_seconds());durations+=dur;hp+=dur*v[2];ap+=dur*v[3]
  if durations and end[2]-hp/durations-(end[3]-ap/durations)<-1e-9:g='D';side='away'
 elif not l and shape=='never_changed':
  vals=[v[3]/(v[2]+v[3]) for v in seq];p0=vals[0];p1=vals[-1];p3=mid[3]/(mid[2]+mid[3]);moves=[b-a for a,b in zip(vals,vals[1:]) if abs(b-a)>1e-10]
  a,b=sg(p3-p0),sg(p1-p3);net=sg(p1-p0);s=net or a or b or (sg(moves[-1]) if moves else 0)
  if s and moves:
   up=any(v>0 for v in moves);down=any(v<0 for v in moves)
   if up and down and not net:g='E';side='away' if s>0 else 'home'
   elif (not up or not down) and a==0 and b*s==1:g='F';side='home' if s>0 else 'away'
 if g is None and shape=='reverted':
  z={'date':k.date().isoformat(),'league':str(x['l_id']),'home':str(x.get('h_id') or ''),'away':str(x.get('a_id') or '')}
  rates=calc_rates(z)
  if rates:
   market=sg(end[3]/(end[2]+end[3])-start[3]/(start[2]+start[3]))
   eh,ea=expect({'score_rates':rates,'end_line':l,'home_price':end[2],'away_price':end[3]});model=sg(eh-ea) or 1
   if market and market==model:g='G';side='away' if model>0 else 'home'
  else:C['G_no_team_ID']+=1
 r={'fid':fid,'kickoff_utc':k.isoformat(),'league':str(f['league_id']),'cohort':g,'side':side,'home':f['home'],'away':f['away'],'line':l,'odds':end[2] if side=='home' else end[3] if side else None,'receipt_utc':recv.isoformat(),'source_event_utc':end[0].isoformat(),'raw_sha256':rawsha,'snapshot_sha256':snapsha,'evaluation_type':'locked_before_kickoff' if k>now else 'retrospective_from_pregame_receipt','lock_utc':now.isoformat(),'pnl':None,'score':None}
 # Result joined only after signal computed. Exact fixture and kickoff, source FT and observation earlier than run.
 if g and k<=now and (scores/f'{fid}.json').exists():
  result=json.load((scores/f'{fid}.json').open())
  if result.get('status')=='FT' and str(result.get('match_id'))==fid and dt(result['kickoff_at'])==k and k<dt(result['observed_at'])<=now:
   h,a=int(result['home_goals']),int(result['away_goals']);r['score']=f'{h}-{a}';r['pnl']=settle_score('AH',l,side,h,a,r['odds'])[1]
 out.append(r)
def stats(z):
 s=[r for r in z if r['cohort']];a=[r for r in s if r['pnl'] is not None];u=sum(r['pnl'] for r in a)
 return {'eligible':len(z),'signals':len(s),'settled':len(a),'unsettled':len(s)-len(a),'net_U':round(u,3),'ROI':round(100*u/len(a),3) if a else None}
res={'asof_utc':now.isoformat(),'new_candidate_fixtures':len(groups),'counts':dict(C),'by_type':{},'by_cohort':{},'all':stats(out)}
for typ in ('retrospective_from_pregame_receipt','locked_before_kickoff'):
 z=[r for r in out if r['evaluation_type']==typ];res['by_type'][typ]=stats(z);res['by_cohort'][typ]={g:stats([r for r in z if r['cohort']==g]) for g in ('base','A','B','C','D','E','F','G')}
print('RESULT',json.dumps(res,ensure_ascii=False),flush=True)
(R/'m8_new_receipt_frozen_eight_20261115.json').write_text(json.dumps(res,ensure_ascii=False,indent=2))
(R/'m8_new_receipt_frozen_eight_20261115.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in out))
