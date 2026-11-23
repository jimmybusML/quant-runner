#!/usr/bin/env python3
"""Freeze independent R8, retaining private original actual Crown HTTP archive
and verified FT data locally. GitHub will receive only public code, summaries
and SHA256 hashes. Never overwrite an earlier frozen R5/R6/R7 or R8 artifact.
"""
from pathlib import Path
import hashlib,json,shutil,tarfile,os,datetime
ROOT=Path('/Users/mac/QuantAsiaDesk/research-work')
HERE=ROOT/'r8_market_timing_bayes_20261123'
DIR=ROOT/'frozen_research_snapshots'
NAME='R8_CROWN_HTTP_TIMING_BAYES_POSTERIOR_20261123'
FINAL=DIR/NAME
TEMP=DIR/(NAME+'.building')
ARC=DIR/(NAME+'.tar.gz')
if any(x.exists() for x in (FINAL,TEMP,ARC)):
    raise RuntimeError('R8 output already frozen, will not overwrite')
files=[
 'r8_actual_HTTP_market_timing.py','r8_full_posterior_predictive.py',
 'r8_paired_timing_uncertainty.py','r8_posterior_direction_attribution.py',
 'validate_r8_independent_math.py','freeze_r8.py',
 'R8_CROWN_REAL_HTTP_TIME_AND_BAYES_POSTERIOR_20261123.md',
 'r8_11club_Crown_actual_receipt_market_timing.jsonl',
 'r8_11club_Crown_actual_receipt_market_timing_summary.json',
 'r8_11club_market_timing_paired_bootstrap_20261123.json',
 'r8_full_posterior_predictive_club_20261123.jsonl',
 'r8_full_posterior_predictive_club_summary_20261123.json',
 'r8_posterior_vs_point_mean_attribution_20261123.json',
 'r8_independent_source_and_cash_validation.json']
inputs={
 'm8_MR1_actual_HTTP_archive.jsonl':ROOT/'m8_MR1_full_actual_Crown_receipt_archive_20261113.jsonl',
 'm7_verified_actual_FT.jsonl':ROOT/'m7/m7_full_scope_8_axis_combo_pending_FT_recovered_20261110.jsonl'}
previous={
 'R5':ROOT/'frozen_research_snapshots/R5_BAYES_BIVAR_FROZEN_20261123/FROZEN_SHA256_MANIFEST.json',
 'R6':ROOT/'frozen_research_snapshots/R6_BAYES_BIVAR_COMPLEMENT_20261123/R6_FREEZE_MANIFEST.json',
 'R7':ROOT/'frozen_research_snapshots/R7_CROWN_MARKET_PRICING_20261123/R7_FROZEN_SHA256_MANIFEST.json'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for ch in iter(lambda:f.read(1024*1024),b''):h.update(ch)
 return h.hexdigest()
TEMP.mkdir()
out=[]
for n,source in ([(n,HERE/n) for n in files]+[('private_inputs/'+n,v) for n,v in inputs.items()]):
 if not source.is_file():raise FileNotFoundError(source)
 dst=TEMP/n
 dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(source,dst)
 digest=sha(source)
 if sha(dst)!=digest:raise RuntimeError('Copy checksum mismatch '+n)
 out.append({'relative_path':n,'sha256':digest,'size_bytes':dst.stat().st_size,
             'public_safe':not n.startswith('private_inputs/') and not n.endswith('.jsonl')})
meta={'freeze_name':NAME,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'frozen_count':len(out),'frozen_total_bytes':sum(x['size_bytes'] for x in out),
      'prior_frozen_manifest_sha256':{key:sha(value) for key,value in previous.items()},
      'privacy':'Actual Crown quote time snapshots and full line-by-line research ledgers never published to public GitHub.',
      'files':out}
(TEMP/'R8_FROZEN_SHA256_MANIFEST.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
for item in out:
 if sha(TEMP/item['relative_path'])!=item['sha256']:raise RuntimeError('Tampered build')
os.rename(TEMP,FINAL)
tmp=DIR/(NAME+'.tar.gz.building')
with tarfile.open(tmp,'w:gz',compresslevel=1) as tar:tar.add(FINAL,arcname=NAME)
os.rename(tmp,ARC)
with tarfile.open(ARC,'r:gz') as tar:
 f=tar.extractfile(NAME+'/R8_FROZEN_SHA256_MANIFEST.json')
 assert f and json.loads(f.read())['frozen_count']==len(out)
for v in FINAL.rglob('*'):
 if v.is_file():v.chmod(0o444)
for v in sorted([v for v in FINAL.rglob('*') if v.is_dir()],reverse=True):v.chmod(0o555)
FINAL.chmod(0o555)
summary={'status':'VERIFIED','snapshot_dir':str(FINAL),'archive_path':str(ARC),
 'archived_file_count':len(out),'source_total_bytes':meta['frozen_total_bytes'],
 'archive_bytes':ARC.stat().st_size,'R8_archive_sha256':sha(ARC),
 'R8_frozen_manifest_sha256':sha(FINAL/'R8_FROZEN_SHA256_MANIFEST.json'),
 'prior_frozen_manifest_sha256':meta['prior_frozen_manifest_sha256'],
 'private_Crown_linelevel_kept_local':True}
verify=DIR/(NAME+'_FREEZE_VERIFICATION.json')
verify.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
verify.chmod(0o444)
print(json.dumps(summary,ensure_ascii=False))