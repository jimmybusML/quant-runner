#!/usr/bin/env python3
"""R4: Controlled cross-season vs current-season independent club xG study.
Always same league, same home/away venue role, asof prior calendar dates only.
For each pair, keep pooling formula and decay specification identical while
changing ONLY whether history from earlier seasons is allowed.
Research-only, no national-team inputs, no EV or order eligibility Gate.
"""
import csv,math,json,datetime,hashlib
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
DATA=HERE/"xgtables_understat_2017_2025"
BASE=HERE/"attack_defense_xg_20261123.jsonl"
OUT=HERE/"r4_season_scope_xg_predictions_20261123.jsonl"
REPORT=HERE/"r4_season_scope_xg_predictions_20261123.json"
base={}
for raw in BASE.open():
    z=json.loads(raw);base[(z["league"],z["season"],z["fixture_id"])]=z
VARIANTS=(
    "xg3_same_season",
    "arithmetic_3_same_season",
    "arithmetic_3_cross_season",
    "arithmetic_decay_same_season",
    "arithmetic_decay_cross_season",
    "ratio_decay_same_season",
    "ratio_decay_cross_season",
)
HL=365.
COUNTS=Counter()
out=[]

def weighted(events,day,limit=None):
    seq=(events[-limit:] if limit is not None else events)
    wsum=sx=sy=0.0
    c=0
    for t,x,y in seq:
        if x is None or y is None:continue
        age=(day-t).days
        assert age>0,(day,t)
        w=math.exp(-math.log(2)*age/HL)
        wsum+=w;sx+=w*x;sy+=w*y;c+=1
    if not wsum:return None
    return sx/wsum,sy/wsum,c

def equal_last(events,limit=3):
    seq=events[-limit:]
    if len(seq)<limit or any(x is None or y is None for t,x,y in seq):return None
    return sum(x for t,x,y in seq)/limit,sum(y for t,x,y in seq)/limit

def forecast(home,away):
    if min(home,away)<=0:return None
    def poi(x):
        a=[math.exp(-x)]
        for i in range(1,21):a.append(a[-1]*x/i)
        sm=sum(a)
        return [v/sm for v in a]
    x=poi(home);y=poi(away)
    hw=dr=0.0
    for i,p in enumerate(x):
        for j,q in enumerate(y):
            if i>j:hw+=p*q
            if i==j:dr+=p*q
    aw=max(0,1-hw-dr);tot=hw+dr+aw
    return [hw/tot,dr/tot,aw/tot]

def measure(home,away,hg,ag):
    p=forecast(home,away)
    if p is None:return None
    k=0 if hg>ag else (2 if ag>hg else 1)
    return {"lambda_home":home,"lambda_away":away,
            "brier":sum((x-(i==k))**2 for i,x in enumerate(p)),
            "logloss":-math.log(max(p[k],1e-15)),
            "goal_diff_mae":abs(home-away-(hg-ag)),
            "accuracy":int(max(range(3),key=lambda i:p[i])==k)}

