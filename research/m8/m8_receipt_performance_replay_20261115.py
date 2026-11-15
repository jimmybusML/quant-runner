import json,hashlib,datetime,collections,math
from pathlib import Path
import numpy as np
from research.m3.probabilities import settle_score
P=Path('/Users/mac/QuantAsiaDesk/research-work')
def load(n):return list(map(json.loads,(P/n).open()))
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def digest(b):return hashlib.sha256(b).hexdigest()
g={};src=(P/'m8_efficiency_probability_audit_20261115.py').read_text();exec(src[:src.rindex("out={'method'")],g)
audit={};src=(P/'m8_independent_receipt_coverage_20261115.py').read_text();exec(src[:src.index('rows=[];errors=')],audit)
records=load('m8_independent_receipt_coverage_20261115.jsonl')
assert len(records)==1470
E=g['ep'];T=g['T'];tr=[r for r in g['esvalid'] if r['league'] in ('1','14') and r['year']<2026]
assert len(tr)==3342 and len(E)==4122 and len(T)==406
def histindex(source):
 idx=collections.defaultdict(list)
 for r in source.values():
  for role,other in [('h','a'),('a','h')]:
   team=r['home'] if role=='h' else r['away']
   idx[(str(r['league']),str(team))].append((datetime.date.fromisoformat(r['date']),r['fid'],[r[role+'shots'],r[role+'sot'],r[role+'poss'],r[role+'g']],[r[other+'shots'],r[other+'sot'],r[other+'poss'],r[other+'g']]))
 return idx
def feature(r,idx):
 t=datetime.date.fromisoformat(r['date']);cut=t-datetime.timedelta(days=3)
 v=[];counts=[];effective=[];last=[]
 for team in (r['home_id'],r['away_id']):
  h=[a for a in idx.get((r['league'],team),[]) if a[0]<=cut]
  w=np.array([2**(-(t-a[0]).days/180) for a in h]);counts.append(len(h));effective.append(float(w.sum()));last.append(max(a[0] for a in h).isoformat() if h else None)
  for j in (2,3):
   prior=np.array([12.,4.,50.,1.4]);a=(sum((weight*np.array(x[j]) for weight,x in zip(w,h)),np.zeros(4))+8*prior)/(w.sum()+8)
   v+=list(a)+[a[3]/max(a[1],.01)]
 return v,counts,effective,last
idxs={'ESPN':histindex(E),'TC':histindex(T)}
# Verify independent implementation reproduces previous features on existing fixtures.
for source,base,features in [('ESPN',E,g['esfeat']),('TC',T,g['tcfeat'])]:
 for r in list(base.values())[::17]:
  v,*_=feature({'date':r['date'],'league':str(r['league']),'home_id':str(r['home']),'away_id':str(r['away'])},idxs[source]);assert np.allclose(v,features[r['fid']])
obs=[];featuremaps={s:{} for s in idxs};bad=collections.Counter();rows=[]
for a in records:
 if not a['verified_receipt'] or a['FT'] is None:continue
 f=a['fid'];q=next(q for q in audit['by'][f] if q['received_utc']==a['receipt_utc'] and q['snapshot_horizon']==a['horizon'])
 x=audit['verify'](q);ft,err=audit['final'](f,x);assert ft==a['FT'] and err is None
 ko=dt(q['kickoff_utc']);cut=ko-datetime.timedelta(hours=12)
 ah=q['markets']['AH'];ou=q['markets']['OU'];hg,ag=ft
 r={'fid':f,'year':ko.year,'date':ko.date().isoformat(),'league':str(x['l_id']),'home_id':str(x['h_id']),'away_id':str(x['a_id']),'hg':hg,'ag':ag,'al':ah['line'],'ol':ou['line'],'ah':ah['odds']['home'],'aa':ah['odds']['away'],'oo':ou['odds']['over'],'ou':ou['odds']['under'],'age_ah':(cut-dt(ah['source_event_utc'])).total_seconds()/3600,'age_ou':(cut-dt(ou['source_event_utc'])).total_seconds()/3600}
 for side in ('over','under'):r[side+'_U']=settle_score('OU',r['ol'],side,hg,ag,ou['odds'][side])[1]
 assert min(r['age_ah'],r['age_ou'])>=0
 r['source_features']={}
 for s,idx in idxs.items():
  v,n,eff,last=feature(r,idx);featuremaps[s][f]=v;r['source_features'][s]={'counts':n,'effective':eff,'last':last}
 obs.append(r)
