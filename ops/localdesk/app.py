#!/usr/bin/env python3
# coding: utf-8
"""Local-only QuantAsia control plane. Business models remain in their repos."""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import display_data
import research_notify
import job_explain

BASE = Path(__file__).resolve().parent
REPOS = {"m1": BASE / "repos/m1", "mr1": BASE / "repos/mr1", "m3": BASE / "repos/runner", "m4": BASE / "repos/runner"}
STATE = BASE / "state"
LOGS = BASE / "logs"
WEB = BASE / "web"
PORT = 8765
ACCOUNT = os.environ.get("USER", "mac")
CSRF = secrets.token_urlsafe(32)
CREDENTIAL_KEYS = ("TOTALCORNER_TOKEN", "M1_TELEGRAM_BOT_TOKEN", "M1_TELEGRAM_CHAT_ID", "MR1_TG_BOT_TOKEN", "MR1_TG_CHAT_ID", "RESEARCH_TG_BOT_TOKEN", "RESEARCH_TG_CHAT_ID")
DEFAULT = {"timezone": "Asia/Shanghai", "models": {
    "m1": {"schedule_enabled": False, "schedule_type": "times", "times": "00:05,06:05,12:05,18:05", "interval_minutes": 0, "tg_enabled": False},
    "mr1": {"schedule_enabled": False, "schedule_type": "interval", "times": "", "interval_minutes": 5, "tg_enabled": False},
    "m3": {"schedule_enabled": False, "schedule_type": "times", "times": "06:00,12:00", "interval_minutes": 0, "tg_enabled": False},
    "m4": {"schedule_enabled": False, "schedule_type": "manual", "times": "", "interval_minutes": 0, "tg_enabled": False},
}}
LOCK = threading.RLock()
ACTIVE = {}
JOBS = {}
SCHEDULED = {}
for directory in (BASE, STATE, LOGS, WEB):
    directory.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: Path, fallback=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def atomic_json(path: Path, data):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def settings():
    d = read_json(STATE / "settings.json")
    if not isinstance(d, dict):
        return json.loads(json.dumps(DEFAULT))
    result = json.loads(json.dumps(DEFAULT))
    result["timezone"] = d.get("timezone", DEFAULT["timezone"])
    for key in REPOS:
        if isinstance(d.get("models", {}).get(key), dict):
            result["models"][key].update(d["models"][key])
    return result


def save_settings(conf):
    atomic_json(STATE / "settings.json", conf)


def keychain_name(key):
    return "QuantAsiaDesk." + key


def credentials(key: str, get_value=False):
    if key not in CREDENTIAL_KEYS:
        raise ValueError("Unknown credential key")
    args = ["/usr/bin/security", "find-generic-password", "-a", ACCOUNT, "-s", keychain_name(key)]
    if get_value:
        args.append("-w")
    p = subprocess.run(args, capture_output=True, text=True, timeout=12)
    if not get_value:
        return p.returncode == 0
    return p.stdout.strip() if p.returncode == 0 else None


