#!/usr/bin/env python3
"""Hash and execution manifest for the M8 transfer inference audit."""
import hashlib,json,pathlib,datetime
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FILES=[
 "exact_rule_cross_league_all_complete_paths.jsonl.gz",
 "exact_rule_cross_league_orders.jsonl.gz",
 "m8_cross_league_transfer_inference_20261120.py",
 "verify_cross_league_transfer_inference_20261120.py",
 "build_transfer_inference_manifest_20261120.py",
 "cross_league_transfer_inference_20261120.json",
 "cross_league_transfer_inference_orders_20261120.jsonl.gz",
 "prior_year_group_selector_orders_20261120.jsonl.gz",
 "cross_league_transfer_inference_verification_20261120.json",
 "EXACT_RULE_TRANSFER_INFERENCE_20261120.md",
 "TRANSFER_INFERENCE_EXECUTION_20261120.md",
]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
manifest={"created_local":datetime.datetime.now().astimezone().isoformat(),"study":"M8 frozen exact-rule cross-league portability and uncertainty audit","files":{x:{"sha256":sha(HERE/x),"bytes":(HERE/x).stat().st_size} for x in FILES},"files_from_repo_root":{"PROJECT_HANDOFF.md":{"sha256":sha(ROOT/"PROJECT_HANDOFF.md"),"bytes":(ROOT/"PROJECT_HANDOFF.md").stat().st_size}},"execution":{"main":"python3 m8_cross_league_transfer_inference_20261120.py","independent_verifier":"python3 verify_cross_league_transfer_inference_20261120.py","main_exit":0,"independent_verifier_pass":json.loads((HERE/"cross_league_transfer_inference_verification_20261120.json").read_text())["pass"],"bootstrap_replicates":20000},"production_changes":False,"actual_telegram_orders":0,"formal_ledger_writes":0}
(HERE/"TRANSFER_INFERENCE_SHA256_MANIFEST_20261120.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
