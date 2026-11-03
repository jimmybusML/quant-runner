"""On-demand isolated tests for M1/MR1/M3/M4.

No model candidate, official Telegram dispatch, bankroll, production ledger, or
schedule is changed. Optional Telegram test is sent only on an enabled switch.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPOS = BASE / "repos"
STATE = BASE / "state"
RECEIPTS = STATE / "manual_test_telegram_receipts.jsonl"
PY = str(BASE / "venv/bin/python")
NODE = "/usr/local/bin/node"
MODEL_NAMES={"m1":"M1 AH","mr1":"MR1 AH","m3":"M3","m4":"M4"}


def offline_test(model: str):
    if model not in MODEL_NAMES:
        raise ValueError("未知模型")
    plan = {
        "m1": ([PY, "-m", "unittest", "-q", "test_m1_formal_runtime.py"], REPOS / "m1", 12),
        "mr1": ([NODE, "--test", "test-v6-ah-formal.js", "test-crown-source.js"], REPOS / "mr1", 6),
        "m3": ([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_m3_segmented_ledger.py", "-q"], REPOS / "runner", 2),
        "m4": ([PY, "research/m4/mr1_two_league_pass_study.py",
                str(REPOS / "mr1/data/mr1-v6-cross-market/formal/settled.json")], REPOS / "runner", None),
    }
    cmd, cwd, expected = plan[model]
    if not cwd.is_dir() or not Path(cmd[0]).exists():
        return {"ok": False, "message": "本机模型或执行环境缺失。"}
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=90, env={
                                    **os.environ,
                                    "PYTHONDONTWRITEBYTECODE": "1",
                                    "PYTHONUNBUFFERED": "1",
                                })
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "模型验证执行超时，未完成。"}
    if result.returncode:
        return {"ok":False,"message":"核心程序未通过验证。原始错误已保留在本机测试记录。"}
    if model=="m4":
        try:
            data=json.loads(result.stdout)
            if not data.get("research_only") or data.get("production_change") is not False:
                return {"ok":False,"message":"M4 研究结果标识异常，不能宣称通过。"}
            n=data["all_history"]["original"]["orders"]
            return {"ok":True,"message":f"历史研究计算正常，读取 MR1 已结订单 {n} 笔。M4 尚无独立赛前订单。"}
        except (ValueError,TypeError,KeyError):
            return {"ok":False,"message":"M4 的研究报告结构不完整。"}
    import re
    combined = result.stdout + "\n" + result.stderr
    if model=="mr1":
        match = re.search(r"(?:ℹ |# )?pass\s+(\d+)",combined)
        total=int(match.group(1)) if match else None
    else:
        match=re.search(r"Ran (\d+) tests?",combined)
        total=int(match.group(1)) if match else None
    if total is None or total<1:
        return {"ok":False,"message":"程序未提供可核实的测试结果。"}
    return {"ok":True,"message":f"核心程序已通过 {total} 项离线测试。未产生正式订单。"}


def telegram_test(model: str, token: str, chat_id: str):
    """Actual single test message, not a bet. Never includes token in logs."""
    if not token or not chat_id:
        return {"status":"missing","message":"Telegram 连接资料尚未保存，没有发送测试消息。"}
    note="研究消息测试" if model in ("m3","m4") else "正式派单通道测试"
    message=f"【量化亚洲盘｜{MODEL_NAMES[model]}】\n{note}成功连接本机。\n这是一条测试消息，不是投注单，不计入任何模型实战成绩。"
    payload=urllib.parse.urlencode({"chat_id":chat_id,"text":message}).encode("utf-8")
    request=urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",data=payload,method="POST")
    outcome={"model":model,"at":dt.datetime.now(dt.timezone.utc).isoformat(),
             "kind":"TEST_ONLY","status":"UNKNOWN"}
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            reply=json.loads(response.read())
        message_id=reply.get("result",{}).get("message_id")
        if reply.get("ok") is True and message_id is not None:
            outcome.update({"status":"SENT","message_id":str(message_id)})
            result={"status":"sent","message":"测试消息已由 Telegram 确认送达。"}
        else:
            outcome["status"]="UNKNOWN"
            result={"status":"unknown","message":"没有收到 Telegram 的确认回执，不自动重复发送。"}
    except urllib.error.HTTPError as exc:
        # A bot token is part of the URL: NEVER include exception details.
        outcome["status"]="REJECTED"
        result={"status":"rejected","message":f"Telegram 拒绝请求（HTTP {exc.code}）。请检查机器人和接收位置。"}
    except (urllib.error.URLError,TimeoutError,ValueError,UnicodeDecodeError):
        outcome["status"]="UNKNOWN"
        result={"status":"unknown","message":"发送状态不确定，已记录待核实，不自动重复发送。"}
    RECEIPTS.parent.mkdir(parents=True,exist_ok=True)
    # Append separated from historical formal, research and shadow records.
    with RECEIPTS.open("a", encoding="utf-8") as fd:
        fd.write(json.dumps(outcome,ensure_ascii=False)+"\n")
    return result


def discover_chat_ids(token: str):
    """Read only chat identities from recent bot updates. Never acknowledge or delete updates."""
    if not token:
        return {"ok":False,"message":"先保存机器人的 Token。","chats":[]}
    url="https://api.telegram.org/bot"+token+"/getUpdates"
    req=urllib.request.Request(url,headers={"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=12) as res:
            payload=json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code==409:
            return {"ok":False,"message":"机器人正在使用其他接收方式，不能自动查找；可以填写原有接收位置。","chats":[]}
        return {"ok":False,"message":"Telegram 未能查询接收位置，请核对机器人。","chats":[]}
    except (urllib.error.URLError,TimeoutError,ValueError):
        return {"ok":False,"message":"Telegram 查询暂时失败，未改变任何设置。","chats":[]}
    if not payload.get("ok"):
        return {"ok":False,"message":"Telegram 没有提供接收位置。","chats":[]}
    chats={}
    for u in payload.get("result",[]):
        for field in ("message","edited_message","channel_post","edited_channel_post",
                      "my_chat_member","chat_member"):
            data=u.get(field) or {}
            chat=data.get("chat") or {}
            cid=chat.get("id")
            if cid is None:
                continue
            label=chat.get("title") or " ".join(filter(None,(chat.get("first_name"),chat.get("last_name")))) or chat.get("username") or str(cid)
            chats[str(cid)]={"id":str(cid),"label":str(label),"type":chat.get("type","")}
    return {"ok":True,"message":("请选择正确的接收位置。" if chats else
               "没有查到最近的聊天。可先在 Telegram 给这个机器人发一条消息再试。"),
            "chats":list(chats.values())}
