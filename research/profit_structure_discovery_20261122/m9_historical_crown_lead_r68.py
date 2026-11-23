#!/usr/bin/env python3
"""R68 archived Crown movement quote time-slice exploration at T-6h and T-12h.

These are comparison scenarios, NOT newly approved trading time limits.
Historical quote source times can be earlier than kickoff despite first system
receipt occurring years later. Each underlying selected response SHA verified.
No M9 formal sends used.
"""
import sqlite3,hashlib,json,datetime as dt,collections,math
from pathlib import Path
ROOT=Path.home()/"QuantAsiaDesk"
DB=ROOT/"data/crown_quote_store/crown_quotes.sqlite3"
H=ROOT/"repos/m1/data/m1_history_cache"
P=Path(__file__).resolve().parent
PRIVATE=ROOT/"state/m9_r68_lead_crown_private.json"
PUBLIC=P/"M9_HISTORICAL_CROWN_LEAD_R68.json"
def parse(x):return dt.datetime.fromisoformat(str(x).replace("Z","+00:00"))
history={}
for f in H.glob("*.json"):
    lid=f.stem
    for r in json.loads(f.read_text()).get("rows",[]):
        if r.get("status")!="full":continue
        try:
            year=r["start"][:4]
            if year not in ("2023","2024","2025","2026"):continue
            h,a=str(r["h_id"]),str(r["a_id"])
            gh,ga=int(r["hg"]),int(r["ag"])
            if min(gh,ga)<0 or h==a:continue
            kick=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
            history[str(r["id"])]={"year":year,"league_id":lid,"home_id":h,"away_id":a,
             "home_goals":gh,"away_goals":ga,"kickoff":kick}
        except (ValueError,KeyError,TypeError):continue
cx=sqlite3.connect("file:"+str(DB)+"?mode=ro",uri=True)
query="""SELECT q.fixture_id,q.quote_kind,q.handicap_home,q.home_decimal,q.away_decimal,
q.quote_source_at_utc,c.kickoff_at_utc,c.source_file,c.response_sha256,
c.response_received_at_utc,c.capture_mode,c.prospective_observation,c.status
FROM asian_quote q JOIN capture c ON c.capture_key=q.capture_key
WHERE c.kickoff_at_utc >= '2023' AND c.kickoff_at_utc < '2027'
AND q.quote_kind IN ('open','movement') AND q.quote_before_kickoff=1"""
chosen={};counters=collections.Counter()
for item in cx.execute(query):
    fid,kind,line,home,away,source_at,kickoff,filepath,sha,received,mode,prospective,status=item
    counters["scanned_pre_kickoff_rows"]+=1
    match=history.get(str(fid))
    if match is None:continue
    try:
        t=parse(source_at)
        k=parse(kickoff)
        if abs((k-match["kickoff"]).total_seconds())>180:
            counters["kickoff_identity_conflict"]+=1;continue
        line=float(line);home=float(home);away=float(away)
        if not all(map(math.isfinite,(line,home,away))) or home<=1 or away<=1 or abs(line*4-round(line*4))>1e-7:continue
        if status!="QUOTES_SAVED":continue
        for hours in (6,12):
            if not t<=k-dt.timedelta(hours=hours):continue
            key=(fid,hours)
            row={"fid":fid,"year":match["year"],"kind":f"lead{hours}h","quote_source_utc":source_at,
                 "kickoff_utc":kickoff,"line":line,"home_decimal":home,"away_decimal":away,
                 "capture_mode":mode,"response_received_utc":received,
                 "source_file":filepath,"raw_sha256":sha,
                 "prospective":bool(prospective),
                 **{col:match[col] for col in ("league_id","home_id","away_id","home_goals","away_goals")}}
            prior=chosen.get(key)
            # Latest eligible source timestamp; tie-break by source identity and exact quote
            if prior is None or (source_at,filepath or "",line,home,away)>(prior["quote_source_utc"],prior["source_file"] or "",prior["line"],prior["home_decimal"],prior["away_decimal"]):
                chosen[key]=row
    except (ValueError,TypeError):counters["invalid_quote_row"]+=1
verify={}
for row in chosen.values():
    key=(row["source_file"],row["raw_sha256"],row["fid"])
    if key not in verify:
        path=Path(row["source_file"] or "")
        if not path.is_file():verify[key]="missing"
        else:
            try:
                raw=path.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=row["raw_sha256"]:verify[key]="bad_hash"
                else:
                    obj=json.loads(raw)
                    matches=[r for r in obj.get("data",[]) if str(r.get("id"))==row["fid"]]
                    books=[b for b in matches[0].get("bookmakers",[]) if b.get("slug")=="crown"] if len(matches)==1 else []
                    verify[key]="ok" if obj.get("success")==1 and len(books)==1 else "bad_crown_identity"
            except Exception as e:verify[key]="error_"+type(e).__name__
    row["raw_verification"]=verify[key]
selected=list(chosen.values())
for row in selected:
    counters["selected_"+row["kind"]]+=1
    counters["raw_"+row["raw_verification"]]+=1
    if row["response_received_utc"]:
        if parse(row["response_received_utc"])<parse(row["kickoff_utc"]):counters["actually_received_pre_kickoff"]+=1
        else:counters["actually_received_after_kickoff"]+=1
    else:counters["no_received_timestamp"]+=1
PRIVATE.write_text(json.dumps({"rows":selected},ensure_ascii=False)+"\n")
public={"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"method":"For each completed 2023-26 fixture select most recent genuine Crown source event timestamp no later than T-6h or T-12h, across original open and historical movement rows. Replay analysis only, not actually pre-received prices.","counts":dict(counters),
 "by_year_kind":{y:{k:sum(r["year"]==y and r["kind"]==k and r["raw_verification"]=="ok" for r in selected) for k in ("lead6h","lead12h")} for y in ("2023","2024","2025","2026")},
 "distinct_checked_response_and_fixture":len(verify),
 "hash_or_identity_failures":dict(collections.Counter(v for v in verify.values() if v!="ok"))}
PUBLIC.write_text(json.dumps(public,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(public,ensure_ascii=False,indent=2))
