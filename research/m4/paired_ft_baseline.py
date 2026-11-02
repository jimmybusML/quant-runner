#!/usr/bin/env python3
"""M4 read-only paired MR1 forward/FT evaluation. Run inside checkout of MR1 state."""
import json, pathlib, collections, datetime
R=pathlib.Path("data/mr1-v6-cross-market")
F=R/"forward/records"
FT=pathlib.Path("data/strategy-shadow-ledger/results")
OUT=pathlib.Path("m4_paired_research.json")
def parse(s):
 try:return datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
 except (AttributeError,ValueError):return None
def get(row,market):
 e=row.get("evaluation",{})
 if not isinstance(e,dict) or e.get("status")!="ok":return None
 v=e.get(market,{})
 if not isinstance(v,dict):return None
 return v.get("selected")
def settlement(side,line,price,hg,ag,market):
 if side not in (("home","away") if market=="AH" else ("over","under")):return None
 try:line=float(line);price=float(price)
 except (TypeError,ValueError):return None
 if price<=1 or abs(line*4-round(line*4))>1e-8:return None
 # Side-relative Asian handicap lines; OU line is total threshold.
 if abs(line*2-round(line*2))<1e-8:parts=[line,line]
 else:parts=[int(line*2//1)/2, int(line*2//1)/2+0.5]
 outcome=0
 for part in parts:
  delta=(hg-ag if side=="home" else ag-hg)+part if market=="AH" else (hg+ag-part)*(1 if side=="over" else -1)
  outcome+=(price-1 if delta>1e-9 else -1 if delta< -1e-9 else 0)/2
 return outcome
results={}
for f in FT.glob("*.json"):
 try:
  x=json.loads(f.read_text())
  if x.get("status")=="FT" and str(x.get("match_id"))==f.stem and all(isinstance(x.get(z),int) and x[z]>=0 for z in ("home_goals","away_goals")):
   results[f.stem]=x
 except (OSError,ValueError):continue
group=collections.defaultdict(list);counts=collections.Counter(); inventory=collections.defaultdict(lambda:{"files":0,"matches":set()}); valid_leagues=collections.defaultdict(set)
for f in F.glob("*.json"):
 counts["forward_files"]+=1
 match=f.name.split("-")[0];ft=results.get(match)
 try:x=json.loads(f.read_text())
 except (OSError,ValueError):counts["bad_json"]+=1;continue
 lname=str(x.get("league") or "UNKNOWN");inventory[lname]["files"]+=1;inventory[lname]["matches"].add(match)
 if not ft:continue
 kickoff=parse(x.get("kickoff_at"));received=parse(x.get("received_at"));observed=parse(ft.get("observed_at"))
 if not kickoff or not received or received>=kickoff or not observed or observed<=kickoff:
  counts["invalid_time"]+=1;continue
 if x.get("source_bookmaker")!="crown" or x.get("source_bookmaker_verified") is not True:
  counts["unverified_crown"]+=1;continue
 if str(x.get("match_id"))!=match:counts["wrong_identity"]+=1;continue
 counts["paired_valid_forward"]+=1
 group[match].append((x,ft));valid_leagues[lname].add(match)
agg=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"positive_ev_n":0})
league=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"positive_ev_n":0})
def add(d,key,pnl,ev):
 z=d[key];z["n"]+=1;z["pnl"]+=pnl;z["positive_ev_n"]+=int(ev>0) if isinstance(ev,(float,int)) else 0
# Same-match multi-horizon comparison: one record per match per horizon/market.
for match,entries in group.items():
 for market in ("AH","OU"):
  seen=set()
  for x,ft in sorted(entries,key=lambda p:p[0].get("received_at","")):
   h=x.get("horizon")
   if h in seen:continue
   c=get(x,market)
   if not c:continue
   side=c.get("side");line=c.get("line");price=c.get("price")
   p=settlement(side,line,price,ft["home_goals"],ft["away_goals"],market)
   if p is None:counts["invalid_contract"]+=1;continue
   seen.add(h)
   add(agg,(market,h),p,c.get("EV"))
   add(league,(str(x.get("league") or "UNKNOWN"),market,h),p,c.get("EV"))
   counts["settled_counterfactual_records"]+=1
   # This is synthetic replay of saved historical model choices, not real trades.
