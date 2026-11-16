import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_joint_path_incremental_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# For AH, a more negative home handicap strengthens the home side;
# for OU, a higher line strengthens over. Normalize reciprocal odds.
def movement(a,b,market):
 x=snapshot(a);y=snapshot(b);j=0 if market=='AH' else 1
 dl=(y[j]-x[j])*(-1 if market=='AH' else 1)
 dp=y[j+2]-x[j+2]
 # Same fixed side at both times. A change of line changes the contract,
 # so a price change across different lines is not a like-for-like probability.
 return dl,dp
def extra(a,b,market,kind):
 dl,dp=movement(a,b,market)
 if kind=='interaction':
  return [abs(dl),abs(dp),dl*dp,abs(dl)*dp,dl*abs(dp),dl**2,dp**2,dl*abs(dl)]
 if kind=='regime':
  return [float(dl==0),float(abs(dl)==.25),float(abs(dl)>.25),dp*(dl==0),dp*(abs(dl)==.25),dp*(abs(dl)>.25),abs(dp)*(dl==0),abs(dp)*(dl!=0),float(dl>0)*dp,float(dl<0)*dp]
 raise ValueError(kind)
def design(a,b,market,kind):
 f=feature(a,b,'path')
 return f if kind=='path' else f+extra(a,b,market,kind)
def label(dl,dp):
 if dl==0:return 'same_line_water_up' if dp>1e-10 else 'same_line_water_down' if dp<-1e-10 else 'unchanged'
 size='quarter' if abs(dl)==.25 else 'multi_quarter'
 if abs(dp)<=1e-10: rel='flat'
 else:rel='aligned' if dl*dp>0 else 'offset'
 return size+'_'+rel
def slim(x):return {k:v for k,v in x.items() if k!='weekly_counts'}
def part(q,pp,mask,lab):
 rs={}
 for k in sorted(set(lab)):
  a=mask&(lab==k)
  if a.any():rs[k]=score(q,pp,a)
 assert sum(v['n'] for v in rs.values())==mask.sum()
 return rs
assert len(hist)==38846 and len(pairs)==1230
out={'method':'R23 fixed R22 paired Crown T24/T12 data and incremental membership; same chronological ridge100 fit, no additional selection. Signed line change toward home/over and no-vig probability share change of same side; different contract across changed lines, not directly comparable. Continuous interactions and natural quarter-line regimes compared with fixed original path. All outcomes and periods retained; no EV gate; results retrospective.','coverage':{'pairs_history':len(hist),'pairs_receipt':len(pairs)},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);ra=vec(R,sb);y=hu-au
 labs=np.array([label(*movement(a,b,market)) for a,b in hist]);rlabs=np.array([label(*movement(a,b,market)) for a,b in pairs])
 for kind in ('path','interaction','regime'):
  X=np.asarray([design(a,b,market,kind) for a,b in hist]);Z=np.asarray([design(a,b,market,kind) for a,b in pairs])
  hp=np.zeros(len(H));pr=np.zeros(len(R));used=np.zeros(len(H),bool);rused=np.zeros(len(R),bool)
  coefs={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind;te=HY==yr;re=RY==yr
   assert HY[tr].max()<yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
   hp[te]=((X[te]-mu)/sd)@beta;pr[re]=((Z[re]-mu)/sd)@beta
   used|=te;rused|=re;coefs[str(yr)]={'train_n':int(tr.sum()),'coefficients':beta.tolist()}
  pnl=np.where(hp>=0,hu,au);rpnl=np.where(pr>=0,ru,ra)
  hm=used&foundation&other;rm=rused&rf&ro
  a={'history':score(H,pnl,hm),'history_disjoint_receipt':score(H,pnl,hm&history_ind),'receipt':score(R,rpnl,rm),'years':{str(yr):score(H,pnl,hm&(HY==yr)) for yr in (2024,2025,2026)},'history_regimes':part(H,pnl,hm,labs),'receipt_regimes':part(R,rpnl,rm,rlabs),'fit':coefs}
  if kind=='path':
   prev=json.loads((P/'m8_early_joint_path_incremental_20261116.json').read_text())['models'][market+'_path']
   assert a['history']['U']==prev['historical_incremental']['U'] and a['receipt']['U']==prev['receipt_incremental']['U']
  out['models'][market+'_'+kind]=a
  print(market,kind,'H',slim(a['history']),'R',slim(a['receipt']),'Y',{k:slim(v) for k,v in a['years'].items()},flush=True)
  print('REGIMES',market,kind,'H',[(k,v['n'],v['U'],v['ROI']) for k,v in a['history_regimes'].items()],'R',[(k,v['n'],v['U'],v['ROI']) for k,v in a['receipt_regimes'].items()],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_early_line_water_interaction_20261116.json').write_text(json.dumps(out,indent=2))
