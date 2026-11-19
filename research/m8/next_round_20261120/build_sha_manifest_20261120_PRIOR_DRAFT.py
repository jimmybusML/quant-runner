#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
FILES=['build_sha_manifest_20261120.py','m8_strength_distribution_20261120.py','verify_m8_strength_distribution_settlement_20261120.py','verify_m8_strength_distribution_crown_ft_20261120.py','M8_NEXT_ROUND_CONTINUOUS_AH_STRENGTH_DISTRIBUTION_20261120.md','M8_NEXT_ROUND_RESULTS_20261120.json','calibration_metrics_20261120.json','per_fixture_walkforward_20261120.jsonl.gz','independent_settlement_audit_20261120.json','crown_ft_independent_audit_summary_20261120.json','crown_ft_independent_audit_20261120.jsonl.gz','RUN_RECORD_20261120.md']
INPUTS={'crown_ah_path':'/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl','ft_score_rows':'/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl','frozen_eight':'/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl'}
def h(p):
 z=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):z.update(b)
 return z.hexdigest()
out={'manifest':'M8 next-round continuous AH strength distribution','date':'2026-11-20','inputs':{k:{'path':v,'sha256':h(v)} for k,v in INPUTS.items()},'outputs':{p:{'sha256':h(D/p),'bytes':(D/p).stat().st_size} for p in FILES}}
(D/'SHA256SUMS_20261120.txt').write_text(''.join(f"{v['sha256']}  {k}\n" for k,v in out['outputs'].items()))
out['manifest_file_sha256_excluded_self']=h(D/'SHA256SUMS_20261120.txt')
(D/'EXECUTION_MANIFEST_20261120.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
