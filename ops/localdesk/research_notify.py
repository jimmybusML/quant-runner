"""Opt-in Telegram research delivery for M3 forecast signals and M4 study.

Uses a separate research notification receipt book. Never mutates or relabels
M1/MR1 official Telegram entries. No selection gate, stake or bet instruction.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
RECORD = BASE / "state/research_telegram_receipts.json"
LEDGER = BASE / "repos/runner/research/m3/results/totalcorner/forward_ev_ledger.jsonl"


def load():
    if not RECORD.exists():
        return {}
    return json.loads(RECORD.read_text(encoding="utf-8"))


def store(records):
    tmp = RECORD.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, RECORD)


def deliver(message, token, chat):
    payload = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode("utf-8")
    req = urllib.request.Request("https://api.telegram.org/bot" + token + "/sendMessage",
                                 data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.loads(response.read())
    if not result.get("ok") or not result.get("result", {}).get("message_id"):
        raise RuntimeError("Telegram did not confirm successful delivery")
    return str(result["result"]["message_id"])


def emit_m3(run_id, token, chat):
    """Send every new order derived in that run once. No EV filtering."""
    receipt = load()
    events = []
    with LEDGER.open(encoding="utf-8") as reader:
        for line in reader:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("protocol") == "M3_SHADOW_ORDER_V1" and event.get("run_id") == run_id:
                events.append(event)
    sent = 0
    for item in events:
        eid = "m3:" + str(item["event_id"])
        if eid in receipt:
            continue
        model = {"poisson":"泊松", "dixon_coles":"Dixon-Coles","bivariate_poisson":"双变量泊松"}.get(item["model"], item["model"])
        market = "让球" if item["market"] == "AH" else "大小球"
        side = {"home":"主队", "away":"客队", "over":"大球","under":"小球"}.get(str(item["side"]).lower(), item["side"])
        msg = ("【M3 模型预测 · 研究记录】\n"
               f"模型：{model}（{market}）\n"
               f"比赛：{item['home_team']} vs {item['away_team']}\n"
               f"预测：{side} 盘口 {item['line']}，赔率 {item['decimal_odd']}\n"
               "此消息来自 M3 影子预测，不计入正式 TG 实战成绩。")
        # Make uncertain transport errors visible; never automatically retry unknown sends.
        try:
            result_id = deliver(msg, token, chat)
        except Exception:
            receipt[eid] = {"status": "UNKNOWN", "time": datetime.now(timezone.utc).isoformat()}
            store(receipt)
            raise RuntimeError("M3 TG 发送状态不确定，已标记待核实，不会自动重复发送")
        receipt[eid] = {"status": "SENT", "telegram_message_id": result_id, "time": datetime.now(timezone.utc).isoformat()}
        store(receipt)
        sent += 1
    return {"sent": sent, "candidate_messages": len(events)}


def emit_m4(run_id, report, token, chat):
    """M4 has a retrospective study, not a prospective order selector."""
    receipt = load()
    key = "m4-study:" + run_id
    if key in receipt:
        return {"sent": 0}
    baseline = report.get("all_history", {}).get("original", {})
    sample = report.get("all_history", {}).get("pass_study", {})
    msg = ("【M4 联赛研究结果】\n"
           "当前 M4 仍是 MR1 的历史对比研究，没有独立的新赛前下注信号。\n"
           f"原 MR1 已结：{baseline.get('orders',0)} 单，{float(baseline.get('pnl_units',0)):+.3f} U\n"
           f"假设跳过两联赛：{sample.get('orders',0)} 单，{float(sample.get('pnl_units',0)):+.3f} U\n"
           "以上为事后研究比较，不是正式实战派单。")
    try:
        message_id = deliver(msg, token, chat)
    except Exception:
        receipt[key] = {"status": "UNKNOWN", "time": datetime.now(timezone.utc).isoformat()}
        store(receipt)
        raise RuntimeError("M4 TG 发送状态不确定，已记录待核实，不自动重发")
    receipt[key] = {"status": "SENT", "telegram_message_id": message_id, "time": datetime.now(timezone.utc).isoformat()}
    store(receipt)
    return {"sent": 1}
