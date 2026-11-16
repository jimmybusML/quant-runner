import json,collections,datetime,hashlib,math,bisect
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_frozen_eight_adjacent_structure_20261116.py').read_text()
exec(s[:s.index('groups=collections.defaultdict(list);unassigned=')])
exec(s[s.index('def stat(z,'):s.index("out={'method'")])
def dt(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
target=[r for r in rows if r['fid'] not in ids and not r['end_zero'] and r['path_shape']=='never_changed']
assert len(target)==26055
# Cached schedule archive, all available competition IDs, not an assumption of
# all competitions. Keep only unambiguous complete match identities.
root=P.parent/'data/m5-crown-authorized/schedules'
seen=collections.defaultdict(set);qc0=collections.Counter();pages=collections.defaultdict(set)
for p in sorted(root.glob('*/page-*.raw.json')):
 try:
  b=json.loads(p.read_bytes());qc0['pages']+=1;pages[p.parent.name].add(int(p.stem.split('-')[1].split('.')[0]))
  for q in b['data']['matches']:
   qc0['rows']+=1
   f=str(q.get('id') or '');l=str(q.get('l_id') or '');h=str(q.get('h_id') or '');a=str(q.get('a_id') or '')
   if not (f and l and h and a and h!=a and l==p.parent.name):qc0['invalid_rows']+=1;continue
   t=dt(q['start']);seen[f].add((l,h,a,t,q.get('status')=='full'))
 except Exception as ex:qc0['page_error_'+type(ex).__name__]+=1
 # No external requests.
sched={};conflicts=0
for f,e in seen.items():
 ident={x[:4] for x in e}
 if len(ident)!=1:conflicts+=1;continue
 if not any(x[4] for x in e):continue
 sched[f]=next(iter(ident))
idx_all=collections.defaultdict(list);idx_league=collections.defaultdict(list)
for f,(l,h,a,t) in sched.items():
 for team in (h,a):
  idx_all[team].append(t.timestamp());idx_league[(l,team)].append(t.timestamp())
for ix in (idx_all,idx_league):
 for k in ix:ix[k]=np.array(sorted(ix[k]))
# Verify target identity versus independent historical score rows.
S={r['fid']:(str(r['league']),r['home'],r['away'],dt(r['ko'])) for r in load('m8_independent_score_strength_20261114.jsonl')}
S.update({r['fid']:(str(r['score_row']['league']),r['score_row']['home'],r['score_row']['away'],dt(r['score_row']['ko'])) for r in extra if 'score_row' in r})
def simple(q):
 return dict(fid=q['fid'],year=q['year'],date=q['date'],league=str(q['league']),line=q['end_line'],ph=q['home_price'],pa=q['away_price'],pnl=q['end_home_U'],other_pnl=q['end_away_U'])
def loadfeat(ident):
 l,h,a,t=ident
 # Prior kickoffs on earlier UTC dates only: proxy, not exact elapsed rest.
 limit=t.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
 ts=t.timestamp()
 values=[]
 for ix,keys in ((idx_all,(h,a)),(idx_league,((l,h),(l,a)))):
  for k in keys:
   dates=ix.get(k,np.array([]));n=np.searchsorted(dates,limit,side='left')
   if n==0:return None
   dates=dates[:n]
   values.append([math.log1p((ts-dates[-1])/86400),*[int(n-np.searchsorted(dates,ts-w*86400,side='left')) for w in (7,14,28)]])
 aa,bb,cc,dd=map(np.array,values)
 return np.r_[aa-bb,aa+bb,cc-dd,cc+dd]
H=[];F=[];missing=collections.Counter();hmiss=collections.Counter()
for r in target:
 f=r['fid'];ident=S.get(f)
 if not ident:missing['no_target_identity']+=1;hmiss[str(r['year'])]+=1;continue
 if f not in sched:missing['target_not_unambiguous_full_schedule']+=1;hmiss[str(r['year'])]+=1;continue
 if sched[f]!=ident:missing['target_identity_mismatch']+=1;hmiss[str(r['year'])]+=1;continue
 v=loadfeat(ident)
 if v is None:missing['either_team_no_prior']+=1;hmiss[str(r['year'])]+=1;continue
 H.append(simple(r));F.append(v)
F=np.array(F)
out={'method':'R34 all original49 nonzero unchanged AH paths outside eight at T1. Cached completed fixture identities across available competitions, exact target kickoff/team/league match; last prior kickoff on earlier UTC day and previous 7/14/28-day match counts (research explanatory windows). Compare both-teams schedule features from all cached competitions and same league, not complete real calendar or physiological fatigue. Receipt-side calendar supplemented separately by verified M7 archive FT identities; completeness not guaranteed, historical fit unchanged. Earlier annual ridge100 direct home-away settled payout differences; matched cohort explicit, missing data not zero. All matched fixtures settled; no return-based filtering, no production rules. Historical and receipt replay not independent prospective.','foundation':foundation,'schedule':{'pages':qc0['pages'],'cached_competitions':len(pages),'raw_rows':qc0['rows'],'unique_ids':len(seen),'conflicting_identity':conflicts,'unambiguous_full':len(sched),'quality':dict(qc0),'earliest':min(q[3] for q in sched.values()).isoformat(),'latest':max(q[3] for q in sched.values()).isoformat()},'coverage':{'target_n':len(target),'matched_n':len(H),'unmatched':dict(missing),'unmatched_years':dict(hmiss),'target_2026':sum(r['year']==2026 for r in target),'matched_2026':sum(r['year']==2026 for r in H)},'models':{}}
print('COVERAGE',out['schedule'],out['coverage'],flush=True)
# Actual receipt cohort: same validated quotes/FT as R32. Keep exact unchanged
# nonzero lines, and add schedule attributes before joining result.
block=s[s.index('import math,bisect'):s.index("print('RECEIPT'")]
old="g,side=classify(a);qc['verified_quote']+=1"
new="""g='unchanged_nonzero'
  side='home' if l and shape=='never_changed' else None
  qc['verified_quote']+=1"""
assert old in block
block=block.replace(old,new)
old2="record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'side':side,'pnl':None,'other_pnl':None}"
new2="""ident=(str(x['l_id']),str(x.get('h_id') or ''),str(x.get('a_id') or ''),ko)
  record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'league':r['league'],'side':side,'pnl':None,'other_pnl':None,'line':l,'ph':end[2],'pa':end[3],'ident':ident}"""
assert old2 in block
block=block.replace(old2,new2)
exec(compile(block,'R32_verified_receipt_R34_classifier','exec'))
RR=res.get('unchanged_nonzero',[]);R=[];RF=[];rmiss=collections.Counter();rmiss_settled=0;pend=0
# Extend only receipt-side calendar from independently archived FT evidence.
# Existing historical fit/coverage not changed. Missing competitions remain unknown.
original_receipt_match=sum(a['fid'] in sched and sched[a['fid']]==a['ident'] for a in RR)
aquality=collections.Counter();rawcache={};adds={};collision=set()
for e in map(json.loads,(P/'m7/m7_schedule_verified_FT_receipt_events_20261111.jsonl').open()):
 f=str(e['fixture_id'])
 if f in sched:continue
 try:
  rawname=e['raw_path'];sha=e['raw_sha256'];k=(rawname,sha)
  if k not in rawcache:
   raw=Path(rawname).read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
   rawcache[k]={str(z['id']):z for z in json.loads(raw)['data']['matches']}
  z=rawcache[k][f];t=dt(z['start']);obs=dt(e['observed_at_utc'])
  ident=(str(z['l_id']),str(z['h_id']),str(z['a_id']),t)
  assert ident==(str(e['league_id']),str(e['home_id']),str(e['away_id']),dt(e['kickoff_utc']))
  assert z['status']=='full' and obs>t and int(z['hg'])==int(e['home_goals']) and int(z['ag'])==int(e['away_goals']) and ident[1]!=ident[2]
  if f in adds and adds[f]!=ident:collision.add(f)
  adds[f]=ident
 except Exception as ex:aquality['archive_error_'+type(ex).__name__]+=1
for f in collision:adds.pop(f,None)
aquality['new_verified_FT_ids']=len(adds);aquality['conflicting_new_ids']=len(collision)
aquality['target_match_before_extension']=original_receipt_match
sched.update(adds)
for ix in (idx_all,idx_league):
 for k,v in list(ix.items()):ix[k]=v.tolist()
for l,h,a,t in adds.values():
 for team in (h,a):
  idx_all.setdefault(team,[]).append(t.timestamp());idx_league.setdefault((l,team),[]).append(t.timestamp())
for ix in (idx_all,idx_league):
 for k in ix:ix[k]=np.array(sorted(ix[k]))
out['receipt_schedule_extension']={'source':'M7 independently verified FT receipts; exact raw SHA, UTC identity and goals checked again; receipt-side only; missing competitions and matches not proven complete','quality':dict(aquality),'latest':max(q[3] for q in sched.values()).isoformat()}
print('EXTENSION',out['receipt_schedule_extension'],flush=True)
for a in RR:
 f=a['fid'];ident=a['ident']
 if f not in sched or sched[f]!=ident:
  rmiss['target_not_matched_schedule']+=1;rmiss_settled+=a['pnl'] is not None;continue
 v=loadfeat(ident)
 if v is None:rmiss['either_team_no_prior']+=1;rmiss_settled+=a['pnl'] is not None;continue
 if a['pnl'] is None:pend+=1;continue
 R.append(a);RF.append(v)
RF=np.array(RF).reshape(-1,16)
out['receipt_coverage']={'archive_n':306,'unselected_n':256,'quote_quality':dict(qc),'fixed_nonzero_quotes':len(RR),'fixed_nonzero_settled':sum(a['pnl'] is not None for a in RR),'matched_settled':len(R),'matched_unsettled':pend,'unmatched':dict(rmiss),'unmatched_settled':rmiss_settled}
# drop raw receipt metadata output: already verified and aggregated in counts
out.pop('receipt_replay',None)
print('RECEIPT_COVERAGE',out['receipt_coverage'],flush=True)
# Same target rows and annual training for all experiment arms.
HY=np.array([r['year'] for r in H]);RY=np.array([r['year'] for r in R])
receipt_ids={r['fid'] for r in load('m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl') if 'fid' in r} # actual archive uses fixture_id
receipt_ids|={str(r.get('fixture_id')) for r in load('m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl')}
receipt_ids|={r['fid'] for r in receipt}
ind=np.array([r['fid'] not in receipt_ids for r in H])
def vec(q,k):return np.array([r[k] for r in q],float)
def market(q):
 l,ph,pa=[vec(q,k) for k in ('line','ph','pa')]
 return np.column_stack([np.ones(len(q)),l,abs(l),pa/(ph+pa),1/ph+1/pa])
def make(q,f,mode):
 base=market(q)
 if mode=='market':return base
 if mode=='schedule_only':return np.column_stack((base[:,:1],f[:,:8]))
 if mode=='market_all_schedule':return np.column_stack((base,f[:,:8]))
 if mode=='market_same_league':return np.column_stack((base,f[:,8:]))
 if mode=='market_both':return np.column_stack((base,f))
 raise ValueError(mode)
# Map pre-specified features to one home-away choice per fixture using past years.
y=vec(H,'pnl')-vec(H,'other_pnl')
for mode in ('market','schedule_only','market_all_schedule','market_same_league','market_both'):
 X=make(H,F,mode);Z=make(R,RF,mode);p=np.zeros(len(H));rp=np.zeros(len(R));fit={};used=np.zeros(len(H),bool);ru=np.zeros(len(R),bool)
 for yr in (2024,2025,2026):
  tr=(HY<yr)&ind;te=HY==yr;re=RY==yr
  mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
  beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
  p[te]=((X[te]-mu)/sd)@beta;rp[re]=((Z[re]-mu)/sd)@beta
  used|=te;ru|=re;fit[str(yr)]={'train_n':int(tr.sum()),'coef':(beta/sd).tolist()}
 def settle(q,p,mask):
  return [{**r,'pnl':r['pnl'] if v>=0 else r['other_pnl']} for r,v,k in zip(q,p,mask) if k]
 h=settle(H,p,used);r=settle(R,rp,ru);dis=settle(H,p,used&ind)
 assert len({r['fid'] for r in h})==len(h) and not ({r['fid'] for r in h}&ids)
 v={'history':desc(h),'disjoint_history':desc(dis),'receipt':desc(r),'combined':desc([r for r in frozen if r['year']>=2024]+h),'fit':fit}
 out['models'][mode]=v
 print('RESULT',mode,'H',v['history']['all'],'2026',v['history']['2026'],'R',v['receipt']['all'],'combined26',v['combined']['2026'],'years',[(yr,s['n'],s['ROI']) for yr,s in v['history']['years'].items() if s['n']],flush=True)
(P/'m8_fixed_line_schedule_load_20261117.json').write_text(json.dumps(out,indent=2))
