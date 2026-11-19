"""M9 formal AH, M3 fixture scope and lead-time preserved.

Only SENT Telegram receipts count as formal bets. No research Telegram.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from research.m3.m1_history_forward import candidate, load_history
from research.m3.m1_mr1_scope_audit import MR1_PATH
from research.m3.openfootball_shadow import MODELS, _serialize_score_probability_grid
from research.m3.totalcorner_forward_ev import calculate, get_latest
from research.m3.totalcorner_schedule_discovery import get_schedule
from research.m3.kickoff_gate import gate, totalcorner_shanghai_kickoff
from research.m3.probabilities import settle_score

UTC=dt.timezone.utc
HOME=Path.home()
DESK=HOME/"QuantAsiaDesk"
STATE=DESK/"state"
LEDGER=STATE/"m9_formal_events.jsonl"
EVIDENCE=STATE/"m9_crown_evidence"
LOCK=STATE/"m9_formal.lock"
HISTORY=DESK/"repos/m1/data/m1_history_cache"
MODEL="bivariate_poisson"
MARKET="AH"
MAX_DATES=2

def iso(value):
    x=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if x.tzinfo is None:
        x=x.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    return x.astimezone(UTC)

def now():
    return dt.datetime.now(UTC).isoformat()

def load_events():
    if not LEDGER.exists():return []
    return [json.loads(row) for row in LEDGER.read_text().splitlines() if row.strip()]

def append(event):
    STATE.mkdir(parents=True,exist_ok=True)
    with LEDGER.open("a",encoding="utf-8") as out:
        out.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+"\n")
        out.flush()
        os.fsync(out.fileno())

def digest(data):
    return hashlib.sha256(data).hexdigest()

def receipt_id(mid):
    return "M9_BIVARIATE_AH:"+str(mid)

def latest_state(events):
    result={}
    for event in events:
        key=event.get("order_key")
        if key and event.get("kind") in ("M9_PREPARED","M9_TG_SENT","M9_TG_UNKNOWN","M9_TG_REJECTED"):
            result.setdefault(key,{})["tg"]=event
        if key and event.get("kind")=="M9_SETTLED":
            result.setdefault(key,{})["settlement"]=event
    return result

def crown_ah(mid,token,kickoff):
    url="https://api.totalcorner.com/v1/match/bookmaker_odds/"+str(mid)
    response=requests.get(url,params={"token":token,"bookmaker":"crown","columns":"asianList"},
        headers={"Accept":"application/json","User-Agent":"M9-Crown-Formal/1.0"},timeout=30)
    response.raise_for_status()
    received=dt.datetime.now(UTC)
    body=response.content
    record=response.json()
    if record.get("success")!=1:
        raise RuntimeError("Crown AH响应未成功："+str((record.get("error") or {}).get("code")))
    matched=[x for x in record.get("data",[]) if str(x.get("id"))==str(mid)]
    if len(matched)!=1:raise ValueError("Crown返回比赛身份不唯一")
    books=[x for x in matched[0].get("bookmakers",[]) if x.get("slug")=="crown"]
    if len(books)!=1:raise ValueError("本场没有可验证的Crown盘口")
    quote=get_latest(books[0].get("asian_list"))
    if not quote:raise ValueError("Crown AH未返回完整双边报价")
    source,line,home_odd,away_odd=quote
    source_at=iso(source)
    if not (source_at<=received<iso(kickoff)):
        raise ValueError("Crown报价不具备赛前已知的时间证明")
    if not all(math.isfinite(float(v)) and float(v)>1 for v in (home_odd,away_odd)):
        raise ValueError("Crown赔率无效")
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    sha=digest(body)
    target=EVIDENCE/(str(mid)+"-"+sha+".json")
    if not target.exists():target.write_bytes(body)
    return {"market":"AH","bookmaker":"crown","bookmaker_verified":True,
            "line":line,"home_decimal":home_odd,"away_decimal":away_odd,
            "source_at":source_at.isoformat(),"received_at":received.isoformat(),
            "raw_sha256":sha,"raw_path":str(target)}

def choose(matrix,quote):
    line=quote["line"]
    scores={side:calculate(matrix,"AH",line,side,2.0) for side in ("home","away")}
    side=max(("home","away"),key=lambda s:(scores[s],s=="home"))
    price=quote["home_decimal"] if side=="home" else quote["away_decimal"]
    return side,price,scores

def deliver(token,chat,message):
    payload=urllib.parse.urlencode({"chat_id":chat,"text":message}).encode()
    url="https://api.telegram.org/bot"+token+"/sendMessage"
    req=urllib.request.Request(url,data=payload,method="POST")
    with urllib.request.urlopen(req,timeout=25) as response:
        body=json.loads(response.read())
    message_id=(body.get("result") or {}).get("message_id")
    if body.get("ok") is not True or message_id is None:
        raise RuntimeError("Telegram没有确认发送")
    return str(message_id)

def prediction(frame,home,away):
    cls=MODELS[MODEL]
    model=cls(frame.home_goals,frame.away_goals,frame.home_team,frame.away_team)
    model.fit()
    return _serialize_score_probability_grid(model.predict(home,away))

def format_order_message(row,side,quote,price,names=None):
    """Single-line formal order format shared with the user's MR1 example."""
    names=names or {}
    kickoff=iso(row["kickoff"]).astimezone(ZoneInfo("Asia/Shanghai"))
    time_text=kickoff.strftime("%Y-%m-%d %H:%M")
    league=names.get("competitions",{}).get(str(row.get("league") or "").strip().casefold()) or str(row.get("league") or "未知联赛")
    home=names.get("teams",{}).get(str(row["home"]).strip().casefold()) or row["home"]
    away=names.get("teams",{}).get(str(row["away"]).strip().casefold()) or row["away"]
    selected_team=home if side=="home" else away
    selection_line=quote["line"] if side=="home" else -quote["line"]
    line=f"{selection_line:+g}" if selection_line else "0"
    hong_kong_odds=float(price)-1.0
    return f"【M9】{time_text} {league} {home} vs {away} 全场让球 {selected_team} {line}@{hong_kong_odds:.2f}"