def put_credential(key, value):
    if key not in CREDENTIAL_KEYS or not isinstance(value, str) or not value.strip():
        raise ValueError("Missing credential")
    # Stored in the user's macOS login Keychain, never in app JSON or logs.
    # -w without a value accepts the password from stdin. Avoid secrets in ps argv.
    p = subprocess.run(["/usr/bin/security", "add-generic-password", "-U", "-a", ACCOUNT,
        "-s", keychain_name(key), "-w"], input=value.strip() + "\n",
        capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise RuntimeError("macOS Keychain could not store the credential")


def git_info(path):
    if not (path / ".git").exists():
        return {"installed": False, "commit": None}
    try:
        p = subprocess.run(["/usr/bin/git", "-C", str(path), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=3)
        return {"installed": True, "commit": p.stdout.strip() if p.returncode == 0 else "unknown"}
    except Exception:
        return {"installed": True, "commit": "unknown"}


def model_metrics():
    m1 = read_json(REPOS["m1"] / "results/m1_formal_report.json", {})
    r1 = read_json(REPOS["mr1"] / "data/mr1-v6-cross-market/formal/performance.json", {})
    m3 = read_json(STATE / "m3_latest.json") or read_json(REPOS["m3"] / "research/m3/results/totalcorner/shadow_performance_summary.json", {})
    m4 = read_json(STATE / "m4_latest.json", {})
    a = ((m1.get("markets") or {}).get("AH") or {})
    x = (r1.get("states") or {})
    lines = []
    for name, data in (m3.get("models") or {}).items():
        for market, metrics in data.items():
            lines.append({"model": name, "market": market, "settled": metrics.get("settled"), "pnl": metrics.get("net_units"), "roi": metrics.get("roi_percent")})
    return {
        "m1": {"source_time": m1.get("generated_at"), "sent": a.get("picks"), "settled": a.get("settled"), "pending": a.get("pending"), "pnl": a.get("pnl_u"), "roi": float(a["roi"])*100 if a.get("roi") is not None else None},
        "mr1": {"source_time": r1.get("generated_at"), "sent": (r1.get("n", 0) or 0) + (r1.get("pending", 0) or 0), "settled": r1.get("n"), "pending": r1.get("pending"), "pnl": r1.get("pnl_units"), "roi": float(r1["roi"])*100 if r1.get("roi") is not None else None},
        "m3": {"source_time": m3.get("generated_at_utc"), "sent": m3.get("unique_shadow_orders"), "settled": sum(int(x["settled"] or 0) for x in lines), "pending": sum(int(z.get("unsettled_or_invalid", 0)) for v in (m3.get("models") or {}).values() for z in v.values()), "pnl": sum(float(x["pnl"] or 0) for x in lines), "roi": None, "lines": lines, "shadow_only": True, "dedup_ready": m3.get("unique_shadow_orders") is not None},
        "m4": {"source_time": m4.get("ledger_generated_at"), "study": m4.get("all_history"), "research_only": True},
    }


def status():
    with LOCK:
        recent = [dict(j) for j in sorted(JOBS.values(), key=lambda j: j["started_at"], reverse=True)[:24]]
    for j in recent:
        if not j.get("message") and j.get("status") in ("succeeded", "failed"):
            logpath = LOGS / (j["id"] + ".log")
            if j["status"] == "succeeded" and logpath.exists():
                try:
                    j["message"] = job_explain.summarize(j["model"], j["action"], logpath.read_text(errors="replace")[-20000:])
                except Exception:
                    j["message"] = "这次任务已执行结束。"
            else:
                j["message"] = job_explain.friendly_error(j.get("error", "Unknown failure"))
    return {"server_time": now(), "csrf": CSRF, "timezone": settings()["timezone"],
        "settings": settings(), "credentials": {k: credentials(k) for k in CREDENTIAL_KEYS},
        "repos": {key: git_info(repo) for key, repo in REPOS.items()},
        "metrics": model_metrics(), "performance": display_data.readable_stats(), "jobs": recent, "origin": "127.0.0.1", "port": PORT}


def validate_settings(input_obj):
    old = settings()
    if not isinstance(input_obj, dict) or input_obj.get("timezone", old["timezone"]) not in ("Asia/Shanghai", "America/Los_Angeles"):
        raise ValueError("Unsupported display timezone")
    old["timezone"] = input_obj.get("timezone", old["timezone"])
    supplied = input_obj.get("models", {})
    if not isinstance(supplied, dict):
        raise ValueError("Invalid models")
    for model, patch in supplied.items():
        if model not in REPOS or not isinstance(patch, dict):
            raise ValueError("Unknown model")
        conf = old["models"][model]
        typ = patch.get("schedule_type", conf["schedule_type"])
        if typ not in ("times", "interval", "manual"):
            raise ValueError("Invalid schedule type")
        times = str(patch.get("times", conf["times"])).strip()
        for value in filter(None, (x.strip() for x in times.split(","))):
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
                raise ValueError("Time needs HH:MM in chosen timezone")
        interval = int(patch.get("interval_minutes", conf["interval_minutes"]))
        if typ == "interval" and interval <= 0:
            raise ValueError("Interval must be positive")
        for key in ("schedule_enabled", "tg_enabled"):
            if key in patch and not isinstance(patch[key], bool):
                raise ValueError("Invalid setting " + key)
        conf.update({"schedule_type": typ, "times": times, "interval_minutes": interval,
            "schedule_enabled": patch.get("schedule_enabled", conf["schedule_enabled"]),
            "tg_enabled": patch.get("tg_enabled", conf["tg_enabled"])})
    save_settings(old)
    return old


def job_steps(model: str, action: str):
    project = REPOS[model]
    runner = REPOS["m3"]
    py = str(BASE / "venv/bin/python") if (BASE / "venv/bin/python").exists() else "/opt/homebrew/bin/python3.12"
    env = dict(os.environ)
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["TOTALCORNER_TZ_OFFSET"] = "8"
    env["MR1_RUNTIME_EXECUTOR"] = "LOCAL_QUANT_ASIA_DESK"
    config = settings()["models"][model]
    api = credentials("TOTALCORNER_TOKEN", get_value=True)
    if api:
        env["TOTALCORNER_TOKEN"] = api
    if action == "sync":
        if model == "m4":
            project = REPOS["m3"]
        return [(["/usr/bin/git", "pull", "--ff-only"], project)], env
    if action == "report":
        if model == "m1":
            return [([py, "m1_formal_runtime.py", "report"], project)], env
        if model == "mr1":
            return [(["/usr/local/bin/node", "src/v6-ah-formal-settlement.js"], project)], env
        if model == "m3":
            out = str(STATE / "m3_latest.json")
            return [([py, "-m", "research.m3.segmented_ledger", "materialize"], runner),
                ([py, "-m", "research.m3.shadow_performance_report", "--ledger", "research/m3/results/totalcorner/forward_ev_ledger.jsonl", "--output", out], runner)], env
        if model == "m4":
            f = project / "research/m4/mr1_two_league_pass_study.py"
            source = REPOS["mr1"] / "data/mr1-v6-cross-market/formal/settled.json"
            return [([py, str(f), str(source), "--output", str(STATE / "m4_latest.json")], runner)], env
    if action == "settle":
        if model == "m1":
            return [([py, "m1_formal_runtime.py", "settle"], project), ([py, "m1_formal_runtime.py", "report"], project)], env
        if model == "mr1":
            return [(["/usr/local/bin/node", "src/v6-ah-formal-settlement.js"], project)], env
        if model == "m3":
            return [([py, "-m", "research.m3.segmented_ledger", "materialize"], runner),
                ([py, "-m", "research.m3.totalcorner_shadow_settle", "--ledger", "research/m3/results/totalcorner/forward_ev_ledger.jsonl"], runner),
                ([py, "-m", "research.m3.persist_append_ledger", "--candidate", "research/m3/results/totalcorner/forward_ev_ledger.jsonl"], runner)], env
    if action == "run":
        if model == "m1":
            approved_ev_patch = ([py, str(BASE / "scripts/ensure_m1_ev_policy.py"), str(project),
                                  str(runner / "ops/m1_ah_ev_cap.py")], project)
            if config["tg_enabled"]:
                bot = credentials("M1_TELEGRAM_BOT_TOKEN", True)
                chat = credentials("M1_TELEGRAM_CHAT_ID", True)
                if not bot or not chat:
                    raise ValueError("M1 TG enabled but its local Keychain credentials are missing")
                env.update({"M1_TELEGRAM_BOT_TOKEN": bot, "M1_TELEGRAM_CHAT_ID": chat})
                return [approved_ev_patch, ([py, "m1_immediate_delivery.py"], project)], env
            return [approved_ev_patch, ([py, str(BASE / "scripts/m1_preview.py")], project)], env
        if model == "mr1":
            steps = [(["/usr/local/bin/node", "src/github-shadow-runtime.js"], project),
                (["/usr/local/bin/node", "src/v6-cross-market-forward.js"], project),
                (["/usr/local/bin/node", "src/v6-ah-formal-settlement.js"], project)]
            if config["tg_enabled"]:
                bot = credentials("MR1_TG_BOT_TOKEN", True)
                chat = credentials("MR1_TG_CHAT_ID", True)
                if not bot or not chat:
                    raise ValueError("MR1 TG enabled but its local Keychain credentials are missing")
                env.update({"MR1_TG_BOT_TOKEN": bot, "MR1_TG_CHAT_ID": chat})
                steps.append((["/usr/local/bin/node", str(BASE / "scripts/mr1_notify.mjs")], project))
            steps.append((["/usr/local/bin/node", "src/persist-github-state.js"], project))
            return steps, env
        if model == "m3":
            ledger = "research/m3/results/totalcorner/forward_ev_ledger.jsonl"
            run = "local-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
            return [
                ([py, "-m", "research.m3.segmented_ledger", "materialize"], runner),
                ([py, "-m", "research.m3.future_fixture_audit", "--output", ledger, "--max-dates", "2", "--run-id", run], runner),
                ([py, "-m", "research.m3.persist_append_ledger", "--candidate", ledger], runner),
                ([py, "-m", "research.m3.m1_mr1_scope_audit", "--ledger", ledger, "--run-id", run], runner),
                ([py, "-m", "research.m3.m1_history_forward", "--cache-dir", str(REPOS["m1"] / "data/m1_history_cache"), "--ledger", ledger, "--max-dates", "2", "--run-id", run], runner),
                ([py, "-m", "research.m3.m3_shadow_orders", "--ledger", ledger, "--run-id", run], runner),
                ([py, "-m", "research.m3.future_fixture_model_status", "--ledger", ledger, "--run-id", run], runner),
                ([py, "-m", "research.m3.totalcorner_shadow_settle", "--ledger", ledger], runner),
                ([py, "-m", "research.m3.persist_append_ledger", "--candidate", ledger], runner),
                ([py, "-m", "research.m3.shadow_performance_report", "--ledger", ledger, "--output", str(STATE / "m3_latest.json")], runner)
            ], env
        if model == "m4":
            return job_steps("m4", "report")
    raise ValueError("Unsupported model action")


def needs_api(model, action):
    return (model == "m1" and action in ("run", "settle")) or (model == "mr1" and action == "run") or (model == "m3" and action in ("run", "settle"))


def worker(job_id, model, action):
    with LOCK:
        job = JOBS[job_id]
    logpath = LOGS / (job_id + ".log")
    returncode = None
    try:
        if needs_api(model, action) and not credentials("TOTALCORNER_TOKEN"):
            raise ValueError("TotalCorner credential not saved in local Keychain; add it from the dashboard")
        if action == "run" and model in ("m3", "m4") and settings()["models"][model]["tg_enabled"]:
            if not (credentials("RESEARCH_TG_BOT_TOKEN") and credentials("RESEARCH_TG_CHAT_ID")):
                raise ValueError("research TG credentials missing")
        steps, env = job_steps(model, action)
        run_identity = None
        for cmd, _ in steps:
            if "--run-id" in cmd:
                run_identity = cmd[cmd.index("--run-id") + 1]
        with logpath.open("a", encoding="utf-8") as log:
            for index, (cmd, cwd) in enumerate(steps, 1):
                if not cwd.is_dir():
                    raise FileNotFoundError("Local repo missing: " + str(cwd))
                label = f"[{now()}] Step {index}/{len(steps)}: " + " ".join(cmd[:4])
                log.write(label + "\n")
                log.flush()
                with subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=log, stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL, start_new_session=True) as proc:
                    with LOCK:
                        job["pid"] = proc.pid
                    returncode = proc.wait()
                if returncode:
                    raise RuntimeError(f"Step {index} exited with code {returncode}; see log")
        summary = job_explain.summarize(model, action, logpath.read_text(encoding="utf-8", errors="replace"))
        with LOCK:
            job["status"] = "succeeded"
            job["message"] = summary
        if action == "run" and model in ("m3", "m4") and settings()["models"][model]["tg_enabled"]:
            try:
                token = credentials("RESEARCH_TG_BOT_TOKEN", True)
                chat = credentials("RESEARCH_TG_CHAT_ID", True)
                if model == "m3":
                    outcome = research_notify.emit_m3(run_identity, token, chat)
                    note = "TG 已确认发送 " + str(outcome["sent"]) + " 条研究预测。"
                else:
                    outcome = research_notify.emit_m4(job_id, read_json(STATE / "m4_latest.json", {}), token, chat)
                    note = "TG 已确认发送 " + str(outcome["sent"]) + " 条 M4 研究报告（非正式派单）。"
                with LOCK:
                    job["tg_count"] = outcome["sent"]
                    job["message"] += " " + note
            except Exception as notify_error:
                with LOCK:
                    job["status"] = "partial"
                    job["message"] += " 研究执行成功，但 TG 未确认发送成功。"
                    job["error"] = job_explain.friendly_error(notify_error)
    except Exception as exc:
        with LOCK:
            job["status"] = "failed"
            job["message"] = job_explain.friendly_error(exc)
            job["error"] = job_explain.friendly_error(exc)
        with logpath.open("a", encoding="utf-8") as log:
            log.write("\n[ERROR] " + str(exc) + "\n")
    finally:
        with LOCK:
            job["finished_at"] = now()
            ACTIVE.pop(model, None)
            atomic_json(STATE / "last_jobs.json", list(JOBS.values())[-50:])


def launch(model, action, source="manual"):
    if model not in REPOS or action not in ("run", "report", "settle", "sync"):
        raise ValueError("Unknown action")
    if model == "m4" and action == "settle":
        raise ValueError("M4 has no formal order settlement: research only")
    with LOCK:
        current = ACTIVE.get(model)
        if current:
            raise ValueError("This model already has an active local job: " + current)
        job_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:7]
        job = {"id": job_id, "model": model, "action": action, "source": source, "status": "running", "started_at": now(), "finished_at": None}
        ACTIVE[model] = job_id
        JOBS[job_id] = job
    threading.Thread(target=worker, args=(job_id, model, action), daemon=True).start()
    return dict(job)


