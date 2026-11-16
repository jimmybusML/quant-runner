import json,collections,datetime,hashlib,math,bisect,sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
s=(R/'m8_frozen_eight_earlier_window_replay_20261116.py').read_text()
exec(s[:s.index('windows=[')])
exec(s[s.index('def stat(a):'):s.index('fset=')])
exec(s[s.index('def run(f,old,ko,path,times,h,a,w):'):s.index('for n,(f,old) in enumerate(univ.items()):')])
scope={str(r['league']) for r in univ.values()};assert len(scope)==49
def dt(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
lo=datetime.date(2019,1,1);hi=datetime.date(2026,11,4)
# Freeze historical horizon to latest existing path archive date. Post-cutoff
# fixtures only counted separately, not added to existing backtest.
sched=collections.defaultdict(set);sched_latest=collections.defaultdict(set);quality=collections.Counter()
root=P/'data/m5-crown-authorized/schedules'
for l in sorted(scope):
 for p in sorted((root/l).glob('page-*.raw.json')):
  try:
   b=json.loads(p.read_bytes());quality['schedule_pages']+=1
   for q in b['data']['matches']:
    if str(q.get('l_id'))!=l:continue
    if q.get('status')!='full':continue
    f=str(q.get('id') or '');t=dt(q['start']);h=str(q.get('h_id') or '');a=str(q.get('a_id') or '')
    if not(f and h and a and h!=a):quality['invalid_schedule_identity']+=1;continue
    row=(l,t,h,a,int(q['hg']),int(q['ag']))
    if lo<=t.date()<=hi:sched[f].add(row)
    elif t.date()>hi:sched_latest[f].add(row)
  except Exception as e:quality['schedule_error_'+type(e).__name__]+=1
conflicts={f for f,v in sched.items() if len(v)!=1}
sched={f:next(iter(v)) for f,v in sched.items() if len(v)==1}
known=set(univ);miss=set(sched)-known
alln=len(sched|{f:None for f in known});qc=collections.Counter()
print('SCHEDULE',len(sched),len(conflicts),'known_in_schedule',len(known&set(sched)),'known_outside_schedule',len(known-set(sched)),'unique_union',alln,'unknown_schedule',len(miss),'later_FT',len(sched_latest),flush=True)
# Analyze all candidate capture layers using exact hash-proven source, including
# directly indexed responses not present in the read-only SQLite capture table.
cx=sqlite3.connect(f'file:{P}/data/crown_quote_store/crown_quotes.sqlite3?mode=ro',uri=True)
caps=collections.defaultdict(list);latest=cx.execute('select max(processed_at_utc) from capture').fetchone()[0]
for fid,src,sha,layer in cx.execute("select fixture_id,source_file,response_sha256,data_layer from capture where capture_mode='historical' and data_layer in ('movement','summary') order by processed_at_utc desc,capture_key desc"):
 if fid in miss:caps[fid].append((src,sha,layer))
cx.close()
direct=0
for q in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open()):
 f=str(q['match_id'])
 if f in miss and q.get('response_sha256'):
  rec=(str(P/f'data/m5-crown-authorized/crown-responses/{f}.json'),q['response_sha256'],'direct_index')
  if not any((z[0],z[1])==rec[:2] for z in caps[f]):caps[f].append(rec);direct+=1
