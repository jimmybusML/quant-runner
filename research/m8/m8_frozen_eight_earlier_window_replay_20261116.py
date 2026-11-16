import json,collections,datetime,math,bisect,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk');R=P/'research-work'
load=lambda p:[json.loads(l) for l in (R/p).open()]
m=json.loads((R/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((R/k).read_bytes()).hexdigest()
foundation={'membership':dig(m['historical_membership']['local_file'])==m['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in m['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in m['script_sha256'].items())}
assert all(foundation.values())
frozen=load(m['historical_membership']['local_file']);ids={r['fid'] for r in frozen}
src=load('m8_late_full_path_water_features_20261114.jsonl');extras=load('m8_extra_inventory_frozen_eight_20261115.jsonl')+load('m8_raw_capture_unindexed_frozen_replay_20261115.jsonl')
univ={r['fid']:r for r in src+extras};assert len(univ)==len(src)+len(extras) and ids<=univ.keys()
S={r['fid']:(r['lambda_home_0.025'],r['lambda_away_0.025']) for r in load('m8_independent_score_strength_20261114.jsonl')}
S.update({r['fid']:r['score_rates'] for r in extras if 'score_rates' in r})
idx={str(r['match_id']):r for r in map(json.loads,(P/'data/m5-crown-authorized/crown-response-index.jsonl').open())}
sources={}
for r in load('m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl'):
 f=str(r['fixture_id'])
 if f in univ and univ[f]['year']<2026:sources[f]=(Path(r['source_file']),None)
for r in load('m8_2026_Jan_Nov_49league_cached_complete_schedule_20261113.jsonl'):
 f=str(r['fid'])
 if f in univ:sources[f]=(P/f'data/m5-crown-authorized/crown-responses/{f}.json',idx.get(f,{}).get('response_sha256'))
for r in extras:sources[r['fid']]=(Path(r['source_file']),None)
def dt(s):return datetime.datetime.fromisoformat(str(s).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
def sg(v):return 1 if v>1e-9 else -1 if v<-1e-9 else 0
def prob(q):return q[3]/(q[2]+q[3])
def pmf(lam):
 a=[math.exp(-lam)]
 for j in range(1,40):a.append(a[-1]*lam/j)
 return np.array(a)
def model(f,l,h,a):
 hp,ap=map(pmf,S[f]);D=np.arange(40)[:,None]-np.arange(40)[None,:];p=hp[:,None]*ap[None,:];w=lose=0.
 for z in (math.floor(l*2+1e-8)/2,math.ceil(l*2-1e-8)/2):
  w+=p[D+z>0].sum()/2;lose+=p[D+z<0].sum()/2
 return sg(w*(h-1)-lose-(lose*(a-1)-w)) or 1
windows=[(6,3,1),(11,8,6),(17,14,12)]
data={w:[] for w in windows};coverage={w:collections.Counter() for w in windows};bad=collections.Counter()
def run(f,old,ko,path,times,h,a,w):
 cut=[ko-datetime.timedelta(hours=i) for i in w];ix=[bisect.bisect_right(times,t)-1 for t in cut]
 if min(ix)<0:return
 i,j,k=ix;start,mid,end=[path[z] for z in ix];seq=path[i:k+1];steps=[(u,v) for u,v in zip(seq,seq[1:]) if u[1]!=v[1]]
 l=end[1];sl=start[1];ml=mid[1]
 def state(x,y):return 'deepen' if (y-x)*l>0 else 'weaken' if (y-x)*l<0 else 'same'
 shape='never_changed' if not steps else 'reverted' if sl==l else 'one_way' if all((v[1]-u[1])*(l-sl)>0 for u,v in steps) else 'oscillating'
 dog='home' if l>0 else 'away';fav='away' if l>0 else 'home'
 g=side=None
 if (l-sl)*l>0:g='base';side=dog
 elif l and state(sl,ml)+'_'+state(ml,l)=='deepen_weaken':g='A';side=dog
 elif l and state(sl,ml)+'_'+state(ml,l)=='weaken_same':g='B';side=dog
 elif l and shape=='oscillating':g='C';side=fav
 elif not l and shape=='reverted':
  dur=0.;sh=sa=0.
  for n,q in enumerate(seq):
   if q[1]!=l:continue
   lo=max(cut[0],q[0]);hi=seq[n+1][0] if n+1<len(seq) else cut[2];dd=max(0.,(hi-lo).total_seconds())
   dur+=dd;sh+=dd*q[2];sa+=dd*q[3]
  if dur and (end[2]-sh/dur)-(end[3]-sa/dur)<-1e-9:g='D';side='away'
 elif not l and shape=='never_changed':
  p0,p3,p1=map(prob,(start,mid,end));x,y=sg(p3-p0),sg(p1-p3);net=sg(p1-p0)
  moves=[prob(v)-prob(u) for u,v in zip(seq,seq[1:]) if abs(prob(v)-prob(u))>1e-10]
  ss=net or x or y or sg(moves[-1] if moves else 0)
  if ss and moves:
   up=any(z>0 for z in moves);down=any(z<0 for z in moves)
   if up and down and not net:g='E';side='away' if ss>0 else 'home'
   elif (not up or not down) and x==0 and y*ss==1:g='F';side='home' if ss>0 else 'away'
 if g is None and shape=='reverted' and f in S:
  market=sg(prob(end)-prob(start));mod=model(f,l,end[2],end[3])
  if market and market==mod:g='G';side='away' if mod>0 else 'home'
 coverage[w][str(old['year'])]+=1
 if g:
  price=end[2] if side=='home' else end[3]
  pnl=settle_score('AH',l,side,h,a,price)[1]
  data[w].append(dict(fid=f,year=old['year'],date=old['date'],cohort=g,pnl=pnl,side=side,line=l,price=price))
for n,(f,old) in enumerate(univ.items()):
 try:
  p,sha=sources[f];raw=p.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('sha')
  q=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  ko=dt(q['start']);assert str(q['l_id'])==str(old['league']) and ko.date().isoformat()==old['date'] and q['status']=='full'
  h,a=int(q['hg']),int(q['ag']);b=next(x for x in q['bookmakers'] if x['slug']=='crown')
  path=[]
  for ev in b.get('asian_list') or []:
   try:
    t=dt(ev[4]);l,ph,pa=map(float,ev[1:4])
    if t<ko and ph>1 and pa>1 and all(math.isfinite(z) for z in (l,ph,pa)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,ph,pa))
   except Exception:continue
  path.sort(key=lambda q:q[0]);times=[q[0] for q in path]
  for w in windows:run(f,old,ko,path,times,h,a,w)
 except Exception as ex:bad[type(ex).__name__]+=1
 if (n+1)%10000==0:print('PROGRESS',n+1,dict(bad),flush=True)
def stat(a):
 n=len(a);u=sum(r['pnl'] for r in a);d=collections.defaultdict(float)
 for r in a:d[r['date']]+=r['pnl']
 c=peak=dd=0.
 for _,v in sorted(d.items()):c+=v;peak=max(peak,c);dd=max(dd,peak-c)
 return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None,'daily_mdd':round(dd,3)}
def desc(a):
 return {'all':stat(a),'year':{str(y):stat([r for r in a if r['year']==y]) for y in range(2019,2027)},'2026':stat([r for r in a if r['year']==2026]),'2026_weekly':round(sum(r['year']==2026 for r in a)/45,3)}
fset={r['fid']:r for r in frozen};replay={r['fid']:r for r in data[windows[0]]}
missing=set(fset)-set(replay);added=set(replay)-set(fset)
mismatch=[f for f in fset.keys()&replay.keys() if fset[f]['cohort']!=replay[f]['cohort'] or abs(fset[f]['pnl']-replay[f]['pnl'])>1e-7]
print('BASELINE',len(fset),len(replay),'missing',len(missing),'added',len(added),'mismatch',len(mismatch),'bad',dict(bad),flush=True)
out={'method':'Apply original eight path classification at equal-length earlier windows T11/8/6 and T17/14/12. All available original49 original+extra+database-audit FIDs; no change to strategy rules. Historic source time not actual receipt. Future original T1 membership excluded only for retrospective incremental measurement, NOT a usable early routing decision. Earlier windows are separate hypothetical replays; no independent forward testing or combined causal strategy. All groups retained.','foundation':foundation,'base_reproduction':{'frozen_n':len(fset),'replay_n':len(replay),'missing_n':len(missing),'added_n':len(added),'mismatch_n':len(mismatch)},'universe':len(univ),'source_errors':dict(bad),'windows':{}}
for w in windows:
 a=data[w];inc=[r for r in a if r['fid'] not in ids]
 k='/'.join(map(str,w));v={'coverage':dict(coverage[w]),'all':desc(a),'incremental':desc(inc),'combined_retrospective':desc(frozen+inc),'groups':{g:{'all':desc([r for r in a if r['cohort']==g]),'incremental':desc([r for r in inc if r['cohort']==g])} for g in ('base','A','B','C','D','E','F','G')}}
 out['windows'][k]=v
 print('RESULT',k,'coverage',sum(coverage[w].values()),'increment',v['incremental']['all'],v['incremental']['2026'],v['incremental']['2026_weekly'],'combined26',v['combined_retrospective']['2026'], 'groups',[(g,x['incremental']['all'],x['incremental']['2026']) for g,x in v['groups'].items()],flush=True)
(R/'m8_frozen_eight_earlier_window_replay_20261116.json').write_text(json.dumps(out,indent=2))
# A causal signal ordering simulation, not a production policy: once the earlier
# signal fires, it owns that fixture; otherwise keep the original late signal.
# Report EVERY group and both windows; D/E/F union is explicitly post-hoc descriptive.
assert not missing and not added and not mismatch and not bad
def causal(early,late):
 ef={r['fid'] for r in early};latekeep=[r for r in late if r['fid'] not in ef]
 return early+latekeep,[r for r in late if r['fid'] in ef]
out['causal_simulation']={}
for w in windows[1:]:
 k='/'.join(map(str,w));a=data[w];vv={}
 for gn in ('base','A','B','C','D','E','F','G','all','posthoc_DEF'):
  early=[r for r in a if gn=='all' or gn=='posthoc_DEF' and r['cohort'] in ('D','E','F') or r['cohort']==gn]
  mix,replaced=causal(early,frozen)
  assert len({r['fid'] for r in mix})==len(mix)
  ef=[r for r in early if r['year']==2026];rr=[r for r in replaced if r['year']==2026]
  inc=[r for r in early if r['fid'] not in ids]
  vv[gn]={'earlier_full':desc(early),'causal_combined':desc(mix),'original_replaced':desc(replaced),'incremental_retrospective':desc(inc),'2026_overlap_n':len(rr),'2026_replaced_U':round(sum(r['pnl'] for r in rr),3)}
  print('CAUSAL',k,gn,'early_all',stat(early),'early26',stat(ef),'overlap26',len(rr),'replaced26',stat(rr),'combined_all',stat(mix),'combined26',vv[gn]['causal_combined']['2026'],'weekly',vv[gn]['causal_combined']['2026_weekly'],'annual_extra',[(y,x['n'],x['ROI']) for y,x in vv[gn]['incremental_retrospective']['year'].items()],flush=True)
 out['causal_simulation'][k]=vv
out['causal_simulation_note']='Earlier signal takes precedence at the earlier observation point in a separate simulation; otherwise original late signal is retained. No knowledge of future late membership enters early selection. Cannot preserve every original order in this simulation; original frozen strategies remain untouched. All individual groups and all-group experiment reported; D/E/F combination is post-hoc descriptive ONLY, not independent validation or a chosen rule.'
(R/'m8_frozen_eight_earlier_window_replay_20261116.json').write_text(json.dumps(out,indent=2))
