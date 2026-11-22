#!/usr/bin/env python3
"""Rebuild output SHA256 manifests after study/report regeneration."""
import datetime,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
FILES=('m8_low_score_dependence_20261120.py','verify_m8_low_score_dependence_20261120.py','build_low_score_report_20261120.py','build_manifest_20261120.py','m8_low_score_dependence_orders_20261120.jsonl.gz','m8_low_score_dependence_summary_20261120.json','independent_verification_20261120.json','M8_LOW_SCORE_DEPENDENCE_RESEARCH_20261120.md')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 s=json.loads((HERE/'m8_low_score_dependence_summary_20261120.json').read_text());v=json.loads((HERE/'independent_verification_20261120.json').read_text())
 m={'generated_at_local':datetime.datetime.now().astimezone().isoformat(),'study':'Time-forward Crown AH settlement-state probability and low-score dependence; research only','inputs_sha256':s['inputs_sha256'],'outputs_sha256':{n:{'sha256':sha(HERE/n),'bytes':(HERE/n).stat().st_size} for n in FILES},'execution':{'main':'python3 research/m8/low_score_dependence_20261120/m8_low_score_dependence_20261120.py','verify':'python3 research/m8/low_score_dependence_20261120/verify_m8_low_score_dependence_20261120.py','build_report':'python3 research/m8/low_score_dependence_20261120/build_low_score_report_20261120.py','verify_pass':v['pass'],'verified_rows':v['independent_ledger_rows_checked']},'production_changes':False,'formal_telegram_orders':0,'formal_ledger_writes':0}
 (HERE/'EXECUTION_MANIFEST_20261120.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 (HERE/'SHA256SUMS_20261120.txt').write_text(''.join(f"{v['sha256']}  {k}\n" for k,v in m['outputs_sha256'].items()))
 print(json.dumps({'manifest':str(HERE/'EXECUTION_MANIFEST_20261120.json'),'files':len(FILES),'verified_rows':v['independent_ledger_rows_checked'],'pass':v['pass']}))
if __name__=='__main__':main()