def formatted(d):
 return {("|".join(map(str,k)) if isinstance(k,tuple) else str(k)):{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"positive_ev_count":v["positive_ev_n"]} for k,v in sorted(d.items()) if v["n"]}

# One independent fixture, one retrospective quote per market: latest valid received_at before kickoff.
# This is a research replay, not the formal MR1 Telegram selection algorithm.
unique=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"win":0,"loss":0,"push":0,"half_win":0,"half_loss":0,"positive_ev_n":0})
unique_league=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"win":0,"loss":0,"push":0,"half_win":0,"half_loss":0,"positive_ev_n":0})
by_fixture={}
for match,entries in group.items():
 for market in ("AH","OU"):
  for x,ft in sorted(entries,key=lambda q:q[0].get("received_at",""),reverse=True):
   c=get(x,market)
   if not c:continue
   p=settlement(c.get("side"),c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],market)
   if p is None:continue
   league_name=str(x.get("league") or "UNKNOWN")
   neutral=settlement(c.get("side"),c.get("line"),2.0,ft["home_goals"],ft["away_goals"],market)
   classification="push" if abs(neutral)<1e-10 else "win" if neutral>0.75 else "half_win" if neutral>0 else "loss" if neutral< -0.75 else "half_loss"
   for d,key in ((unique,market),(unique_league,(league_name,market))):
    z=d[key];z["n"]+=1;z["pnl"]+=p;z[classification]+=1
    z["positive_ev_n"]+=int(isinstance(c.get("EV"),(int,float)) and c["EV"]>0)
   by_fixture[(match,market)]={"horizon":x.get("horizon"),"league":league_name,"pnl":round(p,6)}
   break
def unique_formatted(d):
 return {("|".join(map(str,k)) if isinstance(k,tuple) else str(k)):{**{field:v[field] for field in ("n","win","loss","push","half_win","half_loss","positive_ev_n")},"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6)} for k,v in sorted(d.items()) if v["n"]}

# M4-A diagnostic: model-estimated EV versus realized unit return, based on one
# independently settled fixture/market. Beijing hour is an observation, not
# an approved dispatch schedule. All divisions are descriptive only.
diagnostic=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"ev_n":0,"estimated_ev_sum":0.0,"quote_age_n":0,"quote_age_sum":0.0,"quote_age_min":None,"quote_age_max":None})
def diagnostic_add(key,pnl,ev,age):
 z=diagnostic[key];z["n"]+=1;z["pnl"]+=pnl
 if isinstance(ev,(int,float)):
  z["ev_n"]+=1;z["estimated_ev_sum"]+=ev
 if isinstance(age,(int,float)) and age>=0:
  z["quote_age_n"]+=1;z["quote_age_sum"]+=age
  z["quote_age_min"]=age if z["quote_age_min"] is None else min(z["quote_age_min"],age)
  z["quote_age_max"]=age if z["quote_age_max"] is None else max(z["quote_age_max"],age)
