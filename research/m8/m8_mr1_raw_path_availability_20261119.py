#!/usr/bin/env python3
"""Read-only proof of whether MR1 raw Crown asian_list paths were available at T1 receipt."""
import bisect,collections,datetime as dt,hashlib,json,math
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"research/m8"
MR1=Path("/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23")
OUT=BASE/"mr1_m8_ft_evidence_20261119"
FIDS={json.loads(l)["fid"] for l in (BASE/"mr1_m8_ft_feature_audit_20261119/per_fixture.jsonl").open() if json.loads(l)["kickoff_reached_asof"]}
def utc(s):
    if not s:return None
    v=dt.datetime.fromisoformat(str(s).replace("Z","+00:00").replace(" ","T"))
    return v if v.tzinfo else v.replace(tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(dt.timezone.utc)
def main():
    rows=[];issues=collections.Counter()
    for l in (MR1/"snapshot-index.jsonl").open():
        r=json.loads(l);fid=str(r.get("match_id"))
        if fid not in FIDS or r.get("classification")!="SNAPSHOT_OK" or r.get("target_horizon")!="T1":continue
        p=MR1/r["snapshot_path"];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r["snapshot_sha256"]:
            issues["snapshot_sha_mismatch"]+=1;continue
        s=json.loads(raw);received=utc(s.get("received_at"));kickoff=utc(s.get("kickoff_at"))
        attempts=[a for a in s.get("request_attempts",[]) if str(a.get("endpoint","")).startswith("/match/bookmaker_odds/")]
        if not attempts:issues["no_bookmaker_attempt"]+=1;continue
        attempt=attempts[-1];content=attempt.get("raw_response")
        if not isinstance(content,str):issues["no_raw_response"]+=1;continue
        if hashlib.sha256(content.encode()).hexdigest()!=attempt.get("raw_sha256"):
            issues["raw_body_sha_mismatch"]+=1;continue
        try:
            b=json.loads(content)
            records=b["data"] if isinstance(b.get("data"),list) else b.get("data",{}).get("matches",[])
            record=next(x for x in records if str(x.get("id"))==fid)
            book=next(x for x in record["bookmakers"] if x.get("slug")=="crown")
        except Exception:
            issues["raw_parse_or_identity"]+=1;continue
        lines=[];future_events=0
        for v in book.get("asian_list") or []:
            try:
                at=utc(v[4]);line=float(v[1]);hp=float(v[2]);ap=float(v[3])
                if at is None or not all(math.isfinite(x) for x in (line,hp,ap)) or hp<=1 or ap<=1:continue
                if at>received:
                    future_events+=1;continue
                lines.append((at,line,hp,ap))
            except Exception:continue
        lines.sort(key=lambda x:x[0]);times=[x[0] for x in lines]
        t6=kickoff-dt.timedelta(hours=6);t3=kickoff-dt.timedelta(hours=3);t1=kickoff-dt.timedelta(hours=1)
        i=bisect.bisect_right(times,t6)-1;j=bisect.bisect_right(times,t1)-1
        k=bisect.bisect_right(times,t3)-1
        seq=lines[i:j+1] if i>=0 and j>=i else []
        movements=sum(seq[z][1]!=seq[z-1][1] or seq[z][2]!=seq[z-1][2] or seq[z][3]!=seq[z-1][3] for z in range(1,len(seq)))
        row={"fid":fid,"received_utc":received.isoformat(),"kickoff_utc":kickoff.isoformat(),
             "received_minutes_before_kickoff":round((kickoff-received).total_seconds()/60,3),
             "T1_cutoff_utc":t1.isoformat(),
             "snapshot_sha256":r["snapshot_sha256"],"raw_sha256":attempt["raw_sha256"],
             "full_raw_asian_events_available_at_receipt":len(lines),
             "future_events_excluded":future_events,
             "has_T6_source_event":i>=0,"has_T3_source_event":k>=0,
             "T6_to_T1_historical_source_events_in_saved_receipt":len(seq),
             "movements_within_saved_path":movements,
             "full_path_at_exact_T1_known_from_T1_receipt":False,
             "note":"T1 MR1 receipt arrives before exact T-1h cutoff; events after HTTP receipt but before cutoff cannot be asserted observed."}
        rows.append(row)
    out={"past_fids_under_review":len(FIDS),"T1_receipt_fids_audited":len(rows),
         "snapshot_and_raw_sha_valid":len(rows),"issues":dict(issues),
         "with_T6_quote":sum(x["has_T6_source_event"] for x in rows),
         "with_T6_and_T3":sum(x["has_T6_source_event"] and x["has_T3_source_event"] for x in rows),
         "with_two_or_more_saved_in_window_events":sum(x["T6_to_T1_historical_source_events_in_saved_receipt"]>=2 for x in rows),
         "with_any_in_window_price_or_line_change":sum(x["movements_within_saved_path"]>0 for x in rows),
         "source_future_events_excluded":sum(x["future_events_excluded"] for x in rows),
         "meaning":"Observed movement histories can supplement feature research; not an exact frozen M8 T1 executable signal or a trading strategy."}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"mr1_raw_path_availability_summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    with (OUT/"mr1_raw_path_availability_per_fid.jsonl").open("w") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps(out,ensure_ascii=False))
if __name__=="__main__":main()
