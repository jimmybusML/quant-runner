#!/usr/bin/env python3
"""Research CLI: run dynamic EKF to an explicit as-of time and forecast one fixture.

This is NOT production M9 and does not place/send orders. The +3h postkickoff
result-availability rule is a simulation proxy, NOT an actual receipt timestamp.
Use same timezone/naive clock representation as cache fixtures.
"""
import argparse,datetime as dt,json,heapq
from pathlib import Path
import numpy as np
from dynamic_poisson_ekf_r62 import DynamicPoissonEKF

P=Path.home()/"QuantAsiaDesk/repos/m1/data/m1_history_cache"
def history(league):
    path=P/f"{league}.json"
    if not path.exists():raise ValueError(f"No historical cache for league {league}")
    data={}
    for r in json.loads(path.read_text()).get("rows",[]):
        if r.get("status")!="full":continue
        try:
            t=dt.datetime.strptime(r["start"][:19],"%Y-%m-%d %H:%M:%S")
            h,a=str(r["h_id"]),str(r["a_id"])
            hg,ag=int(r["hg"]),int(r["ag"])
            if min(hg,ag)<0 or h==a:continue
            data[str(r["id"])]=(t,h,a,hg,ag)
        except (KeyError,ValueError,TypeError):continue
    return sorted(data.values())
def handicap_states(grid,line):
    diff=np.indices(grid.shape)[0]-np.indices(grid.shape)[1]
    if round(line*4)%2:
        a=np.floor(line*2)/2;b=np.ceil(line*2)/2
    else:a=b=line
    outcome=.5*(np.sign(diff+a)+np.sign(diff+b))
    labels=[(-1.,"full_loss"),(-.5,"half_loss"),(0.,"push"),(.5,"half_win"),(1.,"full_win")]
    return {name:float(grid[outcome==x].sum()) for x,name in labels}
def forecast(league,home,away,kickoff,as_of,home_handicap):
    if as_of>kickoff:raise ValueError("as_of must not be later than fixture kickoff")
    rows=history(league)
    # Only prior completed records with hypothetically visible results are used.
    training=[r for r in rows if r[0]+dt.timedelta(hours=3)<=as_of]
    if not training:raise ValueError("No available historical training matches")
    pre2024=[r for r in training if r[0].year<2024]
    initial=pre2024 if pre2024 else training
    model=DynamicPoissonEKF(home_goal_rate=sum(r[3] for r in initial)/len(initial),
                            away_goal_rate=sum(r[4] for r in initial)/len(initial))
    for kickoff0,h,a,gh,ga in training:
        model.update(h,a,gh,ga,kickoff0+dt.timedelta(hours=3))
    previously_seen=set(t for r in training for t in (r[1],r[2]))
    grid,(lh,la)=model.predict(home,away,kickoff)
    diff=np.indices(grid.shape)[0]-np.indices(grid.shape)[1]
    return {"model":"research-diagonal-EKF-v1","league":league,"home_team_id":home,"away_team_id":away,
            "fixture_kickoff":kickoff.isoformat(),"as_of":as_of.isoformat(),
            "historical_result_proxy":"kickoff+3h (NOT actual received time)",
            "trained_matches":len(training),"unseen_team_ids":sorted({home,away}-previously_seen),
            "lambda_home":lh,"lambda_away":la,
            "one_x_two":{"home":float(grid[diff>0].sum()),
                         "draw":float(grid[diff==0].sum()),
                         "away":float(grid[diff<0].sum())},
            "home_handicap":home_handicap,
            "handicap_outcomes":handicap_states(grid,home_handicap),
            "score_grid_0_to_14":grid.tolist(),"snapshot":model.snapshot()}
if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--league",required=True)
    ap.add_argument("--home",required=True)
    ap.add_argument("--away",required=True)
    ap.add_argument("--kickoff",type=dt.datetime.fromisoformat,required=True)
    ap.add_argument("--as-of",type=dt.datetime.fromisoformat,required=True)
    ap.add_argument("--home-handicap",type=float,required=True)
    args=ap.parse_args()
    print(json.dumps(forecast(args.league,args.home,args.away,args.kickoff,args.as_of,args.home_handicap),ensure_ascii=False,indent=2))
