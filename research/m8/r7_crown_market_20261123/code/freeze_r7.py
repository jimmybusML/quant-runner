#!/usr/bin/env python3
"""One-shot non-overwriting local R7 research archive. Public copy is separate.
Sensitive per-game Crown price research stays on Mac.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r7_market_pricing_20261123'
FOLDER=ROOT/'frozen_research_snapshots'
NAME='R7_CROWN_MARKET_PRICING_20261123'
DEST=FOLDER/NAME
BUILD=FOLDER/(NAME+'.building')
ARC=FOLDER/(NAME+'.tar.gz')
if any(p.exists() for p in (DEST,BUILD,ARC)):
    raise RuntimeError('R7 already frozen; will not overwrite')
files=[
 'r7_market_implied_poisson.py',
 'r7_HW_style_pivot.py',
 'r7_market_bayes_incremental.py',
 'validate_r7_market_and_R5.py',
 'freeze_r7.py',
 'EXTERNAL_MARKET_CROWN_R7_PRICING_BENCHMARK_20261123.md',
 'r7_market_implied_2market_20261123.jsonl',
 'r7_market_implied_2market_summary_20261123.json',
 'r7_empirical_refund_AH_ledger.jsonl',
 'r7_empirical_refund_AH_summary.json',
 'r7_market_vs_Bayes_fixed_blend_score.jsonl',
 'r7_market_vs_Bayes_fixed_blend_score.json',
 'r7_independent_market_audit.json',
]
def sha(fp):
    h=hashlib.sha256()
    with fp.open('rb') as fd:
        for z in iter(lambda:fd.read(1024*1024),b''):h.update(z)
    return h.hexdigest()
BUILD.mkdir(parents=True)
meta=[]
for name in files:
    f=HERE/name
    if not f.exists():raise FileNotFoundError(f)
    copy=BUILD/name
    shutil.copy2(f,copy)
    b=sha(f);a=sha(copy)
    if a!=b:raise RuntimeError('copy corruption: '+name)
    meta.append({'relative_path':name,'sha256':b,'bytes':f.stat().st_size})
FROZEN_R5=ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json'
m={'snapshot_name':NAME,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Domestic club leagues, AH/OU market pricing research only, never formal TG orders',
 'source_R5_218_sha_manifest_sha256':sha(FROZEN_R5),
 'file_count':len(meta),'total_source_bytes':sum(r['bytes'] for r in meta),
 'files':meta}
manifest=BUILD/'R7_FROZEN_SHA256_MANIFEST.json'
manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
for item in meta:
    if sha(BUILD/item['relative_path'])!=item['sha256']:raise RuntimeError('bad written file')
os.rename(BUILD,DEST)
tmp=FOLDER/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as tar:
    tar.add(DEST,arcname=NAME)
os.rename(tmp,ARC)
with tarfile.open(ARC,'r:gz') as tar:
    fd=tar.extractfile(NAME+'/R7_FROZEN_SHA256_MANIFEST.json')
    assert fd and json.loads(fd.read())['file_count']==len(files)
for f in DEST.iterdir():
    if f.is_file():f.chmod(0o444)
DEST.chmod(0o555)
v={'status':'VERIFIED','snapshot_dir':str(DEST),'archive_path':str(ARC),
   'source_file_count':len(files),'source_bytes':m['total_source_bytes'],
   'archive_bytes':ARC.stat().st_size,
   'R7_archive_sha256':sha(ARC),
   'R7_snapshot_manifest_sha256':sha(DEST/'R7_FROZEN_SHA256_MANIFEST.json'),
   'R5_snapshot_manifest_sha256':sha(FROZEN_R5),
   'historical_Crown_data_in_public_GitHub':False}
verify=FOLDER/(NAME+'_FREEZE_VERIFICATION.json')
verify.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
verify.chmod(0o444)
print(json.dumps(v,ensure_ascii=False))