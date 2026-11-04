#!/usr/bin/env python3
"""Join independent M5 goal forecasts to the existing private verified Crown archive.

Public output is aggregate-only. Private MR1 predictions/ledger are not read;
only source-verified Crown quotes, fixture identity and post-kickoff verified FT
receipts are used. The saved MR1 selected side is read only for a same-quote
benchmark when that selection is embedded in the exact snapshot.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,unicodedata
import sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path

M3_CODES={"England Premier League":"E0","Germany Bundesliga":"D1","Belgium First Division A":"B1","Belgium Jupiler Pro League":"B1","France Ligue 1":"F1","Italy Serie A":"I1","Spain La Liga":"SP1"}
MODELS=("poisson","dixon_coles","bivariate_poisson")

def sha(b):return hashlib.sha256(b).hexdigest()
def instant(x):
 try:
  d=datetime.fromisoformat(str(x).replace("Z","+00:00"));return d.astimezone(timezone.utc) if d.tzinfo else None
 except (TypeError,ValueError):return None
def norm(x):
 return re.sub(r"[^a-z0-9]+","",unicodedata.normalize("NFKD",str(x or "")).encode("ascii","ignore").decode().lower())
def digest_json_set(values):return sha("\n".join(sorted(values)).encode())
def select_saved(snapshot,market):
 entry=(snapshot.get("evaluation") or {}).get(market) or {}
 return entry.get("selected") if isinstance(entry,dict) else None

def run(mr1_root:Path, forecasts_path:Path, m3_csv:Path|None, output:Path, source_timezone:str):
 repo_root=Path(__file__).resolve().parents[2]
 if str(repo_root) not in sys.path:sys.path.insert(0,str(repo_root))
 base=mr1_root/"data/prospective-market/shadow-v23"; index_path=base/"snapshot-index.jsonl"; reg_path=base/"fixtures.json"
 result_dir=mr1_root/"data/strategy-shadow-ledger/results"
 idx_raw=index_path.read_bytes(); reg_raw=reg_path.read_bytes(); registry=json.loads(reg_raw)
 forecast_raw=forecasts_path.read_bytes(); forecasts={}
 for line in forecast_raw.decode().splitlines():
  try:
   x=json.loads(line);forecasts[str(x["match_id"])]=x
  except Exception:continue
 verified_ft={}; ft_hashes=[]
 for p in result_dir.glob("*.json"):
  try:
   raw=p.read_bytes();x=json.loads(raw)
   if (x.get("status")=="FT" and str(x.get("match_id"))==p.stem and
       isinstance(x.get("home_goals"),int) and isinstance(x.get("away_goals"),int) and
       x["home_goals"]>=0 and x["away_goals"]>=0):
    verified_ft[p.stem]=x;ft_hashes.append(sha(raw))
  except Exception:continue
 mr1_records=defaultdict(list); mr1_record_hashes=[]
 forward_dir=mr1_root/"data/mr1-v6-cross-market/forward/records"
 for p in forward_dir.glob("*.json"):
  try:
   raw=p.read_bytes();record=json.loads(raw);mid=str(record.get("match_id") or "")
   if mid in forecasts and record.get("source_bookmaker")=="crown" and record.get("source_bookmaker_verified") is True:
    mr1_records[mid].append(record);mr1_record_hashes.append(sha(raw))
  except Exception:continue
 m3={}
 m3_raw=b""
 if m3_csv and m3_csv.exists():
  m3_raw=m3_csv.read_bytes()
  for row in csv.DictReader(m3_raw.decode().splitlines()):
   key=(row.get("league"),row.get("match_date_utc","")[:10],norm(row.get("home_team")),norm(row.get("away_team")))
   m3.setdefault(key,{})[row.get("model")]=row
 index_rows=defaultdict(list); stats=Counter(); snap_hashes=set(); api_hashes=set(); snap_stats={}
 for line in idx_raw.decode().splitlines():
  try: e=json.loads(line)
  except: stats["bad_index_json"]+=1;continue
  mid=str(e.get("match_id") or "")
  if mid not in forecasts:continue
  if e.get("classification")!="SNAPSHOT_OK":continue
  path=base/str(e.get("snapshot_path") or "")
  try:
   st=path.stat();snap_stats[path]=(st.st_size,st.st_mtime_ns);raw=path.read_bytes();s=json.loads(raw)
  except Exception:stats["unreadable_snapshot"]+=1;continue
  f=forecasts[mid]; reg=registry.get(mid,{})
  if s.get("match_id")!=mid or reg.get("match_id")!=mid:stats["identity_bad_id"]+=1;continue
  # Snapshot payloads omit team names; validate fixture identity against the
  # canonical MR1 registry, then require the snapshot to keep that same ID.
  if any(reg.get(k)!=f.get(k) for k in ("league","home","away")):
   stats["identity_team_league_mismatch"]+=1;continue
  ko=instant(f.get("kickoff")); snap_ko=instant(s.get("kickoff_at"));reg_ko=instant(reg.get("kickoff_at"))
  if not ko or snap_ko!=ko or reg_ko!=ko:stats["kickoff_mismatch"]+=1;continue
  if (int(f["home_goals"]),int(f["away_goals"]))!=(int(s.get("actual_home_goals",f["home_goals"])),int(s.get("actual_away_goals",f["away_goals"]))):
   stats["snapshot_ft_mismatch"]+=1;continue
  ft=verified_ft.get(mid)
  if not ft or (int(ft["home_goals"]),int(ft["away_goals"]))!=(int(f["home_goals"]),int(f["away_goals"])):stats["no_matching_verified_ft"]+=1;continue
  if instant(ft.get("observed_at")) is None or instant(ft.get("observed_at"))<=ko:stats["ft_not_observed_after_kickoff"]+=1;continue
  received=instant(s.get("received_at")); prediction_asof=instant(f.get("prediction_asof_utc"))
  if not received or received>=ko or not prediction_asof or received<prediction_asof:stats["bad_prediction_receipt_time"]+=1;continue
  if (s.get("source_bookmaker")!="crown" or s.get("source_bookmaker_verified") is not True or
      s.get("prematch_valid") is not True or s.get("classification")!="SNAPSHOT_OK"):
   continue
  snap_hashes.add(sha(raw)); observed_by_market={}
  for market in ("AH","OU"):
   q=s.get(market) or {}
   observed=instant(q.get("observed_at_utc") or q.get("observed_at"))
   if not observed or observed>=ko or observed>received or observed<prediction_asof or q.get("closed") is True:continue
   try:
    line=float(q["line"]); prices=(float(q["home_price"]),float(q["away_price"])) if market=="AH" else (float(q["over_price"]),float(q["under_price"]))
   except (TypeError,ValueError,KeyError):continue
   if not math.isfinite(line) or abs(line*4-round(line*4))>1e-8 or any(not math.isfinite(p) or p<=1 for p in prices):continue
   observed_by_market[market]={"observed":observed,"received":received,"line":line,"prices":prices,"snapshot":s,"snapshot_hash":sha(raw)}
  for market,q in observed_by_market.items():
   index_rows[(mid,market)].append((q,f,ft))
   stats[f"verified_{market}_snapshot_rows"]+=1
 # Direct Crown endpoint archives retain each provider source event timestamp.
 # Restrict them to fixtures with the same MR1-registered identity and a
 # separate post-kickoff verified FT receipt.
 crown_dir=Path("/Users/mac/QuantAsiaDesk/data/m5-crown-authorized/crown-responses")
 zone=ZoneInfo(source_timezone)
 for mid,f in forecasts.items():
  path=crown_dir/f"{mid}.json"
  if not path.exists():continue
  try:
   raw=path.read_bytes();payload=json.loads(raw);matches=[m for m in payload.get("data",[]) if isinstance(m,dict) and str(m.get("id"))==mid]
   books=[book for m in matches for book in (m.get("bookmakers") or []) if isinstance(book,dict) and book.get("slug")=="crown"]
   reg=registry.get(mid,{});ft=verified_ft.get(mid);ko=instant(f.get("kickoff"))
   if payload.get("success")!=1 or len(matches)!=1 or len(books)!=1 or not ko or len(reg)==0:continue
   match=matches[0]
   if any(reg.get(k)!=f.get(k) for k in ("league","home","away")):continue
   if (match.get("h"),match.get("a"),match.get("l"))!=(f["home"],f["away"],f["league"]):continue
   if instant(reg.get("kickoff_at"))!=ko or local_to_utc(match.get("start"),zone)!=ko:continue
   if (int(match.get("hg")),int(match.get("ag")))!=(int(f["home_goals"]),int(f["away_goals"])):continue
   if not ft or (int(ft["home_goals"]),int(ft["away_goals"]))!=(int(f["home_goals"]),int(f["away_goals"])) or instant(ft.get("observed_at")) is None or instant(ft.get("observed_at"))<=ko:continue
   prediction_asof=instant(f.get("prediction_asof_utc")); raw_hash=sha(raw); api_hashes.add(raw_hash)
   for market,list_key in (("AH","asian_list"),("OU","goal_list")):
    eligible=[]
    for movement in books[0].get(list_key) or []:
     if not isinstance(movement,list) or len(movement)!=8 or movement[0] is not None or movement[7] not in (0,"0",False):continue
     observed=local_to_utc(movement[4],zone)
     try:
      pieces=[float(x.strip()) for x in str(movement[1]).split(",")];line=sum(pieces)/len(pieces)
      prices=(float(movement[2]),float(movement[3]))
     except (TypeError,ValueError,ZeroDivisionError):continue
     if (not observed or observed<prediction_asof or observed>=ko or len(pieces) not in (1,2) or
         abs(line*4-round(line*4))>1e-8 or any(not math.isfinite(p) or p<=1 for p in prices)):continue
     eligible.append({"observed":observed,"received":observed,"line":line,"prices":prices,
                      "snapshot":None,"snapshot_hash":raw_hash,"source":"totalcorner_crown_historical_endpoint"})
    if eligible:
     q=max(eligible,key=lambda item:item["observed"]);index_rows[(mid,market)].append((q,f,ft));stats[f"verified_{market}_api_rows"]+=1
  except Exception:continue
 # latest one valid Crown observation per fixture-market, with stable tie-break by receipt time
 selected={}
 for key,records in index_rows.items():
  selected[key]=max(records,key=lambda rec:(rec[0]["observed"],rec[0]["received"]))
 from research.m5.m3_grid_crown_replay import expected_return,legs_result,payout
 output_markets={}
 for market in ("AH","OU"):
  entries=[]; favorite_entries=[]; outcomes=Counter(); favorite_outcomes=Counter(); by_year=defaultdict(list); by_quarter=defaultdict(list); favorite_by_quarter=defaultdict(list); by_league=defaultdict(list); m3same=defaultdict(list); m5same=[]; mr1same=[];proper=[]
  for (mid,mkt),(q,f,ft) in selected.items():
   if mkt!=market:continue
   grid=f["prediction"]["grid"];prices=q["prices"];line=q["line"]
   sides=("home","away") if market=="AH" else ("over","under")
   evs=[expected_return(grid,market,side,line,price) for side,price in zip(sides,prices)]
   side_idx=0 if evs[0]>=evs[1] else 1;side=sides[side_idx];price=prices[side_idx]
   hg,ag=int(f["home_goals"]),int(f["away_goals"]);legs,cat=legs_result(market,side,line,hg,ag);units=payout(legs,price)
   row={"observed":q["observed"],"mid":mid,"league":f["league"],"year":q["observed"].year,"units":units,"category":cat}
   entries.append(row);outcomes[cat]+=1;by_year[str(q["observed"].year)].append(units);by_league[f["league"]].append(units)
   quarter=f"{q['observed'].year}-Q{(q['observed'].month-1)//3+1}"
   by_quarter[quarter].append(row)
   # Same verified Crown contract and stake, but select the shorter-priced side
   # without looking at model probabilities. This is a descriptive baseline,
   # not a gate or a proposed production rule.
   favorite_idx=0 if prices[0]<=prices[1] else 1
   favorite_side=sides[favorite_idx];favorite_price=prices[favorite_idx]
   favorite_legs,favorite_category=legs_result(market,favorite_side,line,hg,ag)
   favorite_units=payout(favorite_legs,favorite_price)
   favorite_row={"observed":q["observed"],"mid":mid,"units":favorite_units,"category":favorite_category}
   favorite_entries.append(favorite_row);favorite_by_quarter[quarter].append(favorite_row)
   favorite_outcomes[favorite_category]+=1
   distribution=Counter()
   for gh,gridrow in enumerate(grid):
    for ga,prob in enumerate(gridrow):
     _legs,predicted_category=legs_result(market,side,line,gh,ga)
     distribution[predicted_category]+=float(prob)
   category_order=("win","half_win","push","half_loss","loss")
   predicted_p=max(distribution[cat],1e-15)
   proper.append((-math.log(predicted_p),sum((distribution[k]-(1.0 if k==cat else 0.0))**2 for k in category_order)))
   fields=("home","away") if market=="AH" else ("over","under")
   for record in mr1_records.get(mid,[]):
    rec_ko=instant(record.get("kickoff_at"));rec_received=instant(record.get("received_at"))
    rec_quote=instant((record.get("quote_times") or {}).get(market))
    if rec_ko!=ko or not rec_received or rec_received>=ko or rec_quote!=q["observed"] or rec_quote>rec_received:
     continue
    saved=select_saved(record,market)
    if not isinstance(saved,dict):continue
    try:
     saved_line=float(saved.get("line"));saved_price=float(saved.get("price"));saved_side=str(saved.get("side"))
     if (saved_side in fields and abs(saved_line-line)<1e-9 and
         abs(saved_price-prices[fields.index(saved_side)])<1e-9):
      sett=settle_saved(saved_side,line,saved_price,hg,ag,market)
      if sett:mr1same.append((q["observed"],sett[0]))
    except Exception:pass
   code=M3_CODES.get(f["league"]);key=(code,f["kickoff"][:10],norm(f["home"]),norm(f["away"]))
   modelrows=m3.get(key,{})
   if len(modelrows)==3 and line==(0.0 if market=="AH" else 2.5):
    m5same.append((q["observed"],units))
    for model in MODELS:
     r=modelrows.get(model,{})
     try:
      if market=="AH":
       probs=[float(r["ah_home_0_p_win"]),float(r["ah_home_0_p_push"]),float(r["ah_home_0_p_lose"])]
       side_values=[]
       for mside in sides:
        ep=0.0
        for cls,pb in zip(("win","push","loss"),probs):
         # Reuse tie-aware AH0 probabilities and the exact Crown price.
         if mside=="home": mult=(prices[0]-1 if cls=="win" else 0 if cls=="push" else -1)
         else: mult=(prices[1]-1 if cls=="loss" else 0 if cls=="push" else -1)
         ep+=pb*mult
        side_values.append(ep)
      else:
       over=float(r["ou_p_over_2_5"]);side_values=[over*(prices[0]-1)-(1-over), (1-over)*(prices[1]-1)-over]
      mside=sides[0] if side_values[0]>=side_values[1] else sides[1]
      if market=="AH":
       probwin=probs[0];probpush=probs[1];
       if mside=="home": unitsm=(prices[0]-1)*int(hg>ag)-int(hg<ag)
       else: unitsm=(prices[1]-1)*int(ag>hg)-int(ag<hg)
      else:
       unitsm=(prices[0]-1 if hg+ag>2.5 else -1) if mside=="over" else (prices[1]-1 if hg+ag<2.5 else -1)
      m3same[model].append((q["observed"],unitsm))
     except (KeyError,ValueError,TypeError):pass
  entries.sort(key=lambda r:(r["observed"],r["mid"]))
  equity=peak=dd=0.0
  for r in entries:
   equity+=r["units"];peak=max(peak,equity);dd=max(dd,peak-equity)
  favorite_equity=favorite_peak=favorite_dd=0.0
  for r in sorted(favorite_entries,key=lambda x:(x["observed"],x["mid"])):
   favorite_equity+=r["units"];favorite_peak=max(favorite_peak,favorite_equity);favorite_dd=max(favorite_dd,favorite_peak-favorite_equity)
  def time_bucket_summary(rows):
   ordered=sorted(rows,key=lambda x:(x["observed"],x["mid"]));counts=Counter(x["category"] for x in ordered)
   equity=peak=drawdown=0.0
   for item in ordered:
    equity+=item["units"];peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
   bucket_net=sum(x["units"] for x in ordered);bucket_n=len(ordered)
   return {"bets":bucket_n,"full_win":counts["win"],"half_win":counts["half_win"],"full_loss":counts["loss"],"half_loss":counts["half_loss"],"push":counts["push"],"net_units":round(bucket_net,6),"roi_pct":round(100*bucket_net/bucket_n,6) if bucket_n else None,"max_drawdown_units_by_quote_time":round(drawdown,6) if bucket_n else None}
  n=len(entries);net=sum(r["units"] for r in entries)
  output_markets[market]={"unique_forecast_fixtures":len(forecasts),"verified_quote_covered_fixtures":n,"simulated_bets":n,"settled_bets":n,"full_win":outcomes["win"],"half_win":outcomes["half_win"],"full_loss":outcomes["loss"],"half_loss":outcomes["half_loss"],"push":outcomes["push"],"net_units":round(net,6),"roi_pct":round(100*net/n,6) if n else None,"oos_roi_pct":round(100*net/n,6) if n else None,"max_drawdown_units_by_quote_time":round(dd,6) if n else None,
    "by_year":{y:{"bets":len(v),"net_units":round(sum(v),6),"roi_pct":round(100*sum(v)/len(v),6)} for y,v in sorted(by_year.items())},
    "by_quote_utc_quarter":{q:{"m5":time_bucket_summary(by_quarter[q]),"crown_short_price_side_baseline":time_bucket_summary(favorite_by_quarter[q])} for q in sorted(by_quarter)},
    "by_league":{k:{"bets":len(v),"net_units":round(sum(v),6),"roi_pct":round(100*sum(v)/len(v),6)} for k,v in sorted(by_league.items())},
    "settlement_log_loss":round(sum(x[0] for x in proper)/len(proper),8) if proper else None,
    "settlement_brier":round(sum(x[1] for x in proper)/len(proper),8) if proper else None,
    "same_quote_saved_MR1_selection":{"bets":len(mr1same),"net_units":round(sum(x[1] for x in mr1same),6),"roi_pct":round(100*sum(x[1] for x in mr1same)/len(mr1same),6) if mr1same else None},
    "same_quote_crown_short_price_side_baseline":{"bets":len(favorite_entries),"settled_bets":len(favorite_entries),"full_win":favorite_outcomes["win"],"half_win":favorite_outcomes["half_win"],"full_loss":favorite_outcomes["loss"],"half_loss":favorite_outcomes["half_loss"],"push":favorite_outcomes["push"],"net_units":round(sum(x["units"] for x in favorite_entries),6),"roi_pct":round(100*sum(x["units"] for x in favorite_entries)/len(favorite_entries),6) if favorite_entries else None,"max_drawdown_units_by_quote_time":round(favorite_dd,6) if favorite_entries else None},
    "same_quote_M5_on_M3_contract_fixtures":{"bets":len(m5same),"net_units":round(sum(x[1] for x in m5same),6),"roi_pct":round(100*sum(x[1] for x in m5same)/len(m5same),6) if m5same else None},
    "same_quote_M3_OOS_models":{model:{"bets":len(v),"net_units":round(sum(x[1] for x in v),6),"roi_pct":round(100*sum(x[1] for x in v)/len(v),6) if v else None} for model,v in sorted(m3same.items())}}
 # Guard against concurrent edits while hashing/replaying private read-only sources.
 if index_path.read_bytes()!=idx_raw or reg_path.read_bytes()!=reg_raw:raise RuntimeError("MR1 Crown archive index/registry changed during replay; rerun on a stable snapshot")
 for p,(size,mtime) in snap_stats.items():
  if p.stat().st_size!=size or p.stat().st_mtime_ns!=mtime:raise RuntimeError("MR1 Crown snapshot changed during replay; rerun on a stable snapshot")
 report={"protocol":"M5_MR1_VERIFIED_CROWN_COMMON_OOS_REPLAY_V1","generated_utc":datetime.now(timezone.utc).isoformat(),"forecast_sha256":sha(forecast_raw),"forecast_rows":len(forecasts),"MR1_snapshot_index_sha256":sha(idx_raw),"MR1_fixture_registry_sha256":sha(reg_raw),"MR1_verified_FT_receipts_sha256":digest_json_set(ft_hashes),"MR1_quote_snapshot_hash_set_sha256":digest_json_set(snap_hashes),"MR1_forward_record_sha256_set":digest_json_set(mr1_record_hashes),"TotalCorner_Crown_response_hash_set_sha256":digest_json_set(api_hashes),"strict_M3_OOS_csv_sha256":sha(m3_raw) if m3_raw else None,"market_quote_rows":dict(stats),"markets":output_markets,"method":"One unique M5 UTC-year OOS forecast per fixture; latest verified Crown source quote with observed<=received<kickoff and quote observed after prediction_asof; FT independently verified after kickoff; choose the side with higher model expected return and no EV gate; quarter-line split settlement; no duplicated fixture within each market.","limitations":["The source schedule universe is partial, not all 51 frozen scope leagues.","MR1 saved model selections are compared only when decision record, Crown quote source hash, market, line, price and event time match exactly.","M3 comparison is limited to same fixtures and exact AH0 or OU2.5 contracts where strict M3 probability fields exist.","This is retrospective research, not live results or a deployment recommendation."]}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n");print(json.dumps({"markets":{m:{k:v for k,v in d.items() if k in ('verified_quote_covered_fixtures','net_units','roi_pct','same_quote_saved_MR1_selection','same_quote_M3_OOS_models')} for m,d in output_markets.items()},"output":str(output)}))

def settle_saved(side,line,price,hg,ag,market):
 from research.m5.m3_grid_crown_replay import legs_result,payout
 legs,cat=legs_result(market,side,line,hg,ag);return payout(legs,price),cat

def main():
 p=argparse.ArgumentParser();p.add_argument('--mr1-root',type=Path,required=True);p.add_argument('--forecasts',type=Path,required=True);p.add_argument('--m3-csv',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-timezone',default='Asia/Shanghai');a=p.parse_args();run(a.mr1_root,a.forecasts,a.m3_csv,a.output,a.source_timezone)
if __name__=='__main__':main()
