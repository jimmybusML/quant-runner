"""Human-readable accounting views. Never mutate formal or research ledgers."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
BJ = timezone(timedelta(hours=8))
M1 = BASE / "repos/m1/results/m1_formal_ledger.json"
MR_SENT = BASE / "repos/mr1/data/mr1-v6-cross-market/formal/sent.jsonl"
MR_SETTLED = BASE / "repos/mr1/data/mr1-v6-cross-market/formal/settled.json"
M3_REPORT = BASE / "state/m3_latest.json"
M4_REPORT = BASE / "state/m4_latest.json"
STATES = ("FULL_WIN", "HALF_WIN", "PUSH", "HALF_LOSS", "FULL_LOSS")
STATE_NAMES = ("全赢", "半赢", "走水", "半输", "全输")


def parse(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(BJ)


def summary(rows):
    out = {"sent": len(rows), "settled": 0, "pending": 0, "pnl": 0.0, "roi": None, "states": dict(zip(STATE_NAMES, (0,)*5))}
    for item in rows:
        result = item.get("result")
        if result is not None:
            out["settled"] += 1
            out["pnl"] += float(result.get("pnl", 0))
            state = result.get("state")
            if state in STATES:
                out["states"][STATE_NAMES[STATES.index(state)]] += 1
    out["pending"] = out["sent"] - out["settled"]
    out["pnl"] = round(out["pnl"], 4)
    if out["settled"]:
        out["roi"] = round(out["pnl"] / out["settled"] * 100, 3)
    return out


@lru_cache(maxsize=3)
def formal_rows(m1_sig, sent_sig, settled_sig):
    m = json.loads(M1.read_text(encoding="utf-8"))
    m1 = []
    for ident, pick in m["picks"].items():
        if pick.get("market") != "AH":
            continue
        tg = m["notifications"].get(ident, {}).get("telegram", {})
        if tg.get("status") != "SENT" or not tg.get("provider_message_id") or not tg.get("sent_at"):
            continue
        settle = m["settlements"].get(ident) or []
        m1.append({
            "sent": parse(tg["sent_at"]),
            "result": {"state": settle[-1]["state"], "pnl": settle[-1]["pnl_u"]} if settle else None,
        })
    settled = json.loads(MR_SETTLED.read_text(encoding="utf-8"))["entries"]
    mr = []
    with MR_SENT.open(encoding="utf-8") as reader:
        for text in reader:
            if not text.strip():
                continue
            pick = json.loads(text)
            data = settled.get(pick["signal_id"])
            if not pick.get("telegram_message_id") or not pick.get("sent_at"):
                continue
            mr.append({
                "sent": parse(pick["sent_at"]),
                "result": {"state": data["settlement"], "pnl": data["realized_pnl"]} if data else None,
            })
    return {"m1": m1, "mr1": mr}


def identity(path):
    if not path.exists():
        return None
    s = path.stat()
    return (s.st_mtime_ns, s.st_size)


def weeks():
    nowbj = datetime.now(BJ).date()
    current = nowbj - timedelta(days=nowbj.weekday())
    prev = current - timedelta(days=7)
    formal = formal_rows(identity(M1), identity(MR_SENT), identity(MR_SETTLED))
    out = {}
    for model, rows in formal.items():
        out[model] = {
            "all": summary(rows),
            "this": summary([x for x in rows if x["sent"].date() >= current and x["sent"].date() < current + timedelta(days=7)]),
            "last": summary([x for x in rows if x["sent"].date() >= prev and x["sent"].date() < current]),
        }
    return {
        "label": {
            "this": f"{current.month}月{current.day}日—{(current+timedelta(days=6)).month}月{(current+timedelta(days=6)).day}日",
            "last": f"{prev.month}月{prev.day}日—{(current-timedelta(days=1)).month}月{(current-timedelta(days=1)).day}日",
        },
        "m1": out["m1"],
        "mr1": out["mr1"],
    }


def readable_stats():
    result = weeks()
    m3 = json.loads(M3_REPORT.read_text(encoding="utf-8")) if M3_REPORT.exists() else {}
    models = []
    names = {"poisson": "泊松", "dixon_coles": "迪克森-科尔斯", "bivariate_poisson": "双变量泊松"}
    for name, line in m3.get("models", {}).items():
        for side in ("AH", "OU"):
            item = line.get(side)
            if not item:
                continue
            models.append({
                "name": names.get(name, name),
                "market": "让球" if side == "AH" else "大小球",
                "sent": item.get("orders", 0),
                "settled": item.get("settled", 0),
                "pending": item.get("unsettled_or_invalid", 0),
                "pnl": item.get("net_units", 0.0),
                "roi": item.get("roi_percent"),
                "states": dict(zip(STATE_NAMES, [item.get(k.lower(), 0) for k in STATES])),
            })
    result["m3"] = {"lines": models, "source": m3.get("generated_at_utc"), "shadow": True}
    m4 = json.loads(M4_REPORT.read_text(encoding="utf-8")) if M4_REPORT.exists() else {}
    base = m4.get("all_history", {})
    result["m4"] = {"source": m4.get("ledger_generated_at"), "baseline": base.get("original"),
                    "excluded": base.get("excluded"), "hypothetical": base.get("pass_study"),
                    "research_only": True, "leagues": m4.get("study_leagues", [])}
    return result
