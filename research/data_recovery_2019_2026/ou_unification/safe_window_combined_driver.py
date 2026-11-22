#!/usr/bin/env python3
"""Run combined AH+OU collection only outside known scheduled production jobs."""
import argparse,datetime as dt,json,os,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
COLLECTOR=HERE/'collect_crown_ah_ou_64.py'
UNSAFE=(
 '/Users/mac/QuantAsiaDesk/scripts/unified_settlement.py',
 '/Users/mac/QuantAsiaDesk/scripts/local_rescheduled_results.py',
 '/Users/mac/QuantAsiaDesk/scripts/local_result_fallback.py',
 '/Users/mac/QuantAsiaDesk/repos/mr1/src/shadow-v23.js',
 'research.m3.totalcorner_shadow_settle',
)
STOP=False
def sig(_s,_f):
 global STOP;STOP=True
signal.signal(signal.SIGINT,sig);signal.signal(signal.SIGTERM,sig)
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def active(exclude=None):
 p=subprocess.run(['/bin/ps','-Ao','pid=,command='],capture_output=True,text=True,check=True);out=[]
 for line in p.stdout.splitlines():
  try:pid=int(line.strip().split(None,1)[0]);cmd=line.strip().split(None,1)[1]
  except (ValueError,IndexError):continue
  if pid in (exclude,os.getpid()):continue
  if any(x in cmd for x in UNSAFE):out.append({'pid':pid,'command':cmd})
 return out
def log(path,event):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a') as f:f.write(json.dumps({'at_utc':utc(),**event},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
 print(json.dumps(event,ensure_ascii=False),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--schedule',required=True);p.add_argument('--queue',required=True);p.add_argument('--collection-log',required=True);p.add_argument('--event-log',required=True);p.add_argument('--interval-seconds',type=float,default=5.2);p.add_argument('--quiet-seconds',type=float,default=12);p.add_argument('--poll-seconds',type=float,default=2)
 a=p.parse_args();events=Path(a.event_log);outlog=Path(a.collection_log);quiet=None;child=None;was_stopped=False
 while not STOP:
  jobs=active(child.pid if child else None)
  if jobs:
   quiet=None
   if child and child.poll() is None:
    log(events,{'event':'collection_paused_for_scheduled_job','collector_pid':child.pid,'scheduled_jobs':jobs})
    child.send_signal(signal.SIGTERM)
    try:child.wait(timeout=50)
    except subprocess.TimeoutExpired:child.kill();child.wait()
    child=None;was_stopped=True
   time.sleep(a.poll_seconds);continue
  if child and child.poll() is not None:
   code=child.returncode;log(events,{'event':'collection_batch_exited','return_code':code})
   if code!=0:log(events,{'event':'collection_driver_stopped_on_error','return_code':code});return code
   child=None;quiet=None;time.sleep(a.poll_seconds);continue
  if child is None:
   if quiet is None:quiet=time.monotonic()
   if time.monotonic()-quiet>=a.quiet_seconds:
    build=[sys.executable,str(COLLECTOR),'--mode','build-queue','--database',a.database,'--schedule',a.schedule,'--queue',a.queue,'--log',a.collection_log]
    r=subprocess.run(build,capture_output=True,text=True)
    if r.returncode:
     log(events,{'event':'queue_build_failed','return_code':r.returncode,'stderr':r.stderr[-1000:]});return r.returncode
    try:summary=json.loads(r.stdout)
    except Exception:summary={'stdout_tail':r.stdout[-1000:]}
    count=sum(1 for _ in Path(a.queue).open()) if Path(a.queue).exists() else 0
    log(events,{'event':'queue_checkpoint','queue_count':count,'missing_requests':summary.get('missing_requests'),'covered':summary.get('covered'),'attempted_nonretryable_fids':summary.get('attempted_nonretryable_fids')})
    if count==0:
     log(events,{'event':'collection_scope_complete'});return 0
    cmd=[sys.executable,str(COLLECTOR),'--mode','collect','--database',a.database,'--schedule',a.schedule,'--queue',a.queue,'--log',a.collection_log,'--interval-seconds',str(a.interval_seconds)]
    outlog.parent.mkdir(parents=True,exist_ok=True)
    with outlog.open('ab') as f:child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=str(HERE.parent.parent.parent))
    log(events,{'event':'combined_collector_started','collector_pid':child.pid,'queue_count':count,'interval_seconds':a.interval_seconds});quiet=None;was_stopped=False
  time.sleep(a.poll_seconds)
 if child and child.poll() is None:
  log(events,{'event':'driver_interrupted','collector_pid':child.pid});child.send_signal(signal.SIGTERM)
  try:child.wait(timeout=50)
  except subprocess.TimeoutExpired:child.kill();child.wait()
 log(events,{'event':'driver_stopped_by_signal'});return 130
if __name__=='__main__':raise SystemExit(main())