for match,entries in group.items():
 for market in ("AH","OU"):
  selected=None
  for x,ft in sorted(entries,key=lambda q:q[0].get("received_at",""),reverse=True):
   c=get(x,market)
   if not c:continue
   p=settlement(c.get("side"),c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],market)
   if p is not None:selected=(x,c,p);break
  if selected is None:continue
  x,c,p=selected
  age=x.get("quote_ages_minutes",{}).get(market)
  ev=c.get("EV")
  hour=parse(x["received_at"]).astimezone(datetime.timezone(datetime.timedelta(hours=8))).hour
  diagnostic_add((market,"overall"),p,ev,age)
  diagnostic_add((market,"league",str(x.get("league") or "UNKNOWN")),p,ev,age)
  line_value=c.get("line")
  if isinstance(line_value,(int,float)):
   diagnostic_add((market,"line",str(line_value)),p,ev,age)
  diagnostic_add((market,"side",str(c.get("side"))),p,ev,age)
  diagnostic_add((market,"beijing_hour",str(hour)),p,ev,age)
  if isinstance(age,(int,float)):
   age_band="<30m" if age<30 else "30-60m" if age<60 else "60-120m" if age<120 else ">=120m"
   diagnostic_add((market,"quote_age",age_band),p,ev,age)
  if isinstance(ev,(int,float)):
   ev_band="< -0.05" if ev<-.05 else "-0.05 to 0" if ev<0 else "0 to 0.05" if ev<.05 else ">= 0.05"
   diagnostic_add((market,"model_ev",ev_band),p,ev,age)
def diagnostic_formatted():
 return {"|".join(map(str,k)):{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"model_ev_n":v["ev_n"],"mean_estimated_ev":round(v["estimated_ev_sum"]/v["ev_n"],6) if v["ev_n"] else None,"realized_minus_estimated_ev":round(v["pnl"]/v["n"]-v["estimated_ev_sum"]/v["ev_n"],6) if v["ev_n"]==v["n"] else None,"mean_quote_age_min":round(v["quote_age_sum"]/v["quote_age_n"],2) if v["quote_age_n"] else None} for k,v in sorted(diagnostic.items())}


# Fixed Beijing clock replay: for every hour 0..23, each fixture/market contributes
# at most one result, using its latest snapshot available by the most recent daily
# decision clock strictly before kickoff. This is a historical observability
# replay, not a simulated real-world snapshot acquisition at that clock.
daily=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"ev_n":0,"ev_sum":0.0,"age_sum":0.0,"age_n":0})
local_tz=datetime.timezone(datetime.timedelta(hours=8))
for match,entries in group.items():
 kickoff=parse(entries[0][0].get("kickoff_at"))
 if not kickoff:continue
 kickoff_local=kickoff.astimezone(local_tz)
 for hour in range(24):
  cutoff=kickoff_local.replace(hour=hour,minute=0,second=0,microsecond=0)
  if cutoff>=kickoff_local:cutoff-=datetime.timedelta(days=1)
  for market in ("AH","OU"):
   candidates=[]
   for x,ft in entries:
    received=parse(x.get("received_at"))
    if received and received<=cutoff:
     c=get(x,market)
     if c:
      pnl=settlement(c.get("side"),c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],market)
      if pnl is not None:candidates.append((received,x,c,pnl))
   if not candidates:continue
   received,x,c,pnl=max(candidates,key=lambda z:z[0])
   z=daily[(market,hour)];z["n"]+=1;z["pnl"]+=pnl
   if isinstance(c.get("EV"),(int,float)):z["ev_n"]+=1;z["ev_sum"]+=c["EV"]
   age=x.get("quote_ages_minutes",{}).get(market)
   if isinstance(age,(int,float)) and age>=0:z["age_n"]+=1;z["age_sum"]+=age
def daily_formatted():
 return {"|".join(map(str,k)):{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"mean_model_ev":round(v["ev_sum"]/v["ev_n"],6) if v["ev_n"] else None,"mean_quote_age_min":round(v["age_sum"]/v["age_n"],2) if v["age_n"] else None} for k,v in sorted(daily.items()) if v["n"]}


