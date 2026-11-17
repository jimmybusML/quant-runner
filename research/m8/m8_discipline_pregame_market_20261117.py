import json,collections,hashlib,datetime,math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Independent from new match outcomes: historic completed fixtures only
# and pregame lookup by day, not the target's current cards.
scope={str(r['league']) for r in H+R}
def dt0(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
seen=collections.defaultdict(set);quality=collections.Counter()
for page in sorted((P.parent/'data/m5-crown-authorized/schedules').glob('*/page-*.raw.json')):
 if page.parent.name not in scope:continue
 try:
  raw=page.read_bytes();quality['pages']+=1
  for q in json.loads(raw)['data']['matches']:
   if q.get('status')!='full':continue
   l,h,a,f=map(str,(q['l_id'],q['h_id'],q['a_id'],q['id']))
   if l!=page.parent.name or not h or not a or h==a:continue
   try:
    hy,ay,hr,ar=map(int,(q['hyc'],q['ayc'],q['hrc'],q['arc']))
    if min(hy,ay,hr,ar)<0:quality['negative_cards']+=1;continue
    # Verify that recorded FT score is a valid fixture, but never use it as a feature.
    hg,ag=map(int,(q['hg'],q['ag']))
    if min(hg,ag)<0:quality['invalid_FT_goals']+=1;continue
   except (TypeError,ValueError,KeyError):quality['missing_cards_or_FT']+=1;continue
   t=dt0(q['start'])
   seen[f].add((l,h,a,t.date().toordinal(),hy,ay,hr,ar))
 except Exception as ex:quality['page_error_'+type(ex).__name__]+=1
ft={f:next(iter(v)) for f,v in seen.items() if len(v)==1}
quality['conflicting_ids']=len(seen)-len(ft);quality['cached_valid_unique']=len(ft)
# M7 receipt-side FT extension; no new data retrieval. Exact raw hash & event checks.
rawcache={};supp={};collisions=set()
for e in map(json.loads,(P/'m7/m7_schedule_verified_FT_receipt_events_20261111.jsonl').open()):
 f=str(e['fixture_id'])
 if f in seen or str(e['league_id']) not in scope:continue
 try:
  k=(e['raw_path'],e['raw_sha256'])
  if k not in rawcache:
   raw=Path(k[0]).read_bytes();assert hashlib.sha256(raw).hexdigest()==k[1]
   rawcache[k]={str(z['id']):z for z in json.loads(raw)['data']['matches']}
  z=rawcache[k][f];t=dt0(z['start']);obs=dt0(e['observed_at_utc'])
  assert t==dt0(e['kickoff_utc']) and obs>t and z['status']=='full'
  l,h,a=map(str,(z['l_id'],z['h_id'],z['a_id']))
  assert (l,h,a)==tuple(map(str,(e['league_id'],e['home_id'],e['away_id'])))
  hg,ag=int(z['hg']),int(z['ag']);assert (hg,ag)==(int(e['home_goals']),int(e['away_goals']))
  hy,ay,hr,ar=map(int,(z['hyc'],z['ayc'],z['hrc'],z['arc']))
  if min(hy,ay,hr,ar)<0:quality['supplement_negative_cards']+=1;continue
  v=(l,h,a,t.date().toordinal(),hy,ay,hr,ar)
  if f in supp and supp[f]!=v:collisions.add(f)
  supp[f]=v
 except Exception as ex:quality['supplement_error_'+type(ex).__name__]+=1
for f in collisions:supp.pop(f,None)
quality['supplement']=len(supp);quality['supplement_conflicts']=len(collisions)
ft.update(supp)
print('FT',len(ft),dict(quality),flush=True)
events=collections.defaultdict(list)
for f,(l,h,a,day,hy,ay,hr,ar) in ft.items():events[l].append((day,h,a,hy,ay,hr,ar))
for v in events.values():v.sort()
# The two windows and three-day lag are experimental feature definitions
# only. Team-side totals do not use the current fixture's future cards.
def features(q):
 out=np.full((len(q),14),np.nan)
 by=collections.defaultdict(list)
 for i,r in enumerate(q):
  day=datetime.date.fromisoformat(r['date']).toordinal()
  by[str(r['league'])].append((day,i,r))
 for l,targets in by.items():
  ev=events.get(l,[])
  accum={w:collections.defaultdict(lambda:np.zeros(3)) for w in (90,365)}
  lo={90:0,365:0};hi=0;last=None
  def apply(w,z,sgn):
   day,h,a,hy,ay,hr,ar=z
   accum[w][h]+=sgn*np.array([1,hy,hr])
   accum[w][a]+=sgn*np.array([1,ay,ar])
  for day,i,r in sorted(targets,key=lambda z:z[0]):
   if day!=last:
    cutoff=day-3
    while hi<len(ev) and ev[hi][0]<=cutoff:
     for w in accum:apply(w,ev[hi],1)
     hi+=1
    for w in accum:
     while lo[w]<hi and ev[lo[w]][0]<=cutoff-w:
      apply(w,ev[lo[w]],-1);lo[w]+=1
    last=day
   h,a=str(r['home_id']),str(r['away_id'])
   lh,la=accum[365][h],accum[365][a];sh,sa=accum[90][h],accum[90][a]
   if min(lh[0],la[0],sh[0],sa[0])<=0:continue
   hy,hr=lh[1:]/lh[0];ay,ar=la[1:]/la[0]
   hs,hrs=sh[1:]/sh[0];as_,ars=sa[1:]/sa[0]
   # Main effects including team asymmetry and recent change.
   base=[hy-ay,hy+ay,hr-ar,hr+ar,
    hs-as_,hs+as_,hrs-ars,hrs+ars,
    math.log1p(lh[0]+la[0]),math.log1p(sh[0]+sa[0])]
   # Nonlinear joint-red / yellow asymmetry, not a causal discipline claim.
   interact=[hy*ar-ay*hr,hr*ar,(hy-ay)*(hr-ar),(hs-hy)-(as_-ay)]
   out[i]=base+interact
 return out
HF=features(H);RF=features(R)
hvalid=np.isfinite(HF).all(1);rvalid=np.isfinite(RF).all(1)
hm1=hm&hvalid;rm1=rm&rvalid
print('COVERAGE',len(H),int(hvalid.sum()),int(hm1.sum()),len(R),int(rvalid.sum()),int(rm1.sum()),flush=True)
out={'method':'R48 independent pregame discipline-history features. Reconstruct same-league home/away yellow/red card rates from archived earlier FT only, 365/90 day trailing windows through preceding three UTC dates; explicit zero-sample missingness, no current-game cards in features, no ROI based fixture selection. Compare original Crown T24/T12 priced response baseline with discipline main effects and interactions under previous-year fixed-ridge100 realized AH/OU 1U payout-difference regression. Fourteen features built from team prior yellow/red records. Values are recovered retrospectively from historical schedules, not proven independently accessible at that time; not an independently locked forward. Previous-year fit excludes all receipt IDs. Original eight and prior candidates excluded only for retrospective incremental results, not a new realtime eligibility gate. All markets/years/weeks included.','source':dict(quality),'coverage':{'historical_full':len(H),'receipt_full':len(R),'feature_history':int(hvalid.sum()),'feature_receipt':int(rvalid.sum()),'historical_incremental':int(hm1.sum()),'receipt_incremental':int(rm1.sum()),'year_counts':{str(y):int((hm1&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
def design(x,f,mode):
 z=make_x(x,'response')
 if mode=='market':return z
 if mode=='discipline':return np.column_stack((z,f[:,:10]))
 return np.column_stack((z,f))
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);rminus=vec(R,sb)
 for mode in ('market','discipline','discipline_interaction'):
  X=design(hx,HF,mode);Z=design(rx,RF,mode)
  hp=np.zeros(len(H));rp=np.zeros(len(R));fit={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind&hvalid;te=(HY==yr)&hvalid;re=(RY==yr)&rvalid
   assert HY[tr].max()<yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xt=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xt.T@xt+pen,xt.T@(hu[tr]-au[tr]))
   hp[te]=((X[te]-mu)/sd)@beta
   if re.any():rp[re]=((Z[re]-mu)/sd)@beta
   fit[str(yr)]={'train_n':int(tr.sum()),'coefficients':beta.tolist()}
  p=np.where(hp>=0,hu,au);r=np.where(rp>=0,ru,rminus)
  z={'history':score(H,p,hm1),'history_disjoint_receipt':score(H,p,hm1&history_ind),'receipt':score(R,r,rm1),'years':{str(yr):score(H,p,hm1&(HY==yr)) for yr in (2024,2025,2026)},'fit':fit}
  out['models'][market+'_'+mode]=z
  slim=lambda q:{k:v for k,v in q.items() if k!='weekly_counts'}
  print('RESULT',market,mode,slim(z['history']),slim(z['receipt']),'annual',{y:slim(s) for y,s in z['years'].items()},'disjoint',slim(z['history_disjoint_receipt']),flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_discipline_pregame_market_20261117.json').write_text(json.dumps(out,indent=2))
