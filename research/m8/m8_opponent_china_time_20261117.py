import json,datetime,collections,hashlib,math
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work');A=P/'m8_opponent_20261117'
def load(p):return list(map(json.loads,(P/p).open()))
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def local(s):return dt(s.replace(' ','T')+'+08:00').astimezone(datetime.timezone.utc)
def hash0(b):return hashlib.sha256(b).hexdigest()
picks={}
for p in sorted(A.glob('opponent_picks*.json')):
 for r in json.loads(p.read_bytes())['records']:picks[r['gmail_id']]=r
ledger=json.loads((A/'opponent_settlement_latest.json').read_bytes());known={r['gmail_id']:r for r in ledger['settled']}
scorelist=load('m8_independent_score_strength_20261114.jsonl');scoremap={r['fid']:r for r in scorelist};scope={r['league'] for r in scorelist}
# Source ID linkage: explicit previous result match_id, or exact kickoff and
# both exact registry labels and league (no fuzzy names).
regp=P.parent/'repos/m1/data/football_display_names/display_names.json'
reg=json.loads(regp.read_bytes())
def norm(x):return ''.join(str(x).casefold().split()).replace('足球','')
def labels(q):
 return {norm(v) for v in [q.get('canonical_zh',''),q.get('provider_name',''),*q.get('aliases',[])] if v}
idx=collections.defaultdict(list)
for r in scorelist:
 if r['year']==2026:idx[dt(r['ko'])].append(r)
resolved=[];qc=collections.Counter();pairset=set()
for r in picks.values():
 if r.get('market') not in ('AH','OU'):qc['other_market']+=1;continue
 ko=local(r['kickoff_bj']);email=dt(r['email_ts'])
 if not email.tzinfo:email=email.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
 email=email.astimezone(datetime.timezone.utc)
 if email>=ko:qc['not_pregame']+=1;continue
 anchor=known.get(r['gmail_id']);match=None
 if anchor:
  v=scoremap.get(str(anchor['match_id']))
  if v and dt(v['ko'])==ko and (v['hg'],v['ag'])==(anchor['home_goals'],anchor['away_goals']):match=v
 else:
  cand=[v for v in idx[ko] if norm(r['league_cn']) in labels(reg['competitions'].get(v['league'],{})) and norm(r['home_cn']) in labels(reg['teams'].get(v['home'],{})) and norm(r['away_cn']) in labels(reg['teams'].get(v['away'],{}))]
  if len(cand)==1:match=cand[0]
 if not match:qc['unresolved_or_outside_score_archive']+=1;continue
 side=('home' if r['selection_cn']==r['home_cn'] else 'away' if r['selection_cn']==r['away_cn'] else None) if r['market']=='AH' else {'大':'over','小':'under'}.get(r['selection_cn'])
 if side is None:qc['unknown_side']+=1;continue
 key=(match['fid'],r['market'])
 if key in pairset:qc['duplicate_fixture_market']+=1;continue
 pairset.add(key);resolved.append((email,ko,r,match,side,bool(anchor)))
print('PICKS',len(picks),'resolved',len(resolved),dict(qc),flush=True)
# Rebuild score-only prior using earlier UTC dates relative to actual email,
# not fixture date. Same original prediction function, no current outcomes.
src=(P/'m8_raw_capture_unindexed_frozen_replay_20261115.py').read_text()
assert all(a['date']<=b['date'] for a,b in zip(scorelist,scorelist[1:]))
attack=collections.defaultdict(float);defense=collections.defaultdict(float);baseline=collections.defaultdict(lambda:[math.log(1.45),math.log(1.15)])
def predict(r):
 h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']]
 return float(np.exp(np.clip(b[0]+attack[h]+defense[a],-2.5,2.3))),float(np.exp(np.clip(b[1]+attack[a]+defense[h],-2.5,2.3)))
def update(r):
 h=(r['league'],r['home']);a=(r['league'],r['away']);b=baseline[r['league']];x,y=predict(r);e1=r['hg']-x;e2=r['ag']-y
 for k,e in [(h,e1),(a,e2)]:attack[k]=.997*attack[k]+.025*float(np.clip(e,-4,4))
 for k,e in [(a,e1),(h,e2)]:defense[k]=.997*defense[k]+.025*float(np.clip(e,-4,4))
 b[0]+=.003*float(np.clip(e1,-4,4));b[1]+=.003*float(np.clip(e2,-4,4))
