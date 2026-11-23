#!/usr/bin/env python3
"""Independent read-only R11 snapshot and compressed archive on authorized Mac.
No new production workflows, model filters or public source line-level prices.
This may be run once only: never overwrite earlier frozen R5-R10 or R11.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r11_open_method_research_20261123'
S=ROOT/'frozen_research_snapshots'
NAME='R11_DC_MARKET_RESIDUAL_XG_OBSERVATION_SOURCE_20261123'
DEST=S/NAME;TMP=S/(NAME+'.building');TARGZ=S/(NAME+'.tar.gz')
if any(p.exists() for p in (DEST,TMP,TARGZ)):raise RuntimeError('Already frozen: cannot overwrite')
files=[
 'r11_Dixon_Coles_prior_seasons.py',
 'r11_market_xg_incremental_walkforward.py',
 'r11_xG_observation_CDF_calibration.py',
 'r11_totalcorner_default_source_inventory.py',
 'validate_r11_independent_method_source.py',
 'freeze_r11.py',
 'R11_OPEN_RESEARCH_DIXON_COLES_XG_MARKET_DATA_SOURCE_20261123.md',
 'r11_Dixon_Coles_rolling_prior_2seasons_CrownT12.jsonl',
 'r11_Dixon_Coles_rolling_prior_2seasons_summary.json',
 'r11_market_residual_walk_forward_2021_2025.jsonl',
 'r11_market_residual_walk_forward_summary.json',
 'r11_xG_observation_calibration_2019_2025.jsonl',
 'r11_xG_observation_calibration_summary.json',
 'r11_independent_totalcorner_default_snapshot_coverage.json',
 'r11_independent_full_validation.json']
prior={
 'R5':S/'R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json',
 'R6':S/'R6_BAYES_BIVAR_COMPLEMENT_20261123/R6_FREEZE_MANIFEST.json',
 'R7':S/'R7_CROWN_MARKET_PRICING_20261123/R7_FROZEN_SHA256_MANIFEST.json',
 'R8':S/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123/R8_FROZEN_SHA256_MANIFEST.json',
 'R9':S/'R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123/R9_FROZEN_SHA256_MANIFEST.json',
 'R10':S/'R10_XG_GAMMA_OBS_DYNAMIC_NB_20261123/R10_FROZEN_SHA256_MANIFEST.json'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for z in iter(lambda:f.read(1024*1024),b''):h.update(z)
 return h.hexdigest()
audit=json.loads((HERE/'r11_independent_full_validation.json').read_text())
if audit['status']!='PASS':raise RuntimeError('Audit failed')
TMP.mkdir(parents=True)
records=[]
for name in files:
 src=HERE/name
 if not src.is_file():raise FileNotFoundError(src)
 dst=TMP/name;shutil.copy2(src,dst)
 assert sha(src)==sha(dst)
 records.append({'relative_path':name,'sha256':sha(src),'bytes':dst.stat().st_size,
   'contains_private_fixture_level':src.suffix=='.jsonl'})
meta={'name':NAME,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Independent R11 domestic club research: DC, market logloss year-forward, xG distribution, separate historical Total default snapshot.',
 'no_national_teams':True,'no_production_or_TG_changes':True,
 'prior_R5_to_R10_manifests_SHA256':{k:sha(v) for k,v in prior.items()},
 'audit_status':audit['status'],'frozen_file_count':len(records),
 'source_bytes':sum(f['bytes'] for f in records),
 'original_football_quotes_only_local':True,
 'files':records}
(TMP/'R11_FROZEN_SHA256_MANIFEST.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
for x in records:
 if sha(TMP/x['relative_path'])!=x['sha256']:raise RuntimeError(('Data changed',x['relative_path']))
os.rename(TMP,DEST)
build=S/(NAME+'.tar.gz.building')
with tarfile.open(build,'w:gz',compresslevel=1) as tar:tar.add(DEST,arcname=NAME)
os.rename(build,TARGZ)
with tarfile.open(TARGZ,'r:gz') as tar:
 f=tar.extractfile(NAME+'/R11_FROZEN_SHA256_MANIFEST.json')
 assert f and json.loads(f.read())['frozen_file_count']==len(records)
for p in DEST.iterdir():
 if p.is_file():p.chmod(0o444)
DEST.chmod(0o555)
v={'status':'VERIFIED',
  'snapshot_dir':str(DEST),'archive_path':str(TARGZ),
  'R11_archive_size_bytes':TARGZ.stat().st_size,
  'R11_archive_sha256':sha(TARGZ),
  'R11_manifest_sha256':sha(DEST/'R11_FROZEN_SHA256_MANIFEST.json'),
  'frozen_file_count':len(records),'source_bytes':meta['source_bytes'],
  'prior_R5_to_R10_manifests_SHA256':meta['prior_R5_to_R10_manifests_SHA256'],
  'per_fixture_Crown_and_xG_private':True,
  'public_GitHub_only_aggregate_scripts_hashes':True}
vv=S/(NAME+'_FREEZE_VERIFICATION.json')
vv.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
vv.chmod(0o444)
print(json.dumps(v,ensure_ascii=False))