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
switch_detail=[]
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
 if new_side!=old_side:switch_detail.append({"match":x["match"],"date":x["decision"].date().isoformat(),"old":old_side,"new":new_side,"gain":round(gain,5),"original_pnl":x["sides"][old_side]["pnl"],"corrected_pnl":x["sides"][new_side]["pnl"],"training_n":len(history),"correction":round(correction,5)})
 month=x["decision"].strftime("%Y-%m")
 for key in ("all", "month|"+month, "switch|"+old_side+"_to_"+new_side,"period|"+("first_half" if i<len(cal_rows)//2 else "second_half")):
  z=changes[key];z["n"]+=1;z["original_pnl"]+=x["sides"][old_side]["pnl"];z["corrected_pnl"]+=x["sides"][new_side]["pnl"];z["gain"]+=gain
 mae_baseline+=abs(x["actual"]-x["tau"]);mae_adjusted+=abs(x["actual"]-corrected)
 if len(examples)<4:examples.append({"decision":x["decision"].isoformat(),"training_n":len(history),"correction":round(correction,4),"old_side":old_side,"new_side":new_side})
calibration_report={"candidate":"expanding_window_additive_tau_mean_residual_research_only","chronological_test_fixtures":valid_n,"mean_training_fixtures":round(trained_n/valid_n,2) if valid_n else None,"side_switches":switches,"original_same_fixture_pnl_units":round(baseline_pnl,4),"corrected_same_fixture_pnl_units":round(calibrated_pnl,4),"original_roi":round(baseline_pnl/valid_n,6) if valid_n else None,"corrected_roi":round(calibrated_pnl/valid_n,6) if valid_n else None,"original_mae_goals":round(mae_baseline/valid_n,5) if valid_n else None,"corrected_mae_goals":round(mae_adjusted/valid_n,5) if valid_n else None,"switch_sensitivity":{"worst_to_best_gains":sorted((z["gain"] for z in switch_detail)),"top_positive_switches":sorted(switch_detail,key=lambda z:z["gain"],reverse=True)[:12],"over_to_under_all":[z for z in switch_detail if z["old"]=="over" and z["new"]=="under"],"gain_excluding_top_5_positive":round(sum(z["gain"] for z in switch_detail)-sum(sorted((z["gain"] for z in switch_detail),reverse=True)[:5]),5)},"attribution":{k:{"n":v["n"],"original_pnl":round(v["original_pnl"],4),"corrected_pnl":round(v["corrected_pnl"],4),"gain":round(v["gain"],4),"original_roi":round(v["original_pnl"]/v["n"],6),"corrected_roi":round(v["corrected_pnl"]/v["n"],6)} for k,v in sorted(changes.items())},"examples":examples,"note":"No future outcomes used for correction; outcome availability checked using observed_at. Historical stored Crown quotes and original V6 research candidates, not formal TG. Candidate was proposed after inspecting this dataset, so this does not establish untouched holdout validity."}


# Alternative OU research candidates: shrink raw chronological mean residual
# and market-line anchored tau. Compare on same fixture with prior FT only.
candidate_stats=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"changes":0})
for i,x in enumerate(cal_rows):
 history=[h for h in cal_rows[:i] if h["finished"]<x["decision"]]
 if not history:continue
 residual=sum(h["actual"]-h["tau"] for h in history)/len(history)
 old=max(x["sides"],key=lambda side:x["sides"][side]["saved_ev"] if isinstance(x["sides"][side]["saved_ev"],(int,float)) else -999)
 # Research variants only, no user-approved model coefficient or production rules.
 anchor=x["sides"]["under"]["line"]
 candidates={"original_v6":x["tau"],"tau_full_correction":max(.05,x["tau"]+residual),
             "tau_half_correction":max(.05,x["tau"]+residual*.5),
             "tau_market_line_half_blend":max(.05,(x["tau"]+anchor)/2),
             "tau_market_line_full_anchor":max(.05,anchor)}
 for name,tau in candidates.items():
  ev={side:poisson_ou_ev(tau,c["line"],c["price"],side) for side,c in x["sides"].items()}
  chosen=max(ev,key=ev.get)
  z=candidate_stats[name];z["n"]+=1;z["pnl"]+=x["sides"][chosen]["pnl"];z["changes"]+=int(chosen!=old)
