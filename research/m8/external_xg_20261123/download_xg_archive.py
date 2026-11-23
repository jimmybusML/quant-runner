#!/usr/bin/env python3
"""Read-only research-source acquisition, no production changes.
Archive: https://www.xgtables.io/history/index.json
Source attribution: Understat via xGTables historical archive.
"""
import csv
import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://www.xgtables.io/history/"
ROOT = Path(__file__).resolve().parent / "xgtables_understat_2017_2025"
ROOT.mkdir(parents=True, exist_ok=True)
HEADERS={"User-Agent":"Mozilla/5.0 (research data audit)"}

def get(path):
    req=urllib.request.Request(BASE+path,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=25) as resp:
        return resp.read()

index=json.loads(get("index.json"))
seasons=index.get("seasons",[])
tasks=[]
for z in seasons:
    for filename in ("fixtures.csv","shots.csv"):
        path=z["downloads"][filename]
        tasks.append((z,path,filename))

def worker(task):
    meta,path,filename=task
    out=ROOT/path
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        raw=out.read_bytes() if out.is_file() else get(path)
        if not out.is_file():out.write_bytes(raw)
        decoded=raw.decode("utf-8-sig")
        records=list(csv.DictReader(decoded.splitlines()))
        expected=int(meta["fixtures"] if filename=="fixtures.csv" else meta["shots"])
        return {"path":path,"rows":len(records),"expected_rows":expected,
                "count_matches":len(records)==expected,"bytes":len(raw),
                "sha256":hashlib.sha256(raw).hexdigest(),"ok":True}
    except Exception as e:
        return {"path":path,"ok":False,"error":str(e)[:300]}

with ThreadPoolExecutor(max_workers=5) as pool:
    results=list(pool.map(worker,tasks))
report={
    "archive_index":BASE+"index.json",
    "provider":"Understat",
    "archive":"xGTables",
    "downloaded_at_utc":datetime.now(timezone.utc).isoformat(),
    "archive_seasons":len(seasons),
    "total_expected_fixtures":sum(int(x["fixtures"]) for x in seasons),
    "total_expected_shots":sum(int(x["shots"]) for x in seasons),
    "files":results,
}
dest=ROOT/"source_manifest.json"
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
failed=[r for r in results if not r.get("ok") or not r.get("count_matches")]
print(json.dumps({"seasons":len(seasons),"files":len(results),
"success":sum(r.get("ok",False) for r in results),
"verified_count":sum(r.get("count_matches",False) for r in results),
"fixture_rows":sum(r.get("rows",0) for r in results if r["path"].endswith("fixtures.csv")),
"shot_rows":sum(r.get("rows",0) for r in results if r["path"].endswith("shots.csv")),
"total_bytes":sum(r.get("bytes",0) for r in results),
"failed":failed},ensure_ascii=False))
