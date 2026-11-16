import json,collections,datetime,math
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_crossyear_round10_replay_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
z,H=historical([r for r in history.values() if r['fid'] in audit['target'] and r['year']>=2023],idx)
assert len(z)==3029 and len(ex)==308 and len(history)==3168
ei=histindex(E)
train=[r for r in g['esvalid'] if r['league'] in ('1','14') and r['year']<2026]
def histories(z,index):
 out={}
 for r in z:
  t=datetime.date.fromisoformat(r['date']);cut=t-datetime.timedelta(days=3); h=[]
  for team in (r['home_id'],r['away_id']):
   a=[a for a in index.get((r['league'],team),[]) if a[0]<=cut]
   ages=np.array([(t-x[0]).days for x in a],dtype=float)
   data=np.array([[x[2],x[3]] for x in a],dtype=float).reshape(-1,2,4)
   h.append((ages,data))
  out[r['fid']]=h
 return out
trh=histories(train,ei);zh=histories(z,idx);rh=histories(ex,idx);prior=np.array([12.,4.,50.,1.4])
def features(hist,half_life,mass_matched=False):
 fs={};mass={}
 for fid,h in hist.items():
  v=[];m=[]
  for ages,data in h:
   w=np.exp2(-ages/half_life) if half_life is not None else np.ones(len(ages))
   if mass_matched and w.sum()>0:
    w=w*np.exp2(-ages/180.).sum()/w.sum()
   m.append(float(w.sum()))
   a=((w[:,None,None]*data).sum(0)+8*prior)/(w.sum()+8)
   for x in a:v.extend([*x,x[3]/max(x[1],.01)])
  fs[fid]=v;mass[fid]=min(m)
 return fs,mass
def fit(tr,te,TF,F):
 X=np.array([g['base'](r,TF,'full_shot_efficiency') for r in tr]);Xt=np.array([g['base'](r,F,'full_shot_efficiency') for r in te])
 return g['goals_predict'](X,vec(tr,'hg')+vec(tr,'ag'),np.log(vec(tr,'mh')+vec(tr,'ma')),Xt,np.log(vec(te,'mh')+vec(te,'ma')))
def predict(z,TF,F):
 total=np.zeros(len(z))
 for y in sorted({r['year'] for r in z}):
  mask=np.array([r['year']==y for r in z]);te=[r for r,m in zip(z,mask) if m];tr=[r for r in train if r['year']<y]
  assert tr and max(r['year'] for r in tr)<y
  total[mask]=fit(tr,te,TF,F)
 return total
def summarize(z,total,market):
 p=g['make_pred'](z,total);a=g['probstats'](z,total);m=g['probstats'](z,market)
 return {**g['stat'](p[2]),'brier':a['line_brier'],'logloss':a['line_logloss'],'goal_bias':a['mean_goal_bias'],'delta_brier_market':round(a['line_brier']-m['line_brier'],6),'delta_logloss_market':round(a['line_logloss']-m['line_logloss'],6)}
specs=[('180',180,False),('30',30,False),('60',60,False),('90',90,False),('365',365,False),('uniform',None,False),('30_mass180',30,True),('60_mass180',60,True),('90_mass180',90,True),('365_mass180',365,True),('uniform_mass180',None,True)]
models={};preds={};mz=vec(z,'mh')+vec(z,'ma');mr=vec(ex,'mh')+vec(ex,'ma');rids={r['fid'] for r in rows}
for name,hl,match in specs:
 tf,_=features(trh,hl,match);zf,zm=features(zh,hl,match);rf,rm=features(rh,hl,match)
 if name=='180':
  assert all(np.allclose(tf[k],g['esfeat'][k]) for k in tf)
  assert all(np.allclose(zf[k],H[k]) for k in zf)
  assert all(np.allclose(rf[k],F[k]) for k in rf)
 p=predict(z,tf,zf);q=predict(ex,tf,rf)
 if name=='180':
  assert g['stat'](g['make_pred'](z,p)[2])['U']==-13.82 and g['stat'](g['make_pred'](ex,q)[2])['U']==-8.54
 def sub(mask):
  return summarize([r for r,b in zip(z,mask) if b],p[mask],mz[mask])
 unique=np.array([r['fid'] not in rids for r in z])
 models[name]={'historical_all':summarize(z,p,mz),'historical_disjoint':sub(unique),'year':{str(y):sub(np.array([r['year']==y for r in z])) for y in sorted({r['year'] for r in z})},'year_disjoint':{str(y):sub(unique&np.array([r['year']==y for r in z])) for y in sorted({r['year'] for r in z})},'receipt':summarize(ex,q,mr),'median_min_effective_historical':round(float(np.median(list(zm.values()))),4),'median_min_effective_receipt':round(float(np.median(list(rm.values()))),4)}
 preds[name]=(p,q)
 print(name,[(y,v['ROI'],v['delta_brier_market']) for y,v in models[name]['year'].items()], 'all',models[name]['historical_all'],'receipt',models[name]['receipt'],flush=True)
# Prespecified evaluation logic: select lowest Brier on earlier historical year(s) then evaluate subsequent year; retrospective not independent forward validation.
# Do not optimize ROI. Compare to fixed 180 on both held-out calendar years.
transfers={}
for y in (2025,2026):
 prev=[a for a in (2024,2025) if a<y]
 scores={k:sum(m['year'][str(a)]['brier']*m['year'][str(a)]['n'] for a in prev)/sum(m['year'][str(a)]['n'] for a in prev) for k,m in models.items()}
 choice=min(scores,key=scores.get)
 transfers[str(y)]={'selection_years':prev,'selected':choice,'earlier_brier':scores[choice],'test':models[choice]['year'][str(y)],'fixed180':models['180']['year'][str(y)],'receipt_if_2026':models[choice]['receipt'] if y==2026 else None}
# paired diagnostic compare dates as blocks, quantify uncertainty of Brier differences using bootstrap.
def individual_brier(z,t):
 y=vec(z,'hg')+vec(z,'ag');line=vec(z,'ol')
 c=g['pmf'](t).cumsum(axis=1);v=[]
 for q in g['halves'](line):
  w=1-g['cdf_at'](c,np.floor(q)[:,None])[:,0];l=g['cdf_at'](c,(np.ceil(q)-1)[:,None])[:,0];p=np.maximum(0,1-w-l)
  pr=np.column_stack([w,p,l]);obs=np.column_stack([y>q,y==q,y<q])
  v.append(((pr-obs)**2).sum(1))
 return np.mean(v,axis=0)
# Check available numerical helper identities from existing probability audit.
out={'method':'Identical R10 targets, no fresh API. Experimental half-lives only; rebuild BOTH ESPN training and TC test features; annual training strictly before target year; date lag and shrinkage unchanged. Matched-mass experiments preserve original effective weight sum, varying recency only. All variants retained; selection historical only, no production rule. Market implicit used for probability not directional ROI.','models':models,'calendar_transfer':transfers,'historical_n':len(z),'receipt_n':len(ex),'history_n':len(history)}
(P/'m8_tc_recency_research_20261116.json').write_text(json.dumps(out,indent=2))
print('TRANSFER',json.dumps(transfers),flush=True)
