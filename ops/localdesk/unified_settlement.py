#!/usr/bin/env python3
"""One autonomous reconciliation coordinator; no Telegram and no model prediction.

Settlement formulas and immutable model-specific ledgers remain model-owned.
All execution attempts are journaled; model failures cannot hide other models.
"""
from __future__ import annotations
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path.home()/'QuantAsiaDesk'
STATE=BASE/'state'
REPOS=BASE/'repos'
JOURNAL=STATE/'unified_settlement_events.jsonl'
LOCK=STATE/'unified_settlement.lock'
PY=str(BASE/'venv/bin/python')
NODE='/usr/local/bin/node'


def emit(model,status,**details):
    event={'at':dt.datetime.now(dt.timezone.utc).isoformat(),'model':model,'status':status,**details}
    with JOURNAL.open('a',encoding='utf-8') as f:
        f.write(json.dumps(event,ensure_ascii=False,default=str)+'\n')
        f.flush();os.fsync(f.fileno())
    print(json.dumps(event,ensure_ascii=False),flush=True)


def execute(model,commands,env):
    emit(model,'START')
    for i,(cmd,cwd) in enumerate(commands,1):
        try:
            p=subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=3600)
        except Exception as exc:
            emit(model,'FAILED',step=i,error=type(exc).__name__,message=str(exc)[:400]);return False
        output=(p.stdout or '').strip()
        if output:
            for line in output.splitlines()[-4:]:print(model,line[:1500],flush=True)
        if p.returncode:
            emit(model,'FAILED',step=i,returncode=p.returncode,stderr=(p.stderr or '')[-1200:],stdout=output[-1200:]);return False
        emit(model,'STEP_SUCCEEDED',step=i)
    emit(model,'SUCCEEDED');return True


def main():
    STATE.mkdir(parents=True,exist_ok=True)
    with LOCK.open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            emit('all','ALREADY_RUNNING');return 0
        token=subprocess.run(['/usr/bin/security','find-generic-password','-s','QuantAsiaDesk.TOTALCORNER_TOKEN','-a',os.environ.get('USER','mac'),'-w'],capture_output=True,text=True)
        if token.returncode or not token.stdout.strip():
            emit('all','FAILED',error='TOTALCORNER_CREDENTIAL_MISSING');return 1
        env={**os.environ,'TOTALCORNER_TOKEN':token.stdout.strip()}
        runner=REPOS/'runner';m1=REPOS/'m1';mr1=REPOS/'mr1'
        commands={
          'm1':[([PY,'m1_formal_runtime.py','settle'],m1),([PY,'m1_formal_runtime.py','report'],m1),
                (['/usr/bin/python3',str(BASE/'scripts/m1_persist_settlements.py')],BASE)],
          'mr1':[([NODE,str(BASE/'scripts/mr1_formal_result_reconcile.mjs')],mr1),
                 (['/usr/bin/python3',str(BASE/'scripts/mr1_persist_local.py')],BASE)],
          'm3':[([PY,'-m','research.m3.segmented_ledger','materialize'],runner),
                ([PY,'-m','research.m3.totalcorner_shadow_settle','--ledger','research/m3/results/totalcorner/forward_ev_ledger.jsonl'],runner),
                ([PY,'-m','research.m3.persist_append_ledger','--candidate','research/m3/results/totalcorner/forward_ev_ledger.jsonl'],runner),
                ([PY,'-m','research.m3.shadow_performance_report','--ledger','research/m3/results/totalcorner/forward_ev_ledger.jsonl','--output',str(STATE/'m3_latest.json')],runner)]}
        selected=sys.argv[1:] or list(commands)
        if any(x not in commands for x in selected):raise SystemExit('usage: unified_settlement.py [m1] [mr1] [m3]')
        failed=[]
        for model in selected:
            if not execute(model,commands[model],env):failed.append(model)
        audit=subprocess.run(['/usr/bin/python3',str(BASE/'scripts/settlement_pending_audit.py')],capture_output=True,text=True,timeout=30)
        if audit.returncode:
            emit('all','AUDIT_FAILED',stderr=audit.stderr[-800:]);failed.append('pending_audit')
        else:
            emit('all','PENDING_AUDITED',summary=audit.stdout.strip()[:1500])
        emit('all','COMPLETED' if not failed else 'PARTIAL_FAILURE',failed=failed)
        return bool(failed)

if __name__=='__main__':sys.exit(main())
