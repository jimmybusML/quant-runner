import json,collections,datetime,hashlib,math,bisect
from pathlib import Path
import numpy as np
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_frozen_eight_earlier_window_replay_20261116.py').read_text()
exec(s[:s.index('windows=[')])
P=R
exec(s[s.index('def stat(a):'):s.index('fset=')])
# Same quote list used to freeze the eight groups; OU list and timestamped
# open/close, 1X2 timestamped open/close only. No fabricated 1X2 history.
target={f:r for f,r in univ.items() if f not in ids and not r['end_zero'] and r['path_shape']=='never_changed'}
assert len(target)==26055
def extract(x,ko,cap,ah):
 b=next(q for q in x['bookmakers'] if q.get('slug')=='crown')
 cut=ko-datetime.timedelta(hours=1);assert cap<=cut
 ou=[];od=[]
 def add(t,l,a,c):
  if t<=cap and t<ko and min(a,c)>1 and all(math.isfinite(v) for v in (l,a,c)) and abs(l*4-round(l*4))<1e-7:ou.append((t,l,a,c))
 for q in b.get('goal_list') or []:
  try:add(dt(q[4]),*map(float,q[1:4]))
  except Exception:pass
 for tag in ('open','close'):
  try:
   q=b['goal'][tag];add(dt(q['time']),float(q['line']),float(q['over']),float(q['under']))
  except Exception:pass
  try:
   q=b['odds'][tag];t=dt(q['time']);o=[float(q[k]) for k in ('home','draw','away')]
   if t<=cap and t<ko and min(o)>1 and all(math.isfinite(v) for v in o):
    p=np.reciprocal(o);od.append((t,(p/p.sum()).tolist()))
  except Exception:pass
 if not ou:return None
 q=max(ou,key=lambda q:q[0])
 a={'al':ah[1],'ah':ah[2],'aa':ah[3],'ol':q[1],'oo':q[2],'ou':q[3],'age_ah':(cut-ah[0]).total_seconds()/3600,'age_ou':(cut-q[0]).total_seconds()/3600}
 if od:
  t,p=max(od,key=lambda q:q[0]);a.update(p1x2=p,age_1x2=(cut-t).total_seconds()/3600)
 return a
H=[];qc0=collections.Counter()
for f,r in target.items():
 try:
  p,sha=sources[f];raw=p.read_bytes()
  if sha:assert hashlib.sha256(raw).hexdigest()==sha
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f);ko=dt(x['start']);cut=ko-datetime.timedelta(hours=1)
  assert str(x['l_id'])==str(r['league']) and ko.date().isoformat()==r['date'] and x['status']=='full'
  b=next(q for q in x['bookmakers'] if q.get('slug')=='crown');path=[]
  for q in b.get('asian_list') or []:
   try:
    t=dt(q[4]);l,a,c=map(float,q[1:4])
    if t<=cut and t<ko and min(a,c)>1 and all(math.isfinite(v) for v in (l,a,c)) and abs(l*4-round(l*4))<1e-7:path.append((t,l,a,c))
   except Exception:pass
  path.sort(key=lambda q:q[0]);ah=path[-1]
  assert (ah[1],ah[2],ah[3])==(r['end_line'],r['home_price'],r['away_price'])
  feat=extract(x,ko,cut,ah)
  if feat is None:qc0['missing_OU']+=1;continue
  H.append(dict(fid=f,year=r['year'],date=r['date'],league=r['league'],pnl=r['end_home_U'],other_pnl=r['end_away_U'],**feat))
 except Exception as ex:qc0['error_'+type(ex).__name__]+=1
print('HIST',len(H),'triple',sum('p1x2' in r for r in H),'quality',dict(qc0),flush=True)
# Use R32 verified receipt path & independently verified FT. The exact same
# cap is the receipt timestamp, not the later historical T1 quote.
src=(P/'m8_frozen_eight_adjacent_structure_20261116.py').read_text()
exec(src[src.index('def stat(z,'):src.index("out={'method'")])
block=src[src.index('import math,bisect'):src.index("print('RECEIPT'")]
block=block.replace("g,side=classify(a);qc['verified_quote']+=1","g='fixed_nonzero';side='home' if l and shape=='never_changed' else None;qc['verified_quote']+=1")
old="record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'side':side,'pnl':None,'other_pnl':None}"
new="""feat=extract(x,ko,recv,end)
  if feat is None:qc['missing_OU']+=1;continue
  record={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'league':r['league'],'side':side,'pnl':None,'other_pnl':None,**feat}"""
assert old in block
block=block.replace(old,new)
def opposite(side):return 'away' if side=='home' else 'home'
out={}
block=block[:block.index("out['receipt_replay']=")]
exec(compile(block,'verified_receipt','exec'))
RR=res.get('fixed_nonzero',[]);assert all((r['pnl'] is None)==(r['other_pnl'] is None) for r in RR);R=[r for r in RR if r['pnl'] is not None]
print('RECEIPT',len(RR),len(R),'triple settled',sum('p1x2' in r for r in R),dict(qc),flush=True)
# Exact inversion of normalized price shares, not true outcome probabilities.
latent=(P/'m8_cross_market_latent_pricing_20261114.py').read_text()
exec(latent[latent.index('K=40;'):latent.index('for suffix,ahkey')])
def vec(q,k):return np.array([r[k] for r in q],float)
def derive(q):
 if not q:return []
 al,ol,ah,aa,oo,ou=map(lambda k:vec(q,k),('al','ol','ah','aa','oo','ou'))
 t,ok,e=solve(ou/(oo+ou),.0001,20.,lambda x:ou_share(x,ol))
 f,ok2,e2=solve(aa/(ah+aa),.00001,.99999,lambda x:ah_share(t,x,al))
 valid=ok&ok2&(e<1e-5)&(e2<1e-5)
 h=pmf(t*f);a=pmf(t*(1-f));win=(h*cdf_at(a.cumsum(1),goals-1+np.zeros((len(q),1)))).sum(1);draw=(h*a).sum(1)
 for i,r in enumerate(q):
  r['latent']=[float(t[i]),float(t[i]*(2*f[i]-1)),float(win[i]),float(draw[i]),float(1-win[i]-draw[i])]
  r['latent_valid']=bool(valid[i])
 return q