def candidate_formatted():
 return {k:{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"changed_directions":v["changes"]} for k,v in sorted(candidate_stats.items()) if v["n"]}


# Distribution-calibration alternatives: Poisson vs negative-binomial variance
# at identical estimated mean. Dispersion candidate parameters are research
# choices, not production rules; prior completion only for tau residual.
def negative_binomial_ou_ev(tau,line,price,side,shape):
 if tau<=0 or price<=1:return None
 prob=shape/(shape+tau)
 pmf=prob**shape
 ans=pmf*settlement(side,line,price,0,0,"OU")
 for k in range(1,51):
  pmf*=((k-1+shape)/k)*(1-prob)
  ans+=pmf*settlement(side,line,price,k,0,"OU")
 return ans
dist_stats=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"switches":0,"logloss":0.0})
for i,x in enumerate(cal_rows):
 history=[h for h in cal_rows[:i] if h["finished"]<x["decision"]]
 if not history:continue
 correction=sum(h["actual"]-h["tau"] for h in history)/len(history)
 means={"original":x["tau"],"chronological_mean_corrected":max(.05,x["tau"]+correction)}
 old=max(x["sides"],key=lambda side:x["sides"][side]["saved_ev"] if isinstance(x["sides"][side]["saved_ev"],(int,float)) else -999)
 for mname,tau in means.items():
  for distribution,shape in (("poisson",None),("negative_binomial_k2",2.0),("negative_binomial_k5",5.0),("negative_binomial_k10",10.0)):
   if shape:
    ev={side:negative_binomial_ou_ev(tau,c["line"],c["price"],side,shape) for side,c in x["sides"].items()}
    k=x["actual"];p0=(shape/(shape+tau))**shape
    p=p0
    for t in range(1,k+1):p*=((t-1+shape)/t)*(tau/(shape+tau))
   else:
    ev={side:poisson_ou_ev(tau,c["line"],c["price"],side) for side,c in x["sides"].items()}
    p=math.exp(-tau)*tau**x["actual"]/math.factorial(x["actual"])
   chosen=max(ev,key=ev.get);z=dist_stats[(mname,distribution)]
   z["n"]+=1;z["pnl"]+=x["sides"][chosen]["pnl"];z["switches"]+=int(chosen!=old);z["logloss"]-=math.log(max(1e-300,p))
def dist_formatted():
 return {"|".join(k):{"n":v["n"],"roi":round(v["pnl"]/v["n"],6),"pnl_units":round(v["pnl"],4),"direction_changes":v["switches"],"mean_goal_logloss":round(v["logloss"]/v["n"],6)} for k,v in sorted(dist_stats.items()) if v["n"]}


# Crown 1X2 + Crown OU joint information experiment.
# Infer OU-implied Poisson total-goal mean from equality of quoted expected
# returns across the two opposing OU contracts (bookmaker margin cancels).
# Compare convex blends of that mean with 1X2-implied tau at identical quotes.
joint=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"switches":0,"goal_logloss":0.0,"tau_gap_sum":0.0})
def infer_ou_tau(sides):
 def imbalance(tau):
  a=sides["over"];b=sides["under"]
  return poisson_ou_ev(tau,a["line"],a["price"],"over")-poisson_ou_ev(tau,b["line"],b["price"],"under")
 lo=.05;hi=12.0
 if imbalance(lo)*imbalance(hi)>0:return None
 for _ in range(42):
  mid=(lo+hi)/2
  if imbalance(mid)>0:hi=mid
  else:lo=mid
 return (lo+hi)/2
