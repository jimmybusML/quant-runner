import json,collections,hashlib,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Use reconstructed trailing league results, not official season standings.
# No invented season start dates, point deductions or playoff rules.
# Match histories are observed cached FT, not proof of exact historical receipt.
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
   if l!=page.parent.name or h==a or not h or not a:continue
   t=dt0(q['start']);hg,ag=int(q['hg']),int(q['ag'])
   if min(hg,ag)<0:continue
   seen[f].add((l,h,a,t.date().toordinal(),hg,ag))
 except Exception as ex:quality['page_error_'+type(ex).__name__]+=1
ft={f:next(iter(v)) for f,v in seen.items() if len(v)==1};quality['conflicting_ids']=len(seen)-len(ft)
# Independent FT supplement for recently-observed receipt fixtures; source IDs and original raw hashes verified.
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
  v=(l,h,a,t.date().toordinal(),hg,ag)
  if f in supp and supp[f]!=v:collisions.add(f)
  supp[f]=v
 except Exception as ex:quality['supplement_error_'+type(ex).__name__]+=1
for f in collisions:supp.pop(f,None)
quality['supplement']=len(supp);quality['supplement_conflicts']=len(collisions)
ft.update(supp)
print('SCHEDULE',len(ft),dict(quality),flush=True)
events=collections.defaultdict(list)
for f,(l,h,a,day,hg,ag) in ft.items():
 events[l].append((day,h,a,hg,ag))
for v in events.values():v.sort()
# Rolling table as of prior UTC dates, same three-day lag as prior team research.
# A trailing 365-day table is an intentionally different proxy from actual season points.
# All teams having observed league results enter rank percentiles; no minimum sample cutoff.
# A second window (90 days) measures points momentum relative to longer table.
def features(q):
 f=np.full((len(q),12),np.nan);by=collections.defaultdict(list)
 for i,r in enumerate(q):
  day=datetime.date.fromisoformat(r['date']).toordinal()
  by[str(r['league'])].append((day,i,r))
 for l,targets in by.items():
  ev=events.get(l,[])
  acc={w:collections.defaultdict(lambda:np.zeros(3)) for w in (90,365)}
  lo={90:0,365:0};hi=0
  def apply(w,z,sgn):
   day,h,a,hg,ag=z
   p1=3 if hg>ag else 1 if hg==ag else 0;p2=3 if ag>hg else 1 if hg==ag else 0
   acc[w][h]+=sgn*np.array([1,p1,hg-ag]);acc[w][a]+=sgn*np.array([1,p2,ag-hg])
  last=None
  for day,i,r in sorted(targets,key=lambda z:z[0]):
   if day!=last:
    cutoff=day-3
    while hi<len(ev) and ev[hi][0]<=cutoff:
     for w in acc:apply(w,ev[hi],1)
     hi+=1
    for w in acc:
     while lo[w]<hi and ev[lo[w]][0]<=cutoff-w:
      apply(w,ev[lo[w]],-1);lo[w]+=1
    current={k:(v[1]/v[0],v[2]/v[0]) for k,v in acc[365].items() if v[0]>0}
    ordered=sorted(current.values());last=day
   h,a=str(r['home_id']),str(r['away_id'])
   if h not in current or a not in current:continue
   v,z=acc[365][h],acc[365][a]
   vh,va=acc[90][h],acc[90][a]
   # Short window absent -> missing; no fake points or arbitrary shrinkage.
   if min(vh[0],va[0])<=0:continue
   hp,ap=v[1]/v[0],z[1]/z[0];hd,ad=v[2]/v[0],z[2]/z[0]
   sh,sa=vh[1]/vh[0],va[1]/va[0]
   def pct(k):return sum(x<current[k] for x in ordered)/max(1,len(ordered)-1)
   ph,pa=pct(h),pct(a)
   f[i]=[hp-ap,hp+ap,hd-ad,hd+ad,ph-pa,ph+pa,abs(ph-pa),np.log1p(v[0]+z[0]),sh-hp-(sa-ap),sh-hp+sa-ap,np.log1p(vh[0]+va[0]),abs(hp-ap)]
 return f
HF=features(H);RF=features(R);hvalid=np.isfinite(HF).all(1);rvalid=np.isfinite(RF).all(1)
hm1=hm&hvalid;rm1=rm&rvalid
print('MATCH',len(H),int(hvalid.sum()),int(hm1.sum()),len(R),int(rvalid.sum()),int(rm1.sum()),flush=True)
out={'method':'R44 rolling league table proxy using cached previous FT results only, 365/90 day points per game, goal differential, rank percentile of teams with observed matches, recent relative points momentum and played counts. Three UTC day lag, same R26 research convention. No true season standings, official deductions, relegation/promotion or motivation claims. Source coverage incomplete; no invented missing values. Prior calendar-year training excludes receipt archive ID targets; same matched cohort across models. No league selection or new strategy gates. Retrospective complement, not tradeable real-time membership. Historical and actual receipts distinct.', 'schedule':dict(quality),'coverage':{'history_full':len(H),'history_feature_matched':int(hvalid.sum()),'historical_incremental':int(hm1.sum()),'receipt_full':len(R),'receipt_feature_matched':int(rvalid.sum()),'receipt_incremental':int(rm1.sum())},'models':{}}
a,b,c,d=state(hx);ra,rb,rc,rd=state(rx)
for mode in ('global','table_only','table_market'):
 def design(x,f):
  base=make_x(x,'response')
  if mode=='global':return base
  if mode=='table_only':return np.column_stack((np.ones(len(x)),f))
  return np.column_stack((base,f))
 X=design(hx,HF);Z=design(rx,RF)
 ht,hf=rates(hx);rt,rf0=rates(rx);fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind&hvalid;te=(HY==yr)&hvalid;re=(RY==yr)&rvalid
  ht[te],bt=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te]);hf[te],bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
  if re.any():
   rt[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb[re]);rf0[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd[re])
  fits[str(yr)]={'train_n':int(tr.sum()),'total_coef':bt.tolist(),'share_coef':bf.tolist()}
 result={'history_probability':evaluate(H,ht,hf,hm1),'receipt_probability':evaluate(R,rt,rf0,rm1),'fit':fits,'markets':{}}
 for m in ('AH','OU'):
  p=pay(H,ht,hf,m);r=pay(R,rt,rf0,m)
  z={'history':score(H,p,hm1),'history_disjoint_receipt':score(H,p,hm1&history_ind),'receipt':score(R,r,rm1),'year':{str(yr):score(H,p,hm1&(HY==yr)) for yr in (2024,2025,2026)}}
  result['markets'][m]=z
  print('RESULT',mode,m,slim(z['history']),slim(z['receipt']),'annual',{y:slim(v) for y,v in z['year'].items()},flush=True)
 out['models'][mode]=result
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_league_table_context_20261117.json').write_text(json.dumps(out,indent=2))
