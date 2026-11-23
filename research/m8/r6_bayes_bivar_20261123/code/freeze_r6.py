#!/usr/bin/env python3
"""Snapshot ONLY independent R6 outputs, no mutation of R5 or M8.
Public GitHub gets aggregate JSON, source code and public SHA manifest only.
Sensitive line-level Crown pseudo-bets remain on research Mac.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r6_bayes_bivar_20261123'
SNAPROOT=ROOT/'frozen_research_snapshots'
NAME='R6_BAYES_BIVAR_COMPLEMENT_20261123'
DEST=SNAPROOT/NAME
BUILD=SNAPROOT/(NAME+'.building')
ARC=SNAPROOT/(NAME+'.tar.gz')
if any(p.exists() for p in (DEST,BUILD,ARC)):
    raise RuntimeError('R6 snapshot destination already exists: refusing overwrite')
names=[
 'r6_prior_bivar_complement.py',
 'r6_equal_blend_calibrate.py',
 'r6_equal_blend_actual_receipt.py',
 'validate_r6_frozen_and_contract.py',
 'freeze_r6.py',
 'EXTERNAL_XG_BAYES_BIVAR_R6_COMPLEMENT_CALIBRATION_20261123.md',
 'r6_prior_bivar_complement.json',
 'r6_equal_weight_blends_and_rolling_calibration.json',
 'r6_contract_calibration_ledger.jsonl',
 'r6_actual_receipt_equal_weight_blends.json',
 'r6_actual_receipt_equal_weight_blends.jsonl',
 'r6_independent_math_and_freeze_audit.json']
def sh(path):
    h=hashlib.sha256()
    with path.open('rb') as fd:
        for x in iter(lambda:fd.read(1024*1024),b''):h.update(x)
    return h.hexdigest()
BUILD.mkdir(parents=True)
manifest=[]
for n in names:
    p=HERE/n
    if not p.is_file():raise FileNotFoundError(p)
    dst=BUILD/n
    shutil.copy2(p,dst)
    before=sh(p);after=sh(dst)
    if before!=after:raise RuntimeError(('corrupt',n))
    manifest.append({'file':n,'sha256':after,'bytes':dst.stat().st_size})
info={'name':NAME,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':'Independent R6 research on readonly frozen R5 inputs',
 'source_R5_frozen':ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json',
 'source_R5_FROZEN_manifest_sha256':'6f465b284492eca97b311753e3850cd08e783a0fc93ba8c2af5e194f496996c2',
 'n_files':len(manifest),'files':manifest}
info['source_R5_frozen']=str(info['source_R5_frozen'])
(BUILD/'R6_FREEZE_MANIFEST.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
os.rename(BUILD,DEST)
tmp=SNAPROOT/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as f:
    f.add(DEST,arcname=NAME)
os.rename(tmp,ARC)
with tarfile.open(ARC,'r:gz') as f:
    doc=f.extractfile(NAME+'/R6_FREEZE_MANIFEST.json')
    assert doc and json.loads(doc.read())['n_files']==len(names)
for p in DEST.iterdir():
    if p.is_file():p.chmod(0o444)
DEST.chmod(0o555)
report={'status':'VERIFIED','source_R5_unmodified':True,
   'R6_archive_sha256':sh(ARC),'R6_manifest_sha256':sh(DEST/'R6_FREEZE_MANIFEST.json'),
   'files':len(manifest),'source_bytes':sum(x['bytes'] for x in manifest),
   'compressed_bytes':ARC.stat().st_size,'snapshot_dir':str(DEST),
   'archive_path':str(ARC)}
v=SNAPROOT/(NAME+'_FREEZE_VERIFICATION.json')
v.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
v.chmod(0o444)
print(json.dumps(report,ensure_ascii=False))