for x in cal_rows:
 inferred=infer_ou_tau(x["sides"])
 if inferred is None:continue
 old=max(x["sides"],key=lambda side:x["sides"][side]["saved_ev"] if isinstance(x["sides"][side]["saved_ev"],(int,float)) else -999)
 for name,weight in (("one_x_two_only",0),("joint_25pct_ou",.25),("joint_50pct_ou",.5),("joint_75pct_ou",.75),("ou_only",1)):
  tau=(1-weight)*x["tau"]+weight*inferred
  ev={side:poisson_ou_ev(tau,c["line"],c["price"],side) for side,c in x["sides"].items()}
  if abs(ev["over"]-ev["under"])<1e-8:continue # Price-implied OU fair mean has no directional edge; do not turn numerical ties into pseudo-trades.
  selected=max(ev,key=ev.get)
  z=joint[name];z["n"]+=1;z["pnl"]+=x["sides"][selected]["pnl"]
  z["switches"]+=int(selected!=old)
  z["goal_logloss"]-=(-tau+x["actual"]*math.log(tau)-math.lgamma(x["actual"]+1))
  z["tau_gap_sum"]+=inferred-x["tau"]
def joint_formatted():
 return {k:{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"direction_changes":v["switches"],"goal_logloss":round(v["goal_logloss"]/v["n"],6),"mean_ou_implied_minus_1x2_tau":round(v["tau_gap_sum"]/v["n"],6)} for k,v in sorted(joint.items()) if v["n"]}


# Signed cross-market disagreement diagnostic: infer OU-side fair tau,
# measure realized total-goal residual and original strategy PnL by gap.
gap_groups=collections.defaultdict(lambda:{"n":0,"total_gap":0.0,"goal_residual":0.0,"pnl":0.0,"under":0})
for x in cal_rows:
 inferred=infer_ou_tau(x["sides"])
 if inferred is None:continue
 gap=inferred-x["tau"]
 selected=max(x["sides"],key=lambda side:x["sides"][side]["saved_ev"] if isinstance(x["sides"][side]["saved_ev"],(int,float)) else -999)
 bucket="negative" if gap<0 else "0_to_0.1" if gap<.1 else "0.1_to_0.2" if gap<.2 else "0.2_to_0.4" if gap<.4 else ">=0.4"
 for key in ("all","gap|"+bucket,"month|"+x["decision"].strftime("%Y-%m"),"month_gap|"+x["decision"].strftime("%Y-%m")+"|"+bucket):
  z=gap_groups[key];z["n"]+=1;z["total_gap"]+=gap;z["goal_residual"]+=x["actual"]-x["tau"];z["pnl"]+=x["sides"][selected]["pnl"];z["under"]+=int(selected=="under")
def gap_formatted():
 return {k:{"n":v["n"],"mean_market_tau_gap":round(v["total_gap"]/v["n"],5),"actual_minus_1x2_goals":round(v["goal_residual"]/v["n"],5),"original_roi":round(v["pnl"]/v["n"],6),"under_share":round(v["under"]/v["n"],5)} for k,v in sorted(gap_groups.items()) if v["n"]}


# Composition audit, descriptive: explain gap bands through line/league cells.
composition=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"gap_sum":0.0,"actual_residual":0.0})
for x in cal_rows:
 implied=infer_ou_tau(x["sides"])
 if implied is None:continue
 gap=implied-x["tau"]
 band="negative" if gap<0 else "0-.1" if gap<.1 else ".1-.2" if gap<.2 else ".2-.4" if gap<.4 else ">=.4"
 side=max(x["sides"],key=lambda y:x["sides"][y]["saved_ev"] if isinstance(x["sides"][y]["saved_ev"],(int,float)) else -999)
 line=x["sides"][side]["line"]
 # Line x gap composition is grounded by the identical fixture and quote.
 for key in ("gap|"+band,"line|"+str(line),"line_gap|"+str(line)+"|"+band):
  z=composition[key];z["n"]+=1;z["pnl"]+=x["sides"][side]["pnl"];z["gap_sum"]+=gap;z["actual_residual"]+=x["actual"]-x["tau"]
