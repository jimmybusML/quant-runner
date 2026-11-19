#!/usr/bin/env python3
"""Read-only TotalCorner FT evidence audit for MR1-only pregame Crown AH fixtures.

Reads existing authorized token locally, never prints or saves it.
Does not request betting odds, does not generate bets, and does not edit production.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import requests

ROOT=Path(__file__).resolve().parents[2]
ROWS=ROOT/"research/m8/mr1_m8_ft_feature_audit_20261119/per_fixture.jsonl"
OUT=ROOT/"research/m8/mr1_m8_ft_evidence_20261119"
RAW=OUT/"raw"
TOKEN=Path("/Users/mac/Desktop/totalcorner_token.txt")
def utc(s):
    v=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
    return v if v.tzinfo else v.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
def main():
    src=[json.loads(line) for line in ROWS.open() if line.strip()]
    todo=[r for r in src if r["kickoff_reached_asof"]]
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(exist_ok=True)
    key=TOKEN.read_text().strip()
    cache={}
    index=OUT/"ft_query_evidence.jsonl"
    if index.exists():
        for line in index.open():
            try:
                r=json.loads(line);cache[r["fid"]]=r
            except Exception:pass
    for i,match in enumerate(todo,1):
        fid=match["fid"]
        if fid in cache:continue
        event={"fid":fid,"league":match.get("league"),"home":match.get("home"),"away":match.get("away"),"kickoff_utc":match.get("kickoff_utc")}
        try:
            response=requests.get("https://api.totalcorner.com/v1/match/view/"+fid,params={"token":key},
                headers={"Accept":"application/json","User-Agent":"M8-FT-Evidence/1.0"},timeout=20)
            received=dt.datetime.now(dt.timezone.utc)
            body=response.content;h=hashlib.sha256(body).hexdigest()
            path=RAW/(fid+"-"+h+".json");path.write_bytes(body)
            event.update({"received_utc":received.isoformat(),"http_status":response.status_code,
                          "raw_sha256":h,"raw_file":str(path.relative_to(OUT))})
            try:
                b=json.loads(body)
                matches=b["data"] if isinstance(b.get("data"),list) else b.get("data",{}).get("matches",[])
                record=next((m for m in matches if str(m.get("id"))==fid),None)
                if record is None:event["status"]="no_matching_fixture"
                else:
                    event["provider_status"]=record.get("status")
                    same=(str(record.get("h","")).strip().casefold()==str(match.get("home","")).strip().casefold() and str(record.get("a","")).strip().casefold()==str(match.get("away","")).strip().casefold())
                    kt=utc(record.get("start")) if record.get("start") else None
                    expected=utc(match["kickoff_utc"])
                    event["exact_team_match"]=same
                    event["provider_kickoff_utc"]=kt.isoformat() if kt else None
                    event["kickoff_equal"]=kt==expected
                    if record.get("status")=="full" and same and kt==expected and received>kt:
                        try:
                            hg=int(record["hg"]);ag=int(record["ag"])
                            if hg>=0 and ag>=0:
                                event.update({"status":"verified_ft","hg":hg,"ag":ag})
                            else:event["status"]="invalid_score"
                        except (TypeError,ValueError,KeyError):event["status"]="invalid_score"
                    elif record.get("status")=="full":event["status"]="ft_identity_or_kickoff_mismatch"
                    else:event["status"]="not_verified_ft"
            except Exception as ex:
                event["status"]="parse_error_"+type(ex).__name__
        except Exception as ex:
            event["status"]="http_error_"+type(ex).__name__
        with index.open("a") as f:f.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+"\n")
        print(json.dumps({"completed":i,"total":len(todo),"fid":fid,"status":event["status"]},ensure_ascii=False),flush=True)
        time.sleep(3.5)
    final=[json.loads(line) for line in index.open() if line.strip()]
    from collections import Counter
    summary={"examined":len(final),"status":dict(Counter(r["status"] for r in final)),"verified_scores":sum(r["status"]=="verified_ft" for r in final),"notice":"No model signals or trading orders created; raw responses retained only for research and not committed publicly."}
    (OUT/"ft_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
