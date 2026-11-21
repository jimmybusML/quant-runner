#!/usr/bin/env python3
"""Hash the research code, source inputs and delivered evidence files."""
import hashlib,pathlib

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[2]
WORK=pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
DATA=pathlib.Path('/Users/mac/QuantAsiaDesk/data')
inputs={
 'frozen_membership':WORK/'m8_foundation_20261115/historical_membership.jsonl',
 'actual_Crown_receipt_archive':WORK/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',
 'formation_games_archive':WORK/'m8_pregame_info_source_20261117/games.csv.gz',
 'historical_T12_market_inventory':WORK/'m8_early_joint_market_inventory_20261115.jsonl',
 'historical_full_path_inventory':WORK/'m8_late_full_path_water_features_20261114.jsonl',
 'historical_M7_raw_response_inventory':WORK/'m7/m7_original49_historical_Crown_dual_market_close_expanded_inventory_20261113T0344Z.jsonl',
 'historical_extra_frozen_inventory':WORK/'m8_extra_inventory_frozen_eight_20261115.jsonl',
 'historical_unindexed_frozen_replay_inventory':WORK/'m8_raw_capture_unindexed_frozen_replay_20261115.jsonl',
 'M5_Crown_response_index':DATA/'m5-crown-authorized/crown-response-index.jsonl',
 'prior_manager_identity_bridge':WORK/'m8_prior_manager_turnover_20261117.py',
 'market_calibration_prefix':ROOT/'research/m8/m8_early_market_response_calibration_20261116.py',
 'market_latent_path_dependency':ROOT/'research/m8/m8_early_latent_path_20261116.py',
 'market_joint_path_dependency':ROOT/'research/m8/m8_early_joint_path_incremental_20261116.py',
 'market_line_water_dependency':ROOT/'research/m8/m8_early_line_water_interaction_20261116.py',
}
code={p.name:p for p in OUT.glob('*.py')}
outputs={p.name:p for p in OUT.iterdir() if p.is_file() and p.name not in ('SHA256SUMS_20261121.txt',)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
lines=['M8 prior formation mix × Crown AH study — SHA256 manifest','',
       'INPUTS (local research inputs and code; raw fixture SHA values are itemized in historical_crown_raw_fid_audit_20261121.jsonl.gz)']
for name,p in inputs.items():
 lines.append(f'INPUT {sha(p)}  {name}  {p}')
lines+=['','OUTPUTS / EXECUTED CODE']
for name,p in sorted({**code,**outputs}.items()):
 lines.append(f'OUTPUT {sha(p)}  {name}  {p.relative_to(ROOT)}')
(OUT/'SHA256SUMS_20261121.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'inputs={len(inputs)} outputs_and_code={len({**code,**outputs})}')
