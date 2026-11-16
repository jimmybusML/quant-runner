import json,collections,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_candidate_complementarity_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
# A prediction needs prior team statistics, not the target match's own post-match
# statistics. Retain fixed R10 training pool; expand targets only.
leagues={r['league'] for r in zz}
oldids={r['fid'] for r in zz}
receiptids={r['fid'] for r in rows}
targets=[r for r in audit['target'].values() if r['league'] in leagues and 2024<=r['year']<=2026 and r['fid'] not in oldids and r['fid'] not in receiptids and r['fid'] not in ids]
assert len({r['fid'] for r in targets})==len(targets)
new,ff=historical(targets,idx)
assert not ({r['fid'] for r in new}&(oldids|receiptids|ids))
NF=fset(histories(new,idx))
# Frozen existing training targets only, including the prior chronological splits.
NA,_=run_mode('baseline','mixed',new,NF)
NB=np.zeros(len(new));filled=np.zeros(len(new),bool)
for y in sorted({r['year'] for r in new}):
 e=[r for r in train if r['year']<y];seen={r['fid'] for r in e};c=[r for r in z if r['year']<y and r['fid'] not in seen]
 for l in sorted({r['league'] for r in new if r['year']==y}):
  add=[r for r in c if r['league']==l];tr=e+add
  assert max(r['year'] for r in tr)<y
  X=np.asarray([EA[r['fid']] for r in e]+[CA[r['fid']] for r in add])
  mask=np.array([r['year']==y and r['league']==l for r in new]);te=[r for r,b in zip(new,mask) if b]
  assert not ({r['fid'] for r in tr}&{r['fid'] for r in te})
  NB[mask]=fitmat(tr,X,te,matrix(te,NF,kind));filled|=mask
assert filled.all()
# Check existing A/B reproduction before reporting.
assert assess(zz,A,mz)['U']==24.205 and assess(zz,B,mz)['U']==64.425
base26=[r for r in load('m8_foundation_20261115/historical_membership.jsonl') if r['year']==2026]
baseweek=collections.Counter(datetime.date.fromisoformat(r['date']).strftime('%G-W%V') for r in base26)
def weekly(t,p):
 x=collections.defaultdict(lambda:[0,0.])
 for r,v in zip(t,g['make_pred'](t,p)[2]):
  k=datetime.date.fromisoformat(r['date']).strftime('%G-W%V');x[k][0]+=1;x[k][1]+=float(v)
 return {k:{'n':v[0],'U':round(v[1],3)} for k,v in sorted(x.items())}
def group(t,p):
 if not t:return {'n':0}
 m=vec(t,'mh')+vec(t,'ma');a=assess(t,p,m);w=weekly(t,p)
 a['active_weeks']=len(w);a['active_week_avg']=round(len(t)/len(w),3);a['weeks']=w
 return a
def subgroup(t,p,mask):return group([r for r,b in zip(t,mask) if b],p[mask])
out={'method':'Fixed R10 training and A/B/C model recipes. Expand historical T12 targets without requiring the target match own later performance data; require only existing prior team history, same original lag. Exclude all original eight fixture IDs, previous R10 historical targets and verified receipt archive. No parameter change. Historical retrieval not prospective; potential prior exploration in other research remains.','eligible_targets_without_prior_check':len(targets),'new_targets':len(new),'history_n':len(history),'dates':[min(r['date'] for r in new),max(r['date'] for r in new)],'target_counts_by_year':dict(collections.Counter(r['year'] for r in targets)),'new_counts_by_year':dict(collections.Counter(r['year'] for r in new)),'models':{}}
# Prior target coverage diagnostic: exclude any fixture whose own ESPN or TC performance record was previously present.
fresh=np.array([r['fid'] not in E and r['fid'] not in history for r in new])
prev_mask=np.array([r['fid'] not in ids for r in zz])
for name,p,oldp in [('A',NA,A),('B',NB,B),('C',(NA+NB)/2,(A+B)/2)]:
 a={'new':group(new,p),'new_without_existing_performance_record':subgroup(new,p,fresh),'new_year':{str(y):subgroup(new,p,np.array([r['year']==y for r in new])) for y in sorted({r['year'] for r in new})},'league':{l:subgroup(new,p,np.array([r['league']==l for r in new])) for l in sorted(leagues)}}
 old=[r for r,b in zip(zz,prev_mask) if b];combined=old+new;cp=np.concatenate([oldp[prev_mask],p])
 assert len({r['fid'] for r in combined})==len(combined)
 a['combined_outside_eight']=group(combined,cp)
 a['combined_2026']=subgroup(combined,cp,np.array([r['year']==2026 for r in combined]))
 w=a['combined_2026']['weeks'];keys=sorted(set(baseweek)|set(w));a['combined_2026_with_base_count']=len(base26)+a['combined_2026']['n'];a['combined_2026_with_base_avg_observed_weeks']=round(a['combined_2026_with_base_count']/len(keys),3)
 a['combined_2026_with_base_calendar_avg']=round(a['combined_2026_with_base_count']/45,3) if min(keys)=='2026-W01' and max(keys)=='2026-W45' else None
 out['models'][name]=a
 def trim(x):return {k:v for k,v in x.items() if k!='weeks'}
 print(name,'new',trim(a['new']),'years',{y:trim(v) for y,v in a['new_year'].items()},'fresh',trim(a['new_without_existing_performance_record']),'combined_outside',trim(a['combined_outside_eight']),'combined26',trim(a['combined_2026']),'base_combo',a['combined_2026_with_base_calendar_avg'],flush=True)
print('coverage', {k:v for k,v in out.items() if k!='models'},flush=True)
print('league', {l:{name:[a['league'][l].get(k) for k in ('n','U','ROI')] for name,a in out['models'].items()} for l in sorted(leagues)},flush=True)
manifest=json.loads((P/'m8_foundation_20261115/manifest.json').read_text());d=lambda k:hashlib.sha256((P/k).read_bytes()).hexdigest()
out['foundation']={'membership':d(manifest['historical_membership']['local_file'])==manifest['historical_membership']['sha256'],'inputs':all(d(k)==v for k,v in manifest['input_sha256'].items()),'scripts':all(d(k)==v for k,v in manifest['script_sha256'].items())};assert all(out['foundation'].values())
(P/'m8_tc_target_coverage_expansion_20261116.json').write_text(json.dumps(out,indent=2))
