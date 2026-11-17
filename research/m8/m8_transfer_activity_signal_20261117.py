import json,csv,gzip,datetime,collections,hashlib,unicodedata,re,difflib,bisect,math
from pathlib import Path
import numpy as np
from zoneinfo import ZoneInfo
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_prior_manager_turnover_20261117.py').read_text()
exec(s[:s.index('# Build historical coach timeline')])
# Reuse only the externally matched (league, teamID) anchors from R49.
# Crown fixture IDs, home and away team IDs, result and UTC date were
# independently verified at R22; this is a static research identity join.
source_transfer=P/'m8_pregame_info_source_20261117/transfers.csv.gz'
raw=source_transfer.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='90326983daf7e6ac7aabdfe62b90936d9bf1dd2171e53dec75c3751eb1620a83'
trans=list(csv.DictReader(gzip.open(source_transfer,'rt',encoding='utf-8')))
quality=collections.Counter()
tx={};end_date=datetime.date(2026,7,6).toordinal()
for row in trans:
 try:
  day=datetime.date.fromisoformat(row['transfer_date']).toordinal()
  src,dst=row['from_club_id'],row['to_club_id']
  player=row['player_id']
  if not src or not dst or src==dst or not player:
   quality['incomplete_or_same_club']+=1;continue
  if day>end_date:
   quality['future_or_post_dataset_cutoff']+=1;continue
  if day<datetime.date(2019,1,1).toordinal():continue
  key=(player,day,src,dst)
  if key in tx:
   quality['duplicate_transfer']+=1
   # Different retrospective values of same transfer make value ambiguous.
   if tx[key][4]!=row['market_value_in_eur']:quality['conflicting_duplicate_transfer_value']+=1
   continue
  value=row['market_value_in_eur'];valid=bool(value)
  val=float(value) if valid else 0.
  assert val>=0 and math.isfinite(val)
  tx[key]=(day,src,dst,player,value,val)
  quality['valid_transfer']+=1
  if valid:quality['with_transfer_market_value']+=1
 except Exception as ex:quality['transfer_error_'+type(ex).__name__]+=1
# v = [count incoming, count outgoing, known-value incoming/outgoing in EUR millions, known-count incoming/outgoing]
events=collections.defaultdict(list)
for day,src,dst,player,value,val in tx.values():
 known=int(bool(value))
 events[src].append((day,np.array([0,1,0,val/1e6,0,known],dtype=float)))
 events[dst].append((day,np.array([1,0,val/1e6,0,known,0],dtype=float)))
seq={};ds={};prefix={}
for club,arr in events.items():
 arr.sort(key=lambda e:e[0])
 ds[club]=np.array([v[0] for v in arr],int)
 seq[club]=arr
 prefix[club]=np.vstack((np.zeros(6),np.cumsum([v[1] for v in arr],axis=0)))
print('SOURCE',len(trans),'deduplicated',len(tx),'clubs',len(seq),'qc',dict(quality),flush=True)
def club_features(club,target):
 if not club:return None
 dates=ds.get(club)
 if dates is None:
  # No historical transfer observed in TM source for a mapped team is
  # explicitly 0 observed event, not an inferred full roster.
  return np.zeros(12)
 pc=prefix[club]
 upto=bisect.bisect_right(dates,target-3)
 n90=pc[upto]-pc[bisect.bisect_left(dates,target-90)]
 n365=pc[upto]-pc[bisect.bisect_left(dates,target-365)]
 return np.r_[n90,n365]
def features(rows):
 X=np.full((len(rows),24),np.nan);stats=collections.Counter()
 for i,r in enumerate(rows):
  target=datetime.date.fromisoformat(r['date']).toordinal()
  if target>end_date:stats['beyond_source_end']+=1;continue
  l=str(r['league']);h=teammap.get((l,str(r['home_id'])));a=teammap.get((l,str(r['away_id'])))
  if h is None or a is None:stats['unmapped_team']+=1;continue
  hv=club_features(h,target);av=club_features(a,target)
  X[i]=np.r_[hv-av,hv+av]
  stats['mapped_teams']+=1
  if float(hv[0]+hv[1]+av[0]+av[1])>0:stats['some_transfer_last90']+=1
  if float(hv[6]+hv[7]+av[6]+av[7])>0:stats['some_transfer_last365']+=1
 return X,stats
