#!/usr/bin/env python3
"""Shared read-only match history collection from previously configured MR1 scoped league IDs.
No model selection, official bets or bookmaker substitution. Source history only."""
import datetime as dt, hashlib, json, os, pathlib, time, urllib.parse, urllib.request
ROOT=pathlib.Path("research/shared_history/totalcorner")
ROOT.mkdir(parents=True,exist_ok=True)
TARGETS={"15":"Spain Segunda","57":"Portugal Segunda Liga","63":"Ukraine Persha Liga","121":"Netherlands Eerste Divisie","128":"Japan J2-League","210":"China Division 1","252":"Israel Leumit Liga","270":"Scotland Championship","337":"Serbia Prva Liga","542":"Lithuania 1 Lyga","765":"Northern Ireland Championship","10808":"Kosovo Division 1","10989":"Republic of Ireland First Division","11958":"Wales Championship North","11959":"Wales Championship South"}
GOAL=int(os.environ.get("TARGET_UNIQUE_MATCHES","10000"))
MAX_REQUESTS=int(os.environ.get("MAX_REQUESTS_PER_RUN","350"))
token=os.environ["TOTALCORNER_TOKEN"]
seen=set(); per_league={}; total_lines=0
for path in ROOT.glob("league-*.jsonl"):
 for line in path.read_text().splitlines():
  if not line.strip():continue
  row=json.loads(line)
  seen.add(str(row["id"]));total_lines+=1
def fetch(lid,page):
 params=urllib.parse.urlencode({"token":token,"page":page,"columns":"events,attacks,dangerousAttacks,shotOn,shotOff,possession,asian,goalLine"})
 url=f"https://api.totalcorner.com/v1/league/schedule/{lid}?{params}"
 req=urllib.request.Request(url,headers={"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=45) as response:return json.load(response)
requests=0;errors=[]
for lid,name in TARGETS.items():
 path=ROOT/f"league-{lid}.jsonl"
 existing={}
 if path.exists():
  for line in path.read_text().splitlines():
   if line.strip():
    r=json.loads(line);existing[str(r["id"])]=r
 # Rewalk pages because the API schedule can change. Keep a stable match ID and source hash; do not fabricate historical quote timestamps.
 page=1;added=0
 while len(seen)<GOAL and requests<MAX_REQUESTS:
  try:
   result=fetch(lid,page);requests+=1
   if str(result.get("success",result.get("status",""))) not in ("1","True"):raise ValueError("API returned unsuccessful response")
   data=result.get("data",[])
   batch=data if isinstance(data,list) else data.get("matches",[])
   if not isinstance(batch,list):raise ValueError("API matches is not an array")
   observed=dt.datetime.now(dt.timezone.utc).isoformat()
   for raw in batch:
    mid=str(raw.get("id",""))
    if not mid or mid in existing:continue
    record={"id":mid,"league_id":lid,"league_name":name,"source":"TotalCorner /league/schedule","observed_at_utc":observed,"source_sha256":hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),"match":raw}
    existing[mid]=record;seen.add(mid);added+=1
   nxt=result.get("pagination",{}).get("next")
   if not batch or not nxt:break
   page+=1
   time.sleep(3.0)
  except Exception as exc:
   errors.append({"league_id":lid,"page":page,"error":str(exc)[:160]});break
 if added:
  path.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in sorted(existing.values(),key=lambda r:r["id"])))
 per_league[name]={"unique_stored":len(existing),"added":added,"pages_read":page}
 print(json.dumps({"league":name,"unique":len(existing),"added":added,"total_unique":len(seen)},ensure_ascii=False),flush=True)
 if len(seen)>=GOAL or requests>=MAX_REQUESTS:break
summary={"source":"TotalCorner historical schedules","generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"goal_unique_matches":GOAL,"stored_unique_ids":len(seen),"stored_rows":total_lines+sum(x["added"] for x in per_league.values()),"api_requests_this_run":requests,"market_history_verified":False,"is_official_order_backtest":False,"per_league":per_league,"errors":errors}
(ROOT/"latest_collection_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print("SHARED_HISTORY_RESULT="+json.dumps(summary,ensure_ascii=False),flush=True)
