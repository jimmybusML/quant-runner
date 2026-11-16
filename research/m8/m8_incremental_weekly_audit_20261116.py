import json,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_tc_candidate_complementarity_20261116.py').read_text()
exec(s[:s.rindex("out={'method'")])
base=load('m8_foundation_20261115/historical_membership.jsonl')
base26=[r for r in base if r['year']==2026]
def wk(d):return datetime.date.fromisoformat(d).strftime('%G-W%V')
def agg(z,pp):
 d=collections.defaultdict(lambda:{'n':0,'U':0.})
 for r,p in zip(z,pp):
  x=d[wk(r['date'])];x['n']+=1;x['U']+=float(p)
 return {k:{'n':v['n'],'U':round(v['U'],3)} for k,v in sorted(d.items())}
def sumw(d,keys):
 vals=[d.get(k,{'n':0,'U':0}) for k in keys];n=sum(v['n'] for v in vals);u=sum(v['U'] for v in vals)
 return {'weeks':len(keys),'n':n,'U':round(u,3),'ROI':round(u/n*100,3) if n else None,'per_week':round(n/len(keys),3),'median_week':float(np.median([v['n'] for v in vals])),'min_week':min(v['n'] for v in vals),'max_week':max(v['n'] for v in vals),'positive_weeks':sum(v['U']>0 for v in vals)}
def weeks(a,b):
 d=datetime.date.fromisoformat(a);d-=datetime.timedelta(days=d.weekday());e=datetime.date.fromisoformat(b)
 return [wk((d+datetime.timedelta(days=7*i)).isoformat()) for i in range((e-d).days//7+1)]
bd=agg(base26,[r['pnl'] for r in base26]);dups=len(base26)-len({r['fid'] for r in base26})
print('BASE',len(base26),'unique',len(base26)-dups,'dates',min(r['date'] for r in base26),max(r['date'] for r in base26),'active',sumw(bd,list(bd)), 'calendar',sumw(bd,weeks(min(r['date'] for r in base26),max(r['date'] for r in base26))),flush=True)
out={'method':'UTC kickoff ISO calendar weeks. Fixed prior candidates, exclude frozen eight FIDs from added sample, no new rules. Historic events vs actual receipt evidence separate. Missing archive coverage is not zero future opportunities. Base row counts and distinct fixture counts distinguished. No extrapolated formal dispatch.','base2026':{'rows':len(base26),'unique_fids':len(base26)-dups,'active':sumw(bd,list(bd)),'calendar':sumw(bd,weeks(min(r['date'] for r in base26),max(r['date'] for r in base26))),'weekly':bd},'cohorts':{}}
for scope,t,ps in [('history2026',zz,[A,B,(A+B)/2]),('receipt',rr,[AR,BR,(AR+BR)/2])]:
 mask=np.array([r['fid'] not in ids and r['year']==2026 for r in t]);tt=[r for r,b in zip(t,mask) if b];keys=weeks(min(r['date'] for r in tt),max(r['date'] for r in tt))
 a={'dates':[min(r['date'] for r in tt),max(r['date'] for r in tt)],'shared_base':sumw(bd,keys),'models':{}}
 for name,p in zip(('A','B','C'),ps):
  pp=g['make_pred'](tt,p[mask])[2];d=agg(tt,pp)
  combo={k:{q:bd.get(k,{'n':0,'U':0})[q]+d.get(k,{'n':0,'U':0})[q] for q in ('n','U')} for k in keys}
  a['models'][name]={'active':sumw(d,list(d)),'calendar':sumw(d,keys),'combined_same_calendar':sumw(combo,keys),'weekly':d}
 print(scope,'dates',a['dates'],'base',a['shared_base'],flush=True)
 for name,v in a['models'].items():print(name,{k:x for k,x in v.items() if k!='weekly'},flush=True)
 if scope=='receipt':
  print('receipt weekly',[(k,bd.get(k),*[a['models'][n]['weekly'].get(k) for n in ('A','B','C')]) for k in keys],flush=True)
  full=keys[1:-1]
  a['interior_weeks']={'base':sumw(bd,full),'models':{n:sumw(v['weekly'],full) for n,v in a['models'].items()}}
  print('interior weeks',a['interior_weeks'],flush=True)
 out['cohorts'][scope]=a
# Common interior weeks fully within both recorded date ranges; not a completeness assertion.
a=out['cohorts']['receipt']
ks=['2026-W42','2026-W43','2026-W44']
a['shared_covered_interior_weeks']={'weeks':ks,'base':sumw(bd,ks),'models':{}}
for k,m in a['models'].items():
 w=m['weekly']
 a['shared_covered_interior_weeks']['models'][k]={'additional':sumw(w,ks),'combined':sumw({j:{'n':bd[j]['n']+w[j]['n'],'U':bd[j]['U']+w[j]['U']} for j in ks},ks)}
print('base by week',bd,flush=True)
(P/'m8_incremental_weekly_audit_20261116.json').write_text(json.dumps(out,indent=2))