def composition_formatted():
 return {k:{"n":v["n"],"roi":round(v["pnl"]/v["n"],6),"pnl":round(v["pnl"],4),"mean_gap":round(v["gap_sum"]/v["n"],5),"mean_actual_minus_tau":round(v["actual_residual"]/v["n"],5)} for k,v in sorted(composition.items()) if v["n"]}


# Walk-forward multivariate residual calibration, fitted only from already
# observed FT. Continuous features: OU contract line and OU-vs-1X2 tau gap.
# Ridge strength fixed for research numerical stability, not a trading gate.
import numpy as np
walk=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"switches":0,"mae":0.0,"logloss":0.0})
rows=[]
for x in cal_rows:
 t=infer_ou_tau(x["sides"])
 if t is not None:rows.append((x,t))
for i,(x,t) in enumerate(rows):
 hist=[(h,ht) for h,ht in rows[:i] if h["finished"]<x["decision"]]
 if not hist:continue
 line=x["sides"]["under"]["line"]
 def feature(y,ou_tau):
  ln=y["sides"]["under"]["line"]
  return [1.,(ln-2.75),(ou_tau-y["tau"]), (ln-2.75)*(ou_tau-y["tau"])]
 matrix=np.array([feature(h,ht) for h,ht in hist],dtype=float)
 target=np.array([h["actual"]-h["tau"] for h,ht in hist],dtype=float)
 current=np.array(feature(x,t),dtype=float)
 # Center fit around historic intercept; small regularizer for numerical conditioning.
 ridge=np.diag([1e-8,.1,.1,.1])
 beta=np.linalg.solve(matrix.T@matrix+ridge,matrix.T@target)
 baseline=x["tau"];mean_corrected=max(.05,baseline+float(target.mean()))
 linear_corrected=max(.05,baseline+float(current@beta))
 old=max(x["sides"],key=lambda q:x["sides"][q]["saved_ev"])
 for name,tau in [("original_v6",baseline),("mean_only",mean_corrected),("line_gap_linear",linear_corrected)]:
  es={side:poisson_ou_ev(tau,c["line"],c["price"],side) for side,c in x["sides"].items()}
  chosen=max(es,key=es.get)
  z=walk[name];z["n"]+=1;z["pnl"]+=x["sides"][chosen]["pnl"];z["switches"]+=int(chosen!=old)
  z["mae"]+=abs(x["actual"]-tau)
  z["logloss"]-=-tau+x["actual"]*math.log(tau)-math.lgamma(x["actual"]+1)
def walk_formatted():
 return {k:{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"switches":v["switches"],"goal_mae":round(v["mae"]/v["n"],6),"goal_logloss":round(v["logloss"]/v["n"],6)} for k,v in walk.items() if v["n"]}


# Cross-market quote timestamp skew and independent AH/OU diagnostics.
skew=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"ev":0.0,"resid":0.0,"skew_sum":0.0})
for match,entries in group.items():
 for x,ft in sorted(entries,key=lambda z:z[0].get("received_at",""),reverse=True):
  times=x.get("quote_times",{})
  t1=parse(times.get("X1X2"));tou=parse(times.get("OU"));tah=parse(times.get("AH"))
  if not (t1 and tou):continue
  tau=x.get("evaluation",{}).get("one_x_two",{}).get("tau_market")
  if not isinstance(tau,(int,float)):continue
  for market,tm in (("OU",tou),("AH",tah)):
   if not tm:continue
   c=get(x,market)
   if not c:continue
   p=settlement(c.get("side"),c.get("line"),c.get("price"),ft["home_goals"],ft["away_goals"],market)
   if p is None:continue
   diff=abs((tm-t1).total_seconds())/60
   bucket="<15m" if diff<15 else "15-60m" if diff<60 else "1-3h" if diff<180 else ">=3h"
   for key in (market+"|overall",market+"|"+bucket,market+"|direction|"+("market_newer" if tm>t1 else "1X2_newer" if tm<t1 else "same_timestamp")):
    z=skew[key];z["n"]+=1;z["pnl"]+=p;z["ev"]+=float(c["EV"]);z["skew_sum"]+=diff;z["resid"]+=ft["home_goals"]+ft["away_goals"]-tau
  break