derive(H);derive(R)
out={'method':'R35 historical frozen-eight complement nonzero unchanged AH at T1. Same AH list as frozen; OU latest timestamped list/open/close, 1X2 only timestamped open/close. Actual receipt separately capped at receipt, independently archived FT. Three-way probabilities normalized reciprocal odds, AH+OU independent Poisson inversion, 1X2 minus model WDL is pricing discrepancy, not arbitrage or true probabilities. Prior-year ridge100 all matched fixtures home/away, no payout threshold or chosen winning groups. Dual-market and triple-market comparisons separate paired cohorts. Historical quote retrieval not actual receipt, previously explored data not independent forward.','foundation':foundation,'coverage':{'target':len(target),'dual':len(H),'triple':sum('p1x2' in r for r in H),'history_errors':dict(qc0),'receipt_quality':dict(qc),'receipt_dual_signals':len(RR),'receipt_dual_settled':len(R),'receipt_triple_settled':sum('p1x2' in r for r in R),'history_invalid_inversion':sum(not r['latent_valid'] for r in H),'receipt_invalid_inversion':sum(not r['latent_valid'] for r in R)},'cohorts':{}}
receiptids={str(r.get('fixture_id')) for r in map(json.loads,(P/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl').open())}|{r['fid'] for r in receipt}
def feature(q,mode):
 a,b,ph,pa,oo,ou,ag1,ag2=[vec(q,k) for k in ('al','ol','ah','aa','oo','ou','age_ah','age_ou')]
 x=np.column_stack((np.ones(len(q)),a,abs(a),pa/(ph+pa),1/ph+1/pa,np.log1p(ag1)))
 if mode=='AH':return x
 z=np.column_stack((x,b,ou/(oo+ou),1/oo+1/ou,np.log1p(ag2),a*b))
 if mode=='AH_OU':return z
 lat=np.array([r['latent'] for r in q]).reshape(-1,5)
 if mode=='latent':return np.column_stack((z,lat[:,:2]))
 prob=np.array([r['p1x2'] for r in q]).reshape(-1,3);age=vec(q,'age_1x2')
 if mode=='three_raw':return np.column_stack((z,prob,np.log1p(age)))
 return np.column_stack((z,lat[:,:2],prob-lat[:,2:],np.log1p(age)))
for cohort,modes in [('dual',('AH','AH_OU','latent')),('triple',('AH','AH_OU','latent','three_raw','discrepancy'))]:
 hh=[r for r in H if r['latent_valid'] and (cohort=='dual' or 'p1x2' in r)]
 rr=[r for r in R if r['latent_valid'] and (cohort=='dual' or 'p1x2' in r)]
 hy=vec(hh,'year');ry=vec(rr,'year');ind=np.array([r['fid'] not in receiptids for r in hh]);y=vec(hh,'pnl')-vec(hh,'other_pnl')
 v={'history_all_years':len(hh),'receipt_settled':len(rr),'models':{}}
 for mode in modes:
  X=feature(hh,mode);Z=feature(rr,mode);pred=[];rp=[];fits={}
  for year in (2024,2025,2026):
   tr=(hy<year)&ind;te=hy==year;re=ry==year
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
   def settle(q,mat,mask):
    p=((mat[mask]-mu)/sd)@beta
    return [{**r,'pnl':r['pnl'] if a>=0 else r['other_pnl']} for r,a in zip([r for r,k in zip(q,mask) if k],p)]
   pred+=settle(hh,X,te);rp+=settle(rr,Z,re);fits[str(year)]={'train_n':int(tr.sum()),'coefficients':(beta/sd).tolist()}
  assert not ({r['fid'] for r in pred}&ids) and len({r['fid'] for r in pred})==len(pred)
  v['models'][mode]={'history':desc(pred),'disjoint_history':desc([r for r in pred if r['fid'] not in receiptids]),'receipt':desc(rp),'combined':desc([r for r in frozen if r['year']>=2024]+pred),'fit':fits}
  a=v['models'][mode]
  print('RESULT',cohort,mode,a['history']['all'],a['history']['2026'],a['receipt']['all'],'combined26',a['combined']['2026'],flush=True)
 out['cohorts'][cohort]=v
(P/'m8_fixed_line_cross_market_20261117.json').write_text(json.dumps(out,indent=2))
# Descriptive quote ages at T1, without new eligibility limits.
out['quote_age_hours']={}
for name,q in [('history_triple',[r for r in H if 'p1x2' in r and r['latent_valid']]),('receipt_triple',[r for r in R if 'p1x2' in r and r['latent_valid']])]:
 out['quote_age_hours'][name]={k:{'median':round(float(np.median(vec(q,k))),3),'p90':round(float(np.percentile(vec(q,k),90)),3),'max':round(float(np.max(vec(q,k))),3)} for k in ('age_ah','age_ou','age_1x2')}
 out['quote_age_hours'][name]['all_nonnegative']=all(min(r[k] for k in ('age_ah','age_ou','age_1x2'))>=0 for r in q)
 assert out['quote_age_hours'][name]['all_nonnegative']
print('AGE',json.dumps(out['quote_age_hours']),flush=True)
(P/'m8_fixed_line_cross_market_20261117.json').write_text(json.dumps(out,indent=2))
