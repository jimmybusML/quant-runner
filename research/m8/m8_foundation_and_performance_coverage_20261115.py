import json,hashlib,datetime,collections
from pathlib import Path
P=Path('/Users/mac/QuantAsiaDesk/research-work')
s=(P/'m8_full_cohort_robustness_20261115.py').read_text()
exec(s[:s.index('def stat(z):')])
# Preserve the exact historical membership and original profit values, privately.
dst=P/'m8_foundation_20261115';dst.mkdir(exist_ok=True)
rows=[{'fid':r['fid'],'year':r['year'],'date':r['date'],'league':r['league'],'cohort':r['cohort'],'pnl':r['pnl'],'vintage':r['vintage']} for r in Z]
raw=''.join(json.dumps(r,sort_keys=True)+'\n' for r in sorted(rows,key=lambda r:(r['date'],r['fid']))).encode()
(dst/'historical_membership.jsonl').write_bytes(raw)
inputs=['m8_late_full_path_water_features_20261114.jsonl','m8_same_line_probability_path_20261114.jsonl','m8_independent_score_strength_20261114.jsonl','m8_extra_inventory_frozen_eight_20261115.jsonl','m8_raw_capture_unindexed_frozen_replay_20261115.jsonl','m8_new_receipt_frozen_eight_FT_20261115.jsonl']
scripts=['m8_late_6to1_dynamic_path_recovery_20261114.py','m8_late_full_path_water_features_20261114.py','m8_same_line_probability_path_20261114.py','m8_independent_score_strength_20261114.py','m8_score_market_divergence_full_AH_20261114.py','m8_extra_inventory_frozen_eight_20261115.py','m8_raw_capture_unindexed_frozen_replay_20261115.py','m8_full_cohort_robustness_20261115.py','m8_new_receipt_frozen_eight_20261115.py','m8_new_receipt_frozen_eight_FT_20261115.py']
def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()
rob=json.load((P/'m8_full_cohort_robustness_20261115.json').open())
ft=json.load((P/'m8_new_receipt_frozen_eight_FT_20261115.json').open())
m={'identity':'M8 historical eight-structure foundation preserved at user request','snapshot_commit':'c0986b191e8b4ef259d96cd1e6f2ef0e625d99bb','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cohorts':{k:{s:rob[k][s] for s in ('all','2026')} for k in ('base','A','B','C','D','E','F','G','all')},'separate_received_archive':ft['all'],'historical_membership':{'n':len(rows),'sha256':hashlib.sha256(raw).hexdigest(),'local_file':'m8_foundation_20261115/historical_membership.jsonl'},'input_sha256':{n:digest(P/n) for n in inputs},'script_sha256':{n:digest(P/n) for n in scripts}}
(dst/'manifest.json').write_text(json.dumps(m,indent=2))
print('FOUNDATION',len(rows),m['historical_membership'],m['separate_received_archive'],flush=True)
# Audit independent performance field availability in exact prior historical population.
p=(P/'m8_early_exact_cross_market_consistency_20261115.py').read_text()
exec(p[:p.index('C=collections.Counter();rows=[]')])
from collections import Counter,defaultdict
import re
counts=Counter();by_year=defaultdict(Counter);fields=Counter();examples={}
pattern=re.compile(r'xg|expected.?goal|shot|on.?target|off.?target|possession|dangerous.?attack|attack|statistic|stats|lineup|injur',re.I)
def scan(obj,prefix='',depth=0):
 if isinstance(obj,dict) and depth<=5:
  for k,v in obj.items():
   if k in ('bookmakers','odds','asian','goal','odds_list','asian_list','goal_list'):continue
   name=prefix+k
   yield name,v
   if isinstance(v,(dict,list)):yield from scan(v,name+'.',depth+1)
 elif isinstance(obj,list) and depth<=5:
  for v in obj:yield from scan(v,prefix+'[].',depth+1)
def val(x):
 try:return x is not None and not isinstance(x,bool) and float(x)>=0
 except:return False
for f,(file,sha,lid) in jobs.items():
 try:
  raw=file.read_bytes()
  if sha and hashlib.sha256(raw).hexdigest()!=sha:counts['sha_error']+=1;continue
  x=next(q for q in json.loads(raw)['data'] if str(q['id'])==f)
  if str(x['l_id'])!=str(lid) or x.get('status')!='full':counts['identity_or_status']+=1;continue
  y=dt(x['start']).year;counts['valid']+=1;by_year[y]['valid']+=1
  fs=dict(scan(x))
  for k in fs:fields[k]+=1
  matches=[k for k,v in fs.items() if pattern.search(k) and v not in (None, '',[],{})]
  for k in matches:counts['field:'+k]+=1
  if matches:by_year[y]['any_performance_fields']+=1
  if all(val(x.get(k)) for k in ('hc','ac')):by_year[y]['corner_fields_numeric']+=1
  if all(val(x.get(k)) for k in ('hc','ac')) and float(x['hc'])+float(x['ac'])>0:by_year[y]['corners_nonzero']+=1
  if all(val(x.get(k)) for k in ('hf_hg','hf_ag')):by_year[y]['HT_goal_fields_numeric']+=1
 except Exception as e:counts['error_'+type(e).__name__]+=1
out={'counts':dict(counts),'by_year':dict(by_year),'all_non_bookmaker_fields':dict(fields),'notes':'Numeric corner or halftime fields may be placeholders; nonzero corners is evidence of recorded activity, not proof of complete data. No API queried.'}
(R/'m8_independent_performance_data_audit_20261115.json').write_text(json.dumps(out,indent=2))
print('AUDIT',json.dumps(out),flush=True)
