# R33: classify all nonzero unmatched paths; two exhaustive partitions.
import json,collections,datetime,hashlib
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_frozen_eight_adjacent_structure_20261116.py').read_text()
exec(s[:s.index('groups=collections.defaultdict(list);unassigned=')])
exec(s[s.index('def stat(z,'):s.index("out={'method'")])
remaining=[r for r in rows if r['fid'] not in ids]
groups=collections.defaultdict(list)
for r in remaining:
 if r['end_zero']:continue
 # Use natural phases relative to final favorite. Second partition differentiates
 # actual transient deepening from drift without deepening.
 phase=r.get('path_6_3_1')
 assert phase
 shape=r['path_shape'];dog='home' if r['end_line']>0 else 'away';fav=opposite(dog)
 # Base, A, B and C already consumed the corresponding paths.
 z={'fid':r['fid'],'year':r['year'],'date':r['date'],'league':r['league'],'pnl':r['end_'+dog+'_U'],'other_pnl':r['end_'+fav+'_U']}
 groups['phase|'+phase].append(z)
 groups['path|'+phase+'|'+shape+'|'+('transient_deepen' if r['had_step'] else 'no_deepen')].append(z)
N=sum(not r['end_zero'] for r in remaining)
assert sum(len(v) for k,v in groups.items() if k.startswith('phase|'))==N
assert sum(len(v) for k,v in groups.items() if k.startswith('path|'))==N
out={'method':'R33 same T1 complement of frozen eight, all nonzero AH paths, complete three-point phase and phase/full shape/local deepening partitions. Both sides reported. Prior-year side choice and positive prior empirical return experiments are exploratory alternatives not formal gates. No future fixture identity or outcome used for selection. Repeated old historical data; no independent evaluation.','foundation':foundation,'coverage':{'all':len(rows),'remaining':len(remaining),'nonzero':N,'zero':len(remaining)-N},'groups':{},'tests':{}}
for k,z in sorted(groups.items()):
 a={'dog':desc(z),'fav':desc(z,'other_pnl')}
 out['groups'][k]=a
 print(k,'dog',a['dog']['all'],a['dog']['2026'],'fav',a['fav']['all'],a['fav']['2026'],flush=True)
# Learn direction on prior years and report both whole-partition and
# estimated-positive research alternatives (not a new production filter).
for partition in ('phase','path'):
 G={k:z for k,z in groups.items() if k.startswith(partition+'|')}
 for mode in ('all','positive_prior'):
  pred=[];fits={}
  for y in (2024,2025,2026):
   fits[str(y)]={}
   for k,z in G.items():
    tr=[r for r in z if r['year']<y];te=[r for r in z if r['year']==y]
    if not te:continue
    if not tr:
     side='pnl';mean=None
    else:
     side='pnl' if sum(r['pnl'] for r in tr)>=sum(r['other_pnl'] for r in tr) else 'other_pnl'
     mean=sum(r[side] for r in tr)/len(tr)
    active=mode=='all' or (mean is not None and mean>0)
    fits[str(y)][k]={'n':len(tr),'side':side,'mean_U':mean,'active':active,'target_n':len(te)}
    if active:pred.extend({**r,'pnl':r[side]} for r in te)
  assert len({r['fid'] for r in pred})==len(pred)
  a={'standalone':desc(pred),'combined':desc([r for r in frozen if r['year']>=2024]+pred),'fit':fits}
  out['tests'][partition+'_'+mode]=a
  print('FIT',partition,mode,a['standalone']['all'],a['standalone']['2026'],a['combined']['2026'],flush=True)
(P/'m8_frozen_eight_path_boundary_20261116.json').write_text(json.dumps(out,indent=2))
# Reuse R32 actual receipt and independent FT identity/hash verification,
# with the R33 phase classifier rather than the D/E/F classifier.
src=(P/'m8_frozen_eight_adjacent_structure_20261116.py').read_text()
block=src[src.index('import math,bisect'):src.index("print('RECEIPT'")]
old='g,side=classify(a);qc[\'verified_quote\']+=1'
new="""def phase_state(u,v):return 'deepen' if (v-u)*l>0 else 'weaken' if (v-u)*l<0 else 'same'
  g='phase|'+phase_state(start[1],mid[1])+'_'+phase_state(mid[1],l)
  side=('home' if l>0 else 'away') if l else None
  qc['verified_quote']+=1"""
assert old in block
block=block.replace(old,new)
exec(compile(block,'R32_verified_receipt_R33_classifier','exec'))
print('RECEIPT',json.dumps(out['receipt_replay']),flush=True)
# For an identical, chronological application of the phase rules, use the
# history-based annual fit for 2026 and verified receipt results only.
for k in ('phase_all','phase_positive_prior'):
 fit=out['tests'][k]['fit']['2026'];pred=[];unsettled=0
 for g,z in res.items():
  v=fit.get(g)
  if not v or not v['active']:continue
  for r in z:
   if r['pnl'] is None:unsettled+=1;continue
   pred.append({**r,'pnl':r[v['side']]})
 out['tests'][k]['receipt']={'settled':stat(pred),'unsettled':unsettled}
 print('RECEIPT_FIT',k,out['tests'][k]['receipt'],flush=True)
for k in ('phase|weaken_deepen','phase|weaken_weaken'):
 a=out['groups'][k]
 for side in ('dog','fav'):
  print('YEARS',k,side,[(y,v['n'],v['U'],v['ROI']) for y,v in a[side]['years'].items()],flush=True)
(P/'m8_frozen_eight_path_boundary_20261116.json').write_text(json.dumps(out,indent=2))
