import json,collections,datetime,hashlib,math,bisect
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_frozen_eight_earlier_window_replay_20261116.py').read_text()
exec(s[:s.index('windows=[')])
P=R
# Same line: log reciprocal odds split exactly into log ratio (direction)
# and log total overround (common price level). Duration weighting avoids
# treating a flurry of updates as multiple independent matches.
def feature(seq,t6,t1,cap):
 assert seq and len({q[1] for q in seq})==1 and seq[-1][0]<=cap<=t1
 z=np.array([[math.log(q[3]/q[2]),math.log(1/q[2]+1/q[3])] for q in seq])
 # Receipt-side: do not extrapolate unobserved quote persistence until T1.
 # Extend the held quote through the actual observation cap only.
 times=np.array([max(0.,(q[0]-t6).total_seconds()) for q in seq]);end=max(0.,(cap-t6).total_seconds())
 dur=np.maximum(0,np.diff(np.r_[times,end]));tot=dur.sum()
 if tot:mu=dur@z/tot;std=np.sqrt(dur@((z-mu)**2)/tot)
 else:mu=z[-1];std=np.zeros(2)
 delta=np.diff(z,axis=0);variation=np.abs(delta).sum(0);net=z[-1]-z[0]
 # Sign of pressure versus common-priced changes, plus co-movement.
 cross=float((delta[:,0]*delta[:,1]).sum()) if len(delta) else 0.
 # Signed persistence relative to time-weighted midpoint; no divisions
 # by nearly-zero volatility, no result-based feature thresholds.
 age=max(0.,(cap-seq[-1][0]).total_seconds()/3600)
 x=[1,seq[-1][1],abs(seq[-1][1]),*z[-1],math.log1p(age)]
 p=[net[0],z[-1,0]-mu[0],std[0],variation[0],float(delta[-1,0]) if len(delta) else 0.,math.log1p(len(delta))]
 v=[net[1],z[-1,1]-mu[1],std[1],variation[1],float(delta[-1,1]) if len(delta) else 0.,cross,z[-1,0]*net[1],net[0]*net[1]]
 return x,p,v
target={f:r for f,r in univ.items() if f not in ids and r['path_shape']=='never_changed'}
H=[];qc0=collections.Counter()
for f,r in target.items():
 try:
  p,sha=sources[f];raw=p.read_bytes()
  if sha:assert hashlib.sha256(raw).hexdigest()==sha
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  ko=dt(x['start']);t6=ko-datetime.timedelta(hours=6);t1=ko-datetime.timedelta(hours=1)
  assert str(x['l_id'])==str(r['league']) and ko.date().isoformat()==r['date'] and x['status']=='full'
  b=next(q for q in x['bookmakers'] if q['slug']=='crown');path=[]
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l,a,c=map(float,q[1:4])
    if t<=t1 and min(a,c)>1 and all(math.isfinite(v) for v in (l,a,c)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,a,c))
   except Exception:continue
  path.sort(key=lambda q:q[0]);i=bisect.bisect_right([q[0] for q in path],t6)-1;assert i>=0
  seq=path[i:];assert seq[-1][1:]==(r['end_line'],r['home_price'],r['away_price'])
  H.append(dict(fid=f,year=r['year'],date=r['date'],league=r['league'],pnl=r['end_home_U'],other_pnl=r['end_away_U'],features=feature(seq,t6,t1,t1)))
 except Exception as ex:qc0['error_'+type(ex).__name__]+=1
print('HISTORY',len(target),len(H),dict(qc0),flush=True)
# Already verified receipt/FT data, same sample identities, cap at receipt.
src=(P/'m8_frozen_eight_adjacent_structure_20261116.py').read_text()
exec(src[src.index('def stat(z,'):src.index("out={'method'")])
def opposite(side):return 'away' if side=='home' else 'home'
block=src[src.index('import math,bisect'):src.index("out['receipt_replay']=")]
old="g,side=classify(a);qc['verified_quote']+=1"
new="g='same_line';side='home' if shape=='never_changed' else None;qc['verified_quote']+=1"
assert old in block
block=block.replace(old,new)
old2="record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'side':side,'pnl':None,'other_pnl':None}"
new2="record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'league':r['league'],'side':side,'pnl':None,'other_pnl':None,'features':feature(seq,t6,t1,recv)}"
assert old2 in block
block=block.replace(old2,new2)
exec(compile(block,'verified_receipt_quote_pressure','exec'))
RR=res.get('same_line',[]);assert all((r['pnl'] is None)==(r['other_pnl'] is None) for r in RR);R=[r for r in RR if r['pnl'] is not None]
receiptids={str(r.get('fixture_id')) for r in map(json.loads,(P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open())}|{r['fid'] for r in receipt}
def vec(q,k):return np.array([r[k] for r in q])
hy=vec(H,'year');ry=vec(R,'year');ind=np.array([r['fid'] not in receiptids for r in H]);y=vec(H,'pnl')-vec(H,'other_pnl')
out={'method':'R37 same-line AH paths at T6 to T1 in original49, outside frozen membership at same observation time. Log implied odds ratio for directional probability pressure; log sum reciprocal odds for common price level/overround. Duration-weighted deviation, variation and co-movement, not volume or bookmaker liability. Actual receipt features capped at actual receipt, no extrapolated future quote persistence. Earlier calendar-year ridge100 direct home-away return differences; train excludes receipt archive IDs. All matched fixtures settled without new gating. Full history and receipt kept separate; exploratory historical samples not independent forward validation.','foundation':foundation,'coverage':{'target':len(target),'history':len(H),'errors':dict(qc0),'receipt_quotes':len(RR),'receipt_settled':len(R),'receipt_unsettled':len(RR)-len(R),'receipt_quality':dict(qc)},'models':{}}
for mode in ('market','direction','common_price','both'):
 def mat(q):
  return np.array([a[0]+(a[1] if mode in ('direction','both') else [])+(a[2] if mode in ('common_price','both') else []) for a in (r['features'] for r in q)])
 X=mat(H);Z=mat(R);pred=[];rp=[];fit={}
 for yr in (2024,2025,2026):
  tr=(hy<yr)&ind;te=hy==yr;re=ry==yr
  mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
  beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
  def settle(q,mat,mask):
   p=((mat[mask]-mu)/sd)@beta
   return [{**r,'pnl':r['pnl'] if a>=0 else r['other_pnl']} for r,a in zip([r for r,k in zip(q,mask) if k],p)]
  pred+=settle(H,X,te);rp+=settle(R,Z,re);fit[str(yr)]={'train_n':int(tr.sum()),'coef':(beta/sd).tolist()}
 assert len({r['fid'] for r in pred})==len(pred) and not ({r['fid'] for r in pred}&ids)
 a={'history':desc(pred),'disjoint_history':desc([r for r in pred if r['fid'] not in receiptids]),'receipt':desc(rp),'combined':desc([r for r in frozen if r['year']>=2024]+pred),'fit':fit}
 out['models'][mode]=a
 print('RESULT',mode,a['history']['all'],'annual',[(k,v['n'],v['U'],v['ROI']) for k,v in a['history']['years'].items() if v['n']],'R',a['receipt']['all'],'combined26',a['combined']['2026'],flush=True)
(P/'m8_same_line_quote_pressure_20261117.json').write_text(json.dumps(out,indent=2))