def skew_formatted():
 return {k:{"n":v["n"],"roi":round(v["pnl"]/v["n"],6),"pnl_units":round(v["pnl"],4),"mean_model_ev":round(v["ev"]/v["n"],6),"mean_abs_quote_skew_min":round(v["skew_sum"]/v["n"],2),"actual_minus_1x2_goals":round(v["resid"]/v["n"],5)} for k,v in sorted(skew.items()) if v["n"]}


# OU timestamp-skew by market line, time to kickoff and corrected strategy.
skew_cells=collections.defaultdict(lambda:{"n":0,"original":0.0,"corrected":0.0})
for i,x in enumerate(cal_rows):
 hist=[h for h in cal_rows[:i] if h["finished"]<x["decision"]]
 if not hist:continue
 # source record for this fixture at the selected decision timestamp
 entry=next((row for row,ft in group[x["match"]] if parse(row.get("received_at"))==x["decision"]),None)
 if not entry:continue
 times=entry.get("quote_times",{})
 t_ou=parse(times.get("OU"));t_1x2=parse(times.get("X1X2"));ko=parse(entry.get("kickoff_at"))
 if not(t_ou and t_1x2 and ko):continue
 quote_skew_minutes=abs((t_ou-t_1x2).total_seconds())/60
 skew_band="<15m" if quote_skew_minutes<15 else "15-60m" if quote_skew_minutes<60 else "1-3h" if quote_skew_minutes<180 else ">=3h"
 horizon=(ko-x["decision"]).total_seconds()/3600
 horizon_band="<1h" if horizon<1 else "1-6h" if horizon<6 else "6-24h" if horizon<24 else ">=24h"
 line=str(x["sides"]["under"]["line"])
 orig=max(x["sides"],key=lambda q:x["sides"][q]["saved_ev"])
 correction=sum(h["actual"]-h["tau"] for h in hist)/len(hist)
 tau=max(.05,x["tau"]+correction)
 cal=max(x["sides"],key=lambda q:poisson_ou_ev(tau,x["sides"][q]["line"],x["sides"][q]["price"],q))
 for key in ("skew|"+skew_band,"line_skew|"+line+"|"+skew_band,"horizon_skew|"+horizon_band+"|"+skew_band,"newer|"+("OU" if t_ou>t_1x2 else "1X2" if t_ou<t_1x2 else "same")):
  z=skew_cells[key];z["n"]+=1;z["original"]+=x["sides"][orig]["pnl"];z["corrected"]+=x["sides"][cal]["pnl"]
def skew_cells_formatted():
 return {k:{"n":v["n"],"original_roi":round(v["original"]/v["n"],6),"corrected_roi":round(v["corrected"]/v["n"],6),"gain_units":round(v["corrected"]-v["original"],4)} for k,v in sorted(skew_cells.items()) if v["n"]}


