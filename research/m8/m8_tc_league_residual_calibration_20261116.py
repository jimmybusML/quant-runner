import json,datetime,collections,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_target_coverage_expansion_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
oldmask=np.array([r['fid'] not in ids for r in zz]);t=[r for r,b in zip(zz,oldmask) if b]+new
p=np.concatenate([B[oldmask],NB]);m=vec(t,'mh')+vec(t,'ma')
rmask=np.array([r['fid'] not in ids for r in rr]);rt=[r for r,b in zip(rr,rmask) if b];rp=BR[rmask];rm=vec(rt,'mh')+vec(rt,'ma')
assert len(t)==4059 and len(rt)==240 and not ({r['fid'] for r in t}&ids)
assert assess(t,p,m)['U']==4.465 and assess(rt,rp,rm)['U']==-8.745
# Outcomes used only from prior calendar year, or prior month (3-day lag).
# Exclude all archived receipt IDs from calibration so they cannot supply fit outcomes.
# League target grouping is retrospective attribution from R16, not a forward selection.
negative={'14','145','16','290'}
y=vec(t,'hg')+vec(t,'ag')
dates=np.array([r['date'] for r in t]);ls=np.array([r['league'] for r in t])
valid=np.array([r['fid'] not in receiptids for r in t])
def gstats(q,pr,market):
 a=assess(q,pr,market)
 a['over_n']=int(g['make_pred'](q,pr)[1].sum())
 return a
def diagnostic(q,pr,market):
 yy=vec(q,'hg')+vec(q,'ag');side=g['make_pred'](q,pr);s=side[1]
 return {**gstats(q,pr,market),'actual_mean':round(float(yy.mean()),5),'expected_mean':round(float(pr.mean()),5),'market_mean':round(float(market.mean()),5),'over':g['stat'](side[2][s]) if s.any() else {'n':0},'under':g['stat'](side[2][~s]) if (~s).any() else {'n':0}}
def calib(y,b,market,mode):
 if not len(y):return np.array([0.,0.])
 if mode=='intercept':return np.array([np.log(y.sum()/b.sum()),0.]) if y.sum()>0 else np.array([0.,0.])
 # Shrink the additive intercept and relative-model slope correction toward original rate.
 # Existing research ridge magnitude 100; experiment only, not production constraints.
 X=np.column_stack([np.ones(len(b)),np.log(b/market)])
 off=np.log(b);beta=np.zeros(2);pen=np.eye(2)*100
 for i in range(20):
  u=np.exp(np.clip(off+X@beta,-7,5));step=np.linalg.solve(X.T@(u[:,None]*X)+pen,X.T@(y-u)-pen@beta);beta+=step
  if np.max(abs(step))<1e-7:break
 return beta
def predict(q,pr,mm,horizon,mode,scope):
 result=pr.copy();meta=[]
 keys=[r['date'][:7] if horizon=='month' else str(r['year']) for r in q]
 for key in sorted(set(keys)):
  cut=(datetime.date.fromisoformat(key+'-01')-datetime.timedelta(days=3)).isoformat() if horizon=='month' else key+'-01-01'
  for l in sorted({r['league'] for r in q}):
   sel=np.array([k==key and r['league']==l for k,r in zip(keys,q)])
   if not sel.any() or (scope=='negative' and l not in negative):continue
   tr=valid&(dates<cut)&(ls==l)
   if not tr.any():continue
   assert max(dates[tr])<min(r['date'] for r,b in zip(q,sel) if b)
   assert not ({r['fid'] for r,b in zip(t,tr) if b}&{r['fid'] for r,b in zip(q,sel) if b})
   b=calib(y[tr],p[tr],m[tr],mode)
   result[sel]=pr[sel]*np.exp(b[0]+b[1]*np.log(pr[sel]/mm[sel]))
   meta.append({'period':key,'league':l,'training_n':int(tr.sum()),'test_n':int(sel.sum()),'coef':b.tolist()})
 return result,meta
def summarize2(q,pr,market):
 def sub(mask):
  return gstats([r for r,b in zip(q,mask) if b],pr[mask],market[mask])
 return {'all':gstats(q,pr,market),'year':{str(yr):sub(np.array([r['year']==yr for r in q])) for yr in sorted({r['year'] for r in q})},'league':{l:sub(np.array([r['league']==l for r in q])) for l in sorted({r['league'] for r in q})}}
out={'method':'R17 historical diagnostics and prior-period calibration on fixed R16 candidate B, outside-eight 4059 targets and 240 receipt targets. All variants retained; no new trade gates; negative league set follows R16 observed loss, so retrospective subgroup selection. Calibration excludes all 1393 receipt IDs, uses only same-league earlier outcomes; original eight unmodified. Intercept and ridge100 intercept/slope around original rate experimental. No independent forward claim.','diagnostics':{},'models':{}}
for l in sorted(leagues):
 mask=ls==l
 out['diagnostics'][l]=diagnostic([r for r,b in zip(t,mask) if b],p[mask],m[mask])
 print('diagnostic',l,out['diagnostics'][l],flush=True)
out['models']['B']={'history':summarize2(t,p,m),'receipt':summarize2(rt,rp,rm)}
for h in ('year','month'):
 for mode in ('intercept','ridge'):
  for scope in ('negative','all'):
   name=f'{h}_{mode}_{scope}';a,ah=predict(t,p,m,h,mode,scope);b,bh=predict(rt,rp,rm,h,mode,scope)
   v={'history':summarize2(t,a,m),'receipt':summarize2(rt,b,rm),'calibrations_history':ah,'calibrations_receipt':bh}
   out['models'][name]=v
   print(name,'history',v['history']['all'],'years',[(yr,k['ROI'],k['U']) for yr,k in v['history']['year'].items()],'receipt',v['receipt']['all'],'leagues',[(l,k['ROI']) for l,k in v['history']['league'].items()],flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_league_residual_calibration_20261116.json').write_text(json.dumps(out,indent=2))
