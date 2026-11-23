#!/usr/bin/env python3
"""Freeze R5 complete research into independent directory + tar archive.
Only local sensitive line-level Crown data. Public repository receives only
small aggregate report, scripts and hashes -- never full research ledgers.
This archive is NOT a deployment or a new testing Gate.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,tarfile,os,stat
R=Path('/Users/mac/QuantAsiaDesk/research-work/external_xg_independent_20261123')
BASE=R.parent
SNAPROOT=BASE/'frozen_research_snapshots'
SNAPROOT.mkdir(parents=True,exist_ok=True)
NAME='R5_BAYES_BIVAR_FROZEN_20261123'
SNAP=SNAPROOT/NAME
TMP=SNAPROOT/(NAME+'.building')
ARC=SNAPROOT/(NAME+'.tar.gz')
if SNAP.exists() or TMP.exists() or ARC.exists():
    raise SystemExit('STOP: frozen destination already exists, will not overwrite')
TMP.mkdir()
listed=[
    'EXTERNAL_XG_BAYES_BIVAR_R5_FROZEN_20261123.md',
    'r5_bayes_bivar_asof_features.py',
    'r5_bayes_bivar_same_Crown.py',
    'r5_bayes_bivar_2026_actual_receipt.py',
    'validate_r5_bayes_bivar.py',
    'r5_paired_season_diagnostics.py',
    'r5_bayes_bivar_asof_features_20261123.jsonl',
    'r5_bayes_bivar_feature_summary_20261123.json',
    'r5_bayes_bivar_prediction_scores_20261123.jsonl',
    'r5_bayes_bivar_CrownT12_20261123.jsonl',
    'r5_bayes_bivar_comparison_20261123.json',
    'r5_bayes_bivar_actual_receipt_20261123.jsonl',
    'r5_bayes_bivar_actual_receipt_20261123.json',
    'r5_bayes_bivar_season_block_diagnostics_20261123.json',
    'r5_independent_cash_cross_source_validation_20261123.json',
    'r4_season_scope_xg_predictions_20261123.jsonl',
    'r4_season_scope_CrownT12_20261123.jsonl',
    'r4_season_scope_xg_predictions_20261123.json',
    'r4_season_scope_CrownT12_20261123.json',
    'attack_defense_2026_actual_receipt_20261123.jsonl',
    'attack_defense_2026_actual_receipt_20261123.json',
    'r4_season_scope_xg_20261123.py',
    'r4_season_scope_Crown_20261123.py',
    'xg_attack_defense_2026_actual_receipt_20261123.py',
]
additional={
    'historical_xg_source':R/'xgtables_understat_2017_2025',
    'historical_Crown_T12_inventory.jsonl':BASE/'m8_early_joint_market_inventory_20261115.jsonl',
    '2026_actual_Crown_receipt_source.jsonl':BASE/'m7/m7_actual_receipt_1596_xg_profit_replay_20261116.jsonl',
    '2026_football_data_raw':BASE/'m7/football_data_shots_20261116/raw',
    'm7_actual_receipt_processing.py':BASE/'m7/m7_actual_receipt_1596_xg_profit_replay_20261116.py',
    'm7_Asian_settlement_helpers.py':BASE/'m7/m7_shot_residual_profit_replay_11league_20261116.py',
}
def filehash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
results=[]
def freeze_file(src,dst):
    if not src.is_file():raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    before=filehash(src);after=filehash(dst)
    if before!=after:raise RuntimeError(('COPY CORRUPTION',src))
    results.append({'file':str(dst.relative_to(TMP)),'sha256':after,'bytes':dst.stat().st_size,'original':str(src)})
for name in listed:
    freeze_file(R/name,TMP/'research'/name)
for name,src in additional.items():
    if src.is_dir():
        for f in sorted(src.rglob('*')):
            if f.is_file():
                freeze_file(f,TMP/'inputs'/name/f.relative_to(src))
    else:
        freeze_file(src,TMP/'inputs'/name)
manifest={'freeze_id':NAME,'created_utc':datetime.now(timezone.utc).isoformat(),
          'research_not_production':True,
          'source_git_main_at_start':'39471b61ae6978f4706ca07cd1c570c6fa35791a',
          'human_confirmed_scope':'Save all R5 methods/results; no national teams; no original M8 rule change',
          'file_count':len(results),'total_bytes':sum(x['bytes'] for x in results),
          'files':results}
manifest_path=TMP/'FROZEN_SHA256_MANIFEST.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
n=0
for entry in results:
    actual=filehash(TMP/entry['file'])
    if actual!=entry['sha256']:raise RuntimeError(('CHECKSUM FAIL',entry['file']))
    n+=1
assert n==len(results)
# Snapshot directory is independent, not hardlinks. Do not later overwrite.
os.rename(TMP,SNAP)
archive_tmp=SNAPROOT/(NAME+'.tar.gz.building')
with tarfile.open(archive_tmp,'w:gz',compresslevel=1) as tar:
    tar.add(SNAP,arcname=NAME)
os.rename(archive_tmp,ARC)
# Verify content readability in tar and the manifest there, then make read-only.
with tarfile.open(ARC,'r:gz') as tar:
    item=tar.extractfile(NAME+'/FROZEN_SHA256_MANIFEST.json')
    if item is None:raise RuntimeError('manifest missing in archive')
    other=json.loads(item.read().decode())
    assert other['file_count']==manifest['file_count']
for p in sorted(SNAP.rglob('*'),reverse=True):
    if p.is_file():p.chmod(0o444)
    elif p.is_dir():p.chmod(0o555)
SNAP.chmod(0o555)
summary={'status':'VERIFIED','snapshot_dir':str(SNAP),
         'archive_tar_gz':str(ARC),'archive_sha256':filehash(ARC),
         'manifest_sha256':filehash(SNAP/'FROZEN_SHA256_MANIFEST.json'),
         'snapshot_file_count':n,'snapshot_bytes':manifest['total_bytes'],
         'archive_bytes':ARC.stat().st_size}
sidecar=SNAPROOT/(NAME+'_FREEZE_VERIFICATION.json')
sidecar.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
sidecar.chmod(0o444)
print(json.dumps(summary,ensure_ascii=False))