# Prospective-by-decision-time conditional calibration choice.
# Historical knowledge: compare earlier settled fixtures' realized PnL
# under baseline vs mean correction within each quote recency direction.
# No current/future fixture outcome enters selection.
conditional=collections.defaultdict(lambda:{"n":0,"pnl":0.0,"changes":0,"used_calibration":0})
past=[]
conditional_detail=[]
activation_events=[]
for i,x in enumerate(cal_rows):
 hist=[h for h in cal_rows[:i] if h["finished"]<x["decision"]]
 if not hist:continue
 source=next((q for q,ft in group[x["match"]] if parse(q.get("received_at"))==x["decision"]),None)
 if source is None:continue
 ts=source.get("quote_times",{})
 ou_time=parse(ts.get("OU"));one_time=parse(ts.get("X1X2"))
 if not(ou_time and one_time):continue
 recency="OU_newer" if ou_time>one_time else "1X2_newer" if ou_time<one_time else "same"
 old=max(x["sides"],key=lambda q:x["sides"][q]["saved_ev"])
 correction=sum(h["actual"]-h["tau"] for h in hist)/len(hist)
 new_tau=max(.05,x["tau"]+correction)
 new=max(x["sides"],key=lambda q:poisson_ou_ev(new_tau,x["sides"][q]["line"],x["sides"][q]["price"],q))
 old_p=x["sides"][old]["pnl"];new_p=x["sides"][new]["pnl"]
 known=[p for p in past if p["finished"]<x["decision"]]
 for name in ("original","uniform","adaptive_global","adaptive_quote_order"):
  if name=="original":choose=False
  elif name=="uniform":choose=True
  else:
   h=[p for p in known if name=="adaptive_global" or p["recency"]==recency]
   choose=bool(h) and sum(p["new_p"]-p["old_p"] for p in h)>0
  if name=="adaptive_quote_order" and choose:
   h=[p for p in known if p["recency"]==recency]
   activation_events.append({"date":x["decision"].date().isoformat(),"week":x["decision"].strftime("%G-W%V"),"recency":recency,"match":x["match"],"prior_n":len(h),"prior_gain":round(sum(p["new_p"]-p["old_p"] for p in h),4),"current_gain":round(new_p-old_p,4),"side_switched":new!=old})
  picked=new if choose else old
  z=conditional[name];z["n"]+=1;z["pnl"]+=new_p if choose else old_p;z["changes"]+=int(picked!=old);z["used_calibration"]+=int(choose)
 conditional_detail.append({"match":x["match"],"decision":x["decision"],"league":source.get("league","unknown"),"recency":recency,"line":x["sides"]["under"]["line"],"baseline_pnl":old_p,"uniform_pnl":new_p,"adaptive_pnl":new_p if (bool([p for p in known if p["recency"]==recency]) and sum(p["new_p"]-p["old_p"] for p in known if p["recency"]==recency)>0) else old_p})
 past.append({"finished":x["finished"],"recency":recency,"old_p":old_p,"new_p":new_p})
def conditional_formatted():
 return {k:{"n":v["n"],"pnl_units":round(v["pnl"],4),"roi":round(v["pnl"]/v["n"],6),"changed_sides":v["changes"],"calibration_chosen":v["used_calibration"]} for k,v in sorted(conditional.items()) if v["n"]}


