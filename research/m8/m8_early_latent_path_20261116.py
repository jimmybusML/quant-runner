import json,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_early_line_water_interaction_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# All four prices and both lines jointly imply Poisson scoring rates.
# Numerical inversion only; not a claim that market expectations are true probabilities.
def key(a):return tuple(float(a[k]) for k in ('al','ol','ah','aa','oo','ou'))
keys=sorted({key(a) for pp in (hist,pairs) for pair in pp for a in pair})
cache={};invalid=0
for start in range(0,len(keys),1500):
 kk=keys[start:start+1500];al,ol,ah,aa,oo,ou=np.array(kk).T
 op=ou/(oo+ou);ap=aa/(ah+aa)
 total,ok1,e1=g['solve'](op,.0001,20.,lambda x:g['ou_share'](x,ol))
 frac,ok2,e2=g['solve'](ap,.00001,.99999,lambda x:g['ah_share'](total,x,al))
 ok=ok1&ok2&(e1<1e-5)&(e2<1e-5)
 # Re-express both observations later on exact same T12 contract.
 for i,k in enumerate(kk):
  if ok[i]:cache[k]=(float(total[i]),float(frac[i]))
  else:invalid+=1
print('INVERSION unique',len(keys),'valid',len(cache),'invalid',invalid,flush=True)
def latent(pairs):
 valid=np.array([key(a) in cache and key(b) in cache for a,b in pairs])
 n=len(pairs);values=np.zeros((n,12))
 for st in range(0,n,2000):
  ix=np.where(valid[st:st+2000])[0]+st
  if not len(ix):continue
  a=[pairs[i][0] for i in ix];b=[pairs[i][1] for i in ix]
  t0,f0=np.array([cache[key(x)] for x in a]).T;t1,f1=np.array([cache[key(x)] for x in b]).T
  d0=t0*(2*f0-1);d1=t1*(2*f1-1)
  al=vec(b,'al');ol=vec(b,'ol')
  ah0=g['ah_share'](t0,f0,al);ah1=g['ah_share'](t1,f1,al)
  ou0=g['ou_share'](t0,ol);ou1=g['ou_share'](t1,ol)
  values[ix]=np.column_stack((t0,t1,d0,d1,t1-t0,d1-d0,ah0,ah1,ah1-ah0,ou0,ou1,ou1-ou0))
 return valid,values
hv,hx=latent(hist);rv,rx=latent(pairs)
hm0=(HY>=2024)&(HY<=2026)&foundation&other;rm0=rf&ro
print('MATCHED',int(hv.sum()),int(rv.sum()),int((hm0&hv).sum()),int((rm0&rv).sum()),flush=True)
def design_latent(pp,lx,kind):
 if kind=='path':return np.array([feature(a,b,'path') for a,b in pp])
 if kind=='latent_only':
  # Use current price/age plus common scoring-scale movements.
  return np.column_stack((np.array([feature(a,b,'current') for a,b in pp]),lx[:,[0,1,2,3,4,5,6,9,8,11]]))
 if kind=='path_latent':return np.column_stack((np.array([feature(a,b,'path') for a,b in pp]),lx))
 raise ValueError(kind)
def direction(a):
 return np.sign(np.where(abs(a)<1e-6,0,a))
def report_motion(pp,lx,mask,market):
 # Compare direction of raw quote share with common-contract repricing.
 col=8 if market=='AH' else 11
 raw=np.array([movement(a,b,market) for a,b in pp])
 line=raw[:,0];water=raw[:,1];same=lx[:,col]
 change=mask&(line!=0)
 ct=collections.Counter()
 for i in np.where(change)[0]:
  ct[str(int(direction(np.array([water[i]]))[0]))+'|'+str(int(direction(np.array([same[i]]))[0]))]+=1
 return {'changed_line_n':int(change.sum()),'raw_vs_same_contract_share_direction':dict(ct),'same_direction_as_line':int((change&(direction(same)==np.sign(line))).sum()),'opposite_direction_as_line':int((change&(direction(same)==-np.sign(line))).sum()),'flat_same_contract':int((change&(direction(same)==0)).sum())}
out={'method':'R24 fixed R22/R23 cohorts, paired Crown AH/OU price inversion using independent Poisson goal means, no-vig conditional non-push stake share, exact quarter-line splits. Reprice early quote on final T12 contract. Compare prior-calendar-year ridge payout difference baseline, latent-path features and combined path. Matched numerical validity only; full outcomes retained, no selection by profitability. Same historical and receipt archives already explored; not independent forward results.','coverage':{'history_pairs':len(hist),'receipt_pairs':len(pairs),'history_valid':int(hv.sum()),'receipt_valid':int(rv.sum()),'history_incremental_valid':int((hm0&hv).sum()),'receipt_incremental_valid':int((rm0&rv).sum()),'unique_quote_keys':len(keys),'invalid_keys':invalid},'motion':{},'models':{}}
for market,sa,sb in [('AH','home_U','away_U'),('OU','over_U','under_U')]:
 out['motion'][market]={'history':report_motion(hist,hx,hm0&hv,market),'receipt':report_motion(pairs,rx,rm0&rv,market)}
 print('MOTION',market,out['motion'][market],flush=True)
 hu=vec(H,sa);au=vec(H,sb);ru=vec(R,sa);ra=vec(R,sb);y=hu-au
 for kind in ('path','latent_only','path_latent'):
  X=design_latent(hist,hx,kind);Z=design_latent(pairs,rx,kind)
  hp=np.zeros(len(H));pr=np.zeros(len(R));used=np.zeros(len(H),bool);rused=np.zeros(len(R),bool);train={}
  for yr in (2024,2025,2026):
   tr=(HY<yr)&history_ind&hv;te=(HY==yr)&hv;re=(RY==yr)&rv
   assert HY[tr].max()<yr
   mu=X[tr].mean(0);sd=X[tr].std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
   xx=(X[tr]-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
   beta=np.linalg.solve(xx.T@xx+pen,xx.T@y[tr])
   hp[te]=((X[te]-mu)/sd)@beta;pr[re]=((Z[re]-mu)/sd)@beta
   used|=te;rused|=re;train[str(yr)]=int(tr.sum())
  pnl=np.where(hp>=0,hu,au);rpnl=np.where(pr>=0,ru,ra)
  hm=used&foundation&other;rm=rused&rf&ro
  a={'history':score(H,pnl,hm),'history_disjoint_receipt':score(H,pnl,hm&history_ind),'receipt':score(R,rpnl,rm),'years':{str(yr):score(H,pnl,hm&(HY==yr)) for yr in (2024,2025,2026)},'train':train}
  hline=np.array([movement(a,b,market)[0]!=0 for a,b in hist]);rline=np.array([movement(a,b,market)[0]!=0 for a,b in pairs])
  a['line_change']={'history_changed':score(H,pnl,hm&hline),'history_fixed':score(H,pnl,hm&~hline),'receipt_changed':score(R,rpnl,rm&rline),'receipt_fixed':score(R,rpnl,rm&~rline)}
  assert a['line_change']['history_changed']['n']+a['line_change']['history_fixed']['n']==a['history']['n']
  out['models'][market+'_'+kind]=a
  print(market,kind,'H',slim(a['history']),'R',slim(a['receipt']),'Y',{k:slim(v) for k,v in a['years'].items()},'LINE',{k:slim(v) for k,v in a['line_change'].items()},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());dig=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':dig(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(dig(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(dig(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_early_latent_path_20261116.json').write_text(json.dumps(out,indent=2))
