#!/usr/bin/env python3
"""R65 2023-2026 LOCAL Codex history + genuine Crown archive audit.

No M9 formal order records. Read only 61 historical league caches + Crown sqlite
and SHA-verified historical raw response files; private fixture matches remain
only in local /Users/mac/QuantAsiaDesk/state/m9_r65_historical_crown_private.json.
"""
import sqlite3,datetime as dt,hashlib,json,collections,math,os
from pathlib import Path
ROOT=Path.home()/"QuantAsiaDesk"
H=ROOT/"repos/m1/data/m1_history_cache"
DB=ROOT/"data/crown_quote_store/crown_quotes.sqlite3"
P=Path(__file__).resolve().parent
OUT=P/"M9_HISTORICAL_CROWN_AUDIT_R65.json"
PRIVATE=ROOT/"state/m9_r65_historical_crown_private.json"
def parse(s):
    return dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
def score_rows():
    results={}
    by=collections.defaultdict(lambda:collections.Counter())
    league_year=collections.defaultdict(set)
    for f in sorted(H.glob("*.json")):
        lid=f.stem
        z=json.loads(f.read_text())
        for r in z.get("rows",[]):
            year=str(r.get("start",""))[:4]
            if year not in ("2023","2024","2025","2026"):continue
            by[year]["cache_rows"]+=1
            if r.get("status")!="full":
                by[year]["not_full"]+=1
                continue
            try:
                gh,ga=int(r["hg"]),int(r["ag"]);h,a=str(r["h_id"]),str(r["a_id"])
                assert min(gh,ga)>=0 and h!=a
                fid=str(r["id"])
                if fid in results and results[fid]["league_id"]!=lid:
                    by[year]["cross_league_duplicate_id"]+=1;continue
                results[fid]={"year":year,"league_id":lid,"kickoff_source":r["start"],
                              "home_id":h,"away_id":a,"home_goals":gh,"away_goals":ga}
                league_year[year].add(lid)
                by[year]["valid_completed"]+=1
            except (ValueError,KeyError,TypeError,AssertionError):
                by[year]["invalid_full"]+=1
    return results,by,league_year
hist,by,leagues=score_rows()
cx=sqlite3.connect("file:"+str(DB)+"?mode=ro",uri=True)
cur=cx.execute("""SELECT q.fixture_id, c.kickoff_at_utc, q.quote_kind,
 q.handicap_home, q.home_decimal, q.away_decimal,
 q.quote_source_at_utc, q.quote_before_kickoff, c.capture_mode,
 c.response_received_at_utc, c.source_file,c.response_sha256,c.capture_key,
 c.prospective_observation,c.status
 FROM asian_quote q JOIN capture c ON c.capture_key=q.capture_key
 WHERE c.kickoff_at_utc >= '2023' AND c.kickoff_at_utc < '2027'
 AND q.quote_kind in ('open','close')""")
selected={}
coverage=collections.defaultdict(lambda:collections.Counter())
for tup in cur:
    fid,kickoff,kind,line,hodd,aodd,source_at,before,mode,received,path,sha,key,prospective,status=tup
    year=str(kickoff)[:4];coverage[year]["quote_records"]+=1
    if kind=="close":coverage[year]["close_rows"]+=1
    else:coverage[year]["open_rows"]+=1
    if int(before or 0)!=1:
        coverage[year]["quote_not_pre_kickoff"]+=1;continue
    try:
        assert status=="QUOTES_SAVED"
        line=float(line);hodd=float(hodd);aodd=float(aodd)
        assert math.isfinite(line) and abs(line*4-round(line*4))<1e-7
        assert all(math.isfinite(v) and v>1 for v in (hodd,aodd))
        if source_at is None:raise ValueError("source time missing")
        t=parse(source_at);k=parse(kickoff)
        assert t<k
    except Exception:
        coverage[year]["invalid_quote_or_time"]+=1;continue
    if fid not in hist:
        coverage[year]["quote_without_completed_cache_fixture"]+=1;continue
    if hist[fid]["year"]!=year:
        coverage[year]["year_mismatch"]+=1;continue
    # UTC kickoff in archive vs Asia/Shanghai wall clock in history cache:
    hkick=dt.datetime.strptime(hist[fid]["kickoff_source"][:19],"%Y-%m-%d %H:%M:%S")
    hkick=hkick.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).astimezone(dt.timezone.utc)
    if abs((hkick-k).total_seconds())>180:
        coverage[year]["kickoff_disagrees_over_3min"]+=1;continue
    row={"fid":fid,"year":year,"kind":kind,"quote_source_utc":source_at,
         "kickoff_utc":kickoff,"line":line,"home_decimal":hodd,"away_decimal":aodd,
         "capture_mode":mode,"response_received_utc":received,
         "source_file":path,"raw_sha256":sha,"capture_key":key,
         "prospective":bool(prospective),
         **{key:hist[fid][key] for key in ("league_id","home_id","away_id","home_goals","away_goals")}}
    # Pick one latest source-timestamp quote per fixture and kind deterministically.
    k2=(fid,kind);prev=selected.get(k2)
    if prev is None or (row["quote_source_utc"],row["capture_key"])>(prev["quote_source_utc"],prev["capture_key"]):
        selected[k2]=row
