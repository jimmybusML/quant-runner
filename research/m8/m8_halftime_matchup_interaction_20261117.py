import json,collections,hashlib,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Score path is only observed historic information. First-half scores have
# occasionally inconsistent source data; exclude those records from feature
# HISTORY, never fabricate or correct them.
scope={str(r['league']) for r in H+R}
def dt0(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 return t.astimezone(datetime.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc)
seen=collections.defaultdict(set);quality=collections.Counter()
for page in sorted((P.parent/'data/m5-crown-authorized/schedules').glob('*/page-*.raw.json')):
 if page.parent.name not in scope:continue
 try:
  b=page.read_bytes();quality['pages']+=1
  for q in json.loads(b)['data']['matches']:
   if q.get('status')!='full':continue
   l,h,a,f=map(str,(q['l_id'],q['h_id'],q['a_id'],q['id']))
   if l!=page.parent.name or not h or not a or h==a:continue
   try:
    hg,ag,fh,fa=map(int,(q['hg'],q['ag'],q['hf_hg'],q['hf_ag']))
    if not (0<=fh<=hg and 0<=fa<=ag):quality['invalid_half_goal_consistency']+=1;continue
   except (ValueError,TypeError,KeyError):quality['missing_half_goals']+=1;continue
   t=dt0(q['start'])
   seen[f].add((l,h,a,t.date().toordinal(),hg,ag,fh,fa))
 except Exception as ex:quality['page_error_'+type(ex).__name__]+=1
ft={f:next(iter(v)) for f,v in seen.items() if len(v)==1}
quality['conflicting_ids']=len(seen)-len(ft)
quality['cached_valid_unique']=len(ft)
# Revalidate supplemental FT receipt archive with same raw evidence as R44.
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
  hg,ag,fh,fa=map(int,(z['hg'],z['ag'],z['hf_hg'],z['hf_ag']))
  assert (hg,ag)==(int(e['home_goals']),int(e['away_goals']))
  if not (0<=fh<=hg and 0<=fa<=ag):quality['supplement_invalid_halves']+=1;continue
  v=(l,h,a,t.date().toordinal(),hg,ag,fh,fa)
  if f in supp and supp[f]!=v:collisions.add(f)
  supp[f]=v
 except Exception as ex:quality['supplement_error_'+type(ex).__name__]+=1
for f in collisions:supp.pop(f,None)
quality['supplement_valid']=len(supp);quality['supplement_conflicts']=len(collisions)
ft.update(supp)
print('FT',len(ft),dict(quality),flush=True)
events=collections.defaultdict(list)
for f,(l,h,a,day,hg,ag,fh,fa) in ft.items():
 # Home first-half scored & conceded, second-half scored & conceded
 events[l].append((day,h,a,fh,fa,hg-fh,ag-fa))
for v in events.values():v.sort()
# Rolling 365-day observations ending at least two full UTC days before
# target kickoff. The rolling duration and zero-sample exclusion are DATA
# ANALYSIS conventions only; not production rules or arbitrarily set GATES.
def features(q):
 out=np.full((len(q),14),np.nan);by=collections.defaultdict(list)
 for i,r in enumerate(q):by[str(r['league'])].append((datetime.date.fromisoformat(r['date']).toordinal(),i,r))
 for l,targets in by.items():
  ev=events.get(l,[]);acc=collections.defaultdict(lambda:np.zeros(5));hi=lo=0;last=None
  def apply(z,sgn):
   day,h,a,h1,a1,h2,a2=z
   acc[h]+=sgn*np.array((1,h1,a1,h2,a2))
   acc[a]+=sgn*np.array((1,a1,h1,a2,h2))
  for day,i,r in sorted(targets,key=lambda z:z[0]):
   if day!=last:
    cutoff=day-3
    while hi<len(ev) and ev[hi][0]<=cutoff:apply(ev[hi],1);hi+=1
    while lo<hi and ev[lo][0]<=cutoff-365:apply(ev[lo],-1);lo+=1
    last=day
   home,away=str(r['home_id']),str(r['away_id'])
   u=acc[home];v=acc[away]
   if min(u[0],v[0])<=0:continue
   # h / a in order: first scored, first conceded, second scored, second conceded.
   h1,ha1,h2,ha2=u[1:]/u[0]
   a1,aa1,a2,aa2=v[1:]/v[0]
   # Explicit interactions test opponent temporal attack vs conceding vulnerability.
   # These products are not known physical pressure or tactics; score-timing proxies.
   matchup=(h1*aa1,a1*ha1,h2*aa2,a2*ha2)
   styles=((h1-h2)*(aa1-aa2),(a1-a2)*(ha1-ha2))
   out[i]=[h1,ha1,h2,ha2,a1,aa1,a2,aa2,*matchup,*styles]
 return out
HF=features(H);RF=features(R)
hvalid=np.isfinite(HF).all(1);rvalid=np.isfinite(RF).all(1)
hm1=hm&hvalid;rm1=rm&rvalid
print('FEATURE_COVERAGE',len(H),int(hvalid.sum()),int(hm1.sum()),len(R),int(rvalid.sum()),int(rm1.sum()),flush=True)
a,b,c,d=state(hx);ra,rb,rc,rd=state(rx)
out={'method':'R45 opponent temporal goal-style interactions, first/second-half scoring and conceding rates from preceding cached 365-day FT with a three UTC-date lag. Market-only response vs response+eight half-goal main effects vs response+eight main + six opponent pair products. Team-history feature windows are experimental, not eligibility or trading rules; missing half scores not filled in; no selection on realized results. Predict pregame total and conditional home goal share using previous-calendar-year Poisson/binomial offset models, ridge100 inherited from prior research; training excludes all actual-receipt target IDs. Same eligible fixtures for every model. FT cache later recovered is a retrospective proxy, not evidence that those records were accessible pregame. Source half scores are not verified physical playing styles. Crown quote input, T12 observation and cohort exclusions inherited from earlier R25 research; historical and actual receipt replay distinct, not independently precommitted forward test.','source':dict(quality),'coverage':{'historical_full':len(H),'receipt_full':len(R),'historical_feature_matched':int(hvalid.sum()),'receipt_feature_matched':int(rvalid.sum()),'incremental_historical':int(hm1.sum()),'incremental_receipt':int(rm1.sum()),'historical_years':{str(y):int((hm1&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
for mode in ('market_response','half_main','opponent_interaction'):
 def design(x,f):
  z=make_x(x,'response')
  if mode=='market_response':return z
  if mode=='half_main':return np.column_stack((z,f[:,:8]))
  return np.column_stack((z,f))
 X=design(hx,HF);Z=design(rx,RF)
 ht,hf=rates(hx);rt,rf0=rates(rx);fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind&hvalid;te=(HY==yr)&hvalid;re=(RY==yr)&rvalid
  ht[te],bt=fit_total(X[tr],hyn[tr],b[tr],X[te],b[te]);hf[te],bf=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],X[te],d[te])
  if re.any():
   rt[re],_=fit_total(X[tr],hyn[tr],b[tr],Z[re],rb[re]);rf0[re],_=fit_share(X[tr],hyh[tr],hyn[tr],d[tr],Z[re],rd[re])
  fits[str(yr)]={'train_n':int(tr.sum()),'n_features':int(X.shape[1]),'total_coef':bt.tolist(),'share_coef':bf.tolist()}
 result={'history_probability':evaluate(H,ht,hf,hm1),'receipt_probability':evaluate(R,rt,rf0,rm1),'fit':fits,'markets':{}}
 for m in ('AH','OU'):
  p=pay(H,ht,hf,m);r=pay(R,rt,rf0,m)
  z={'history':score(H,p,hm1),'history_disjoint_receipt':score(H,p,hm1&history_ind),'receipt':score(R,r,rm1),'year':{str(yr):score(H,p,hm1&(HY==yr)) for yr in (2024,2025,2026)}}
  result['markets'][m]=z
  print('RESULT',mode,m,slim(z['history']),slim(z['receipt']),'annual',{y:slim(v) for y,v in z['year'].items()},flush=True)
 out['models'][mode]=result
 print('PROB',mode,result['history_probability'],result['receipt_probability'],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_halftime_matchup_interaction_20261117.json').write_text(json.dumps(out,indent=2))
