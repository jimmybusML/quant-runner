import json,datetime,collections,math,hashlib
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
source=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(source[:source.rindex("out={'method'")])
# Historical kickoff from separately archived league/team identity and UTC.
scores={a['fid']:a for a in load('m8_independent_score_strength_20261114.jsonl')}
for r in load('m8_extra_inventory_frozen_eight_20261115.jsonl')+load('m8_raw_capture_unindexed_frozen_replay_20261115.jsonl'):
 if 'score_row' in r:scores[r['fid']]=r['score_row']
def parsed(s):
 t=datetime.datetime.fromisoformat(str(s).replace('Z','+00:00').replace(' ','T'))
 assert t.tzinfo is not None
 return t.astimezone(datetime.timezone.utc)
def identity(a,b):
 return (str(a['league'])==str(b['league']) and str(a['home_id'])==str(b['home']) and str(a['away_id'])==str(b['away']) and str(a['date'])==str(b['date']) and (int(a['hg']),int(a['ag']))==(int(b['hg']),int(b['ag'])))
def restore(q):
 times=[];counts=collections.Counter()
 for a in q:
  r=scores.get(str(a['fid']))
  if not r:times.append(None);counts['no_kickoff_archive']+=1;continue
  if not identity(a,r):times.append(None);counts['identity_mismatch']+=1;continue
  ko=parsed(r['ko'])
  if ko.date().isoformat()!=a['date']:times.append(None);counts['UTC_date_mismatch']+=1;continue
  times.append(ko);counts['verified_kickoff']+=1
 return times,counts
hko,hqc=restore(H)
# Actual receipt fixture identity and kickoff are independently cross-checked in R22.
rko=[];rqc=collections.Counter()
for a in R:
 fid=a['fid'];ko=verified_kickoff.get(fid)
 if ko is None:rko.append(None);rqc['no_verified_receipt_kickoff']+=1;continue
 q=scores.get(fid)
 if q and (not identity(a,q) or parsed(q['ko'])!=ko):rko.append(None);rqc['score_identity_or_time_mismatch']+=1;continue
 rko.append(ko);rqc['verified_receipt_kickoff']+=1
assert len(hko)==len(H) and len(rko)==len(R)
print('KICKOFF',len(H),dict(hqc),'RECEIPT',len(R),dict(rqc),flush=True)
def cal_features(t):
 if t is None:return np.full(8,np.nan)
 hour=t.hour+t.minute/60+t.second/3600
 day=t.weekday()
 y=t.timetuple().tm_yday
 # UTC hour and weekday are observable schedule facts, not team biological clocks.
 return np.array([math.sin(2*math.pi*hour/24),math.cos(2*math.pi*hour/24),
  math.sin(2*math.pi*day/7),math.cos(2*math.pi*day/7),
  float(day>=5),math.sin(2*math.pi*y/365.25),math.cos(2*math.pi*y/365.25),
  math.sin(4*math.pi*hour/24)])
HF=np.array([cal_features(t) for t in hko]);RF=np.array([cal_features(t) for t in rko])
hv=np.isfinite(HF).all(1);rv=np.isfinite(RF).all(1)
hm0=(HY>=2024)&(HY<=2026)&foundation&other&hv
rm0=rf&ro&rv
print('COHORT',int(hm0.sum()),int(rm0.sum()),'disjoint',int((hm0&history_ind).sum()),flush=True)
out={'method':'R46 original48-league Crown paired T24/T12 market and independently verified historical kickoff UTC. Compare R22 original path model vs original path plus calendar (UTC hour, weekday, month/annual cyclic Fourier) and interactions with contemporaneous AH or OU contract price and line. No match subset selection by return, no new trading threshold, no league/day/week exclusion. Previous-year ridge100 direct realized payout-difference regression; exclude receipt-archive targets from training, fixed same historical cohort for all versions. Results are historical retrospective, quote source event time may predate actual retrieval. UTC timing proxy not physical circadian rhythm, local league time, fatigue or causal effect. Other existing candidate identities excluded only to measure retrospective incremental group, not as live criteria. Original M8 eight untouched.','coverage':{'historical_pairs':len(H),'receipt_pairs':len(R),'historical_kickoff_identity':dict(hqc),'receipt_kickoff_identity':dict(rqc),'historical_incremental':int(hm0.sum()),'receipt_incremental':int(rm0.sum()),'years':{str(y):int((hm0&(HY==y)).sum()) for y in (2024,2025,2026)}},'models':{}}
def mat(pair,cal,kind,market):
 x=np.array([feature(a,b,'path') for a,b in pair])
 if kind=='path':return x
 if kind=='calendar':return np.column_stack((x,cal))
 # Current exact market contract information, no future prices.
 line=np.array([float(b['al'] if market=='AH' else b['ol']) for a,b in pair])
 p=np.array([float(b['aa']/(b['ah']+b['aa']) if market=='AH' else b['ou']/(b['oo']+b['ou'])) for a,b in pair])
 xcore=cal[:,[0,1,2,3,4,5,6]]
 return np.column_stack((x,cal,xcore*line[:,None],xcore*p[:,None]))
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);rr=vec(R,sb);y=hu-au
 for kind in ('path','calendar','contract_calendar'):
  X=mat(hist,HF,kind,market);Z=mat(pairs,RF,kind,market)
  pred=np.zeros(len(H));rp=np.zeros(len(R));meta={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv;re=(RY==yr)&rv
   assert HY[tr].max()<yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
   pred[te]=((X[te]-mu)/sd)@beta
   if re.any():rp[re]=((Z[re]-mu)/sd)@beta
   meta[str(yr)]={'train_n':int(tr.sum()),'features':int(X.shape[1]),'coeff':beta.tolist()}
  pay=np.where(pred>=0,hu,au);rpay=np.where(rp>=0,ru,rr)
  d={'history':score(H,pay,hm0),'history_disjoint_receipt':score(H,pay,hm0&history_ind),
     'receipt':score(R,rpay,rm0),'year':{str(yr):score(H,pay,hm0&(HY==yr)) for yr in (2024,2025,2026)},
     'calendar_description':{},'fit':meta}
  for name,hmask,rmask in [
   ('UTC_weekday',(np.array([t.weekday()<5 for t in hko if t]) if False else np.array([bool(t and t.weekday()<5) for t in hko])),np.array([bool(t and t.weekday()<5) for t in rko])),
   ('UTC_weekend',np.array([bool(t and t.weekday()>=5) for t in hko]),np.array([bool(t and t.weekday()>=5) for t in rko]))]:
   d['calendar_description'][name]={'historical':score(H,pay,hm0&hmask),'receipt':score(R,rpay,rm0&rmask)}
  out['models'][market+'_'+kind]=d
  slim=lambda q:{k:v for k,v in q.items() if k!='weekly_counts'}
  print('RESULT',market,kind,'H',slim(d['history']),'R',slim(d['receipt']),
    'annual',{k:slim(z) for k,z in d['year'].items()},'disjoint',slim(d['history_disjoint_receipt']),flush=True)
  if kind=='path':
   old=json.loads((P/'m8_early_joint_path_incremental_20261116.json').read_text())['models'][market+'_path']
   assert d['history']['U']==old['historical_incremental']['U'] and d['receipt']['U']==old['receipt_incremental']['U']
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())}
assert all(out['foundation'].values())
(P/'m8_calendar_market_interaction_20261117.json').write_text(json.dumps(out,indent=2))
