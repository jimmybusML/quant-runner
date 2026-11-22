#!/usr/bin/env python3
"""Crown 2026 historical full-time close supplement: source-SHA verified M5 raw responses.

PRE-KICKOFF source event only, no live receive proof. Local detail JSONL is not published.
"""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized")
INDEX=ROOT/"crown-response-index.jsonl"
RAW=ROOT/"crown-responses"
EARLY=Path("/Users/mac/QuantAsiaDesk/research-work/m8_early_joint_market_inventory_20261115.jsonl")
OUT=HERE/"m5_2026_close_supplement.local.jsonl"
METRICS=HERE/"m5_2026_close_supplement_metrics.json"

def timezone(s):
    t=dt.datetime.fromisoformat(str(s).replace(" ","T").replace("Z","+00:00"))
    return t.astimezone(dt.timezone.utc) if t.tzinfo else t.replace(tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(dt.timezone.utc)

wanted={}
for line in EARLY.open():
    r=json.loads(line)
    if r["year"]==2026 and r["T"]==12 and r["ah_kind"]=="list" and r["ou_kind"]=="list":
        wanted[str(r["fid"])]=r
index={}
for line in INDEX.open():
    r=json.loads(line)
    fid=str(r["match_id"])
    if fid in wanted:
        index[fid]=r
count=collections.Counter()
rows={}
count["wanted"]=len(wanted)
count["with_index"]=len(index)
for fid,e in wanted.items():
    if fid not in index:
        count["missing_index"]+=1;continue
    p=RAW/(fid+".json")
    if not p.is_file():
        count["missing_raw"]+=1;continue
    body=p.read_bytes()
    if hashlib.sha256(body).hexdigest()!=index[fid]["response_sha256"]:
        count["sha_mismatch"]+=1;continue
    dat=json.loads(body)
    if dat.get("success")!=1:
        count["not_success"]+=1;continue
    matches=[x for x in dat.get("data",[]) if str(x.get("id"))==fid]
    if len(matches)!=1:
        count["missing_identity"]+=1;continue
    m=matches[0]
    if str(m.get("l_id"))!=str(e["league"]) or m.get("status")!="full":
        count["not_full_or_league_mismatch"]+=1;continue
    ko=timezone(m["start"])
    if ko.year!=2026:
        count["not_year_2026"]+=1;continue
    h,a=int(m["hg"]),int(m["ag"])
    if (h,a)!=(e["hg"],e["ag"]):
        count["score_mismatch"]+=1;continue
    books=[b for b in m.get("bookmakers",[]) if b.get("slug")=="crown"]
    if len(books)!=1:
        count["wrong_crown_books"]+=1;continue
    b=books[0]
    quotes={}
    for market,field,side0,side1 in (("AH","asian","home","away"),("OU","goal","over","under")):
        options=[]
        close=(b.get(field) or {}).get("close")
        if isinstance(close,dict):
            try:
                t=timezone(close["time"]);li=float(close["line"]);o0=float(close[side0]);o1=float(close[side1])
                if t<ko and o0>1 and o1>1 and abs(li*4-round(li*4))<1e-7:
                    options.append((t,li,o0,o1,"close"))
                else:count["invalid_snapshot_"+market]+=1
            except (ValueError,TypeError,KeyError,OverflowError):
                count["malformed_snapshot_"+market]+=1
        for q in b.get(field+"_list") or []:
            try:
                t=timezone(q[4]);li=float(q[1]);o0=float(q[2]);o1=float(q[3])
                if t<ko and o0>1 and o1>1 and abs(li*4-round(li*4))<1e-7:
                    options.append((t,li,o0,o1,"list"))
            except (ValueError,TypeError,KeyError,IndexError,OverflowError):
                count["malformed_path_"+market]+=1
        if options:
            t,li,o0,o1,kind=max(options,key=lambda q:(q[0],q[4]=="list"))
            quotes[market]={"line":li,"odds":{side0:o0,side1:o1},
                "quote_source_at_utc":t.isoformat(),"kind":kind}
            count["selected_"+market+"_"+kind]+=1
        else:
            count["missing_preko_quote_"+market]+=1
    if len(quotes)!=2:
        count["missing_pair"]+=1;continue
    row=dict(fixture_id=fid,league_id=e["league"],kickoff_utc=ko.isoformat(),
             score=f"{h}-{a}",historical_capture_received_at_utc=index[fid]["captured_at_utc"],
             capture_mode="historical",prospective_observation=False,source_file=str(p),
             raw_sha256=index[fid]["response_sha256"],markets=quotes,
             quote_basis="source-SHA verified M5 Crown raw historical-response latest source-event pre-kickoff quote")
    rows[fid]=row
    count["paired_2026"]+=1
with OUT.open("w") as f:
    for row in rows.values():
        f.write(json.dumps(row,ensure_ascii=False)+"\n")
metrics=dict(
    generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    counts=dict(count),supplement_output=str(OUT),
    note="All prices retrieved after kickoff in November 2026; source event times not real receipt times")
METRICS.write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(metrics,ensure_ascii=False,indent=2))
