import json,hashlib,collections,datetime
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_receipt_performance_replay_20261115.py').read_text()
exec(s[:s.rindex("out={'method'")])
orig=dict(T);bridge=json.loads((P/'m8_tc_local_probe_bridge_20261115.json').read_text())['added']
new=load('m8_tc_continuous_20261116/verified_new.jsonl')
history={**orig,**{r['fid']:r for r in bridge},**{r['fid']:r for r in new}}
assert len(history)==len(orig)+len(bridge)+len(new)
idx=histindex(history)
F={}
N={}
for r in rows:
 v,n,e,last=feature(r,idx);F[r['fid']]=v;N[r['fid']]=n
old=[r for r in rows if r['fid'] in both['TC']]
expanded=[r for r in rows if min(N[r['fid']])>0]
added=[r for r in expanded if r['fid'] not in both['TC']]
assert len(old)==263
p0=g['forecast'](tr,old,featuremaps['TC'],'full_shot_efficiency')
assert g['stat'](p0[2])['U']==22.435
def evaluate(te,source):
 if not te:return {'n':0}
 p=g['forecast'](tr,te,source,'full_shot_efficiency')
 ref=g['make_pred'](te,vec(te,'mh')+vec(te,'ma'))
 mask=np.array([r['fid'] not in ids for r in te])
 def mstat(mask):
  a=[r for r,b in zip(te,mask) if b]
  if not a:return {'n':0}
  daily=collections.defaultdict(float)
  for r,v in zip(a,p[2][mask]):daily[r['date']]+=float(v)
  cum=peak=dd=0
  for day,u in sorted(daily.items()):
   cum+=u;peak=max(peak,cum);dd=max(dd,peak-cum)
  return {**g['metrics'](te,p,mask),**g['probstats'](a,p[0][mask]),'daily_mdd':round(dd,3),'market':g['stat'](ref[2][mask])}
 return {'n':len(te),'all':mstat(np.ones(len(te),bool)),'outside_eight':mstat(mask),'league':{l:mstat(np.array([r['league']==l for r in te])) for l in sorted({r['league'] for r in te})}}
out={'method':'Fixed 3342 pre-2026 ESPN core training and TC historical feature construction; no parameter changes. Expanded history is retrospective, not verified available in real time. Actual receipts held separate from post-match retrieved T12 archive. Coverage strata diagnostic, not trade rules.','history_before':len(orig),'bridge':len(bridge),'new':len(new),'history_after':len(history),'coverage':dict(collections.Counter(r['league'] for r in new)),'old_receipt_original':evaluate(old,featuremaps['TC']),'old_receipt_expanded':evaluate(old,F),'expanded_receipt':evaluate(expanded,F),'newly_covered_receipt':evaluate(added,F)}
p1=g['forecast'](tr,old,F,'full_shot_efficiency')
out['changed_sides_old']=int((p0[1]!=p1[1]).sum())
# new target rows have provider-event T12 historical odds, no real-time receipt evidence.
h=[]
for rr in new:
 f=rr['fid'];r=dict(audit['target'][f]);v,n,e,last=feature(r,idx)
 if min(n)<=0:continue
 F[f]=v;h.append(r)
if h:
 ol,al=vec(h,'ol'),vec(h,'al');op=vec(h,'ou')/(vec(h,'oo')+vec(h,'ou'));ap=vec(h,'aa')/(vec(h,'ah')+vec(h,'aa'))
 tot,ok1,er1=g['solve'](op,.0001,20.,lambda x:g['ou_share'](x,ol));fra,ok2,er2=g['solve'](ap,.00001,.99999,lambda x:g['ah_share'](tot,x,al))
 for i,r in enumerate(h):
  assert ok1[i] and ok2[i] and er1[i]<1e-5 and er2[i]<1e-5
  r['mh']=float(tot[i]*fra[i]);r['ma']=float(tot[i]*(1-fra[i]))
 known=set(E)|set(orig)|{r['fid'] for r in rows}|{r['fid'] for r in bridge}
 fresh=[r for r in h if r['fid'] not in known]
 out['new_target_historical']=evaluate(h,F);out['outside_previous_performance_and_receipt']=evaluate(fresh,F)
 out['new_target_excluded_no_both_prior']=len(new)-len(h)
else:out['new_target_historical']={'n':0};out['outside_previous_performance_and_receipt']={'n':0}
m=json.loads((P/'m8_foundation_20261115/manifest.json').read_text())
out['foundation']={'membership':digest((P/m['historical_membership']['local_file']).read_bytes())==m['historical_membership']['sha256'],'inputs':all(digest((P/k).read_bytes())==v for k,v in m['input_sha256'].items()),'scripts':all(digest((P/k).read_bytes())==v for k,v in m['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_continuous_replay_20261116.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print('HISTORY',len(orig),len(bridge),len(new),len(history),out['coverage'],'SWITCH',out['changed_sides_old'])
for k in ('old_receipt_original','old_receipt_expanded','expanded_receipt','newly_covered_receipt','new_target_historical','outside_previous_performance_and_receipt'):
 a=out[k];print(k,a['n'],{x:{y:a[x][y] for y in ('n','U','ROI','daily_mdd','line_brier') if y in a[x]} for x in ('all','outside_eight') if x in a},flush=True)
print('FOUNDATION',out['foundation'],flush=True)
