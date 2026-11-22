#!/usr/bin/env python3
"""Actual received 2026 Crown cross-market snapshot sequence; read-only SQLite + SHA raw.

Strict same-HTTP receipt: only observed as of received time and before kickoff.
No assumption of quote event time alone being a received executable historical quote.
"""
import collections,datetime as dt,hashlib,json,math,sqlite3,statistics
from pathlib import Path
from zoneinfo import ZoneInfo

DB=Path("/Users/mac/QuantAsiaDesk/data/crown_quote_store/crown_quotes.sqlite3")
OUT=Path(__file__).with_name("real_receipt_information_lead_r4_results.json")
counts=collections.Counter()
def utc(s):
    v=dt.datetime.fromisoformat(str(s).replace("Z","+00:00").replace(" ","T"))
    return v.astimezone(dt.timezone.utc) if v.tzinfo else v.replace(tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(dt.timezone.utc)
def read_q(z,sides,recv,ko,expected_line):
    if not isinstance(z,dict):return None
    try:
        t=utc(z["time"])
        v=tuple(float(z[s]) for s in sides)
        if t>recv or t>=ko or min(v)<=1 or not all(math.isfinite(k) for k in v):
            return None
        if expected_line:
            line=float(z["line"])
            if abs(line*4-round(line*4))>1e-6:return None
            return dict(value=(line,*v),event=t.isoformat())
        return dict(value=v,event=t.isoformat())
    except (KeyError,TypeError,ValueError,OverflowError):return None
def latest(b,field,sides,recv,ko,line=False):
    options=[read_q(z,sides,recv,ko,line) for tag,z in (b.get(field) or {}).items() if tag in ("open","close")]
    options=[z for z in options if z]
    return max(options,key=lambda x:x["event"]) if options else None
c=sqlite3.connect("file:"+str(DB)+"?mode=ro",uri=True)
c.row_factory=sqlite3.Row
Q=("select * from capture where data_layer='summary' and capture_mode='live' "
   "and prospective_observation=1 and status='QUOTES_SAVED' order by response_received_at_utc")
captures=[dict(r) for r in c.execute(Q)]
rawrows=collections.defaultdict(list)
hashes=set()
for r in captures:
    fid=str(r["fixture_id"])
    path=Path(r["source_file"])
    if not path.is_file():counts["missing_raw"]+=1;continue
    content=path.read_bytes()
    sha=hashlib.sha256(content).hexdigest()
    if sha!=r["response_sha256"]:counts["bad_sha"]+=1;continue
    hashes.add(sha)
    o=json.loads(content)
    x=next((z for z in o.get("data",[]) if str(z.get("id"))==fid),None)
    if not x:counts["missing_fixture_id"]+=1;continue
    books=[b for b in x.get("bookmakers",[]) if b.get("slug")=="crown"]
    if len(books)!=1:counts["invalid_crown_count"]+=1;continue
    b=books[0]
    rec=utc(r["response_received_at_utc"]);ko=utc(r["kickoff_at_utc"])
    if rec>=ko:counts["received_at_or_after_kickoff"]+=1;continue
    q={}
    for name,field,sides,line in (
        ("AH","asian",("home","away"),True),
        ("OU","goal",("over","under"),True),
        ("1X2","odds",("home","draw","away"),False)
    ):
        q[name]=latest(b,field,sides,rec,ko,line)
        if q[name] is not None: counts["valid_"+name]+=1
    rawrows[fid].append(dict(received=rec,ko=ko,quote=q,sha=sha))
    counts["read_verified_live_snapshot"]+=1
    if (ko-rec).total_seconds()>=10*3600:counts["received_at_least_10h"]+=1
    if (ko-rec).total_seconds()>=12*3600:counts["received_at_least_12h"]+=1
    if (ko-rec).total_seconds()>=20*3600:counts["received_at_least_20h"]+=1

age={k:[] for k in ("AH","OU","1X2")}
fresho={k:[] for k in ("AH","OU","1X2")}
lead=collections.Counter()
for fid,rs in rawrows.items():
    rs.sort(key=lambda x:x["received"])
    if len(rs)>1:lead["multi_received_fixture"]+=1
    if any((r["ko"]-r["received"]).total_seconds()>=10*3600 for r in rs):
        lead["received_10h_fixture"]+=1
    for r in rs:
        for name in age:
            q=r["quote"][name]
            if q:
                v=(r["received"]-utc(q["event"])).total_seconds()/60
                if v<0:raise ValueError("Future quote source time")
                age[name].append(v)
                fresho[name].append(v<=60)
    # Compare distinct, actual received complete snapshots; no claim if both markets move
    # between the same two receptions.
    qchanges={k:[] for k in age}
    for i in range(1,len(rs)):
        last,now=rs[i-1],rs[i]
        changed=[]
        for k in age:
            a,b=last["quote"][k],now["quote"][k]
            if a and b and a["value"]!=b["value"]:
                qchanges[k].append(i)
                changed.append(k)
        if len(changed)>1:lead["same_observed_interval_multi_market_change"]+=1
        if changed==["1X2"]:lead["1X2_only_changed_between_two_received"]+=1
        if changed==["AH"]:lead["AH_only_changed_between_two_received"]+=1
        if changed==["OU"]:lead["OU_only_changed_between_two_received"]+=1
    if qchanges["AH"]:lead["observed_AH_repriced_fixture"]+=1
    if qchanges["OU"]:lead["observed_OU_repriced_fixture"]+=1
    if qchanges["1X2"]:lead["observed_1X2_repriced_fixture"]+=1
    if qchanges["1X2"] and qchanges["AH"]:
        if min(qchanges["1X2"])<min(qchanges["AH"]):lead["first_1X2_received_change_before_AH_change"]+=1
        if min(qchanges["AH"])<min(qchanges["1X2"]):lead["first_AH_received_change_before_1X2_change"]+=1
        if min(qchanges["AH"])==min(qchanges["1X2"]):lead["same_interval_first_1X2_AH_change"]+=1
    if qchanges["OU"] and qchanges["AH"]:
        if min(qchanges["OU"])<min(qchanges["AH"]):lead["first_OU_received_change_before_AH_change"]+=1
        if min(qchanges["AH"])<min(qchanges["OU"]):lead["first_AH_received_change_before_OU_change"]+=1
        if min(qchanges["AH"])==min(qchanges["OU"]):lead["same_interval_first_OU_AH_change"]+=1

res=dict(created_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    total_summary_live_capture_rows=len(captures),
    validated_receipts=counts["read_verified_live_snapshot"],
    distinct_fixture_ids=len(rawrows),
    distinct_raw_response_sha=len(hashes),
    last_actual_receipt_utc=max([v["received"] for rs in rawrows.values() for v in rs]).isoformat() if rawrows else None,
    source="read-only current local Crown SQLite true live received capture source path and SHA256 verified raw HTTP responses",
    counts=dict(counts),lead_observation=dict(lead),
    quote_source_age_minutes={
        k:dict(n=len(v),median=round(statistics.median(v),2),
               p90=round(sorted(v)[int((len(v)-1)*.9)],2),
               actual_receive_with_source_age_le_60m=int(sum(x<=60 for x in v)))
        for k,v in age.items()},
    caveats=[
        "Each snapshot may repeat stale open/close quote. Observed within-receipt changes do not identify when source quote became available to the user.",
        "Only separate actual received snapshots can order which market was observed repricing first. Same-received-interval changes are unordered.",
        "Observed early lead of 10-20h is extremely sparse. This does not support building a continuously trained early price discovery signal.",
        "No real betting or settlement accounting has been changed."
    ])
assert counts["bad_sha"]==0 and counts["received_at_or_after_kickoff"]==0
OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(res,ensure_ascii=False,indent=2))