stability=collections.defaultdict(lambda:{"n":0,"orig":0.0,"adaptive":0.0,"uniform":0.0})
for y in conditional_detail:
 dt=y["decision"]
 for k in ("month|"+dt.strftime("%Y-%m"),"week|"+dt.strftime("%G-W%V"),"line|"+str(y["line"]),"recency|"+y["recency"],"chronological_half|"+("first" if dt<=conditional_detail[len(conditional_detail)//2]["decision"] else "second")):
  z=stability[k];z["n"]+=1;z["orig"]+=y["baseline_pnl"];z["adaptive"]+=y["adaptive_pnl"];z["uniform"]+=y["uniform_pnl"]
def stability_formatted():
 return {k:{"n":v["n"],"original_roi":round(v["orig"]/v["n"],6),"adaptive_roi":round(v["adaptive"]/v["n"],6),"uniform_roi":round(v["uniform"]/v["n"],6),"adaptive_gain_u":round(v["adaptive"]-v["orig"],4)} for k,v in sorted(stability.items()) if v["n"]}


# Explain chronological drift by league, quote recency and OU line.
drift=collections.defaultdict(lambda:{"n":0,"baseline":0.0,"adaptive":0.0,"uniform":0.0})
for detail_row in conditional_detail:
 week=detail_row["decision"].strftime("%G-W%V")
 league_name=detail_row["league"]
 for key in ("week_recency|"+week+"|"+detail_row["recency"],"week_line|"+week+"|"+str(detail_row["line"]),"week_league|"+week+"|"+league_name,"league|"+league_name):
  z=drift[key];z["n"]+=1;z["baseline"]+=detail_row["baseline_pnl"];z["adaptive"]+=detail_row["adaptive_pnl"];z["uniform"]+=detail_row["uniform_pnl"]
def drift_formatted():
 return {k:{"n":v["n"],"original_roi":round(v["baseline"]/v["n"],6),"adaptive_roi":round(v["adaptive"]/v["n"],6),"gain_u":round(v["adaptive"]-v["baseline"],4)} for k,v in sorted(drift.items()) if v["n"]}


activation_summary=collections.defaultdict(lambda:{"n":0,"switches":0,"gain":0.0,"prior_n_sum":0})
for a in activation_events:
 for k in ("week|"+a["week"]+"|"+a["recency"],"date|"+a["date"]+"|"+a["recency"]):
  z=activation_summary[k];z["n"]+=1;z["switches"]+=int(a["side_switched"]);z["gain"]+=a["current_gain"];z["prior_n_sum"]+=a["prior_n"]
def activation_formatted():
 return {"first_activations":activation_events[:12],"first_ou_newer_switches":[a for a in activation_events if a["recency"]=="OU_newer" and a["side_switched"]][:12],"by_period":{k:{"n":v["n"],"switched":v["switches"],"gain_u":round(v["gain"],4),"mean_prior_count":round(v["prior_n_sum"]/v["n"],2)} for k,v in sorted(activation_summary.items())}}

output={"protocol":"M4_MR1_PAIRED_FT_READ_ONLY_V1","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":"MR1 saved forward Crown quotes and TotalCorner FT records","unique_valid_paired_matches":len(group),"counts":dict(counts),"ou_goal_mean_root_cause":root_formatted(),"m4_chronological_tau_calibration":calibration_report,"m4_ou_exploratory_candidates":candidate_formatted(),"m4_ou_distribution_candidates":dist_formatted(),"m4_ou_joint_market_candidates":joint_formatted(),"m4_signed_market_disagreement":gap_formatted(),"m4_gap_line_composition":composition_formatted(),"m4_walk_forward_line_gap_calibration":walk_formatted(),"m4_cross_market_quote_time_skew":skew_formatted(),"m4_ou_skew_line_horizon_calibration":skew_cells_formatted(),"m4_walk_forward_quote_order_adaptive":conditional_formatted(),"m4_adaptive_temporal_line_stability":stability_formatted(),"m4_week_league_line_drift":drift_formatted(),"m4_adaptive_activation_audit":activation_formatted(),"m4_a_probability_price_diagnostics":diagnostic_formatted(),"daily_fixed_beijing_clock_replay":daily_formatted(),"one_per_fixture_market":unique_formatted(unique),"one_per_fixture_league_market":unique_formatted(unique_league),"one_per_fixture_counts":{"unique_fixtures_with_either_market":len({k[0] for k in by_fixture}),"AH":unique["AH"]["n"],"OU":unique["OU"]["n"]},"per_market_horizon":formatted(agg),"per_league_market_horizon":formatted(league),"league_inventory":{k:{"snapshot_files":v["files"],"unique_matches":len(v["matches"]),"valid_ft_matches":len(valid_leagues[k])} for k,v in sorted(inventory.items())},"note":"Retrospective counterfactual, not Telegram trades or out-of-sample M4 improvement. Same match repeated across horizons; each horizon independently counts at most one observation per match. No new gate or trade rules."}
OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(output,ensure_ascii=False))
