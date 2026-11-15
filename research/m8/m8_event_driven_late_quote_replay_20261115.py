import json,collections,datetime,math,bisect,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
exec((P/'m8_extra_inventory_frozen_eight_20261115.py').read_text().split("print('INVENTORIES'")[0])
# P now root, R research-work; sources contains 7367 unique prior uncovered ids
gap={x['fid']:x['reason'] for x in map(json.loads,(R/'m8_missing_cutoff_archive_audit_20261115.jsonl').open()) if x['reason'] in ('first_quote_T6_to_T1','first_quote_after_T1')}
assert len(gap)==544
known_rows={r['fid']:r for r in map(json.loads,(R/'m8_late_full_path_water_features_20261114.jsonl').open())}
extra_rows={r['fid']:r for r in map(json.loads,(R/'m8_extra_inventory_frozen_eight_20261115.jsonl').open())}
known_rows.update(extra_rows);assert len(known_rows)==44943
# Source inventory for 2026 control; same as prior research.
m5={str(r['match_id']):r.get('response_sha256') for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
jobs=[(fid,sources[fid][1],sources[fid][2],sources[fid][3],gap[fid]) for fid in gap]
for fid,r in known_rows.items():
 if r['year']!=2026:continue
 if fid in extra_rows:
  q=sources[fid];jobs.append((fid,q[1],q[2],q[3],'control_2026'))
 else:jobs.append((fid,str(r['league']),P/f'data/m5-crown-authorized/crown-responses/{fid}.json',m5.get(fid),'control_2026'))
def dt(v):return datetime.datetime.fromisoformat(str(v).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def fside(line):return 'home' if line<0 else 'away' if line>0 else None
def opp(s):return 'away' if s=='home' else 'home'
def deep(a,b):return (b-a)*b>0
OUT=[];C=collections.Counter()
for fid,lid,file,sha,cohort in jobs:
 try:
  raw=file.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('hash mismatch')
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==fid)
  assert str(x['l_id'])==lid and x['status']=='full'
  ko=dt(x['start']);h,a=int(x['hg']),int(x['ag'])
  b=next(q for q in x['bookmakers'] if q.get('slug')=='crown')
  path=[]
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l,ph,pa=map(float,q[1:4])
    if t<ko and ph>1 and pa>1 and all(math.isfinite(z) for z in (l,ph,pa)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,ph,pa))
   except:continue
  path.sort(key=lambda q:q[0]);ts=[q[0] for q in path]
  t6=ko-datetime.timedelta(hours=6);t1=ko-datetime.timedelta(hours=1)
  if cohort=='control_2026':
   i=bisect.bisect_right(ts,t6)-1;j=bisect.bisect_right(ts,t1)-1
   assert i>=0 and j>=i
   seq=path[i:j+1]
  elif cohort=='first_quote_T6_to_T1':
   assert t6<ts[0]<=t1
   seq=path[:bisect.bisect_right(ts,t1)]
  else:
   assert t1<ts[0]<ko
   seq=path
  start=seq[0];end=seq[-1]
  r={'fid':fid,'league':lid,'year':ko.year,'month':ko.strftime('%Y-%m'),'date':ko.date().isoformat(),'population':cohort,'n_quotes':len(seq),'first_hours':(ko-start[0]).total_seconds()/3600,'start_line':start[1],'end_line':end[1],'events':{}}
  def record(name,q,side):
   if side is None:return
   r['events'][name]={'side':side,'hours_to_kickoff':(ko-q[0]).total_seconds()/3600,'line':q[1],'U':settle_score('AH',q[1],side,h,a,q[2] if side=='home' else q[3])[1]}
  # First available anchor, all reference sides; zero line has home/away but no favorite.
  record('anchor_home',start,'home');record('anchor_away',start,'away')
  if fside(start[1]):
   record('anchor_fav',start,fside(start[1]));record('anchor_dog',start,opp(fside(start[1])))
  changed=False;first_excursion_side=None
  for prev,q in zip(seq,seq[1:]):
   if prev[1]!=q[1]:
    if not changed:
     side=fside(q[1])
     if side:
      record('first_change_fav',q,side);record('first_change_dog',q,opp(side))
     direct='home' if q[1]<prev[1] else 'away'
     record('first_change_follow',q,direct);record('first_change_reverse',q,opp(direct))
     first_excursion_side=direct
    changed=True
    if deep(start[1],q[1]) and 'first_anchor_deepen_dog' not in r['events']:
     side=fside(q[1]);record('first_anchor_deepen_dog',q,opp(side));record('first_anchor_deepen_fav',q,side)
    if q[1]==start[1] and 'first_return_follow_excursion' not in r['events']:
     record('first_return_follow_excursion',q,first_excursion_side);record('first_return_reverse_excursion',q,opp(first_excursion_side))
  if cohort!='first_quote_after_T1':
   if deep(start[1],end[1]):
    record('T1_net_deepen_dog',end,opp(fside(end[1])));record('T1_net_deepen_fav',end,fside(end[1]))
   if (end[1]-start[1])*end[1]<0:
    record('T1_net_weaken_dog',end,opp(fside(end[1])));record('T1_net_weaken_fav',end,fside(end[1]))
  r['changed']=changed;OUT.append(r);C[cohort]+=1
 except Exception as e:
  C['error_'+type(e).__name__]+=1
  if C['error_'+type(e).__name__]<=3:print('ERROR',fid,repr(e),flush=True)
def stat(rs,event):
 v=[r['events'][event]['U'] for r in rs if event in r['events']];n=len(v);u=sum(v)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
out={'counts':dict(C),'jobs':len(jobs),'groups':{}}
for cohort in ('first_quote_T6_to_T1','first_quote_after_T1','control_2026'):
 z=[r for r in OUT if r['population']==cohort];ev=sorted({k for r in z for k in r['events']})
 out['groups'][cohort]={'years':dict(collections.Counter(r['year'] for r in z)),'changed':sum(r['changed'] for r in z),'events':{}}
 for k in ev:
  t={'all':stat(z,k)}|{e:stat([r for r in z if era(r)==e],k) for e in ('2019-23','2024-25','2026')}
  out['groups'][cohort]['events'][k]=t
 print('POP',cohort,len(z),'changed',sum(r['changed'] for r in z),'years',out['groups'][cohort]['years'],flush=True)
 for k,t in out['groups'][cohort]['events'].items():print(k,t,flush=True)
(R/'m8_event_driven_late_quote_replay_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_event_driven_late_quote_replay_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in OUT))
print('DONE',C,flush=True)
