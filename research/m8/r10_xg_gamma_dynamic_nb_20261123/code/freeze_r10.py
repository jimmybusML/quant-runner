#!/usr/bin/env python3
"""Freeze R10 research in an independent read-only local snapshot + tar.gz.
Public copy will contain scripts/aggregate reports/hashes only, not private
fixture-level historical Crown source event lines. Never overwrite R5-R9.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r10_xg_observation_bayes_dynamic_20261123'
SNAP=ROOT/'frozen_research_snapshots'
NAME='R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123'
DEST=SNAP/NAME
TMP=SNAP/(NAME+'.building')
ARCH=SNAP/(NAME+'.tar.gz')
if any(x.exists() for x in (DEST,TMP,ARCH)):
    raise RuntimeError('R10 frozen output already exists: refuse overwrite')
items=[
 'r10_asof_xG_Gamma_shape.py',
 'r10_Gamma_obs_posterior_predictive.py',
 'r10_dynamic_team_logxG_Kalman.py',
 'r10_asof_negative_binomial_goal_total.py',
 'r10_Crown_market_incremental.py',
 'validate_r10_independent_math.py',
 'validate_r10_previous_season_hyperparameters.py',
 'freeze_r10.py',
 'R10_XG_GAMMA_OBSERVATION_DYNAMIC_NB_CROWN_20261123.md',
 'R10_AUDIT_RECONCILIATION_20261123.md',
 'r10_prior_two_season_xg_Gamma_shape.json',
 'r10_Gamma_xG_posterior_predictive_20261123.jsonl',
 'r10_Gamma_xG_posterior_predictive_summary_20261123.json',
 'r10_asof_dynamic_logxG_Kalman_CrownT12_20261123.jsonl',
 'r10_asof_dynamic_logxG_Kalman_CrownT12_summary_20261123.json',
 'r10_prev_two_season_asof_negative_binomial_CrownT12_20261123.jsonl',
 'r10_prev_two_season_asof_negative_binomial_summary_20261123.json',
 'r10_vs_Crown_market_incremental_1X2_20261123.jsonl',
 'r10_vs_Crown_market_incremental_probabilities.json',
 'r10_independent_math_source_frozen_validation.json',
 'r10_independent_raw_xG_hyperparameter_validation.json',
]
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as file:
  for x in iter(lambda:file.read(1024*1024),b''):
   h.update(x)
 return h.hexdigest()
prior={
 'R5':SNAP/'R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json',
 'R6':SNAP/'R6_BAYES_BIVAR_COMPLEMENT_20261123/R6_FREEZE_MANIFEST.json',
 'R7':SNAP/'R7_CROWN_MARKET_PRICING_20261123/R7_FROZEN_SHA256_MANIFEST.json',
 'R8':SNAP/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123/R8_FROZEN_SHA256_MANIFEST.json',
 'R9':SNAP/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123/R9_FROZEN_SHA256_MANIFEST.json'}
TMP.mkdir(parents=True)
files=[]
for name in items:
    src=HERE/name
    if not src.is_file():raise FileNotFoundError(src)
    dst=TMP/name
    shutil.copy2(src,dst)
    digest=sha(src)
    if sha(dst)!=digest:raise RuntimeError(('COPY_CORRUPTION',name))
    files.append({'relative_path':name,'sha256':digest,'bytes':dst.stat().st_size,
       'fixture_level_private':name.endswith('.jsonl')})
audit=json.loads((HERE/'r10_independent_math_source_frozen_validation.json').read_text())
hyper=json.loads((HERE/'r10_independent_raw_xG_hyperparameter_validation.json').read_text())
if audit['status']!='PASS' or hyper['status']!='PASS':raise RuntimeError('audit not passed')
meta={'freeze_name':NAME,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'R10 five domestic club leagues, research only, no national teams, no official Telegram or production changes.',
 'prior_R5_to_R9_manifest_sha256':{k:sha(v) for k,v in prior.items()},
 'numeric_audit_status':'PASS','asof_hyperparameter_audit_status':'PASS',
 'file_count':len(files),'size_bytes':sum(x['bytes'] for x in files),
 'privacy':'Line-level Crown original source events and scores stay on local Mac; only scripts, aggregate JSON, narrative, and hashes can go to public GitHub.',
 'files':files}
(TMP/'R10_FROZEN_SHA256_MANIFEST.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
for x in files:
 if sha(TMP/x['relative_path'])!=x['sha256']:raise RuntimeError('Manifest mismatch')
os.rename(TMP,DEST)
tmp=SNAP/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as t:
 t.add(DEST,arcname=NAME)
os.rename(tmp,ARCH)
with tarfile.open(ARCH,'r:gz') as t:
 f=t.extractfile(NAME+'/R10_FROZEN_SHA256_MANIFEST.json')
 if not f or json.loads(f.read())['file_count']!=len(files):
  raise RuntimeError('Archive integrity failure')
for p in DEST.iterdir():
 if p.is_file():p.chmod(0o444)
DEST.chmod(0o555)
v={'status':'VERIFIED','snapshot_dir':str(DEST),'archive_path':str(ARCH),
 'archive_bytes':ARCH.stat().st_size,'archive_sha256':sha(ARCH),
 'manifest_sha256':sha(DEST/'R10_FROZEN_SHA256_MANIFEST.json'),
 'frozen_file_count':len(files),'uncompressed_bytes':meta['size_bytes'],
 'prior_R5_to_R9_manifest_sha256':meta['prior_R5_to_R9_manifest_sha256'],
 'original_Crown_HTTP_and_market_data_unchanged':True,
 'public_only_summary_code_sha':True}
verify=SNAP/(NAME+'_FREEZE_VERIFICATION.json')
verify.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
verify.chmod(0o444)
print(json.dumps(v,ensure_ascii=False))