# Historical raw source index; actual receipts independently verified separately.
m5={str(q['match_id']):q for q in load('../data/m5-crown-authorized/crown-response-index.jsonl')}
inv={str(q['fixture_id']):q for q in load('m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl')}
archive=collections.defaultdict(list)
for a in load('m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl'):archive[str(a['fixture_id'])].append(a)
def pathquote(x,market,cap):
 b=next(z for z in x['bookmakers'] if z['slug']=='crown');key='asian' if market=='AH' else 'goal';ss=('home','away') if market=='AH' else ('over','under');v=[]
 for q in b.get(key+'_list') or []:
  try:
   t=local(q[4]);l,p1,p2=map(float,q[1:4])
   if t<=cap and min(p1,p2)>1 and abs(l*4-round(l*4))<1e-8:v.append((t,l,p1,p2))
  except Exception:continue
 for tag in ('open','close'):
  try:
   q=b[key][tag];t=local(q['time']);l=float(q['line']);p1,p2=map(lambda s:float(q[s]),ss)
   if t<=cap and min(p1,p2)>1 and abs(l*4-round(l*4))<1e-8:v.append((t,l,p1,p2))
  except Exception:continue
 return max(v,key=lambda z:z[0]) if v else None
def ftcheck(x,f):
 assert str(x['id'])==f['fid'] and local(x['start'])==dt(f['ko']) and all(str(x[k])==f[j] for k,j in [('l_id','league'),('h_id','home'),('a_id','away')])
def histquote(f,market,email):
 fid=f['fid'];c=[]
 if fid in m5:
  z=m5[fid];c.append((P.parent/'data/m5-crown-authorized/crown-responses'/f'{fid}.json',z['response_sha256']))
 if fid in inv:
  z=inv[fid];c.append((Path(z['source_file']),z.get('raw_sha256')))
 for p,sha in c:
  try:
   raw=p.read_bytes();assert sha and hash0(raw)==sha
   x=next(z for z in json.loads(raw)['data'] if str(z['id'])==fid);ftcheck(x,f);assert x['status']=='full' and (int(x['hg']),int(x['ag']))==(f['hg'],f['ag'])
   z=pathquote(x,market,email)
   if z:return z
  except Exception:continue
 return None
ixp=P.parent/'repos/mr1/data/prospective-market/shadow-v23/snapshot-index.jsonl'
index={(r['match_id'],r['snapshot_sha256']):r for r in map(json.loads,ixp.open()) if r['classification']=='SNAPSHOT_OK'}
frozen={r['fid'] for r in load('m8_foundation_20261115/historical_membership.jsonl')}
def actualquote(f,market,email):
 for r in sorted(archive[f['fid']],key=lambda r:r['received_utc'],reverse=True):
  try:
   recv=dt(r['received_utc']);assert recv<=email and dt(r['kickoff_utc'])==dt(f['ko']) and market in r['markets']
   ix=index[(f['fid'],r['snapshot_sha256'])];assert recv<=dt(ix['committed_at'])<=email
   p=Path(r['source_file']);a=json.loads(p.read_bytes());raw=a['raw_response'];assert hash0(raw.encode())==a['raw_sha256']==r['raw_sha256'] and dt(a['received_at'])==recv and a['classification']=='SNAPSHOT_OK'
   b=(p.parent.parent/'snapshot.json').read_bytes();sn=json.loads(b)
   assert hash0(b)==r['snapshot_sha256'] and sn['source_bookmaker']=='crown' and sn['source_bookmaker_verified'] is True and dt(sn['received_at'])==recv
   x=next(z for z in json.loads(raw)['data'] if str(z['id'])==f['fid']);ftcheck(x,f)
   # Verify committed actual receipt's quote independently against raw.
   key='asian' if market=='AH' else 'goal';ss=('home','away') if market=='AH' else ('over','under')
   k=next(z for z in x['bookmakers'] if z['slug']=='crown')[key]['close'];v=r['markets'][market];t=local(k['time'])
   assert t<=recv and t==dt(v['source_event_utc']) and float(k['line'])==v['line'] and all(float(k[s])==v['odds'][s] for s in ss)
   return (t,v['line'],v['odds'][ss[0]],v['odds'][ss[1]])
  except Exception:continue
 return None
def pmf(lam):
 a=[math.exp(-lam)]
 for j in range(1,40):a.append(a[-1]*lam/j)
 return np.array(a)
def ev(h,a,market,l,p1,p2):
 g=np.arange(40);p=pmf(h)[:,None]*pmf(a)[None,:];v=(g[:,None]-g[None,:]) if market=='AH' else (g[:,None]+g[None,:]);w=loss=0.
 for cut in (math.floor(l*2+1e-8)/2,math.ceil(l*2-1e-8)/2):
  q=v+cut if market=='AH' else v-cut
  w+=p[q>0].sum()/2;loss+=p[q<0].sum()/2
 return w*(p1-1)-loss,loss*(p2-1)-w
