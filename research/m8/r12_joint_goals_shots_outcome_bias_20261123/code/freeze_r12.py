#!/usr/bin/env python3
"""R12 independent non-overwriting read-only freeze.
Preserve complete 45-season original Understat shot/fixture archive LOCALLY
as well as full fixture-level R12 ledgers, to avoid raw-source drift later.
Only code, report, aggregate, redacted SHA fingerprints go to public GitHub.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r12_joint_goals_outcome_bias_20261123'
DATA=ROOT/'external_xg_independent_20261123/xgtables_understat_2017_2025'
S=ROOT/'frozen_research_snapshots'
NAME='R12_BIVARIATE_OUTCOME_BIAS_SHOT_DATA_20261123'
DEST=S/NAME;TEMP=S/(NAME+'.building');ARCH=S/(NAME+'.tar.gz')
if any(p.exists() for p in (DEST,TEMP,ARCH)):
 raise RuntimeError('R12 archive already exists; never overwrite frozen research')
scripts=['r12_bivariate_Poisson_asof_covariance.py',
 'r12_outcome_bias_market_walkforward.py','r12_shot_profile_incremental.py',
 'r12_shot_uncertainty.py','r12_shot_data_reconcile.py',
 'validate_r12_independent_full.py','freeze_r12.py']
reports=['R12_BIVARIATE_POISSON_OUTCOME_BIAS_SHOT_VOLUME_20261123.md']
aggregates=['r12_bivariate_shared_count_summary_20261123.json',
 'r12_outcome_bias_market_increment_crossyear_summary.json',
 'r12_understat_shot_profile_Crown_increment_summary.json',
 'r12_shot_profile_uncertainty_and_multiple_tests.json',
 'r12_shot_source_reconciliation_2017_2025.json',
 'r12_independent_sources_math_and_prior_freeze_validation.json']
private_ledgers=['r12_bivariate_shared_count_CrownT12_20261123.jsonl',
 'r12_outcome_bias_strict_past_xG_features_2019_2025.jsonl',
 'r12_outcome_bias_market_increment_crossyear_2021_2025.jsonl',
 'r12_understat_shot_profile_prior_features_2019_2025.jsonl',
 'r12_understat_shot_profile_Crown_increment_2021_2025.jsonl']
prior=[
 ('R5',S/'R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json'),
 ('R6',S/'R6_BAYES_BIVAR_COMPLEMENT_20261123/R6_FREEZE_MANIFEST.json'),
 ('R7',S/'R7_CROWN_MARKET_PRICING_20261123/R7_FROZEN_SHA256_MANIFEST.json'),
 ('R8',S/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123/R8_FROZEN_SHA256_MANIFEST.json'),
 ('R9',S/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123/R9_FROZEN_SHA256_MANIFEST.json'),
 ('R10',S/'R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123/R10_FROZEN_SHA256_MANIFEST.json'),
 ('R11',S/'R11_DC_MARKET_RESIDUAL_XG_OBSERVATION_SOURCE_20261123/R11_FROZEN_SHA256_MANIFEST.json')]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
 return h.hexdigest()
audit=json.loads((HERE/'r12_independent_sources_math_and_prior_freeze_validation.json').read_text())
if audit['status']!='PASS':raise RuntimeError('R12 math audit failed')
TEMP.mkdir(parents=True)
files=[]
for name in scripts+reports+aggregates+private_ledgers:
 src=HERE/name
 if not src.is_file():raise FileNotFoundError(src)
 dst=TEMP/name
 shutil.copy2(src,dst)
 if sha(src)!=sha(dst):raise RuntimeError(('copy sha mismatch',name))
 files.append({'path':name,'sha256':sha(src),'bytes':dst.stat().st_size,
   'private_fixture_level':src.suffix=='.jsonl'})
# Preserve original historical source fixture and raw shots, with full SHA.
rawfiles=sorted(p for p in DATA.rglob('*') if p.is_file())
for src in rawfiles:
 sub=src.relative_to(DATA)
 target=TEMP/'private_source_understat_2017_2025'/sub
 target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src,target)
 if sha(src)!=sha(target):raise RuntimeError(('raw source changed',sub))
 files.append({'path':str(target.relative_to(TEMP)),
   'sha256':sha(src),'bytes':target.stat().st_size,'private_fixture_level':True})
meta={'name':NAME,'utc_frozen':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'R12 9,908 historic Crown paired club match source-event research, 7,073 cross-year tests, raw 2017-2025 Understat archived locally only.',
 'R5_to_R11_frozen_manifest_sha256':{key:sha(p) for key,p in prior},
 'R12_independent_audit':'PASS',
 'script_count':len(scripts),'report_count':len(reports),
 'aggregate_count':len(aggregates),'fixture_research_ledger_count':len(private_ledgers),
 'original_understat_file_count':len(rawfiles),
 'file_count':len(files),'uncompressed_bytes':sum(x['bytes'] for x in files),
 'privacy':'Public repo publishes only source code, narrative, aggregated JSON, and SHA hashes. All line-level Crown and original Understat data private on Mac.',
 'files':files}
(TEMP/'R12_FROZEN_SHA256_MANIFEST.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
for z in files:
 if sha(TEMP/z['path'])!=z['sha256']:raise RuntimeError('Manifest digest mismatch')
os.rename(TEMP,DEST)
tmp=S/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as tar:tar.add(DEST,arcname=NAME)
os.rename(tmp,ARCH)
with tarfile.open(ARCH,'r:gz') as tar:
 t=tar.extractfile(NAME+'/R12_FROZEN_SHA256_MANIFEST.json')
 if not t or json.loads(t.read())['file_count']!=len(files):
  raise RuntimeError('archive verification failed')
for folder in sorted((p for p in DEST.rglob('*') if p.is_dir()),reverse=True):
 folder.chmod(0o555)
for p in DEST.rglob('*'):
 if p.is_file():p.chmod(0o444)
DEST.chmod(0o555)
ver={'status':'VERIFIED','path':str(DEST),'archive_path':str(ARCH),
 'archive_bytes':ARCH.stat().st_size,'archive_SHA256':sha(ARCH),
 'frozen_manifest_SHA256':sha(DEST/'R12_FROZEN_SHA256_MANIFEST.json'),
 'frozen_file_count':len(files),
 'original_Understat_raw_files':len(rawfiles),'uncompressed_bytes':meta['uncompressed_bytes'],
 'prior_R5_to_R11_frozen_manifest_SHA256':meta['R5_to_R11_frozen_manifest_sha256'],
 'R12_per_fixture_prices_private':True,
 'raw_Understat_source_preserved_locally':True,
 'no_production_or_TG_changes':True}
vf=S/(NAME+'_FREEZE_VERIFICATION.json')
vf.write_text(json.dumps(ver,ensure_ascii=False,indent=2)+'\n')
vf.chmod(0o444)
print(json.dumps(ver,ensure_ascii=False))
