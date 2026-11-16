import json,hashlib,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_receipt_performance_replay_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
orig=dict(T)
bridge=json.loads((P/'m8_tc_local_probe_bridge_20261115.json').read_text())['added']
r1=load('m8_tc_continuous_20261116/verified_new.jsonl')
r2=load('m8_tc_continuous_round2_20261116/verified_new.jsonl')
r3=load('m8_tc_crossyear_round3_20261116/verified_new.jsonl')
r4=load('m8_tc_crossyear_round4_20261116/verified_new.jsonl')
r5=load('m8_tc_crossyear_round5_20261116/verified_new.jsonl')
before={**orig,**{r['fid']:r for r in bridge+r1+r2+r3+r4}}
history={**before,**{r['fid']:r for r in r5}}
assert len(before)==1614 and len(history)==1614+len(r5)
prioridx=histindex(before);idx=histindex(history)
def features_for(z,index):
 fs={};counts={}
 for r in z:
  v,n,*_=feature(r,index);fs[r['fid']]=v;counts[r['fid']]=n
 return fs,counts
F,N=features_for(rows,idx);prevF,prevN=features_for(rows,prioridx)
old=[r for r in rows if min(prevN[r['fid']])>0]
ex=[r for r in rows if min(N[r['fid']])>0]
increment=[r for r in ex if min(prevN[r['fid']])==0]
assert len(old)==308
def predict_annual(z,fs):
 total=np.zeros(len(z));side=np.zeros(len(z),dtype=bool);pnl=np.zeros(len(z));used=np.zeros(len(z),dtype=bool)
 for y in sorted({r['year'] for r in z}):
  mask=np.array([r['year']==y for r in z]);tt=[r for r in z if r['year']==y];train=[r for r in g['esvalid'] if r['league'] in ('1','14') and r['year']<y]
  assert all(r['year']<y for r in train) and len(train)>0
  total[mask],side[mask],pnl[mask]=g['forecast'](train,tt,fs,'full_shot_efficiency')
  used|=mask
 assert used.all()
 return total,side,pnl
def calc(z,fs):
 if not z:return {'n':0}
 p=predict_annual(z,fs);ref=g['make_pred'](z,vec(z,'mh')+vec(z,'ma'))
 def group(mask):
  if not mask.any():return {'n':0}
  a=[r for r,m in zip(z,mask) if m]
  daily=collections.defaultdict(float)
  for r,v in zip(a,p[2][mask]):daily[r['date']]+=float(v)
  c=k=dd=0.
  for d,u in sorted(daily.items()):c+=u;k=max(k,c);dd=max(dd,k-c)
  return {**g['metrics'](z,p,mask),'market':g['stat'](ref[2][mask]),'daily_mdd':round(dd,3),**g['probstats'](a,p[0][mask])}
 return {'n':len(z),'all':group(np.ones(len(z),bool)),'outside_eight':group(np.array([r['fid'] not in ids for r in z])),'year':{str(y):group(np.array([r['year']==y for r in z])) for y in sorted({r['year'] for r in z})},'league':{l:group(np.array([r['league']==l for r in z])) for l in sorted({r['league'] for r in z})}}
prior=calc(old,prevF);assert prior['all']['U']==13.65
# Historical quote targets: unique and source evidence kept separate from actual receipt rows.
def historical(recs,index):
 h=[];fs={}
 for rr in recs:
  f=rr['fid'];r=dict(audit['target'][f]);v,n,*_=feature(r,index)
  if min(n)<=0:continue
  fs[f]=v;h.append(r)
 if not h:return h,fs
 ol,al=vec(h,'ol'),vec(h,'al');op=vec(h,'ou')/(vec(h,'oo')+vec(h,'ou'));ap=vec(h,'aa')/(vec(h,'ah')+vec(h,'aa'))
 tot,ok1,er1=g['solve'](op,.0001,20.,lambda x:g['ou_share'](x,ol));fra,ok2,er2=g['solve'](ap,.00001,.99999,lambda x:g['ah_share'](tot,x,al))
 for i,r in enumerate(h):
  assert ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5
  r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]))
 return h,fs
h,HF=historical(r1+r2+r3+r4+r5,idx)
h3=[r for r in h if r['fid'] in {q['fid'] for q in r5}]
seen=set(E)|set(before)|{r['fid'] for r in rows}
fresh=[r for r in h3 if r['fid'] not in seen]
out={'method':'Separate retrospective receipt and historical quote replays. Same annual model recipe with training years strictly earlier than each target year; 2026 model unchanged. Same historical feature lag, 180-day decay and shrinkage; no new trade conditions.','prior_n':len(before),'new_n':len(r5),'total_n':len(history),'new_year':dict(collections.Counter(r['year'] for r in r5)),'new_league':dict(collections.Counter(r['league'] for r in r5)),'dates':[min(r['date'] for r in r5),max(r['date'] for r in r5)],'prior_receipt':prior,'same_receipt_updated':calc(old,F),'expanded_receipt':calc(ex,F),'increment_receipt':calc(increment,F),'new_historical':calc(h3,HF),'new_historical_outside_previous':calc(fresh,HF),'all_batches_historical':calc(h,HF),'side_switch_same_receipt':int((predict_annual(old,prevF)[1]!=predict_annual(old,F)[1]).sum()),'train_n':{str(y):len([r for r in g['esvalid'] if r['league'] in ('1','14') and r['year']<y]) for y in sorted({r['year'] for r in h})}}
# Preserve quote evidence split. Evaluate all available historical performance fixtures once per FID.
allhist=[r for r in history.values() if r['fid'] in audit['target'] and r['year']>=2023]
hh,HH=historical(allhist,idx)
out['all_available_historical']=calc(hh,HH)
out['all_available_historical_without_receipt_overlap']=calc([r for r in hh if r['fid'] not in {q['fid'] for q in ex}],HH)
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_crossyear_round5_replay_20261116.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print('DATA',{k:out[k] for k in ('prior_n','new_n','total_n','new_year','new_league','dates','side_switch_same_receipt','train_n','foundation')},flush=True)
for k in ('prior_receipt','same_receipt_updated','expanded_receipt','increment_receipt','new_historical','new_historical_outside_previous','all_batches_historical','all_available_historical','all_available_historical_without_receipt_overlap'):
 a=out[k];print(k,a['n'],{x:{y:a[x][y] for y in ('n','U','ROI','daily_mdd','market') if y in a[x]} for x in ('all','outside_eight') if x in a}, 'YEAR', {y:(v['n'],v['U'],v['ROI'],v['daily_mdd'],v['market']['ROI']) for y,v in a.get('year',{}).items()},flush=True)