raw_checks={}
problems=[]
for row in selected.values():
    key=(row["source_file"],row["raw_sha256"])
    if key not in raw_checks:
        path=Path(row["source_file"] or "")
        if not path.is_file():raw_checks[key]="missing"
        else:
            try:
                blob=path.read_bytes()
                if hashlib.sha256(blob).hexdigest()!=row["raw_sha256"]:raw_checks[key]="hash_mismatch"
                else:
                    obj=json.loads(blob)
                    matches=[r for r in obj.get("data",[]) if str(r.get("id"))==row["fid"]]
                    if obj.get("success")!=1 or len(matches)!=1:raw_checks[key]="identity_mismatch"
                    else:
                        books=[b for b in matches[0].get("bookmakers",[]) if b.get("slug")=="crown"]
                        raw_checks[key]="ok" if len(books)==1 else "not_crown"
            except Exception as exc:raw_checks[key]="read_error:"+type(exc).__name__
    row["raw_verification"]=raw_checks[key]
for row in selected.values():
    year=row["year"];c=coverage[year]
    c["matched_selected_quote_"+row["kind"]]+=1
    c["raw_"+row["raw_verification"]]+=1
    rec=row["response_received_utc"]
    try:
        if rec and parse(rec)<parse(row["kickoff_utc"]):c["received_pre_kickoff"]+=1
        elif rec:c["received_after_kickoff"]+=1
        else:c["no_receive_timestamp"]+=1
    except Exception:c["invalid_receive_timestamp"]+=1
    if row["raw_verification"]!="ok":
        problems.append({"year":year,"kind":row["kind"],"reason":row["raw_verification"]})
public={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "sources":{"history":str(H),"sqlite":str(DB)},
        "method":"Full 2023-2026 completed fixture inventory joined by TotalCorner match ID and kickoff with selected exact Crown summary open and close; all distinct selected source-file SHA256 and Crown identity audited. Quote source timestamp before kickoff is historical provider event time; actual system reception may have occurred in 2026.",
        "source":{y:{"cache":dict(by[y]),"league_count":len(leagues[y]),"valid_completed_unique_ids":sum(x["year"]==y for x in hist.values()),"quote":dict(coverage[y])} for y in ("2023","2024","2025","2026")},
        "selected_quotes":len(selected),"matched_completed_fixtures":len({r["fid"] for r in selected.values()}),
        "verified_distinct_source_files":len(raw_checks),
        "source_file_hash_problems":dict(collections.Counter(v for v in raw_checks.values() if v!="ok")),
        "scope":"Historical Codex recovery only. No formal M9 275-order sample or production state changed."}
OUT.write_text(json.dumps(public,ensure_ascii=False,indent=2)+"\n")
PRIVATE.write_text(json.dumps({"rows":sorted(selected.values(),key=lambda x:(x["year"],x["league_id"],x["fid"],x["kind"]))},ensure_ascii=False)+"\n")
print(json.dumps(public,ensure_ascii=False,indent=2),flush=True)