# M4-A probability-grid root-cause audit: 1X2-implied goal means versus FT.
# Independent fixture only, separated by selected OU side; original model formulas unchanged.
root=collections.defaultdict(lambda:{"n":0,"actual_total":0.0,"predicted_total":0.0,"ou_line":0.0,"pnl":0.0,"predicted_ev":0.0,"under":0,"over":0})
for match,entries in group.items():
 chosen=None
 for x,ft in sorted(entries,key=lambda z:z[0].get("received_at",""),reverse=True):
  c=get(x,"OU")
  if not c:continue
  p=settlement(c.get("side"),c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],"OU")
  val=x.get("evaluation",{}).get("one_x_two",{}).get("tau_market")
  if p is not None and isinstance(val,(int,float)) and val>0:
   chosen=(x,ft,c,p,val);break
 if not chosen:continue
 x,ft,c,p,tau=chosen
 for key in ("all",str(c.get("side"))):
  z=root[key];z["n"]+=1;z["actual_total"]+=ft["home_goals"]+ft["away_goals"]
  z["predicted_total"]+=tau;z["ou_line"]+=float(c["line"]);z["pnl"]+=p
  z["predicted_ev"]+=float(c["EV"]);z["under"]+=int(c["side"]=="under");z["over"]+=int(c["side"]=="over")
def root_formatted():
 return {k:{"n":v["n"],"mean_actual_goals":round(v["actual_total"]/v["n"],5),"mean_1x2_predicted_goals":round(v["predicted_total"]/v["n"],5),"actual_minus_1x2_goals":round((v["actual_total"]-v["predicted_total"])/v["n"],5),"mean_crown_ou_line":round(v["ou_line"]/v["n"],5),"mean_predicted_ev":round(v["predicted_ev"]/v["n"],6),"realized_roi":round(v["pnl"]/v["n"],6)} for k,v in root.items() if v["n"]}


# M4 chronological expanding-window tau calibration; no future label leakage.
# Fixed candidate: additive correction equals mean completed training actual-minus-tau.
# Use observed FT timestamp to ensure each training label existed before decision.
import math
def poisson_ou_ev(tau,line,price,side):
 if tau<=0 or price<=1:return None
 p=math.exp(-tau); probs=[p]
 for k in range(1,31):
  p=p*tau/k;probs.append(p)
 return sum(w*settlement(side,line,price,k,0,"OU") for k,w in enumerate(probs))
cal_rows=[]
for match,entries in group.items():
 for x,ft in sorted(entries,key=lambda q:q[0].get("received_at",""),reverse=True):
  ev=x.get("evaluation",{})
  tau=ev.get("one_x_two",{}).get("tau_market")
  ou=ev.get("OU",{})
  sides=ou.get("all_sides",[])
  if not isinstance(tau,(int,float)) or not isinstance(sides,list) or len(sides)<2:continue
  candidate={}
  for c in sides:
   if not isinstance(c,dict):continue
   side=c.get("side")
   if side not in ("under","over"):continue
   pnl=settlement(side,c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],"OU")
   if pnl is not None:candidate[side]={"pnl":pnl,"line":c["line"],"price":c["price"],"saved_ev":c.get("EV")}
  if len(candidate)!=2:continue
  decision=parse(x.get("received_at"));finished=parse(ft.get("observed_at"))
  if not decision or not finished:continue
  cal_rows.append({"match":match,"decision":decision,"finished":finished,"tau":tau,"actual":ft["home_goals"]+ft["away_goals"],"sides":candidate})
  break
