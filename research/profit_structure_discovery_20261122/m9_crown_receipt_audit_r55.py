#!/usr/bin/env python3
"""Read-only production M9 Crown receipt / score settlement evidence audit."""
import json,collections,hashlib,datetime as dt,math
from pathlib import Path
from research.m3.probabilities import settle_score
ROOT=Path.home()/"QuantAsiaDesk"
LEDGER=ROOT/"state/m9_formal_events.jsonl"
HISTORY=ROOT/"repos/m1/data/m1_history_cache"
OUT=Path(__file__).with_name("M9_CROWN_RECEIPT_AUDIT_R55.json")
events=[json.loads(s) for s in LEDGER.read_text().splitlines() if s.strip()]
orders=collections.defaultdict(dict)
for event in events:
 if event.get("order_key"):orders[event["order_key"]][event["kind"]]=event
count=collections.Counter();fail=[];rows=[];leagues=collections.Counter()
for key,ev in orders.items():
 sent=ev.get("M9_TG_SENT")
 if not sent:continue
 count["telegram_sent"]+=1
 prep=ev.get("M9_PREPARED");settled=ev.get("M9_SETTLED")
 if settled:count["settled"]+=1
 if not prep:fail.append({"order":key,"reason":"missing_prepared"});continue
 quote=prep.get("crown") or {};raw=Path(quote.get("raw_path",""))
 if not raw.is_file() or hashlib.sha256(raw.read_bytes()).hexdigest()!=quote.get("raw_sha256"):
  fail.append({"order":key,"reason":"raw_missing_or_hash_mismatch"});continue
 count["crown_hash_verified"]+=1
 try:
  source=dt.datetime.fromisoformat(quote["source_at"]);received=dt.datetime.fromisoformat(quote["received_at"])
  kickoff=dt.datetime.fromisoformat(prep["kickoff_utc"]);sent_at=dt.datetime.fromisoformat(sent["at_utc"])
  if not source<=received<=sent_at<kickoff:raise ValueError("time order")
  count["crown_time_verified"]+=1
  lid=str(prep["league_id"]);hist=json.loads((HISTORY/(lid+".json")).read_text())
  matches=[x for x in hist["rows"] if str(x.get("id"))==str(prep["fid"])]
  if len(matches)!=1:raise ValueError("fixture identity")
  count["historical_fixture_matched"]+=1
  leagues[lid]+=1
  r={"id":str(prep["fid"]),"league_id":lid,"sent_at":sent_at.isoformat(),"received_at":received.isoformat(),
     "kickoff":kickoff.isoformat(),"line":prep["line"],"side":prep["side"],"decimal":prep["decimal_odd"],
     "settled":bool(settled)}
  if settled:
   state,pnl=settle_score("AH",prep["line"],prep["side"],int(settled["home_goals"]),int(settled["away_goals"]),float(prep["decimal_odd"]))
   r.update({"state":settled["state"],"pnl_u":settled["pnl_u"],"recomputed_state":state,"recomputed_pnl_u":pnl})
   if not math.isclose(float(pnl),float(settled["pnl_u"]),abs_tol=1e-7):
    fail.append({"order":key,"reason":"settlement_pnl_mismatch","computed":pnl,"ledger":settled["pnl_u"]})
   else:count["settlement_pnl_verified"]+=1
  rows.append(r)
 except Exception as e:fail.append({"order":key,"reason":str(e)})
states=collections.Counter(r.get("state") for r in rows if r["settled"])
pnl=sum(float(r["pnl_u"]) for r in rows if r["settled"])
out={"source":str(LEDGER),"audit_generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
"counts":dict(count),"settled_states":dict(states),"settled_pnl_u":pnl,
"settled_roi_percent":100*pnl/count["settled"] if count["settled"] else None,
"unsettled":count["telegram_sent"]-count["settled"],"leagues":dict(leagues),"failures":fail,
"limitations":["Formal recent M9 Telegram sample, not same as R54 historical 3386 fixtures.","Verified quote receipt timestamps support production orders, not historical replay prices for unrelated matches.","No original-versus-residual-enhanced M9 score-grid forecasts saved at the actual historical send time; no valid challenger ROI comparison yet.","Historical cache is a latest snapshot; fixture ID match does not prove past as-of model input availability.","Read-only: no formal Telegram, production code or ledger modification."]}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:out[k] for k in ("counts","settled_states","settled_pnl_u","settled_roi_percent","unsettled","failures")},ensure_ascii=False,indent=2))
