import json,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
R=[json.loads(l) for l in (P/'m8_2026_Crown_early_AH_24h_to_1h_window_study_20261114.jsonl').open()]
W=collections.defaultdict(dict)
for r in R:W[r['window']][r['fid']]=r
def stats(v,key='dog_U'):
 n=len(v);p=sum(r[key] for r in v)
 return {'n':n,'net_U':round(p,3),'ROI_pct':round(100*p/n,3) if n else None}
old={r['fid']:r for r in W['T-6h→T-1h'].values() if r['state']=='deepen'}
OUT={'base':stats(list(old.values())),'early_windows':{},'late_windows':{},'all_states_earlier':{}}
for key in ['T-24h→T-18h','T-24h→T-12h','T-20h→T-12h','T-18h→T-12h','T-16h→T-10h','T-12h→T-8h','T-12h→T-6h','T-10h→T-6h','T-8h→T-4h']:
 rows=list(W[key].values())
 OUT['all_states_earlier'][key]={}
 for state in ('deepen','weaken','unchanged'):
  vals=[r for r in rows if r['state']==state]
  OUT['all_states_earlier'][key][state]={'dog':stats(vals),'favorite':stats(vals,'fav_U'),'Jan-Jun_dog':stats([r for r in vals if r['month']<='2026-06']),'Jul-Nov_dog':stats([r for r in vals if r['month']>='2026-07'])}
 for state in ('deepen','weaken'):
  a={r['fid']:r for r in rows if r['state']==state}
  missing=[r for fid,r in a.items() if fid not in old]
  s={'all':stats(list(a.values())),'overlap_with_original':len(set(a)&set(old)),'new_unique':stats(missing),'new_Jan-Jun':stats([r for r in missing if r['month']<='2026-06']),'new_Jul-Nov':stats([r for r in missing if r['month']>='2026-07']),'new_fav':stats(missing,'fav_U')}
  OUT['early_windows'][key+'|'+state]=s
  print('EARLY',key,state,s,flush=True)
for key in ['T-8h→T-1h','T-6h→T-4h','T-6h→T-2h','T-4h→T-1h','T-3h→T-1h','T-2h→T-1h']:
 sig={r['fid']:r for r in W[key].values() if r['state']=='deepen'}
 extra={fid:r for fid,r in sig.items() if fid not in old}
 combined={**old,**extra}
 s={'all':stats(list(sig.values())),'overlap_with_original':len(set(sig)&set(old)),'extra':stats(list(extra.values())),'extra_JanJun':stats([r for r in extra.values() if r['month']<='2026-06']),'extra_JulNov':stats([r for r in extra.values() if r['month']>='2026-07']),'combined':stats(list(combined.values()))}
 OUT['late_windows'][key]=s
 print('LATE',key,s,flush=True)
P.joinpath('m8_2026_early_AH_both_sides_and_new_unique_vs_original_20261114.json').write_text(json.dumps(OUT,ensure_ascii=False,indent=2))
