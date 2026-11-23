#!/usr/bin/env python3
"""R4 historical season-opening research: previous paper xG3 cohort omits games
until both teams have 3 same-season venue games. Independently inspect earlier
club-league fixtures using cross-season venue history, if it exists.
Crown source event prices are historical, not actual received live quotes.
No national teams, no new trading gate or EV threshold.
"""
import csv,json,math,hashlib,sys,datetime
from collections import defaultdict,Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"m7"))
from m7_shot_residual_profit_replay_11league_20261116 import poisson,settle,split_line
DATA=HERE/"xgtables_understat_2017_2025"
CROWN=HERE.parent/"m8_early_joint_market_inventory_20261115.jsonl"
R4=HERE/"r4_season_scope_CrownT12_20261123.jsonl"
R4P=HERE/"r4_season_scope_xg_predictions_20261123.jsonl"
OUT=HERE/"r4_earlyseason_club_CrownT12_20261123.jsonl"
REPORT=HERE/"r4_earlyseason_club_CrownT12_20261123.json"
LEAGUE={"epl":"1","bundesliga":"16","la-liga":"14","serie-a":"12","ligue-1":"25"}
REV={v:k for k,v in LEAGUE.items()}
price_byfid={}
for s in CROWN.open():
    r=json.loads(s)
    if r.get("T")==12 and str(r["league"]) in REV:
        if r["fid"] in price_byfid:raise ValueError("duplicate Crown match")
        price_byfid[r["fid"]]=r
reference={}
for s in R4P.open():
    r=json.loads(s)
    reference[(r["league"],r["fid"])]=r
votes=defaultdict(Counter)
for s in R4.open():
    r=json.loads(s)
    if r["market"]!="AH":continue
    price=price_byfid[r["fid"]]
    match=reference[(r["league"],r["understat_fixture_id"])]
    lg=str(price["league"])
    votes[(lg,str(price["home_id"]))][match["home"]]+=1
    votes[(lg,str(price["away_id"]))][match["away"]]+=1
identity={}
for key,v in votes.items():
    if len(v)==1:identity[key]=next(iter(v))
reverse=defaultdict(set)
for (lg,tid),name in identity.items():
    reverse[(lg,name)].add(tid)
identity={key:name for key,name in identity.items() if len(reverse[(key[0],name)])==1}
AUDIT=Counter()
AUDIT["unambiguous_team_identity_keys"]=len(identity)
# Index historical Crown fixtures by date and identity, never by target FT.
bycrown=defaultdict(list)
for price in price_byfid.values():
    lg=str(price["league"])
    h=identity.get((lg,str(price["home_id"])))
    a=identity.get((lg,str(price["away_id"])))
    if h is None or a is None:
        AUDIT["price_missing_identity"]+=1
        continue
    bycrown[(REV[lg],price["date"],h,a)].append(price)
price_all_used=set()
HL=365
def weighted(history,now):
    sw=sx=sy=0.
    for time,xg,xa in history:
        if xg is None or xa is None:continue
        delta=(now-time).days
        assert delta>0
        w=math.exp(-math.log(2)*delta/HL)
        sw+=w;sx+=w*xg;sy+=w*xa
    return (sx/sw,sy/sw) if sw else None
def expected_goals(lh,la,m):
    ph=poisson(lh);pa=poisson(la)
    D=defaultdict(float)
    for i,p in enumerate(ph):
        for j,q in enumerate(pa):D[i-j if m=="AH" else i+j]+=p*q
    return D
def EV(m,line,odds,dist,side):
    result=0.
    for v,pr in dist.items():
        for leg,w in split_line(line):
            margin=v+leg if side=="home" else -v-leg if side=="away" else v-leg if side=="over" else leg-v
            ret=odds-1 if margin>1e-9 else -1. if margin<-1e-9 else 0
            result+=pr*w*ret
    return result

