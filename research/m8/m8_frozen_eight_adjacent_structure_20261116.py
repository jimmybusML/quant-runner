import json,collections,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
load=lambda p:[json.loads(l) for l in (P/p).open()]
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
digest=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
foundation={'membership':digest(m['historical_membership']['local_file'])==m['historical_membership']['sha256'],'inputs':all(digest(k)==v for k,v in m['input_sha256'].items()),'scripts':all(digest(k)==v for k,v in m['script_sha256'].items())};assert all(foundation.values())
frozen=load(m['historical_membership']['local_file']);ids={r['fid'] for r in frozen}
base=load('m8_late_full_path_water_features_20261114.jsonl')
extra=load('m8_extra_inventory_frozen_eight_20261115.jsonl')+load('m8_raw_capture_unindexed_frozen_replay_20261115.jsonl')
same={r['fid']:r for r in load('m8_same_line_probability_path_20261114.jsonl')}
rows=[{**r,**same.get(r['fid'],{})} for r in base]+extra
assert len(rows)==44956 and len({r['fid'] for r in rows})==44956
def sg(x):return 1 if x>1e-9 else -1 if x<-1e-9 else 0
def direction(s):return 'home' if s>0 else 'away'
def opposite(side):return 'away' if side=='home' else 'home'
# One deterministic exhaustive structure taxonomy for remaining fixtures.
# Mirror D with price relative to same-line average. E uses reversal of initial
# signed move; F follows monotonic direction. No ROI-derived thresholds.
def classify(r):
 zero=r['end_zero'];line='zero' if zero else 'nonzero'
 shape=r['path_shape']
 if shape=='reverted':
  h,a=r.get('home_price_vs_timeavg'),r.get('away_price_vs_timeavg')
  if h is None or a is None:return 'D_return_'+line+'_unknown',None
  s=sg(h-a)
  if not s:return 'D_return_'+line+'_flat',None
  # D chooses away when home price fell more versus time-average.
  # Reflect to home when the opposite occurs.
  return 'D_return_'+line+('_mirror' if s>0 else '_original_orientation'),direction(s)
 if shape=='never_changed' and r.get('n_price_moves',0):
  x,y=sg(r['p3']-r['p0']),sg(r['p1']-r['p3']);net=sg(r['p1']-r['p0'])
  moves=bool(r['up_moves'] and r['down_moves'])
  if moves:
   if not net:
    s=x or y or sg(r['last_move'])
    return 'E_return_'+line,opposite(direction(s)) if s else None
   if x*y<0:
    # Incomplete cancellation: classify both ways, keep both in report.
    return 'E_partial_'+line+('_first_dominates' if net==x else '_second_dominates'),opposite(direction(x))
   return 'E_other_'+line,None
  s=net or x or y or sg(r['last_move'])
  phase='late' if x==0 and y else 'early' if y==0 and x else 'both'
  return 'F_monotonic_'+line+'_'+phase,direction(s) if s else None
 return 'other_'+line+'_'+shape,None
groups=collections.defaultdict(list);unassigned=collections.Counter()
for r in rows:
 if r['fid'] in ids:continue
 g,side=classify(r)
 if not side:unassigned[g]+=1;continue
 assert r['fid'] not in ids
 groups[g].append({'fid':r['fid'],'year':r['year'],'date':r['date'],'league':r['league'],'cohort':g,'side':side,'pnl':r['end_'+side+'_U'],'other_pnl':r['end_'+opposite(side)+'_U']})
assert sum(map(len,groups.values()))+sum(unassigned.values())==44956-10294
def stat(z,k='pnl'):
 n=len(z);u=sum(r[k] for r in z);days=collections.defaultdict(float)
 for r in z:days[r['date']]+=r[k]
 c=peak=dd=0.
 for _,p in sorted(days.items()):c+=p;peak=max(peak,c);dd=max(dd,peak-c)
 return {'n':n,'U':round(u,3),'ROI':round(u/n*100,3) if n else None,'daily_mdd':round(dd,3)}
def desc(z,k='pnl'):
 return {'all':stat(z,k),'years':{str(y):stat([r for r in z if r['year']==y],k) for y in range(2019,2027)},'2026':stat([r for r in z if r['year']==2026],k),'2026_weekly':round(sum(r['year']==2026 for r in z)/45,3)}
