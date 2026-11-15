import json,math,datetime,collections,bisect,hashlib,statistics
from pathlib import Path
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
def dt(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
known={r['fid']:r for r in map(json.loads,(R/'m8_late_full_path_water_features_20261114.jsonl').open())};assert len(known)==39101
jobs={}
for r in map(json.loads,(R/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl').open()):
 f=str(r['fixture_id'])
 if f in known and known[f]['year']<2026:jobs[f]=(Path(r['source_file']),None,known[f]['league'])
idx={str(r['match_id']):r['response_sha256'] for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
for f,r in known.items():
 if r['year']==2026:jobs[f]=(P/f'data/m5-crown-authorized/crown-responses/{f}.json',idx.get(f),r['league'])
for name in ('m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 for r in map(json.loads,(R/name).open()):
  f=r['fid'];jobs[f]=(Path(r['source_file']),idx.get(f) if 'm5-crown-authorized/crown-responses' in r['source_file'] else None,r['league'])
assert len(jobs)==44956,len(jobs)
C=collections.Counter();rows=[]
def outcome_ev(l,p,od):
 # Exact AH settlement for W/D/L at |line|<=.5, half stakes for quarter line.
 w,d,a=p
 if l==-.5:win,loss=w,d+a
 elif l==-.25:win,loss=w,a+d/2
 elif l==0:win,loss=w,a
 elif l==.25:win,loss=w+d/2,a
 elif l==.5:win,loss=w+d,a
 else:raise ValueError(l)
 return win*(od-1)-loss
for f,(file,sha,league) in jobs.items():
 try:
  raw=file.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:C['SHA_error']+=1;continue
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  if str(x['l_id'])!=str(league) or x['status']!='full':C['identity_or_FT']+=1;continue
  k=dt(x['start']);h,a=int(x['hg']),int(x['ag']);b=next(q for q in x['bookmakers'] if q.get('slug')=='crown')
  path=[]
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l,ph,pa=map(float,q[1:4])
    if t<k and ph>1 and pa>1 and all(math.isfinite(v) for v in (l,ph,pa)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,ph,pa))
   except:continue
  path.sort(key=lambda x:x[0]);ts=[q[0] for q in path]
  quotes=[]
  for tag,q in (b.get('odds') or {}).items():
   if tag not in ('open','close') or not isinstance(q,dict):continue
   try:
    t=dt(q['time']);o=[float(q[s]) for s in ('home','draw','away')]
    if t<k and all(math.isfinite(v) and v>1 for v in o):quotes.append((t,o,tag))
   except:continue
  # Use only documented timestamped dictionary fields; don't assume list layout.
  for hours in (24,12,6):
   cut=k-datetime.timedelta(hours=hours);i=bisect.bisect_right(ts,cut)-1
   label=f'{k.year}|T{hours}'
   if i<0:continue
   C[label+'|AH']+=1
   q=path[i];l=q[1]
   if abs(l)>.5:continue
   C[label+'|exact_AH']+=1
   valid=[v for v in quotes if v[0]<=cut]
   if not valid:continue
   t,o,tag=max(valid,key=lambda v:v[0])
   p=[1/v for v in o];s=sum(p);p=[v/s for v in p]
   eh=outcome_ev(l,p,q[2]);ea=outcome_ev(-l,p[::-1],q[3])
   dh=settle_score('AH',l,'home',h,a,q[2])[1];da=settle_score('AH',l,'away',h,a,q[3])[1]
   rows.append({'fid':f,'year':k.year,'date':k.date().isoformat(),'league':league,'T':hours,'line':l,'home_price':q[2],'away_price':q[3],'eh':eh,'ea':ea,'home_U':dh,'away_U':da,'age_1x2_h':(cut-t).total_seconds()/3600,'age_AH_h':(cut-q[0]).total_seconds()/3600,'source':tag})
  C['read_ok']+=1
 except Exception as e:C['error_'+type(e).__name__]+=1
def stat(z,key='choice'):
 v=[r['home_U'] if (r['eh']>=r['ea'])==(key=='choice') else r['away_U'] for r in z];n=len(v);u=sum(v)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
def era(r):return '2019-23' if r['year']<=2023 else '2024-25' if r['year']<=2025 else '2026'
out={'coverage':dict(C),'joint_rows':len(rows),'unique':len({r['fid'] for r in rows}),'by_horizon':{}}
for T in (24,12,6):
 z=[r for r in rows if r['T']==T]
 out['by_horizon'][str(T)]={}
 for name,subset in [('all',z),('positive_EV_diagnostic',[r for r in z if max(r['eh'],r['ea'])>0]),('aligned_recent_3h_diagnostic',[r for r in z if max(r['age_1x2_h'],r['age_AH_h'])<=3]),('positive_EV_and_recent_3h_diagnostic',[r for r in z if max(r['eh'],r['ea'])>0 and max(r['age_1x2_h'],r['age_AH_h'])<=3])]:
  result={p:{'model':stat([r for r in subset if p=='all' or era(r)==p]),'opposite':stat([r for r in subset if p=='all' or era(r)==p],'opposite')} for p in ('all','2019-23','2024-25','2026')}
  out['by_horizon'][str(T)][name]=result
  print('RESULT',T,name,result,flush=True)
(R/'m8_early_exact_cross_market_consistency_20261115.json').write_text(json.dumps(out,indent=2))
(R/'m8_early_exact_cross_market_consistency_20261115.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
print('COVERAGE',len(rows),out['unique'],C,flush=True)
