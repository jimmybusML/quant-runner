import json,csv,gzip,datetime,collections,hashlib,unicodedata,re,difflib,bisect,math
from pathlib import Path
import numpy as np
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_transfer_activity_signal_20261117.py').read_text()
exec(s[:s.index('for market,sa,sb in')])
print('TRANSFER_LOADED',len(H),len(R),len(teammap),flush=True)
# Full event ID + club/date verification prevents rows from unrelated teams.
tm_game={}
for row in tm:
 try:
  date=datetime.date.fromisoformat(row['date']).toordinal()
  tm_game[row['game_id']]=(date,row['home_club_id'],row['away_club_id'])
 except Exception:continue
source_lineup=P/'m8_pregame_info_source_20261117/game_lineups.csv.gz'
sha_lineups=hashlib.sha256(source_lineup.read_bytes()).hexdigest()
assert sha_lineups=='5e83d6fad28364aadfea608013700cf09990062eede1ad9ef189189b0af47ba2'
mapped={v for v in teammap.values()}
starts=collections.defaultdict(set);qc=collections.Counter();date_max=0
with gzip.open(source_lineup,'rt',encoding='utf-8') as f:
 for row in csv.DictReader(f):
  qc['rows']+=1
  if row['type']!='starting_lineup':continue
  club=row['club_id'];gid=row['game_id'];player=row['player_id']
  if club not in mapped or not player:continue
  v=tm_game.get(gid)
  if v is None or club not in v[1:]:
   qc['no_matching_game_identity']+=1;continue
  try:
   rday=datetime.date.fromisoformat(row['date']).toordinal()
  except:qc['bad_date']+=1;continue
  if rday!=v[0]:qc['game_date_disagreement']+=1;continue
  if rday>end_date:
   qc['post_end_date']+=1;continue
  starts[(club,gid,rday)].add(player)
  qc['verified_starting_rows']+=1
groups=collections.defaultdict(list)
for (club,gid,day),players in starts.items():
 if not players:continue
 groups[club].append((day,gid,frozenset(players)))
 qc['game_club_lineups']+=1
 if len(players)==11:qc['complete_eleven_count']+=1
for c,v in groups.items():v.sort(key=lambda z:(z[0],z[1]))
line_dates={c:[x[0] for x in v] for c,v in groups.items()}
print('LINEUP',dict(qc),'clubs',len(groups),flush=True)
def side(club,target):
 arr=groups.get(club);dates=line_dates.get(club)
 if not arr:return None
 i=bisect.bisect_right(dates,target-3)
 if i<2:return None
 latest=arr[i-1];previous=arr[i-2]
 inter=len(latest[2]&previous[2]);uni=len(latest[2]|previous[2])
 if uni==0:return None
 prev1=target-latest[0];gap=latest[0]-previous[0]
 near=arr[bisect.bisect_left(dates,target-365):i]
 # Existing roster stability from previous games; no target lineup used.
 # Do not claim this captures same lineup that will actually play the target.
 return np.array([inter/uni,inter/max(len(latest[2]),1),
   math.log1p(prev1),math.log1p(gap),math.log1p(len(latest[2])),
   math.log1p(len(near))],float)
def build(q):
 x=np.full((len(q),12),np.nan);c=collections.Counter()
 for i,r in enumerate(q):
  day=datetime.date.fromisoformat(r['date']).toordinal()
  if day>end_date:c['beyond_source_end']+=1;continue
  l=r['league'];h=teammap.get((l,r['home_id']));a=teammap.get((l,r['away_id']))
  if not h or not a:c['unmapped_team']+=1;continue
  fh,fa=side(h,day),side(a,day)
  if fh is None or fa is None:c['missing_two_prior_lineup_records']+=1;continue
  x[i]=np.r_[fh-fa,fh+fa]
  c['paired_history']+=1
 return x,c
HL,hstat=build(H);RL,rstat=build(R)
hvalid=np.isfinite(HL).all(1);rvalid=np.isfinite(RL).all(1)
hmask=(HY>=2024)&(HY<=2026)&foundation&other&hvalid
rmask=rf&ro&rvalid
print('COVERAGE',dict(hstat),dict(rstat),'historical',int(hmask.sum()),'receipt',int(rmask.sum()),flush=True)
result={'method':'R50B prior two known match starting lineups proxy, previous two valid club-game XI records only, neither target starting lineup nor player availability used; compare Crown price path and transfer count data with or without prior XI stability. Historical external file lacks original first-receipt timestamps and stops July 2026, therefore retrospective feature only; not executable in Oct-Nov 2026. All groups in same cohort, no after-outcome profit selection, no new production gate. Team maps from R49 one-to-one strict contest/score/name anchors, targets use IDs only; two prior lineups computed only using dates three days before target. Missing lineups not filled.','external':{'url':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/game_lineups.csv.gz','sha256':sha_lineups,'source_rows':int(qc['rows']),'valid_game_club_lineups':int(qc['game_club_lineups']),'complete_eleven':int(qc['complete_eleven_count']),'provenance':dict(qc),'map_teams':len(teammap),'transfers_sha256':out['external_source']['transfer_sha256']},'coverage':{'historical':len(H),'receipt':len(R),'feature_h':int(hvalid.sum()),'feature_r':int(rvalid.sum()),'incremental_h':int(hmask.sum()),'incremental_r':int(rmask.sum()),'history_reasons':dict(hstat),'receipt_reasons':dict(rstat),'years':{str(y):int((hmask&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);rr=vec(R,sb)
 for mode in ('market_path','prior_lineup','market_prior_lineup','market_transfer_and_lineup'):
  def design(pairs,F,L):
   b=np.array([feature(a,b,'path') for a,b in pairs])
   if mode=='market_path':return b
   if mode=='prior_lineup':return np.column_stack((np.ones(len(L)),L))
   if mode=='market_prior_lineup':return np.column_stack((b,L))
   return np.column_stack((b,L,F[:,count_cols]))
  X=design(hist,HF,HL);Z=design(pairs,RF,RL)
  p=np.zeros(len(H));rp=np.zeros(len(R));fit={}
  for y in (2024,2025,2026):
   tr=(HY<y)&history_ind&hvalid;te=(HY==y)&hvalid;re=(RY==y)&rvalid
   assert tr.sum()>0 and HY[tr].max()<y
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@(hu[tr]-au[tr]))
   p[te]=((X[te]-mu)/sd)@beta
   if re.any():rp[re]=((Z[re]-mu)/sd)@beta
   fit[str(y)]={'train_n':int(tr.sum()),'features':len(beta)}
  hpay=np.where(p>=0,hu,au);rpay=np.where(rp>=0,ru,rr)
  z={'history':score(H,hpay,hmask),'receipt':score(R,rpay,rmask),
     'history_disjoint_receipt':score(H,hpay,hmask&history_ind),
     'years':{str(y):score(H,hpay,hmask&(HY==y)) for y in (2024,2025,2026)},'train':fit}
  result['models'][market+'_'+mode]=z
  small=lambda q:{k:v for k,v in q.items() if k!='weekly_counts'}
  print('RESULT',market,mode,small(z['history']),small(z['receipt']),'YEARS',{k:small(v) for k,v in z['years'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
result['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(result['foundation'].values())
(P/'m8_prior_lineup_stability_20261117.json').write_text(json.dumps(result,indent=2))
