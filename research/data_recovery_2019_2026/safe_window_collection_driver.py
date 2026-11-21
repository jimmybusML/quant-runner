#!/usr/bin/env python3
"""Run the unchanged Crown collector only outside known scheduled TotalCorner jobs."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path

UNSAFE_COMMAND_PARTS=(
    '/Users/mac/QuantAsiaDesk/scripts/unified_settlement.py',
    '/Users/mac/QuantAsiaDesk/scripts/local_rescheduled_results.py',
    '/Users/mac/QuantAsiaDesk/scripts/local_result_fallback.py',
    '/Users/mac/QuantAsiaDesk/repos/mr1/src/shadow-v23.js',
)

def utc():return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')

def active_unsafe(self_pid:int,child_pid:int|None):
    p=subprocess.run(['/bin/ps','-Ao','pid=,command='],capture_output=True,text=True,check=True)
    active=[]
    for line in p.stdout.splitlines():
        try:pid=int(line.strip().split(None,1)[0]);command=line.strip().split(None,1)[1]
        except (ValueError,IndexError):continue
        if pid in {self_pid,child_pid}:continue
        if any(marker in command for marker in UNSAFE_COMMAND_PARTS):active.append({'pid':pid,'command':command})
    return active

def record(path:Path,event:dict):
    event={'at_utc':utc(),**event}
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(event,ensure_ascii=False),flush=True)

def resume_fixture_file(source:Path,output_log:Path,event_log:Path)->Path|None:
    """Build the next pass from FIDs not yet attempted in this batch.

    The underlying collector can be interrupted by scheduled production jobs.
    Restarting it against the original manifest would replay every earlier FID;
    notably, empty Crown responses have no reusable movement rows and can be
    requested again. Keep the source manifest immutable and checkpoint progress
    from the append-only collector log instead.
    """
    if source.suffix.lower()!='.jsonl':
        raise ValueError('resumable collection currently requires a JSONL fixture file')
    candidates=[];seen=set()
    with source.open(encoding='utf-8') as f:
        for line in f:
            if not line.strip():continue
            row=json.loads(line)
            if isinstance(row,(str,int)):row={'match_id':str(row)}
            fid=str(row.get('match_id') or row.get('id') or '')
            if not fid.isdigit() or fid in seen:continue
            seen.add(fid);candidates.append((fid,row))
    attempted=set()
    if output_log.exists():
        with output_log.open(encoding='utf-8') as f:
            for line in f:
                try:row=json.loads(line)
                except json.JSONDecodeError:continue
                if not isinstance(row,dict) or row.get('fixture_id') is None or not row.get('status'):
                    continue
                attempted.add(str(row['fixture_id']))
    remaining=[row for fid,row in candidates if fid not in attempted]
    resume=source.with_name(source.stem+'.resume.jsonl')
    if not remaining:
        record(event_log,{'event':'collector_input_exhausted','candidate_fids':len(candidates),
          'attempted_fids':len(attempted),'remaining_fids':0,
          'retryable_failures_still_pending':0})
        return None
    with resume.open('w',encoding='utf-8') as f:
        for row in remaining:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        f.flush();os.fsync(f.fileno())
    record(event_log,{'event':'resume_manifest_written','source_manifest':str(source),
      'source_manifest_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'resume_manifest':str(resume),'resume_manifest_sha256':hashlib.sha256(resume.read_bytes()).hexdigest(),
      'candidate_fids':len(candidates),'attempted_fids':len(attempted),
      'remaining_fids':len(remaining),'retryable_failures_seen':0})
    return resume

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--fixture-file',type=Path,required=True)
    p.add_argument('--output-log',type=Path,required=True)
    p.add_argument('--event-log',type=Path,required=True)
    p.add_argument('--layer',choices=['summary','movement'],default='movement')
    p.add_argument('--quiet-seconds',type=float,default=12)
    p.add_argument('--poll-seconds',type=float,default=2)
    a=p.parse_args();a.output_log.parent.mkdir(parents=True,exist_ok=True);a.event_log.parent.mkdir(parents=True,exist_ok=True)
    cmd=['/Users/mac/QuantAsiaDesk/venv/bin/python','/Users/mac/QuantAsiaDesk/scripts/crown_capture_store.py','collect',
      '--fixture-file',str(a.fixture_file),'--layer',a.layer,'--capture-mode','historical']
    child=None;interrupted=False;quiet_since=None
    record(a.event_log,{'event':'driver_started','collector_command':cmd,'fixture_file':str(a.fixture_file),
      'fixture_file_sha256':__import__('hashlib').sha256(a.fixture_file.read_bytes()).hexdigest(),
      'output_log':str(a.output_log),'layer':a.layer,'capture_mode':'historical',
      'interval_seconds':'collector default (5.2)'})
    try:
        while True:
            unsafe=active_unsafe(os.getpid(),child.pid if child else None)
            if unsafe:
                quiet_since=None
                if child and child.poll() is None:
                    record(a.event_log,{'event':'collector_paused_for_scheduled_job','collector_pid':child.pid,'scheduled_jobs':unsafe})
                    child.send_signal(signal.SIGTERM)
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    child=None;interrupted=True
                time.sleep(a.poll_seconds)
                continue
            if child and child.poll() is not None:
                code=child.returncode
                record(a.event_log,{'event':'collector_process_exited','return_code':code,'completed_normally':not interrupted and code==0})
                if code==0 and not interrupted:
                    record(a.event_log,{'event':'driver_completed_after_collector_completion'})
                    return 0
                if not interrupted and code!=0:
                    record(a.event_log,{'event':'driver_stopped_on_collector_error','return_code':code})
                    return code
                child=None;quiet_since=None
                time.sleep(a.poll_seconds)
                continue
            if child is None:
                if quiet_since is None:quiet_since=time.monotonic()
                if time.monotonic()-quiet_since>=a.quiet_seconds:
                    resume=resume_fixture_file(a.fixture_file,a.output_log,a.event_log)
                    if resume is None:
                        record(a.event_log,{'event':'driver_completed_all_fixture_ids'})
                        return 0
                    cmd[cmd.index('--fixture-file')+1]=str(resume)
                    with a.output_log.open('ab') as log:
                        child=subprocess.Popen(cmd,cwd='/Users/mac/QuantAsiaDesk',stdout=log,stderr=subprocess.STDOUT)
                    interrupted=False;quiet_since=None
                    record(a.event_log,{'event':'collector_started','collector_pid':child.pid})
            time.sleep(a.poll_seconds)
    except KeyboardInterrupt:
        if child and child.poll() is None:
            record(a.event_log,{'event':'driver_interrupted','collector_pid':child.pid})
            child.send_signal(signal.SIGTERM)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        return 130

if __name__=='__main__':sys.exit(main())