print('CAPTURES',len(caps),sum(len(v) for v in caps.values()),'direct_additions',direct,'db_asof',latest,flush=True)
# Frozen G score history: reconstruct exact prior score-only prediction for
# newly recovered fixtures without training on any newly recovered outcomes.
sc=(R/'m8_raw_capture_unindexed_frozen_replay_20261115.py').read_text()
exec(sc[sc.index('scorelist=list('):sc.index('\nq=0\n')])
# Store source-backed no-signal/missing categories, all years and leagues.
candidates=[];details=[];byyear=collections.defaultdict(collections.Counter);byleague=collections.defaultdict(collections.Counter)
for f in sorted(miss):
 l,ko,hid,aid,hg,ag=sched[f];rs=collections.Counter();found=None
 for path,sha,layer in caps.get(f,[]):
  try:
   raw=Path(path).read_bytes()
   if hashlib.sha256(raw).hexdigest()!=sha:rs['hash_mismatch']+=1;continue
   x=next((q for q in json.loads(raw).get('data',[]) if str(q.get('id'))==f),None)
   if not x or str(x.get('l_id'))!=l or x.get('status')!='full':rs['identity_or_FT_mismatch']+=1;continue
   if (dt(x['start']),str(x.get('h_id') or ''),str(x.get('a_id') or ''),int(x['hg']),int(x['ag']))!=(ko,hid,aid,hg,ag):rs['schedule_identity_or_result_mismatch']+=1;continue
   b=next((q for q in x.get('bookmakers',[]) if q.get('slug')=='crown'),None)
   if not b:rs['no_crown']+=1;continue
   quotes=[]
   for q in b.get('asian_list') or []:
    try:
     t=dt(q[4]);line,ph,pa=map(float,q[1:4])
     if t<ko and min(ph,pa)>1 and all(math.isfinite(z) for z in (line,ph,pa)) and abs(line*4-round(line*4))<1e-7:quotes.append((t,line,ph,pa))
    except Exception:pass
   if not quotes:rs['no_valid_pregame_list']+=1;continue
   quotes.sort(key=lambda q:q[0])
   if quotes[0][0]>ko-datetime.timedelta(hours=6):rs['first_quote_after_T6']+=1;continue
   found=(f,dict(fid=f,year=ko.year,date=ko.date().isoformat(),league=l,home=hid,away=aid),ko,quotes,hg,ag,sha)
   break
  except Exception as ex:rs['error_'+type(ex).__name__]+=1
 if found:
  candidates.append(found);why='recovered_path'
 elif not caps.get(f):why='no_indexed_capture'
 else:why=next((k for k in ('first_quote_after_T6','no_valid_pregame_list','no_crown','schedule_identity_or_result_mismatch','identity_or_FT_mismatch','hash_mismatch') if rs[k]),'source_read_error')
 qc[why]+=1;byyear[str(ko.year)][why]+=1;byleague[l][why]+=1
 details.append(dict(fid=f,year=ko.year,league=l,reason=why,source_attempts=dict(rs)))
 if len(details)%10000==0:print('AUDIT',len(details),dict(qc),flush=True)
# Identical classifier as R31; no shadow or production changes.
q=0;w=(6,3,1);data={w:[]};coverage={w:collections.Counter()}
for f,r,ko,path,h,a,sha in sorted(candidates,key=lambda x:(x[1]['date'],x[0])):
 day=ko.date()
 while q<len(scorelist) and (day-datetime.date.fromisoformat(scorelist[q]['date'])).days>=2:
  update(scorelist[q]);q+=1
 if f in scoremap:
  sc0=scoremap[f];S[f]=(sc0['lambda_home_0.025'],sc0['lambda_away_0.025'])
 else:S[f]=predict(r)
 run(f,r,ko,path,[x[0] for x in path],h,a,w)
new=data[w];assert len({r['fid'] for r in new})==len(new) and not ({r['fid'] for r in new}&known)
for f,l in univ.items():
 reason='original_eight_signal' if f in ids else 'original_eight_no_signal'
 byyear[str(l['year'])][reason]+=1;byleague[str(l['league'])][reason]+=1
