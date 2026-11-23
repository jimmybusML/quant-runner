#!/usr/bin/env python3
"""Non-overwriting R9 snapshot + SHA manifest + read-only tar.gz.
Full private fixture-level Crown research retained on authorized Mac.
Public GitHub publishes code and aggregate evidence only.
"""
from pathlib import Path
import json,hashlib,shutil,os,tarfile,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r9_crown_event_update_bayes_20261123'
ROOTSNAP=ROOT/'frozen_research_snapshots'
NAME='R9_CROWN_TRUE_UPDATE_BAYES_OU_20261123'
FINAL=ROOTSNAP/NAME
BUILD=ROOTSNAP/(NAME+'.building')
ARCHIVE=ROOTSNAP/(NAME+'.tar.gz')
if any(p.exists() for p in (FINAL,BUILD,ARCHIVE)):
    raise RuntimeError('Frozen R9 already exists: refuse overwrite')
filenames=[
 'r9_market_source_event_attribution.py',
 'r9_Bayes_OU_why_Under.py',
 'r9_Bayes_OU_distribution_shape_sensitivity.py',
 'r9_Bayes_OU_variance_calibration.py',
 'validate_r9_sources_OU_math.py',
 'freeze_r9.py',
 'R9_CROWN_TRUE_EVENT_UPDATE_AND_BAYES_OU_VARIANCE_20261123.md',
 'r9_crown_true_source_event_transition_ledger.jsonl',
 'r9_crown_true_source_event_transition_summary.json',
 'r9_Bayes_OU_Over_to_Under_mechanism.jsonl',
 'r9_Bayes_OU_Over_to_Under_summary.json',
 'r9_Bayes_OU_distribution_shape_sensitivity.json',
 'r9_Bayes_OU_variance_calibration_by_year.json',
 'r9_independent_validation.json']
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
prevs={
'R5':ROOTSNAP/'R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json',
'R6':ROOTSNAP/'R6_BAYES_BIVAR_COMPLEMENT_20261123/R6_FREEZE_MANIFEST.json',
'R7':ROOTSNAP/'R7_CROWN_MARKET_PRICING_20261123/R7_FROZEN_SHA256_MANIFEST.json',
'R8':ROOTSNAP/'R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123/R8_FROZEN_SHA256_MANIFEST.json'}
BUILD.mkdir(parents=True)
files=[]
for name in filenames:
    src=HERE/name
    if not src.is_file():raise FileNotFoundError(src)
    dst=BUILD/name
    shutil.copy2(src,dst)
    dh=sha(src)
    if sha(dst)!=dh:raise RuntimeError('Copy sha corruption '+name)
    files.append({'relative_path':name,'sha256':dh,'bytes':dst.stat().st_size,
      'contains_private_fixture_data':name.endswith('.jsonl')})
manifest={'research_id':NAME,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'R9 independent domestic club data research, no national teams, no official telegram or production change',
 'source_frozen_R5_to_R8_SHA256':{k:sha(p) for k,p in prevs.items()},
 'source_research_paths_referenced':'R5 historical xG/Crown and R8 true HTTP+FT already frozen separately. No original source modified.',
 'file_count':len(files),'source_total_bytes':sum(x['bytes'] for x in files),
 'files':files}
(BUILD/'R9_FROZEN_SHA256_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for x in files:
    if sha(BUILD/x['relative_path'])!=x['sha256']:raise RuntimeError('Checksum mismatch')
os.rename(BUILD,FINAL)
tmp=ROOTSNAP/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as tar:
    tar.add(FINAL,arcname=NAME)
os.rename(tmp,ARCHIVE)
with tarfile.open(ARCHIVE,'r:gz') as tar:
    f=tar.extractfile(NAME+'/R9_FROZEN_SHA256_MANIFEST.json')
    assert f and json.loads(f.read())['file_count']==len(files)
for p in FINAL.iterdir():
    if p.is_file():p.chmod(0o444)
FINAL.chmod(0o555)
v={'status':'VERIFIED','R9_folder':str(FINAL),'archive_path':str(ARCHIVE),
 'archive_bytes':ARCHIVE.stat().st_size,'archive_sha256':sha(ARCHIVE),
 'manifest_sha256':sha(FINAL/'R9_FROZEN_SHA256_MANIFEST.json'),
 'frozen_file_count':len(files),'source_total_bytes':manifest['source_total_bytes'],
 'source_R5_to_R8_manifest_sha256':manifest['source_frozen_R5_to_R8_SHA256'],
 'public_safe':'Only source scripts, report and aggregate JSON uploaded publicly, per-fixture Crown lines remain local'}
verification=ROOTSNAP/(NAME+'_FREEZE_VERIFICATION.json')
verification.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
verification.chmod(0o444)
print(json.dumps(v,ensure_ascii=False))