def scheduler():
    while True:
        try:
            s = settings()
            local = dt.datetime.now(ZoneInfo(s["timezone"]))
            for model, conf in s["models"].items():
                if not conf["schedule_enabled"] or conf["schedule_type"] == "manual":
                    continue
                slot = None
                if conf["schedule_type"] == "times":
                    if local.strftime("%H:%M") in [x.strip() for x in conf["times"].split(",")]:
                        slot = local.strftime("%Y-%m-%d %H:%M")
                elif conf["schedule_type"] == "interval":
                    interval = int(conf["interval_minutes"])
                    minute_index = int(local.timestamp() // 60)
                    if interval > 0 and minute_index % interval == 0:
                        slot = "interval:" + str(minute_index // interval)
                if slot:
                    key = model + ":" + slot
                    with LOCK:
                        if key not in SCHEDULED:
                            SCHEDULED[key] = now()
                            try:
                                launch(model, "run", "scheduled")
                            except ValueError:
                                pass
            if len(SCHEDULED) > 5000:
                SCHEDULED.clear()
        except Exception as exc:
            (LOGS / "scheduler.log").open("a").write(f"{now()} {type(exc).__name__}: {exc}\n")
        time.sleep(15)


class Handler(BaseHTTPRequestHandler):
    server_version = "QuantAsiaDesk/0.1"

    def _same_host(self):
        host = self.headers.get("Host", "")
        return host in ("127.0.0.1:8765", "localhost:8765")

    def _json(self, code, value):
        buf = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(buf)))
        self.end_headers()
        self.wfile.write(buf)

    def _body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size > 32768:
            raise ValueError("Request too large")
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        if not self._same_host():
            return self._json(403, {"error": "Local host only"})
        path = urlparse(self.path)
        if path.path in ("/", "/index.html"):
            data = (WEB / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if path.path == "/api/status":
            return self._json(200, status())
        if path.path == "/api/logs":
            jid = parse_qs(path.query).get("id", [""])[0]
            if jid not in JOBS:
                return self._json(404, {"error": "Unknown job"})
            log = LOGS / (jid + ".log")
            if not log.exists():
                return self._json(200, {"log": "Job queued"})
            return self._json(200, {"log": log.read_text(errors="replace")[-24000:]})
        self._json(404, {"error": "Not found"})

    def do_POST(self):
        if not self._same_host():
            return self._json(403, {"error": "Local host only"})
        origin = self.headers.get("Origin")
        if origin and origin not in ("http://localhost:8765", "http://127.0.0.1:8765"):
            return self._json(403, {"error": "Different origin"})
        if self.headers.get("X-CSRF-Token", "") != CSRF:
            return self._json(403, {"error": "Invalid local request token"})
        try:
            data = self._body()
            route = urlparse(self.path).path
            if route == "/api/settings":
                return self._json(200, {"settings": validate_settings(data)})
            if route == "/api/run":
                return self._json(202, {"job": launch(str(data.get("model", "")), str(data.get("action", "")))})
            if route == "/api/credentials":
                put_credential(data.get("key"), data.get("value"))
                return self._json(200, {"stored": True, "key": data.get("key")})
            return self._json(404, {"error": "Not found"})
        except (ValueError, KeyError, FileNotFoundError) as exc:
            return self._json(400, {"error": str(exc)})
        except Exception as exc:
            return self._json(500, {"error": type(exc).__name__ + ": " + str(exc)})

    def log_message(self, fmt, *args):
        with (LOGS / "web.log").open("a", encoding="utf-8") as out:
            out.write("[%s] %s\n" % (now(), fmt % args))


if __name__ == "__main__":
    old = read_json(STATE / "last_jobs.json", [])
    if isinstance(old, list):
        for item in old:
            if item.get("id"):
                item.pop("pid", None)
                if item.get("status") == "running":
                    item["status"] = "interrupted_by_service_restart"
                JOBS[item["id"]] = item
    if not (STATE / "settings.json").exists():
        save_settings(settings())
    threading.Thread(target=scheduler, daemon=True).start()
    print("QuantAsiaDesk http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