assert sum(qc.values())==len(miss)
out={'method':'R36 current cached FT schedule census, original49, UTC2019-01-01 through existing historical path end 2026-11-04 inclusive; union known original path IDs retained even when absent from cached schedule. Exact schedule/raw FT identity and SHA, original frozen T6/T3/T1 classifier, frozen score-only history for G. No new provider requests, no assumption absent quote means no opportunity. Capture universe only historical SQLite movement/summary and direct indexed Crown files; not complete universe of all possible quotes.','foundation':foundation,'schedule':{'FT_exact_ids':len(sched),'conflicting_schedule_ids':len(conflicts),'known_matched':len(known&set(sched)),'known_outside_schedule':len(known-set(sched)),'union':alln,'uncovered':len(miss),'cached_later_FT_ids':len(sched_latest),'quality':dict(quality)},'capture_db_asof':latest,'candidate_capture_ids':len(caps),'candidate_capture_rows':sum(map(len,caps.values())),'direct_index_additions':direct,'uncovered_reasons':dict(qc),'year':{y:dict(v) for y,v in sorted(byyear.items())},'league':{l:dict(v) for l,v in sorted(byleague.items())},'recovered_path_n':len(candidates),'recovered_orders':new,'recovered_no_signal':len(candidates)-len(new),'new_orders':desc(new),'combined':desc(frozen+new),'groups':{g:desc([r for r in new if r['cohort']==g]) for g in ('base','A','B','C','D','E','F','G')}}
(R/'m8_frozen_eight_coverage_audit_20261117.json').write_text(json.dumps(out,indent=2))
(R/'m8_frozen_eight_coverage_audit_20261117.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in details))
print('RESULT',json.dumps({k:v for k,v in out.items() if k not in ('year','league','recovered_orders','groups')},ensure_ascii=False),flush=True)
print('YEAR2026',out['year'].get('2026'),flush=True)
# Separate actual-receipt cross-check for uncovered historical fixtures.
# Do not add its signals to the historical total, or claim actual placement.
B=P/'repos/mr1/data/prospective-market/shadow-v23'
remain=miss-{x[0] for x in candidates}
indexes=collections.defaultdict(list)
for ix in map(json.loads,(B/'snapshot-index.jsonl').open()):
 if ix['match_id'] in remain:indexes[ix['match_id']].append(ix)
rtqc=collections.Counter();rr=[]
exec(sc[sc.index('scorelist=list('):sc.index('\nq=0\n')])
q=0;data={w:[]};coverage={w:collections.Counter()}
for f,ixs in sorted(indexes.items(),key=lambda z:(sched[z[0]][1],z[0])):
 l,ko,hid,aid,hg,ag=sched[f]
 t1=ko-datetime.timedelta(hours=1);t6=ko-datetime.timedelta(hours=6)
 valid=[]
 for ix in ixs:
  if ix['classification']!='SNAPSHOT_OK':continue
  try:
   b=(B/ix['snapshot_path']).read_bytes()
   assert hashlib.sha256(b).hexdigest()==ix['snapshot_sha256']
   sn=json.loads(b);recv=dt(sn['received_at'])
   if dt(sn['kickoff_at'])!=ko or not (recv<=dt(ix['committed_at'])<=t1):continue
   for ap in sorted((B/'snapshots'/f/sn['target_horizon']/'odds').glob('attempt-*.json')):
    a=json.loads(ap.read_bytes());raw=a.get('raw_response','')
    if a.get('classification')!='SNAPSHOT_OK' or not raw or hashlib.sha256(raw.encode()).hexdigest()!=a.get('raw_sha256'):continue
    if abs((dt(a['received_at'])-recv).total_seconds())>.005:continue
    x=next((z for z in json.loads(raw).get('data',[]) if str(z.get('id'))==f),None)
    if not x or (str(x['l_id']),dt(x['start']),str(x.get('h_id')),str(x.get('a_id')))!=(l,ko,hid,aid):continue
    bk=next((z for z in x.get('bookmakers',[]) if z.get('slug')=='crown'),None)
    if not bk:continue
    path=[]
    for z in bk.get('asian_list') or []:
     try:
      t=dt(z[4]);ln,ph,pa=map(float,z[1:4])
      if t<=recv and t<ko and min(ph,pa)>1 and all(math.isfinite(v) for v in (ln,ph,pa)) and abs(ln*4-round(ln*4))<1e-7:path.append((t,ln,ph,pa))
     except Exception:continue
    path.sort(key=lambda z:z[0])
    if path and path[0][0]<=t6:valid.append((recv,path,a['raw_sha256'],ix['snapshot_sha256']))
  except Exception as ex:rtqc['error_'+type(ex).__name__]+=1
 if not valid:rtqc['no_verified_path']+=1;continue
 recv,path,rsha,ssha=max(valid,key=lambda z:z[0]);r=dict(fid=f,year=ko.year,date=ko.date().isoformat(),league=l,home=hid,away=aid)
 while q<len(scorelist) and (ko.date()-datetime.date.fromisoformat(scorelist[q]['date'])).days>=2:update(scorelist[q]);q+=1
 if f in scoremap:
  s0=scoremap[f];S[f]=(s0['lambda_home_0.025'],s0['lambda_away_0.025'])
 else:S[f]=predict(r)
 n=len(data[w]);run(f,r,ko,path,[z[0] for z in path],hg,ag,w)
 order=data[w][-1] if len(data[w])>n else None
 rtqc['verified_path']+=1
 rr.append({'fid':f,'receipt_utc':recv.isoformat(),'raw_sha256':rsha,'snapshot_sha256':ssha,'latest_event_utc':path[-1][0].isoformat(),'original_group':order['cohort'] if order else None,'order':order,'result_source':'separate cached FT schedule with exact fixture/UTC/team identity; retrospective'})
assert len({r['fid'] for r in data[w]})==len(data[w]) and not ({r['fid'] for r in data[w]}&known)
out['separate_actual_receipt_recovery']={'indexed_ids':len(indexes),'quality':dict(rtqc),'matched':len(rr),'signals':desc(data[w]),'no_signal':len(rr)-len(data[w]),'evidence':rr}
(R/'m8_frozen_eight_coverage_audit_20261117.json').write_text(json.dumps(out,indent=2))
print('ACTUAL_RECEIPT_RECOVERY',json.dumps({k:v for k,v in out['separate_actual_receipt_recovery'].items() if k!='evidence'},ensure_ascii=False),flush=True)