out={'method':'R32 boundary transfer of same-T1 known D/E/F structures to all non-frozen fixtures in original49. D mirrored price-relative return, E exact or incomplete reversal, F monotonic timing and same-line nonzero transfer. Groups defined by natural sign/phase, no optimized cutoffs. Both proposed and opposite direction reported; all groups including losses retained. Original identities known at same T1, no future late membership needed. This is repeated retrospective research; no production rule or independently forward-validated candidate.','foundation':foundation,'universe':len(rows),'unassigned':dict(unassigned),'groups':{}}
for g,z in sorted(groups.items()):
 out['groups'][g]={'proposed':desc(z),'opposite':desc(z,'other_pnl'),'combined_with_foundation':desc(frozen+z)}
 v=out['groups'][g]
 print(g,'all',v['proposed']['all'],'2026',v['proposed']['2026'],'opp',v['opposite']['all'],v['opposite']['2026'],'annual',[(y,x['n'],x['ROI']) for y,x in v['proposed']['years'].items()],flush=True)
print('UNASSIGNED',dict(unassigned),flush=True)
# A fixed, broad transfer (same exact E/F path, same D orientation and its mirror)
# is reported without selecting the profitable pieces. Natural partitions preserved.
trans=[r for g,z in groups.items() if g.startswith('D_return_') or g.startswith('E_return_') or g.startswith('F_monotonic_') and g.endswith('_late') for r in z]
allz=[r for z in groups.values() for r in z]
for name,z in [('exact_structure_transfer',trans),('all_adjacent',allz)]:
 out[name]={'standalone':desc(z),'combined':desc(frozen+z)}
 print('COMBO',name,out[name]['standalone']['all'],out[name]['standalone']['2026'],out[name]['combined']['2026'],flush=True)
(P/'m8_frozen_eight_adjacent_structure_20261116.json').write_text(json.dumps(out,indent=2))
# Descriptive combination of two after-the-fact leads; not a selection rule.
leads=[{**r,'pnl':r['other_pnl']} for g in ('F_monotonic_zero_early','E_partial_zero_second_dominates') for r in groups[g]]
out['posthoc_reverse_pair']={'standalone':desc(leads),'combined':desc(frozen+leads)}
# Independently time-ordered experiment: choose one side for each pre-defined
# group using only preceding calendar years, never discard losing groups.
pred=[]
for y in range(2024,2027):
 for g,z in groups.items():
  train=[r for r in z if r['year']<y]
  side='other_pnl' if train and sum(r['other_pnl']-r['pnl'] for r in train)>0 else 'pnl'
  pred.extend({**r,'pnl':r[side]} for r in z if r['year']==y)