cal_rows.sort(key=lambda x:(x["decision"],x["match"]))
cal_rows=sorted({x["match"]:x for x in cal_rows}.values(),key=lambda x:(x["decision"],x["match"]))
baseline_pnl=0.0; calibrated_pnl=0.0; trained_n=0; valid_n=0; switches=0; mae_baseline=0.0;mae_adjusted=0.0
examples=[]
changes=collections.defaultdict(lambda:{"n":0,"original_pnl":0.0,"corrected_pnl":0.0,"gain":0.0})
for i,x in enumerate(cal_rows):
 history=[h for h in cal_rows[:i] if h["finished"]<x["decision"]]
 if not history:continue
 correction=sum(h["actual"]-h["tau"] for h in history)/len(history)
 corrected=max(.05,x["tau"]+correction)
 old_side=max(x["sides"],key=lambda side:x["sides"][side]["saved_ev"] if isinstance(x["sides"][side]["saved_ev"],(int,float)) else -999)
 adjusted_evs={side:poisson_ou_ev(corrected,c["line"],c["price"],side) for side,c in x["sides"].items()}
 new_side=max(adjusted_evs,key=adjusted_evs.get)
 valid_n+=1;trained_n+=len(history);switches+=int(new_side!=old_side)
 baseline_pnl+=x["sides"][old_side]["pnl"];calibrated_pnl+=x["sides"][new_side]["pnl"]
 gain=x["sides"][new_side]["pnl"]-x["sides"][old_side]["pnl"]
 month=x["decision"].strftime("%Y-%m")
 for key in ("all", "month|"+month, "switch|"+old_side+"_to_"+new_side,"period|"+("first_half" if i<len(cal_rows)//2 else "second_half")):
  z=changes[key];z["n"]+=1;z["original_pnl"]+=x["sides"][old_side]["pnl"];z["corrected_pnl"]+=x["sides"][new_side]["pnl"];z["gain"]+=gain
 mae_baseline+=abs(x["actual"]-x["tau"]);mae_adjusted+=abs(x["actual"]-corrected)
 if len(examples)<4:examples.append({"decision":x["decision"].isoformat(),"training_n":len(history),"correction":round(correction,4),"old_side":old_side,"new_side":new_side})
calibration_report={"candidate":"expanding_window_additive_tau_mean_residual_research_only","chronological_test_fixtures":valid_n,"mean_training_fixtures":round(trained_n/valid_n,2) if valid_n else None,"side_switches":switches,"original_same_fixture_pnl_units":round(baseline_pnl,4),"corrected_same_fixture_pnl_units":round(calibrated_pnl,4),"original_roi":round(baseline_pnl/valid_n,6) if valid_n else None,"corrected_roi":round(calibrated_pnl/valid_n,6) if valid_n else None,"original_mae_goals":round(mae_baseline/valid_n,5) if valid_n else None,"corrected_mae_goals":round(mae_adjusted/valid_n,5) if valid_n else None,"attribution":{k:{"n":v["n"],"original_pnl":round(v["original_pnl"],4),"corrected_pnl":round(v["corrected_pnl"],4),"gain":round(v["gain"],4),"original_roi":round(v["original_pnl"]/v["n"],6),"corrected_roi":round(v["corrected_pnl"]/v["n"],6)} for k,v in sorted(changes.items())},"examples":examples,"note":"No future outcomes used for correction; outcome availability checked using observed_at. Historical stored Crown quotes and original V6 research candidates, not formal TG. Candidate was proposed after inspecting this dataset, so this does not establish untouched holdout validity."}

output={"protocol":"M4_MR1_PAIRED_FT_READ_ONLY_V1","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"MR1 saved forward Crown quotes and TotalCorner FT records","unique_valid_paired_matches":len(group),"counts":dict(counts),"ou_goal_mean_root_cause":root_formatted(),"m4_chronological_tau_calibration":calibration_report,"m4_a_probability_price_diagnostics":diagnostic_formatted(),"daily_fixed_beijing_clock_replay":daily_formatted(),"one_per_fixture_market":unique_formatted(unique),"one_per_fixture_league_market":unique_formatted(unique_league),"one_per_fixture_counts":{"unique_fixtures_with_either_market":len({k[0] for k in by_fixture}),"AH":unique["AH"]["n"],"OU":unique["OU"]["n"]},"per_market_horizon":formatted(agg),"per_league_market_horizon":formatted(league),"league_inventory":{k:{"snapshot_files":v["files"],"unique_matches":len(v["matches"]),"valid_ft_matches":len(valid_leagues[k])} for k,v in sorted(inventory.items())},"note":"Retrospective counterfactual, not Telegram trades or out-of-sample M4 improvement. Same match repeated across horizons; each horizon independently counts at most one observation per match. No new gate or trade rules."}
OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(output,ensure_ascii=False))
