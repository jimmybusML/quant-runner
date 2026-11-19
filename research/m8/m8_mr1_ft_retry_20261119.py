#!/usr/bin/env python3
"""Research-only conservative retry of transient FT receipt errors; no trading."""
import datetime as dt, hashlib,json,time
from pathlib import Path
import requests
from m8_mr1_ft_evidence_query_20261119 import ROOT,OUT,RAW,TOKEN,ROWS,utc
def main():
    rows={x["fid"]:x for x in (json.loads(l) for l in ROWS.open() if l.strip())}
    evid=[json.loads(l) for l in (OUT/"ft_query_evidence.jsonl").open() if l.strip()]
    latest={e["fid"]:e for e in evid}
    targets=[fid for fid,e in latest.items() if e["status"] in ("http_error_SSLError","no_matching_fixture")]
    token=TOKEN.read_text().strip()
    print("TRANSIENT_RETRIES",len(targets),flush=True)
    for fid in targets:
        m=rows[fid];e={"fid":fid,"home":m["home"],"away":m["away"],"kickoff_utc":m["kickoff_utc"],"league":m["league"],"retry_of_transient":True}
        try:
            r=requests.get("https://api.totalcorner.com/v1/match/view/"+fid,
                params={"token":token},headers={"Accept":"application/json","User-Agent":"M8-FT-Evidence/1.0"},timeout=20)
            received=dt.datetime.now(dt.timezone.utc)
            body=r.content;h=hashlib.sha256(body).hexdigest()
            p=RAW/(fid+"-"+h+".json");p.write_bytes(body)
            e.update({"http_status":r.status_code,"received_utc":received.isoformat(),
                      "raw_sha256":h,"raw_file":str(p.relative_to(OUT))})
            b=json.loads(body)
            data=b["data"] if isinstance(b.get("data"),list) else b.get("data",{}).get("matches",[])
            x=next((x for x in data if str(x.get("id"))==fid),None)
            if x is None:
                e["status"]="provider_"+str((b.get("error") or {}).get("code") or "no_matching_fixture")
            else:
                identity=(str(x.get("h","")).casefold()==m["home"].casefold() and str(x.get("a","")).casefold()==m["away"].casefold())
                ko=utc(x.get("start"));expected=utc(m["kickoff_utc"])
                e.update({"provider_status":x.get("status"),"exact_team_match":identity,
                          "kickoff_equal":ko==expected,"provider_kickoff_utc":ko.isoformat() if ko else None})
                if x.get("status")=="full" and identity and ko==expected and received>ko:
                    h,a=int(x["hg"]),int(x["ag"])
                    if h>=0 and a>=0:e.update({"status":"verified_ft","hg":h,"ag":a})
                    else:e["status"]="invalid_score"
                else:e["status"]="not_verified_ft"
        except Exception as ex:
            e["status"]="retry_error_"+type(ex).__name__
        with (OUT/"ft_query_evidence.jsonl").open("a") as f:f.write(json.dumps(e,ensure_ascii=False,sort_keys=True)+"\n")
        print(fid,e["status"],flush=True)
        time.sleep(11)
if __name__=="__main__":main()
