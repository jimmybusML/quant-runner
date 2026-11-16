import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_complementary_league_research_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# Keep existing OU research entirely separate. All outside-eight matches are
# evaluated for AH, then report the disjoint incremental opportunity set.
from scipy.special import expit
from research.m3.probabilities import settle_score
def sharefit(tr,X,te,Xt):
 h=vec(tr,'hg');n=h+vec(tr,'ag')
 off=np.log(vec(tr,'mh')/vec(tr,'ma'));ot=np.log(vec(te,'mh')/vec(te,'ma'))
 mu=X.mean(0);sd=X.std(0);mu[0]=0;sd[0]=1;sd[sd<1e-10]=1
 X=(X-mu)/sd;Xt=(Xt-mu)/sd;pen=np.eye(X.shape[1])*100;pen[0,0]=0
 b=np.zeros(X.shape[1])
 for i in range(20):
  f=expit(off+X@b);u=n*f*(1-f)
  step=np.linalg.solve(X.T@(u[:,None]*X)+pen,X.T@(h-n*f)-pen@b);b+=step
  if np.max(abs(step))<1e-7:break
 return expit(ot+Xt@b)
def predict(kind,mode,q,F):
 E1=mapmat(train,TF,kind);C1=mapmat(z,CF,kind)
 result=np.zeros(len(q));counts={};filled=np.zeros(len(q),bool)
 for yy in sorted({a['year'] for a in q}):
  e=[a for a in train if a['year']<yy];c=[a for a in z if a['year']<yy];seen={a['fid'] for a in e}
  groups=sorted({a['league'] for a in q if a['year']==yy}) if mode=='local_add' else [None]
  for l in groups:
   k=np.array([a['year']==yy and (l is None or a['league']==l) for a in q]);te=[a for a,b in zip(q,k) if b]
   if mode=='local_add':
    add=[a for a in c if a['league']==l and a['fid'] not in seen];tr=e+add;X=np.array([E1[a['fid']] for a in e]+[C1[a['fid']] for a in add])
   else:
    seen2={a['fid'] for a in c};ee=[a for a in e if a['fid'] not in seen2];tr=c+ee;X=np.array([C1[a['fid']] for a in c]+[E1[a['fid']] for a in ee])
   assert max(a['year'] for a in tr)<yy and len(tr)==len({a['fid'] for a in tr}) and not ({a['fid'] for a in tr}&{a['fid'] for a in te})
   result[k]=sharefit(tr,X,te,matrix(te,F,kind));filled|=k;counts[f'{yy}:{l}']=len(tr)
 assert filled.all()
 return result,counts
def pnl(q,frac):
 total=vec(q,'mh')+vec(q,'ma');line=vec(q,'al')
 w,l=g['ah_wl'](total,frac,line)
 a,b=vec(q,'ah'),vec(q,'aa');eh=w*(a-1)-l;ea=l*(b-1)-w
 hu=np.array([settle_score('AH',x['al'],'home',int(x['hg']),int(x['ag']),x['ah'])[1] for x in q]);au=np.array([settle_score('AH',x['al'],'away',int(x['hg']),int(x['ag']),x['aa'])[1] for x in q])
 for i,x in enumerate(q):
  if 'home_U' in x:assert abs(hu[i]-x['home_U'])<1e-8 and abs(au[i]-x['away_U'])<1e-8
 side=eh>=ea;u=np.where(side,hu,au)
 return np.maximum(eh,ea),u,side,(hu+au)/2
def summary(q,v,k):
 if not k.any():return {'n':0}
 ev,u,side,ref=v;d=collections.defaultdict(float)
 for a,b,mask in zip(q,u,k):
  if mask:d[a['date']]+=float(b)
 a=b=dd=0.
 for x in sorted(d):a+=d[x];b=max(a,b);dd=max(dd,b-a)
 return {**g['stat'](u[k]),'expected_roi':round(float(ev[k].mean()*100),3),'daily_mdd':round(dd,3),'home_n':int(side[k].sum()),'two_side_equal_stake_reference_roi':round(float(ref[k].mean()*100),3)}
# Same t order old subset then newly expanded; maps disjoint target IDs.
F={k:{**ZF[k],**NF[k]} for k in ZF}
ou=band|static(t);our=rb|static(rt)
assert ou.sum()==2238 and our.sum()==133
out={'method':'R21 exploratory AH share model: conditional binomial home-goal share with market log home/away offset, fixed market total; prior-calendar-year penalty100, same prior training sources/feature recipes as OU research. All matches forecast with higher modeled expected return side; no EV filter. Full outside-eight and separate subset outside saved R19/R20 OU candidates, keep whole periods. No historical reselection, no production/tg; same already-explored targets, not independent future.', 'models':{}}
for name,kind,mode in [('market_calibration','market_only','mixed'),('full_mixed','baseline','mixed'),('shot_local','shot_level_drift','local_add')]:
 h,hn=predict(kind,mode,t,F);rr0,rn=predict(kind,mode,rt,RF);v0=pnl(t,h);vr=pnl(rt,rr0)
 a={'history_all':summary(t,v0,np.ones(len(t),bool)),'history_disjoint':summary(t,v0,ind),'outside_ou':summary(t,v0,~ou),'outside_ou_disjoint':summary(t,v0,~ou&ind),'receipt_all':summary(rt,vr,np.ones(len(rt),bool)),'receipt_outside_ou':summary(rt,vr,~our),'year':{},'train_n':hn,'receipt_train_n':rn}
 for yy in (2024,2025,2026):
  k=years==yy
  a['year'][str(yy)]={'all':summary(t,v0,k),'outside_ou':summary(t,v0,k&~ou),'outside_ou_disjoint':summary(t,v0,k&~ou&ind)}
 out['models'][name]=a
 print(name,{k:v1 for k,v1 in a.items() if k not in ('train_n','receipt_train_n')},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_ah_share_research_20261116.json').write_text(json.dumps(out,indent=2))
