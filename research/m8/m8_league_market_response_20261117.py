import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_market_response_calibration_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# League-specific intercept and movement response with a common prior.
# Features standardized globally using training years, not within each league.
# League deviations retained continuously, not selecting profitable league IDs.
leagues=sorted({r['league'] for r in H+R})
li={l:i for i,l in enumerate(leagues)}
def leagues_idx(q):return np.array([li[r['league']] for r in q])
hl,rl=leagues_idx(H),leagues_idx(R)
hc=make_x(hx,'response');rc=make_x(rx,'response')
def design(q,l,mu,sd,mode):
 x=(q-mu)/sd
 if mode=='global':return x
 one=np.eye(len(leagues))[l]
 if mode=='league_level':return np.column_stack((x,one))
 return np.column_stack((x,one,one*x[:,3,None],one*x[:,4,None]))
def estimate(X,Y,off,Z,ot,n=None):
 pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for i in range(40):
  if n is None:
   p=np.exp(np.clip(off+X@b,-7,5));w=p;e=Y-p
  else:
   p=expit(off+X@b);w=n*p*(1-p);e=Y-n*p
  step=np.linalg.solve(X.T@(w[:,None]*X)+pen,X.T@e-pen@b);b+=step
  if np.max(abs(step))<1e-8:break
 else:raise RuntimeError('IRLS did not converge')
 p=ot+Z@b
 return (np.exp(np.clip(p,-7,5)) if n is None else expit(p)),b
a,b,c,d=state(hx);ra,rb,rc0,rd=state(rx)
out={'method':'R43 league partial pooling of market-implied goal total and home goal share, 3 variants shared response, league intercept, league intercept plus both pre-T12 movement slope deviations. Same earlier calendar years, no receipt target IDs in train; global scale, L2=100 research parameter inherited, all observed leagues retained, no selection using ROI. T12 experiment only. AH/OU separately one side for every matched fixture. Retrospective complement of existing groups/candidates not a real-time known exclusion; history and receipt separately, no claim of true forward or execution.','coverage':{'history_full':len(H),'receipt_full':len(R),'leagues':len(leagues),'historical_incremental':int(hm.sum()),'receipt_incremental':int(rm.sum())},'models':{}}
for mode in ('global','league_level','league_response'):
 ht,hf=rates(hx);rt,rf0=rates(rx);fits={}
 for yr in (2024,2025,2026):
  tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
  mu=hc[tr].mean(0);sd=hc[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
  X=design(hc[tr],hl[tr],mu,sd,mode);Z=design(np.vstack((hc[te],rc[re])),np.r_[hl[te],rl[re]],mu,sd,mode)
  tt,bt=estimate(X,hyn[tr],b[tr],Z,np.r_[b[te],rb[re]])
  ff,bf=estimate(X,hyh[tr],d[tr],Z,np.r_[d[te],rd[re]],hyn[tr])
  k=int(te.sum());ht[te]=tt[:k];rt[re]=tt[k:];hf[te]=ff[:k];rf0[re]=ff[k:]
  fits[str(yr)]={'train_n':int(tr.sum()),'total_coef':bt.tolist(),'share_coef':bf.tolist(),'features':X.shape[1],'global_scale':sd.tolist()}
 result={'history_probability':evaluate(H,ht,hf,hm),'receipt_probability':evaluate(R,rt,rf0,rm),'fit':fits,'markets':{}}
 for market in ('AH','OU'):
  p=pay(H,ht,hf,market);r=pay(R,rt,rf0,market)
  ma={'history':score(H,p,hm),'history_disjoint_receipt':score(H,p,hm&history_ind),'receipt':score(R,r,rm),'year':{str(yr):score(H,p,hm&(HY==yr)) for yr in (2024,2025,2026)},'league':{l:{'history':score(H,p,hm&(hl==i)),'receipt':score(R,r,rm&(rl==i))} for i,l in enumerate(leagues)}}
  result['markets'][market]=ma
  print('RESULT',mode,market,slim(ma['history']),slim(ma['receipt']),'annual',{y:slim(v) for y,v in ma['year'].items()},flush=True)
 out['models'][mode]=result
 print('PROB',mode,result['history_probability'],result['receipt_probability'],flush=True)
(P/'m8_league_market_response_20261117.json').write_text(json.dumps(out,indent=2))