HF,hstat=features(H);RF,rstat=features(R)
hv=np.isfinite(HF).all(1);rv=np.isfinite(RF).all(1)
hm=(HY>=2024)&(HY<=2026)&foundation&other&hv;rm=rf&ro&rv
assert int(hm.sum())>3000
print('COVERAGE',dict(hstat),dict(rstat),'historical',int(hm.sum()),'receipt',int(rm.sum()),'annual',[int((hm&(HY==y)).sum()) for y in (2024,2025,2026)],flush=True)
# 24 feature dimensions include count and transfer-history value (not
# official current squad value); value fields may be absent and are labelled.
# Count-only uses six of the twelve difference and sums from 90/365 windows.
count_cols=[0,1,6,7,12,13,18,19]
value_cols=[2,3,4,5,8,9,10,11,14,15,16,17,20,21,22,23]
out={'method':'R50 historical transfer activity observed as dated effective transfer records, not dated announcements or proof of historical actual knowledge. Map 25 matching Crown leagues and a conservative one-to-one team ID bridge from R49, use only transfers effective at least 3 UTC days before target. Markets entirely Crown T24/T12 quote event; no outcome-driven leg selection and all previously approved eight groups frozen. Compare baseline price path vs club inbound/outbound count momentum vs value/missingness additional fields via strictly prior-calendar-year model fit, excluding actual receipt target IDs. 90/365 day window are experimental historical features and not a production gate. Market values are retrospective transfer-time estimates with missingness, not live or independently verifiable contemporaneous team roster valuations; the future-dated transfers in source are excluded. Original 8 and old unpromoted OU candidates are subtracted only for hindsight incremental cohort reporting. Source stopped 2026-07-06, October-November actual receipt cohort invalid for this dataset; no ROI claimed.','external_source':{'dataset':'dcaribou/transfermarkt-datasets, transfers.csv.gz','uri':'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/transfers.csv.gz','transfer_sha256':hashlib.sha256(raw).hexdigest(),'transfer_rows':len(trans),'unique_transfer_rows_used':len(tx),'games_sha256':sha,'date_cutoff':'2026-07-06','team_crosswalk_count':len(teammap),'mapped_leagues':len(cm),'transfer_quality':dict(quality)},'coverage':{'historical_pairs':len(H),'receipt_pairs':len(R),'historical_feature_covered':int(hv.sum()),'receipt_feature_covered':int(rv.sum()),'historical_incremental':int(hm.sum()),'receipt_incremental':int(rm.sum()),'historical_disjoint_receipt':int((hm&history_ind).sum()),'history_reasons':dict(hstat),'receipt_reasons':dict(rstat),'year_n':{str(y):int((hm&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);rr=vec(R,sb)
 for mode in ('market_path','transfer_counts','market_transfer_counts','market_transfer_values'):
  def design(pp,F):
   b=np.array([feature(a,b,'path') for a,b in pp])
   x=np.column_stack((np.ones(len(F)),F[:,count_cols]))
   if mode=='market_path':return b
   if mode=='transfer_counts':return x
   if mode=='market_transfer_counts':return np.column_stack((b,F[:,count_cols]))
   return np.column_stack((b,F[:,count_cols+value_cols]))
  X=design(hist,HF);Z=design(pairs,RF)
  pred=np.zeros(len(H));rpred=np.zeros(len(R));fit={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv;re=(RY==yr)&rv
   assert tr.sum()>0 and HY[tr].max()<yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xt=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   coef=np.linalg.solve(xt.T@xt+pen,xt.T@(hu[tr]-au[tr]))
   pred[te]=((X[te]-mu)/sd)@coef
   if re.any():rpred[re]=((Z[re]-mu)/sd)@coef
   fit[str(yr)]={'train_n':int(tr.sum()),'features':len(coef),'coefficients':coef.tolist()}
  hp=np.where(pred>=0,hu,au);rp=np.where(rpred>=0,ru,rr)
  z={'history':score(H,hp,hm),'history_disjoint_receipt':score(H,hp,hm&history_ind),'receipt':score(R,rp,rm),
    'years':{str(y):score(H,hp,hm&(HY==y)) for y in (2024,2025,2026)},'train':fit}
  out['models'][market+'_'+mode]=z
  compact=lambda q:{k:v for k,v in q.items() if k!='weekly_counts'}
  print('RESULT',market,mode,'H',compact(z['history']),'R',compact(z['receipt']),'YR',{y:compact(t) for y,t in z['years'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_transfer_activity_signal_20261117.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
