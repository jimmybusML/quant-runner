"""Push M1 formal settlement changes without generating timestamp-only commits."""
import json,subprocess,sys
from pathlib import Path
p=Path.home()/'QuantAsiaDesk/repos/m1'
local=json.loads((p/'results/m1_formal_ledger.json').read_text())
r=subprocess.run(['git','show','origin/master:results/m1_formal_ledger.json'],cwd=p,capture_output=True,text=True)
if r.returncode:
 print('M1_REMOTE_LEDGER_UNAVAILABLE',file=sys.stderr);raise SystemExit(1)
remote=json.loads(r.stdout)
new=set(local['settlements'])-set(remote['settlements'])
if not new:
 print('M1_SETTLEMENT_PERSIST_NO_NEW',len(local['settlements']));raise SystemExit(0)
print('M1_SETTLEMENT_PERSIST_NEW',len(new),flush=True)
raise SystemExit(subprocess.run(['bash','m1_commit_state.sh','formal'],cwd=p,timeout=240).returncode)