out['prior_year_side_choice']={'all_2024_26':desc(pred),'combined_2024_26':desc([r for r in frozen if r['year']>=2024]+pred)}
print('PAIR',out['posthoc_reverse_pair']['standalone']['all'],out['posthoc_reverse_pair']['standalone']['2026'],out['posthoc_reverse_pair']['combined']['2026'],flush=True)
print('PRIOR_CHOICE',out['prior_year_side_choice']['all_2024_26']['all'],out['prior_year_side_choice']['all_2024_26']['2026'],flush=True)
# Reopen prior actual-receipt archive, verify SHA and timing; score only
# fixture identities with independent archived FT evidence. No new API.
import math,bisect
from zoneinfo import ZoneInfo
from research.m3.probabilities import settle_score
B=P.parent/'repos/mr1/data/prospective-market/shadow-v23'
def dt(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
receipt=load('m8_new_receipt_frozen_eight_FT_20261115.jsonl')
assert len(receipt)==306
need={r['fid']:r for r in receipt if not r['cohort']}
ixmap={}
for ix in map(json.loads,(B/'snapshot-index.jsonl').open()):
 if ix['match_id'] in need and ix['snapshot_sha256']==need[ix['match_id']]['snapshot_sha256']:ixmap[ix['match_id']]=ix
ft=collections.defaultdict(list)
for e in map(json.loads,(P/'m7/m7_schedule_verified_FT_receipt_events_20261111.jsonl').open()):
 if str(e['fixture_id']) in need:ft[str(e['fixture_id'])].append(e)
qc=collections.Counter();res=collections.defaultdict(list)
for f,r in need.items():
 try:
  ix=ixmap[f];raw=(B/ix['snapshot_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['snapshot_sha256'];s=json.loads(raw)
  ko=dt(r['kickoff_utc']);recv=dt(r['receipt_utc']);t6=ko-datetime.timedelta(hours=6);t3=ko-datetime.timedelta(hours=3);t1=ko-datetime.timedelta(hours=1)
  assert dt(s['kickoff_at'])==ko and dt(s['received_at'])==recv and recv<=t1 and dt(ix['committed_at'])<=t1
  x=None
  for p in (B/'snapshots'/f/s['target_horizon']/'odds').glob('attempt-*.json'):
   at=json.loads(p.read_text());raw=at.get('raw_response','')
   if at.get('classification')!='SNAPSHOT_OK' or at.get('raw_sha256')!=r['raw_sha256'] or hashlib.sha256(raw.encode()).hexdigest()!=r['raw_sha256']:continue
   if abs((dt(at['received_at'])-recv).total_seconds())>.005:continue
   x=next(z for z in json.loads(raw)['data'] if str(z['id'])==f);break
  assert x and dt(x['start'])==ko and str(x['l_id'])==r['league']
  book=next(z for z in x['bookmakers'] if z['slug']=='crown')
  path=[]
  for q in book.get('asian_list') or []:
   try:
    t=dt(q[4]);l,h,a=map(float,q[1:4])
    if t<=recv and t<ko and h>1 and a>1 and all(math.isfinite(v) for v in (l,h,a)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,h,a))
   except:continue
  path.sort(key=lambda q:q[0]);ts=[q[0] for q in path];i,j,k=[bisect.bisect_right(ts,t)-1 for t in (t6,t3,t1)];assert min(i,j,k)>=0
  start,mid,end=[path[n] for n in (i,j,k)];seq=path[i:k+1];steps=[(a,b) for a,b in zip(seq,seq[1:]) if a[1]!=b[1]]
  l=end[1];assert l==r['line'] and end[0]==dt(r['source_event_utc'])
  shape='never_changed' if not steps else 'reverted' if start[1]==l else 'one_way' if all((v[1]-u[1])*(l-start[1])>0 for u,v in steps) else 'oscillating'
  a={'end_zero':not l,'path_shape':shape}
  if shape=='reverted':
   dur=sh=sa=0.
   for n,q in enumerate(seq):
    if q[1]!=l:continue
    dd=max(0.,((seq[n+1][0] if n+1<len(seq) else t1)-max(t6,q[0])).total_seconds())
    dur+=dd;sh+=dd*q[2];sa+=dd*q[3]
   a.update(home_price_vs_timeavg=end[2]-sh/dur if dur else None,away_price_vs_timeavg=end[3]-sa/dur if dur else None)
  elif shape=='never_changed':
   prob=lambda q:q[3]/(q[2]+q[3])
   vals=list(map(prob,seq));moves=[v-u for u,v in zip(vals,vals[1:]) if abs(v-u)>1e-10]
   a.update(p0=prob(start),p3=prob(mid),p1=prob(end),n_price_moves=len(moves),up_moves=sum(v>0 for v in moves),down_moves=sum(v<0 for v in moves),last_move=moves[-1] if moves else 0.)
  g,side=classify(a);qc['verified_quote']+=1
  if not side:qc['no_adjacent_signal']+=1;continue
  record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'side':side,'pnl':None,'other_pnl':None}
  for e in ft.get(f,[]):
   try:
    raw=Path(e['raw_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==e['raw_sha256']
    z=next(q for q in json.loads(raw)['data']['matches'] if str(q['id'])==f)
    assert str(z['l_id'])==r['league'] and dt(z['start'])==ko and z['status']=='full' and dt(e['observed_at_utc'])>ko
    assert ' '.join(z['h'].casefold().split())==' '.join(r['home'].casefold().split()) and ' '.join(z['a'].casefold().split())==' '.join(r['away'].casefold().split())
    h,a1=int(z['hg']),int(z['ag']);assert (h,a1)==(int(e['home_goals']),int(e['away_goals']))
    record['pnl']=settle_score('AH',l,side,h,a1,end[2] if side=='home' else end[3])[1]
    op=opposite(side);record['other_pnl']=settle_score('AH',l,op,h,a1,end[2] if op=='home' else end[3])[1]
    break
   except Exception:continue
  res[g].append(record)
 except Exception as ex:qc['quote_error_'+type(ex).__name__]+=1
out['receipt_replay']={'archive_n':len(receipt),'unselected_n':len(need),'quality':dict(qc),'groups':{}}
for g,z in sorted(res.items()):
 settled=[r for r in z if r['pnl'] is not None]
 out['receipt_replay']['groups'][g]={'signals':len(z),'settled':len(settled),'unsettled':len(z)-len(settled),'proposed':stat(settled),'opposite':stat(settled,'other_pnl')}
print('RECEIPT',json.dumps(out['receipt_replay']),flush=True)
(P/'m8_frozen_eight_adjacent_structure_20261116.json').write_text(json.dumps(out,indent=2))