j=0;res=collections.defaultdict(list);quality=collections.Counter()
for email,ko,r,f,side,anch in sorted(resolved,key=lambda z:z[0]):
 while j<len(scorelist) and (email.date()-datetime.date.fromisoformat(scorelist[j]['date'])).days>=2:update(scorelist[j]);j+=1
 h,a=predict(f);market=r['market'];ss=('home','away') if market=='AH' else ('over','under')
 line=float(r['line'])*(-1 if side=='away' and market=='AH' else 1)
 # Only quote the same handicap/total; do not conflate opponent price with Crown.
 for label,fn in [('historical_asof',histquote),('actual_received',actualquote)]:
  q=fn(f,market,email)
  if not q:quality[label+'_no_quote']+=1;continue
  t,l,p1,p2=q
  if abs(l-line)>1e-8:quality[label+'_different_line']+=1;continue
  e1,e2=ev(h,a,market,l,p1,p2);model=ss[0] if e1>=e2 else ss[1]
  u={s:settle_score(market,l,s,f['hg'],f['ag'],p)[1] for s,p in zip(ss,(p1,p2))}
  res[label].append({'fid':f['fid'],'market':market,'date':f['date'],'same_direction':side==model,'opponent_at_crown':u[side],'independent_at_crown':u[model],'anchor':anch,'quote_age_hours':(email-t).total_seconds()/3600})
def st(v,k):
 n=len(v);u=sum(r[k] for r in v);return {'n':n,'U':round(u,3),'ROI':round(100*u/n,3) if n else None}
out={'source_commit':(A/'commit.txt').read_text().strip(),'source_sha256':{p.name:hash0(p.read_bytes()) for p in A.glob('*.json')},'registry_sha256':hash0(regp.read_bytes()),'email_count':len(picks),'prior_settlement_asof':ledger['generated_at'],'prior_settlement_n':len(known),'resolved':len(resolved),'identity_quality':dict(qc),'quote_quality':dict(quality),'cohorts':{}}
for name,z in res.items():
 out['cohorts'][name]={'n':len(z),'unique_fixtures':len({r['fid'] for r in z}),'previously_anchored':sum(r['anchor'] for r in z),'outside_eight':sum(r['fid'] not in frozen for r in z),'median_age_h':float(np.median([r['quote_age_hours'] for r in z])),'partitions':{}}
 for market in ('AH','OU','all'):
  for d in ('all','agreement','disagreement'):
   v=[r for r in z if (market=='all' or r['market']==market) and (d=='all' or r['same_direction']==(d=='agreement'))]
   out['cohorts'][name]['partitions'][market+'_'+d]={k:st(v,k) for k in ('opponent_at_crown','independent_at_crown')}
 print(name,out['cohorts'][name],flush=True)
out['overlap_pair_n']=len({(r['fid'],r['market']) for r in res['historical_asof']} & {(r['fid'],r['market']) for r in res['actual_received']})
out['historical_outside_eight']={k:st([r for r in res['historical_asof'] if r['fid'] not in frozen],k) for k in ('opponent_at_crown','independent_at_crown')}
out['actual_outside_eight']={k:st([r for r in res['actual_received'] if r['fid'] not in frozen],k) for k in ('opponent_at_crown','independent_at_crown')}
print('QUALITY',dict(quality),'OVERLAP',out['overlap_pair_n'],'OUTSIDE',out['historical_outside_eight'],out['actual_outside_eight'],flush=True)
(P/'m8_opponent_china_time_20261117.json').write_text(json.dumps(out,indent=2))
# Descriptive all-period partitions, no post-hoc rule or selection.
out['email_time_policy']='User confirmed China Standard Time UTC+8 for unmarked email timestamps; explicit offsets converted to UTC without relabeling.'
out['unmarked_email_n']=sum(dt(r['email_ts']).tzinfo is None for r in picks.values())
out['outside_eight_partitions']={}
for label,z in res.items():
 out['outside_eight_partitions'][label]={}
 for market in ('AH','OU'):
  for d in ('all','agreement','disagreement'):
   v=[r for r in z if r['fid'] not in frozen and r['market']==market and (d=='all' or r['same_direction']==(d=='agreement'))]
   out['outside_eight_partitions'][label][market+'_'+d]={k:st(v,k) for k in ('opponent_at_crown','independent_at_crown')}
 print('OUTSIDE',label,out['outside_eight_partitions'][label],flush=True)
 # All observed calendar weeks, no best/worst-week selection.
 out['cohorts'][label]['weeks']={}
 for w in sorted({datetime.date.fromisoformat(r['date']).strftime('%G-W%V') for r in z}):
  out['cohorts'][label]['weeks'][w]={}
  for market in ('AH','OU'):
   v=[r for r in z if r['market']==market and datetime.date.fromisoformat(r['date']).strftime('%G-W%V')==w]
   out['cohorts'][label]['weeks'][w][market]={k:st(v,k) for k in ('opponent_at_crown','independent_at_crown')}
(P/'m8_opponent_china_time_20261117.json').write_text(json.dumps(out,indent=2))
