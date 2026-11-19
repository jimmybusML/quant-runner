#!/usr/bin/env python3
"""Generate a compact A-D result index and a SHA256 manifest."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'research/m8/next_round_20261120'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
a=json.load(open(D/'strength_shock_results_20261120.json'));b=json.load(open(D/'M8_NEXT_ROUND_RESULTS_20261120.json'));c=json.load(open(D/'A_D_C_OVERLAP_AUDIT_20261120.json'));q=json.load(open(D/'raw_quote_bridge_audit_20261120.json'))
summary={'study':'M8 bold breakthrough A-D','as_of':'2026-11-20 Asia/Shanghai','conclusion':'No validated independent profitable AH source beyond frozen eight.','frozen_membership_sha256':a['data']['frozen_sha256'],'historical_candidates':{'A_and_D':{k:{'all':v['forced_one_side_all_matches'],'ev_positive_only':v['predeclared_positive_model_EV_only']} for k,v in a['summaries'].items()},'B':b['aggregate_2024_2026']},'frozen_eight_union_A_D':a['frozen_eight_and_unfiltered_union_by_year'],'frozen_eight_union_B':b['merged_2024_2026'],'actual_receipts':{'snapshot_rows':a['data']['receipt_snapshot_rows'],'unique_fids':a['data']['receipt_unique_fids'],'joined_model_fids':a['data']['receipt_fids_added'],'exclusion_reasons':a['data']['receipt_exclusion_reasons']},'fid_overlap':c,'raw_quote_ft_settlement_bridge':q,'B_independent_settlement_audit':json.load(open(D/'independent_settlement_audit_20261120.json')),'limitations':a['limitations']}
(D/'M8_BOLD_BREAKTHROUGH_RESULTS_20261120.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
# Include all deliverable files and explicit local inputs; exclude caches and
# the manifest itself so every listed digest is stable and independently checkable.
files=[]
for p in sorted(D.rglob('*')):
 if not p.is_file() or '__pycache__' in p.parts or p.name=='SHA256SUMS_20261120.txt':continue
 files.append((str(p.relative_to(ROOT)),sha(p)))
files.append(('PROJECT_HANDOFF.md',sha(ROOT/'PROJECT_HANDOFF.md')))
receipt_path=ROOT/'research/m8/mr1_m8_receipt_coverage_20261119/verified_receipts.jsonl'
external=[('/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl',a['data']['path_sha256']),('/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl',a['data']['score_sha256']),('/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl',a['data']['frozen_sha256']),(str(receipt_path.relative_to(ROOT)),sha(receipt_path)),('research/m8/frozen_eight_boundary_expansion_20261119/M8_FROZEN_EIGHT_BOUNDARY_EXPANSION_RESULTS_20261119.json',c['C_prior_boundary_expansion']['source_results_sha256']),('research/m8/cross_competition_team_pricing_20261119/independent_raw_crown_audit_20261119.jsonl.gz',q['raw_audit_sha256'])]
lines=[f'{digest}  {path}' for path,digest in external]
lines += [f'{digest}  {path}' for path,digest in files]
(D/'SHA256SUMS_20261120.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps({'output_summary':str((D/'M8_BOLD_BREAKTHROUGH_RESULTS_20261120.json').relative_to(ROOT)),'sha_entries':len(files)+len(external),'manifest_sha256':sha(D/'SHA256SUMS_20261120.txt')},indent=2))
