import os,subprocess,sys
from pathlib import Path
b=Path.home()/'QuantAsiaDesk/repos/mr1'
p=subprocess.run(['/usr/bin/security','find-generic-password','-s','QuantAsiaDesk.TOTALCORNER_TOKEN','-a',os.environ.get('USER','mac'),'-w'],capture_output=True,text=True)
if p.returncode or not p.stdout.strip():raise SystemExit('CREDENTIAL_MISSING')
env={**os.environ,'TOTALCORNER_TOKEN':p.stdout.strip()}
raise SystemExit(subprocess.run(['/usr/local/bin/node','src/persist-github-state.js'],cwd=b,env=env,timeout=240).returncode)
