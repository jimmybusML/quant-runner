import json,csv,gzip,datetime,collections,hashlib,unicodedata,re,difflib,bisect,math
from pathlib import Path
import numpy as np
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
source=P/'m8_pregame_info_source_20261117/games.csv.gz'
tm=list(csv.DictReader(gzip.open(source,'rt',encoding='utf-8')))
sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert sha=='142561989017d379bcf9e72bad0b87e0996bae0e7b710ebb3def9255f464c741'
# Explicit original49 league -> corresponding TM competition crosswalk.
cm={'1':'GB1','12':'IT1','14':'ES1','16':'L1','25':'FR1','29':'A1','31':'BE1','35':'TS1','37':'NL1','48':'PL1','51':'PO1','52':'RO1','61':'C1','62':'TR1','66':'SE1','70':'DK1','73':'JAP1','75':'RSK1','88':'NO1','141':'GR1','262':'SC1','290':'SA1','303':'SER1','319':'UKR1','26540':'KR1'}
covered=set(cm.values())
q=collections.Counter()
allft={}
for page in sorted((P.parent/'data/m5-crown-authorized/schedules').glob('*/page-*.raw.json')):
 l=page.parent.name
 if l not in cm:continue
 try:
  for z in json.loads(page.read_bytes())['data']['matches']:
   if z.get('status')!='full' or str(z.get('l_id'))!=l:continue
   fid=str(z.get('id'));home=str(z.get('h_id'));away=str(z.get('a_id'))
   if not fid or not home or not away or home==away:continue
   row=(l,home,away,z.get('h',''),z.get('a',''),str(z.get('hg')),str(z.get('ag')),datetime.datetime.fromisoformat(str(z.get('start')).replace(' ','T')).replace(tzinfo=ZoneInfo('Asia/Shanghai')).astimezone(datetime.timezone.utc).date().isoformat())
   if fid in allft and allft[fid]!=row:q['duplicate_crown_conflict']+=1;allft[fid]=None
   elif fid not in allft:allft[fid]=row
 except Exception as ex:q['error_'+type(ex).__name__]+=1
reg=json.load(open(P.parent/'repos/m1/data/football_display_names/display_names.json'))['teams']
def normalize(s):
 x=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode('ascii').lower()
 x=re.sub(r'\b(fc|cf|sc|afc|ac|club|football|soccer|fk|fk|as)\b',' ',x)
 return re.sub(r'[^a-z0-9]','',x)
def sim(a,b):
 a,b=normalize(a),normalize(b)
 if not a or not b:return 0.
 if a==b:return 1.
 if min(len(a),len(b))>=6 and (a in b or b in a):return .91
 return difflib.SequenceMatcher(None,a,b).ratio()
tmidx=collections.defaultdict(list);tmrec={}
compdate=collections.defaultdict(list)
for row in tm:
 try:
  comp=row['competition_id'];date=datetime.date.fromisoformat(row['date'])
  h,a=str(row['home_club_id']),str(row['away_club_id'])
  hg,ag=int(row['home_club_goals']),int(row['away_club_goals'])
  if comp not in covered or not h or not a:continue
  v=(date.toordinal(),comp,h,a,hg,ag,row['home_club_name'],row['away_club_name'],str(row['game_id']))
  compdate[(comp,v[0])].append(v);tmrec[str(row['game_id'])]=row
 except Exception:continue
# Build direct, conservative named anchors solely to resolve provider IDs.
anchors=collections.defaultdict(list);ambiguous=collections.Counter()
for f,z in allft.items():
 if z is None:continue
 l,h,a,hn,an,hg,ag,date=z
 try:
  day=datetime.date.fromisoformat(date).toordinal();hg=int(hg);ag=int(ag)
 except:continue
 cands=[]
 for t in (day-1,day,day+1):
  for v in compdate.get((cm[l],t),[]):
   if (hg,ag)!=(v[4],v[5]):continue
   s1,s2=sim(hn,v[6]),sim(an,v[7])
   if min(s1,s2)>=.85:cands.append((min(s1,s2),v))
 cands=sorted(cands,key=lambda e:(-e[0],e[1][-1]))
 if len(cands)==1 or (len(cands)>1 and cands[0][0]>cands[1][0]+.05):
  v=cands[0][1];anchors[(l,h)].append(v[2]);anchors[(l,a)].append(v[3]);q['named_anchors']+=1
 elif cands:q['ambiguous_named_anchors']+=1
teammap={}
reverse=collections.defaultdict(set)
for k,values in anchors.items():
 count=collections.Counter(values)
 if len(count)>1:q['team_id_conflict']+=1;continue
 v=next(iter(count));teammap[k]=v;reverse[(k[0],v)].add(k[1])
teammap={k:v for k,v in teammap.items() if len(reverse[(k[0],v)])==1}
q['accepted_crown_team_map']=len(teammap)
print('SOURCES',len(tm),len(allft),len(compdate),len(teammap),dict(q),flush=True)
# Build historical coach timeline from *completed earlier* TM games.
histories=collections.defaultdict(set);srcmax=datetime.date(2026,7,6).toordinal()
for z in tm:
 try:
  date=datetime.date.fromisoformat(z['date']).toordinal()
  for side in ('home','away'):
   club=z[side+'_club_id'];mgr=z[side+'_club_manager_name'].strip()
   if not club or not mgr:continue
   histories[club].add((date,z['game_id'],mgr))
 except:continue