def display_names():
    path=HOME/"QuantAsiaDesk/repos/m1/data/football_display_names/display_names.json"
    try:doc=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}
    maps={}
    for kind in ("teams","competitions"):
        result={}
        for item in (doc.get(kind) or {}).values():
            source=str(item.get("provider_name") or "").strip().casefold()
            target=item.get("canonical_zh") if item.get("status")=="CANONICAL" else None
            if source and target:result[source]=target
        maps[kind]=result
    return maps

def send_one(row,matrix,token,chat,api):
    mid=str(row["mid"])
    key=receipt_id(mid)
    quote=crown_ah(mid,api,row["kickoff"])
    if not gate({"kickoff_utc_verified":row["kickoff"]},dt.datetime.now(UTC))[0]:
        return "time_expired"
    side,price,scores=choose(matrix,quote)
    row=dict(row)
    record={"kind":"M9_PREPARED","order_key":key,"fid":mid,
        "model":MODEL,"market":"AH","side":side,"line":quote["line"],
        "decimal_odd":price,"home_decimal":quote["home_decimal"],
        "away_decimal":quote["away_decimal"],"home_team":row["home"],
        "away_team":row["away"],"league_id":row["league_id"],
        "league":row.get("league"),"kickoff_utc":row["kickoff"],
        "selection_line":quote["line"] if side=="home" else -quote["line"],
        "hong_kong_odds":round(float(price)-1.0,6),
        "crown":quote,"selected_at_utc":now(),
        "model_only_neutral_odds_scores":scores,"tg_status":"PREPARED"}
    append(record)
    message=format_order_message(row,side,quote,price,display_names())
    try:
        message_id=deliver(token,chat,message)
    except Exception as ex:
        # An attempted send may have succeeded even without a response.
        # Never automatically retry a prepared/unknown order.
        append({"kind":"M9_TG_UNKNOWN","order_key":key,"fid":mid,
                "at_utc":now(),"error_type":type(ex).__name__,"tg_status":"UNKNOWN"})
        return "tg_unknown"
    append({"kind":"M9_TG_SENT","order_key":key,"fid":mid,"at_utc":now(),
            "telegram_message_id":message_id,"tg_status":"SENT"})
    return "sent"

def run():
    api=os.environ.get("TOTALCORNER_TOKEN")
    token=os.environ.get("M9_TG_BOT_TOKEN")
    chat=os.environ.get("M9_TG_CHAT_ID")
    if not api:raise RuntimeError("缺少TotalCorner凭证")
    if not token or not chat:raise RuntimeError("M9正式TG凭证未设置；未发送")
    events=load_events()
    blocked=set(latest_state(events))
    history,coverage=load_history(HISTORY,dt.datetime.now(UTC))
    spec=json.loads(MR1_PATH.read_text())
    today=dt.datetime.now(UTC).astimezone(ZoneInfo("Asia/Shanghai")).date()
    fixtures={}
    stats=collections.Counter()
    for offset in range(MAX_DATES):
        day=(today+dt.timedelta(days=offset)).isoformat()
        matches,pages=get_schedule(day,api)
        stats["schedule_pages"]+=pages
        for r in matches:
            reason,info=candidate(r,dt.datetime.now(UTC),spec,history)
            stats[reason]+=1
            mid=str(r.get("id",""))
            if info and receipt_id(mid) not in blocked:
                fixtures[mid]=(r,info)
    groups=collections.defaultdict(list)
    for mid,(src,info) in fixtures.items():groups[info[0]].append((mid,src,info))
    for league_id,group in groups.items():
        train=group[0][2][4]
        frame=pd.DataFrame([{"home_team":x[2],"away_team":x[3],
            "home_goals":x[4],"away_goals":x[5]} for x in train])
        # As in existing M3, fit the league model once and predict each fixture.
        model=MODELS[MODEL](frame.home_goals,frame.away_goals,frame.home_team,frame.away_team)
        try:model.fit()
        except Exception:
            stats["fit_failed"]+=len(group);continue
        for mid,src,info in group:
            _,home_id,away_id,kickoff,_=info
            if not gate({"kickoff_utc_verified":kickoff},dt.datetime.now(UTC))[0]:
                stats["time_expired"]+=1;continue
            try:
                matrix=_serialize_score_probability_grid(model.predict(home_id,away_id))
                outcome=send_one({"mid":mid,"home":str(src.get("h")),
                    "away":str(src.get("a")),"kickoff":kickoff,"league_id":league_id,
                    "league":str(src.get("l") or "")},
                    matrix,token,chat,api)
                stats[outcome]+=1
            except Exception as ex:
                stats["quote_or_prediction_"+type(ex).__name__]+=1
            time.sleep(2.2)
    report()
    print(json.dumps({"status":"completed","scope":"M3_UNCHANGED","market":"AH",
        "model":MODEL,"formal_sent_now":stats["sent"],"counts":dict(stats),
        "training_coverage":coverage},ensure_ascii=False))

