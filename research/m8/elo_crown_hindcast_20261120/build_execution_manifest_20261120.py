#!/usr/bin/env python3
"""Write SHA256 and execution metadata for the M8 Elo research package."""
import hashlib, json, datetime, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
inputs={
 'scores':'/Users/mac/QuantAsiaDesk/research-work/m8_independent_score_strength_20261114.jsonl',
 'crown_features':'/Users/mac/QuantAsiaDesk/research-work/m8_late_full_path_water_features_20261114.jsonl',
 'frozen_membership':'/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl',
 'actual_crown_receipts':'/Users/mac/QuantAsiaDesk/research-work/m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',
 'verified_ft_index':'/Users/mac/QuantAsiaDesk/research-work/m7/m7_actual_received_Crown_verified_FT_index_20261110_v3.jsonl'}
outputs=[
 'm8_dynamic_elo_crown_ah_20261120.py',
 'independent_verify_m8_dynamic_elo_crown_ah_20261120.py',
 'build_execution_manifest_20261120.py',
 'm8_dynamic_elo_crown_ah_predictions_20261120.jsonl.gz',
 'm8_dynamic_elo_crown_ah_true_receipt_replay_20261120.jsonl.gz',
 'm8_dynamic_elo_crown_ah_summary_20261120.json',
 'independent_verification_20261120.json',
 'M8_DYNAMIC_ELO_CROWN_AH_REPORT_20261120.md']
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 data={k:{'path':p,'sha256':sha(p)} for k,p in inputs.items()}
 result={
  'study':'M8 dynamic Elo versus Crown AH price; research-only time-forward hindcast',
  'generated_at_local':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
  'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'execution_commands':['python3 m8_dynamic_elo_crown_ah_20261120.py','python3 independent_verify_m8_dynamic_elo_crown_ah_20261120.py'],
  'inputs':data,
  'outputs':{p:{'sha256':sha(HERE/p),'bytes':(HERE/p).stat().st_size} for p in outputs},
  'verification':json.load(open(HERE/'independent_verification_20261120.json')),
  'production_changes':False,
  'formal_telegram_orders':0,
  'formal_ledger_writes':0,
  'note':'This manifest intentionally does not hash itself. Source data and Crown raw HTTP bodies remain local; the published receipt ledger contains quote identities and hashes, not raw response bodies.'}
 out=HERE/'execution_manifest_20261120.json'
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