for league_dir in sorted(DATA.iterdir()):
    if not league_dir.is_dir():continue
    league=league_dir.name
    bydate=defaultdict(list)
    for src in sorted(league_dir.glob("*/fixtures.csv")):
        yr=int(src.parent.name)
        with src.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                r=dict(row);r["season"]=yr
                bydate[r["date"]].append(r)
    team_all=defaultdict(list)
    team_season=defaultdict(list)
    league_all=[]
    league_season=defaultdict(list)
    for daystring in sorted(bydate):
        day=datetime.date.fromisoformat(daystring)
        todays=bydate[daystring]
        for r in todays:
            year=r["season"]
            lookup=(league,year,r["fixture_id"])
            original=base.get(lookup)
            if not original:
                COUNTS["not_in_original_fixed_cohort"]+=1
                continue
            home,away=r["home"],r["away"]
            sh=team_season[(year,home,"home")]
            sa=team_season[(year,away,"away")]
            ch=team_all[(home,"home")]
            ca=team_all[(away,"away")]
            eh=equal_last(sh);ea=equal_last(sa)
            if not eh or not ea:
                raise RuntimeError(("missing_same_season_base",lookup))
            crossh=equal_last(ch);crossa=equal_last(ca)
            assert crossh and crossa,lookup
            vsh=weighted(sh,day);vsa=weighted(sa,day)
            vch=weighted(ch,day);vca=weighted(ca,day)
            vlg_s=weighted(league_season[year],day)
            vlg_c=weighted(league_all,day)
            assert all((vsh,vsa,vch,vca,vlg_s,vlg_c)),lookup
            assert max(abs(eh[0]-original["models"]["xg3"]["lambda_home"]),abs(ea[0]-original["models"]["xg3"]["lambda_away"]))<1e-8,lookup
            params={
                "xg3_same_season":(eh[0],ea[0]),
                "arithmetic_3_same_season":((eh[0]+ea[1])/2,(ea[0]+eh[1])/2),
                "arithmetic_3_cross_season":((crossh[0]+crossa[1])/2,(crossa[0]+crossh[1])/2),
                "arithmetic_decay_same_season":((vsh[0]+vsa[1])/2,(vsa[0]+vsh[1])/2),
                "arithmetic_decay_cross_season":((vch[0]+vca[1])/2,(vca[0]+vch[1])/2),
                "ratio_decay_same_season":(vsh[0]*vsa[1]/vlg_s[0],vsa[0]*vsh[1]/vlg_s[1]),
                "ratio_decay_cross_season":(vch[0]*vca[1]/vlg_c[0],vca[0]*vch[1]/vlg_c[1]),
            }
            assert max(abs(params["ratio_decay_cross_season"][0]-original["models"]["attack_defense_dynamic365"]["lambda_home"]),
                       abs(params["ratio_decay_cross_season"][1]-original["models"]["attack_defense_dynamic365"]["lambda_away"]))<1e-8,lookup
            hg,ag=map(int,r["score"].split("-"))
            record={"fid":r["fixture_id"],"league":league,"season":year,"date":daystring,
                "home":home,"away":away,"score":r["score"],
                "history_counts":{
                    "home_same_season":len(sh),"away_same_season":len(sa),
                    "home_cross_season":len(ch),"away_cross_season":len(ca),
                    "league_current_season":len(league_season[year]),"league_cross_season":len(league_all)},
                "models":{}}
            for name,(lh,la) in params.items():
                m=measure(lh,la,hg,ag)
                if m is not None:record["models"][name]=m
                else:COUNTS["invalid_"+name]+=1
            if len(record["models"])!=len(VARIANTS):
                COUNTS["excluded_invalid_sample"]+=1
                # Do not erase the row; preserve analysis coverage and reason.
            out.append(record)
        # No fixtures on same calendar day may enter this date's prior features.
        for r in todays:
            try:
                hx=float(r["home_published_xg"]) if r.get("home_published_xg") else None
                ax=float(r["away_published_xg"]) if r.get("away_published_xg") else None
                if r.get("totals_unreliable","").lower()=="true":hx=ax=None
            except ValueError:
                hx=ax=None
            home,away=r["home"],r["away"];year=r["season"]
            team_all[(home,"home")].append((day,hx,ax))
            team_all[(away,"away")].append((day,ax,hx))
            team_season[(year,home,"home")].append((day,hx,ax))
            team_season[(year,away,"away")].append((day,ax,hx))
            if hx is not None and ax is not None:
                league_all.append((day,hx,ax))
                league_season[year].append((day,hx,ax))
            else:COUNTS["missing_history_xg"]+=1

def agg(data):
    total={"n":len(data)}
    for model in VARIANTS:
        x=[r["models"][model] for r in data if model in r["models"]]
        den=len(x)
        total[model]={"n":den,
            "brier":round(sum(r["brier"] for r in x)/den,7) if den else None,
            "logloss":round(sum(r["logloss"] for r in x)/den,7) if den else None,
            "goal_diff_mae":round(sum(r["goal_diff_mae"] for r in x)/den,7) if den else None,
            "accuracy_pct":round(100*sum(r["accuracy"] for r in x)/den,4) if den else None}
    return total
summary={"study":"R4_SAME_CLUB_LEAGUE_SAME_SEASON_VS_CROSS_SEASON_XG",
    "research_only":True,"user_scope":"Only five domestic club leagues; zero international/national team events",
    "input_sha256":hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "research_specs":{"same_decay_half_life_days":HL,"same_lastN":3,
       "range_pairs":["equal_3_arithmetic","time_decay_arithmetic","time_decay_opponent_ratio"],
       "scope_logic":"Each league trained separately; cross-season uses prior same-league fixtures, never another league. Same calendar date barred from prior history."},
    "counts":dict(COUNTS),"total":agg(out),
    "by_season":{str(y):agg([r for r in out if r["season"]==y]) for y in sorted({r["season"] for r in out})},
    "by_league":{lg:agg([r for r in out if r["league"]==lg]) for lg in sorted({r["league"] for r in out})},
    "limitations":["Not a newly blind holdout: same historical cohort as prior R3",
        "xG published after matches; actual historical publication timestamps unverified",
        "Method parameters are research contrasts, NOT added business or trading rules"]}
with OUT.open("w") as f:
    for r in out:f.write(json.dumps(r,ensure_ascii=False)+"\n")
REPORT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"n":len(out),"counts":dict(COUNTS),"total":summary["total"]},ensure_ascii=False))