def fetch_ft(fid,api):
    response=requests.get("https://api.totalcorner.com/v1/match/view/"+fid,
        params={"token":api},headers={"Accept":"application/json"},timeout=25)
    response.raise_for_status()
    raw=response.content
    data=response.json()
    matched=[x for x in data.get("data",[]) if str(x.get("id"))==fid]
    if len(matched)!=1 or matched[0].get("status")!="full":return None
    return matched[0],digest(raw),raw

def settle():
    api=os.environ.get("TOTALCORNER_TOKEN")
    if not api:raise RuntimeError("缺少TotalCorner凭证")
    events=load_events();states=latest_state(events)
    prepared={x["order_key"]:x for x in events if x.get("kind")=="M9_PREPARED"}
    counts=collections.Counter()
    for key,state in states.items():
        if state.get("tg",{}).get("kind")!="M9_TG_SENT" or state.get("settlement"):
            continue
        order=prepared.get(key)
        if not order or (order.get("crown") or {}).get("bookmaker_verified") is not True:
            continue
        try:
            r=fetch_ft(order["fid"],api)
            if not r:counts["not_full"]+=1;continue
            match,sha,raw=r
            if (str(match.get("h","")).casefold()!=order["home_team"].casefold()
                or str(match.get("a","")).casefold()!=order["away_team"].casefold()
                or iso(match["start"])!=iso(order["kickoff_utc"])):
                counts["identity_unverified"]+=1;continue
            hg,ag=int(match["hg"]),int(match["ag"])
            if min(hg,ag)<0:continue
            status,pnl=settle_score("AH",order["line"],order["side"],hg,ag,order["decimal_odd"])
            EVIDENCE.mkdir(parents=True,exist_ok=True)
            (EVIDENCE/(order["fid"]+"-FT-"+sha+".json")).write_bytes(raw)
            append({"kind":"M9_SETTLED","order_key":key,"fid":order["fid"],"at_utc":now(),
                    "home_goals":hg,"away_goals":ag,"state":status,"pnl_u":pnl,"ft_raw_sha256":sha})
            counts["settled"]+=1
        except Exception as ex:counts["failed_"+type(ex).__name__]+=1
        time.sleep(2.2)
    report()
    print(json.dumps({"action":"settle","results":dict(counts)},ensure_ascii=False))

def report():
    ev=load_events();prepare={x["order_key"]:x for x in ev if x.get("kind")=="M9_PREPARED"}
    latest=latest_state(ev)
    sent=[k for k,v in latest.items()
          if v.get("tg",{}).get("kind")=="M9_TG_SENT"
          and v.get("tg",{}).get("telegram_message_id")
          and k in prepare and prepare[k].get("model")==MODEL
          and prepare[k].get("market")==MARKET
          and (prepare[k].get("crown") or {}).get("bookmaker_verified") is True]
    settled=[latest[k]["settlement"] for k in sent if "settlement" in latest[k]]
    outcomes=collections.Counter(x["state"] for x in settled)
    total=sum(float(x["pnl_u"]) for x in settled)
    output={"model":"M9","identity":"bivariate_poisson_AH_Crown_FORMAL_TG",
        "source_time":now(),"sent":len(sent),"settled":len(settled),
        "pending":len(sent)-len(settled),"pnl":round(total,6),
        "roi":round(100*total/len(settled),6) if settled else None,
        "states":dict(outcomes),"unknown":sum(v.get("tg",{}).get("kind")=="M9_TG_UNKNOWN" for v in latest.values()),
        "unconfirmed_not_formal":len(latest)-len(sent),
        "separate_from_M3_shadow":True}
    STATE.mkdir(parents=True,exist_ok=True)
    (STATE/"m9_latest.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"action":"report",**output},ensure_ascii=False))
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["run","settle","report"])
    a=p.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    with LOCK.open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        {"run":run,"settle":settle,"report":report}[a.action]()
if __name__=="__main__":main()