assert len(obs)==1393
vec=g['vec'];ol,al=vec(obs,'ol'),vec(obs,'al');op=vec(obs,'ou')/(vec(obs,'oo')+vec(obs,'ou'));ap=vec(obs,'aa')/(vec(obs,'ah')+vec(obs,'aa'))
tot,ok1,er1=g['solve'](op,.0001,20.,lambda x:g['ou_share'](x,ol))
fra,ok2,er2=g['solve'](ap,.00001,.99999,lambda x:g['ah_share'](tot,x,al))
for i,r in enumerate(obs):
 if not (ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5):bad['latent_solver']+=1;continue
 r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]));rows.append(r)
ids={r['fid'] for r in load('m8_foundation_20261115/historical_membership.jsonl')}
prior_ids={r['fid'] for r in E.values() if r['year']==2026}|{r['fid'] for r in T.values()}
# Existing model fixed before evaluation of these actual-receipt rows. No optimization.
def evaluate(te,source):
 F=featuremaps[source];ps={'market_implied':g['make_pred'](te,vec(te,'mh')+vec(te,'ma'))}
 for k in ('market','full','full_shot_efficiency'):ps[k]=g['forecast'](tr,te,F,k)
 groups={'all':np.ones(len(te),bool),'outside_eight':np.array([r['fid'] not in ids for r in te]),'outside_previous_ESPN_TC_target':np.array([r['fid'] not in prior_ids for r in te])}
 ret={'n':len(te),'median_min_prior_effective':round(float(np.median([min(r['source_features'][source]['effective']) for r in te])),3),'models':{}}
 for k,p in ps.items():
  ret['models'][k]={}
  for label,m in groups.items():
   if not m.any():continue
   q=[r for r,b in zip(te,m) if b];ret['models'][k][label]={**g['metrics'](te,p,m),**g['probstats'](q,p[0][m])}
 return ret
both={s:{r['fid'] for r in rows if min(r['source_features'][s]['counts'])>0} for s in idxs}
out={'method':'Historical replay of original timestamped Crown AH/OU actually received before T12. Same fixed 2026 annual model fitted on 3342 earlier-year ESPN core rows, source-separated 180 day rolling, 8-match shrinkage, 3 UTC day lag; quote age evaluated at T12. One receipt per fixture; not prospective model lock or performance receipt evidence. Same source history used as coverage diagnostic only. No new rule.','n_receipt_FT':len(obs),'n_latent_valid':len(rows),'solver_errors':dict(bad),'prior_coverage':{s:len(v) for s,v in both.items()},'unique_both_prior':len(both['ESPN']|both['TC']),'both_sources':len(both['ESPN']&both['TC']),'results':{}}
for s in idxs:
 for label,sel in [('all_with_source_history',both[s]),('unique_to_source',both[s]-both['TC' if s=='ESPN' else 'ESPN']),('common_sources',both['ESPN']&both['TC'])]:
  te=[r for r in rows if r['fid'] in sel]
  if te:out['results'][s+'_'+label]=evaluate(te,s)
out['all_market_only']=evaluate(rows,'ESPN')['models']['market_implied']
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_receipt_performance_replay_20261115.json').write_text(json.dumps(out,indent=2))
print('COVERAGE', {k:v for k,v in out.items() if k not in ('results','all_market_only','method')},flush=True)
for k,v in out['results'].items():
 print(k,v['n'],v['median_min_prior_effective'],{model:{label:(x['n'],x['U'],x['ROI'],x['line_brier'],x['line_logloss']) for label,x in result.items()} for model,result in v['models'].items()},flush=True)
