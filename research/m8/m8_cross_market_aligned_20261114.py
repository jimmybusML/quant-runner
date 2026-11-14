import json,math,datetime,collections,bisect,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
old=R/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'
sch=R/'m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'
idx={str(r['match_id']):r for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
base={(r['year'],r['fid']):r for r in map(json.loads,(R/'m8_late_full_path_water_features_20261114.jsonl').open())}
def sg(x):return 1 if x>1e-9 else -1 if x<-1e-9 else 0
# Exact prior research cohort membership, all results retained.
prior={}
for key,r in base.items():
 if r['base']:g='base';u=r['base_U']
 elif r.get('path_6_3_1')=='deepen_weaken':g='A';u=r['end_dog_U']
 elif r.get('path_6_3_1')=='weaken_same':g='B';u=r['end_dog_U']
 elif not r['end_zero'] and r['path_shape']=='oscillating':g='C';u=r['end_fav_U']
 elif r['end_zero'] and r['path_shape']=='reverted' and r['home_price_vs_timeavg'] is not None and r['home_price_vs_timeavg']-r['away_price_vs_timeavg']<-1e-9:g='D';u=r['end_away_U']
 else:continue
 prior[key]=(g,u)
for r in map(json.loads,(R/'m8_same_line_probability_path_20261114.jsonl').open()):
 if not r['end_zero']:continue
 a,b=sg(r['p3']-r['p0']),sg(r['p1']-r['p3']);net=sg(r['p1']-r['p0']);s=net or a or b or sg(r['last_move'])
 if not s or not r['n_price_moves']:continue
 if r['up_moves'] and r['down_moves'] and not net:side='away' if s>0 else 'home';g='E'
 elif (not r['up_moves'] or not r['down_moves']) and a==0 and b*s==1:side='home' if s>0 else 'away';g='F'
 else:continue
 key=(r['year'],r['fid']);assert key not in prior;prior[key]=(g,r['end_'+side+'_U'])
assert sum(y==2026 for y,f in prior)==1799
assert abs(sum(v[1] for (y,f),v in prior.items() if y==2026)-75.27)<1e-5
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def inputs():
 for r in map(json.loads,old.open()):
  y=datetime.datetime.fromisoformat(r['kickoff_utc']).year
  if y<2026:yield y,str(r['fixture_id']),Path(r['source_file']),None
 for r in map(json.loads,sch.open()):
  f=str(r['fid']);yield 2026,f,P/f'data/m5-crown-authorized/crown-responses/{f}.json',idx.get(f,{}).get('response_sha256')
counts=collections.defaultdict(collections.Counter);rows=[]
for y,f,p,sha in inputs():
 key=(y,f)
 if key not in base:continue
 counts[y]['AH_T6_T1']+=1
 try:
  raw=p.read_bytes()
  if y==2026 and (not sha or hashlib.sha256(raw).hexdigest()!=sha):counts[y]['sha_error']+=1;continue
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  ko=dt(x['start']);b=next(q for q in x['bookmakers'] if q.get('slug')=='crown')
  if ko.year!=y:counts[y]['year_mismatch']+=1;continue
  cutoff=[ko-datetime.timedelta(hours=h) for h in (6,3,1)]
  paths={}
  for name,field in [('AH','asian_list'),('OU','goal_list')]:
   path=[]
   for q in b.get(field) or []:
    try:
     t=dt(q[4]);line,od1,od2=map(float,q[1:4])
     if t<ko and od1>1 and od2>1 and all(math.isfinite(z) for z in (line,od1,od2)) and abs(line*4-round(line*4))<1e-7:path.append((t,line,od1,od2))
    except:continue
   path.sort();ts=[q[0] for q in path]
   ix=[bisect.bisect_right(ts,t)-1 for t in cutoff]
   if path:counts[y][name+'_path']+=1
   if min(ix)>=0:
    paths[name]=[path[i] for i in ix]
    if name=='OU':counts[y]['OU_T6_T1']+=1
  # Explicitly census actual 1X2 history fields, don't invent a path from opening/closing.
  od=b.get('odds') or {};op=od.get('open');cl=od.get('close')
  valid_1x2=[]
  for tag,q in [('open',op),('close',cl)]:
   try:
    t=dt(q['time']);probs=[1/float(q[k]) for k in ('home','draw','away')]
    if min(float(q[k]) for k in ('home','draw','away'))<=1:continue
    valid_1x2.append((tag,t,[v/sum(probs) for v in probs]))
   except:continue
  if any(isinstance(b.get(k),list) and b[k] for k in ('odds_list','europe_list','1x2_list')):counts[y]['1X2_list']+=1
  if any(tag=='open' and t<=cutoff[0] for tag,t,pv in valid_1x2):counts[y]['1X2_open_before_T6']+=1
  if any(tag=='close' and t<=cutoff[2] for tag,t,pv in valid_1x2):counts[y]['1X2_close_before_T1']+=1
  if not ('AH' in paths and 'OU' in paths):continue
  ah,ou=paths['AH'],paths['OU']
  a=base[key]
  assert ah[-1][1]==a['end_line']
  def share(q):return q[3]/(q[2]+q[3])
  a0,a3,a1=[share(q) for q in ah];o0,o3,o1=[share(q) for q in ou]
  r=dict(a);r.update({'prior':prior.get(key,(None,None))[0],'AH_p0':a0,'AH_p3':a3,'AH_p1':a1,'OU_p0':o0,'OU_p3':o3,'OU_p1':o1,'OU_l0':ou[0][1],'OU_l3':ou[1][1],'OU_l1':ou[2][1],'OU_over_odds':ou[2][2],'OU_under_odds':ou[2][3]})
  # Only opening odds with event <= T6 for secondary reference; no closing used in model.
  for tag,t,pv in valid_1x2:
   if tag=='open' and t<=cutoff[0]:r['open_1x2']=pv
  rows.append(r)
 except Exception as e:
  counts[y]['errors']+=1
  if counts[y]['errors']<=2:print('ERR',y,f,repr(e),flush=True)
print('COVERAGE',json.dumps(counts,ensure_ascii=False),flush=True)
print('JOINT',len(rows),collections.Counter((r['year'],bool(r['prior'])) for r in rows),flush=True)
(R/'m8_cross_market_coverage_20261114.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))
(R/'m8_cross_market_aligned_20261114.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