records=[]
for league_dir in sorted(DATA.iterdir()):
    if not league_dir.is_dir():continue
    lg=league_dir.name
    bydate=defaultdict(list)
    for csvpath in sorted(league_dir.glob("*/fixtures.csv")):
        season=int(csvpath.parent.name)
        with csvpath.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                z=dict(r);z["season"]=season
                bydate[z["date"]].append(z)
    team_hist=defaultdict(list)
    league_hist=[]
    venue_this_season=Counter()
    for datestr in sorted(bydate):
        now=datetime.date.fromisoformat(datestr)
        todays=bydate[datestr]
        for r in todays:
            if r["season"]<2019:continue
            try: hg,ag=map(int,r["score"].split("-"))
            except ValueError:
                AUDIT["no_final_score"]+=1;continue
            AUDIT["all_2019_2025_club_fixtures"]+=1
            crown=bycrown.get((lg,datestr,r["home"],r["away"]),[])
            if not crown:
                AUDIT["no_matched_Crown_T12"]+=1
                continue
            if len(crown)>1:
                AUDIT["ambiguous_Crown_match"]+=1
                continue
            price=crown[0]
            if (hg,ag)!=(price["hg"],price["ag"]):
                AUDIT["score_disagreement_after_identity_join"]+=1
                continue
            if price["fid"] in price_all_used:
                AUDIT["duplicate_price_identity_match"]+=1
                continue
            price_all_used.add(price["fid"])
            # Distinguish season opening earlier than paper's 3 venue matches;
            # this is cohort-description, not a production filter.
            homecnt=venue_this_season[(r["season"],r["home"],"home")]
            awaycnt=venue_this_season[(r["season"],r["away"],"away")]
            early=min(homecnt,awaycnt)<3
            AUDIT["matched_Crown_T12_club"]+=1
            if early:AUDIT["matched_early_before_xG3_venue_history"]+=1
            else:AUDIT["matched_later_after_xG3_venue_history"]+=1
            home=weighted(team_hist[(r["home"],"home")],now)
            away=weighted(team_hist[(r["away"],"away")],now)
            leagueavg=weighted(league_hist,now)
            if not home or not away or not leagueavg:
                AUDIT["matched_missing_cross_season_xG_history"]+=1
                continue
            candidate={
                "arithmetic_decay_cross_season":((home[0]+away[1])/2,(away[0]+home[1])/2)}
            if leagueavg[0]>0 and leagueavg[1]>0:
                candidate["ratio_decay_cross_season"]=(home[0]*away[1]/leagueavg[0],away[0]*home[1]/leagueavg[1])
            else:AUDIT["zero_league_xG_mean"]+=1
            record={"fid":price["fid"],"fixture_id":r["fixture_id"],"league":lg,
                    "date":datestr,"season":r["season"],"score":r["score"],
                    "early":early,"prior_same_season_home_venue":homecnt,
                    "prior_same_season_away_venue":awaycnt,
                    "source":"Crown historical T12 source-event, NOT actual pregame HTTP receipt",
                    "models":{}}
            for market,ql,od1,od2,sides in (
                ("AH",price["al"],price["ah"],price["aa"],("home","away")),
                ("OU",price["ol"],price["oo"],price["ou"],("over","under"))):
                odds={sides[0]:od1,sides[1]:od2}
                if any(x is None or not math.isfinite(float(x)) or float(x)<=1 for x in odds.values()):
                    AUDIT["market_invalid_odds"]+=1
                    continue
                for model,(lh,la) in candidate.items():
                    dist=expected_goals(lh,la,market)
                    e={side:EV(market,ql,odds[side],dist,side) for side in odds}
                    selected=max(sides,key=lambda x:e[x])
                    profit=settle(market,ql,odds[selected],selected,r["score"])
                    record["models"][model+"_"+market]={
                        "side":selected,"net_U":profit,"predicted_EV":e[selected],
                        "quote_line":ql,"odds":odds,
                        "lambda_home":lh,"lambda_away":la}
            if early and record["models"]:records.append(record)
            elif not early: AUDIT["later_seen_not_recorded_in_early_ledger"]+=1
        # State update only after all same-date predictions.
        for r in todays:
            year=r["season"]
            home=r["home"];away=r["away"]
            hx=float(r["home_published_xg"]) if r.get("home_published_xg") else None
            ax=float(r["away_published_xg"]) if r.get("away_published_xg") else None
            if r.get("totals_unreliable","").lower()=="true":hx=ax=None
            team_hist[(home,"home")].append((now,hx,ax))
            team_hist[(away,"away")].append((now,ax,hx))
            venue_this_season[(year,home,"home")]+=1
            venue_this_season[(year,away,"away")]+=1
            if hx is not None and ax is not None:league_hist.append((now,hx,ax))
            else:AUDIT["historical_xG_missing"]+=1
def agg(items):
    n=len(items)
    ret={"n":n}
    for name in ("arithmetic_decay_cross_season","ratio_decay_cross_season"):
        for market in ("AH","OU"):
            key=name+"_"+market
            z=[x["models"][key] for x in items if key in x["models"]]
            num=len(z);u=sum(x["net_U"] for x in z)
            ret[key]={"n":num,"net_U":round(u,5),"ROI_pct":round(100*u/num,5) if num else None}
    return ret
rep={"research":"R4_CLUB_ONLY_CROSS_SEASON_EARLY_GAMES_CROWN_HISTORICAL_T12",
    "historical_Crown_sha256":hashlib.sha256(CROWN.read_bytes()).hexdigest(),
    "research_scope":"Five domestic club leagues only, zero national teams",
    "method":"As-of strictly previous-date all same-league, same-venue team/league xG weighted 365-day; descriptive early fixtures where either side has less than 3 current-season venue appearances",
    "identity":"Team-ID maps inferred retrospectively from previously matched R3 sample; future fixture matched by league,date,home,away then final score audited",
    "audit":dict(AUDIT),"early":agg(records),
    "by_season":{str(y):agg([r for r in records if r["season"]==y]) for y in range(2019,2026)},
    "by_league":{lg:agg([r for r in records if r["league"]==lg]) for lg in LEAGUE},
    "limitations":["Early category only characterizes previous paper's missing venue3 history; no betting filter or Gate",
       "The first eligible season may not have earlier 2017 onward history; missing preserved in audit",
       "Crown T12 historical source-event quote is NOT a true pregame HTTP receipt or executable price",
       "Retrospective team-ID mapping with score anchors, not independently verified pregame identity",
       "xG publication timestamp unknown; this is not a blind prospective trading simulation",
       "No national teams or non-domestic club competitions analyzed"]}
with OUT.open("w") as f:
    for r in records:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"early":rep["early"],"audit":rep["audit"],"by_season":rep["by_season"]},ensure_ascii=False))