series={k:sorted(v) for k,v in histories.items()}
ds={k:[v[0] for v in x] for k,x in series.items()}
def side_features(club,target):
 if not club:return None
 a=series.get(club,[]);dd=ds.get(club,[])
 ix=bisect.bisect_right(dd,target-3)
 if ix<2:return None
 prior=a[:ix]
 latest=prior[-1];lastmgr=latest[2]
 # Last observed match must be from earlier fixture, not target match.
 changes=[i for i in range(1,len(prior)) if prior[i][2]!=prior[i-1][2]]
 lastchange=changes[-1] if changes else None
 tail365=[z for z in prior if z[0]>=target-365]
 recent_changes=sum(prior[i][0]>=target-365 for i in changes)
 lastage=target-latest[0]
 tenure=sum(1 for r in reversed(prior) if r[2]==lastmgr) # contiguous only below
 tenure=0
 for z in reversed(prior):
  if z[2]!=lastmgr:break
  tenure+=1
 age=target-prior[lastchange][0] if lastchange is not None else None
 return [math.log1p(tenure),math.log1p(lastage),float(recent_changes),
         math.exp(-age/45) if age is not None else 0.,float(lastchange is not None),
         math.log1p(len(tail365))]
def build(qrows):
 x=np.full((len(qrows),12),np.nan);stats=collections.Counter()
 for i,r in enumerate(qrows):
  fid=str(r['fid']);l=str(r['league'])
  target=datetime.date.fromisoformat(r['date']).toordinal()
  if target>srcmax:stats['beyond_source_end']+=1;continue
  k=allft.get(fid)
  if k is None:
   # A verified registry name alone isn't a stable cross-provider identity.
   stats['no_cached_ft_identity']+=1;continue
  if (k[0],k[1],k[2],k[5],k[6],k[7])!=(l,str(r['home_id']),str(r['away_id']),str(r['hg']),str(r['ag']),r['date']):
   stats['crown_identity_score_conflict']+=1;continue
  h,a=teammap.get((l,k[1])),teammap.get((l,k[2]))
  if not h or not a:stats['unmapped_team']+=1;continue
  f1,f2=side_features(h,target),side_features(a,target)
  if not f1 or not f2:stats['no_two_prior_coach_records']+=1;continue
  # Six pair differences and sums, no target manager name used.
  # combine six with pooled sum: only 12 features (6 diff + 6 sum)
  x[i]=np.r_[np.array(f1)-np.array(f2),np.array(f1)+np.array(f2)]
  stats['matched_prior_coaches']+=1
 return x,stats
HF,hstat=build(H);RF,rstat=build(R)
hv=np.isfinite(HF).all(1);rv=np.isfinite(RF).all(1)
hm=(HY>=2024)&(HY<=2026)&foundation&other&hv;rm=rf&ro&rv
print('COVERAGE',dict(hstat),dict(rstat),'historical',int(hm.sum()),'receipt',int(rm.sum()),flush=True)
out={'method':'R49 previous-match manager continuity from external dated TM game-level manager fields, not target-match manager or current lineup. Source published as bulk retrospective archive; prior match coach is a recoverable prior-event fact, but release timing and historical source completeness unproven. Crown and TM match/team identity via explicit league crosswalk, unique named exact-score-date anchors and one-to-one team ID crosswalk; non-matching rows remain missing. Training excludes actual receipt FIDs and uses earlier calendar years only; exact T12 Crown odds for AH/OU payout. Same sample all variants, no profit-triggered league/week/side filtering and no production gates. TM dataset stops July 6, 2026 so Oct-Nov 2026 receipt retrospective cannot be validated; no substitution or fake real-time availability. Source excludes match on same/preceding two UTC days in coach features. No target score/card/manager in the feature calculation, only historical identity joining.','external_source':{'url':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/games.csv.gz','sha256':sha,'rows':len(tm),'max_date':max(z['date'] for z in tm),'mapped_leagues':len(cm),'mapped_teams':len(teammap),'identity_checks':dict(q)},'coverage':{'history_pairs':len(H),'receipt_pairs':len(R),'historical_feature':int(hv.sum()),'receipt_feature':int(rv.sum()),'incremental_history':int(hm.sum()),'incremental_receipt':int(rm.sum()),'history_fail':dict(hstat),'receipt_fail':dict(rstat),'annual_incremental':{str(y):int((hm&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);rr=vec(R,sb)
 for mode in ('market','prior_manager','manager_market'):
  def design(pp,F):
   base=np.array([feature(a,b,'path') for a,b in pp])
   if mode=='market':return base
   if mode=='prior_manager':return np.column_stack((np.ones(len(F)),F))
   return np.column_stack((base,F))
  X=design(hist,HF);Z=design(pairs,RF)
  pred=np.zeros(len(H));rpred=np.zeros(len(R));trained={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv;re=(RY==yr)&rv
   if tr.sum()==0:continue
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   coef=np.linalg.solve(xx.T@xx+pen,xx.T@(hu[tr]-au[tr]))
   pred[te]=((X[te]-mu)/sd)@coef
   if re.any():rpred[re]=((Z[re]-mu)/sd)@coef
   trained[str(yr)]={'train_n':int(tr.sum()),'features':len(coef)}
  hp=np.where(pred>=0,hu,au);rp=np.where(rpred>=0,ru,rr)
  z={'historical':score(H,hp,hm),'historical_disjoint_receipt':score(H,hp,hm&history_ind),
     'receipt':score(R,rp,rm),'years':{str(y):score(H,hp,hm&(HY==y)) for y in (2024,2025,2026)},'train':trained}
  out['models'][market+'_'+mode]=z
  compact=lambda k:{i:v for i,v in k.items() if i!='weekly_counts'}
  print('RESULT',market,mode,'H',compact(z['historical']),'R',compact(z['receipt']),'YEAR',{y:compact(t) for y,t in z['years'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_prior_manager_turnover_20261117.json').write_text(json.dumps(out,indent=2))
