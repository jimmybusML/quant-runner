#!/usr/bin/env python3
"""Independent settlement and FID verification for the M8 transfer audit."""
import collections, datetime as dt, gzip, hashlib, json, math, pathlib

HERE=pathlib.Path(__file__).resolve().parent
PATHS=HERE/"exact_rule_cross_league_all_complete_paths.jsonl.gz"
ORDERS=HERE/"cross_league_transfer_inference_orders_20261120.jsonl.gz"
RESULT=HERE/"cross_league_transfer_inference_20261120.json"
SELECTOR=HERE/"prior_year_group_selector_orders_20261120.jsonl.gz"
FROZEN=pathlib.Path("/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl")
GROUPS=("base","A","B","C","D","E","F","G")

def h(p):
    x=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):x.update(b)
    return x.hexdigest()

def calc(line,side,hg,ag,odds):
    n=round(2*line)
    legs=[line] if abs(2*line-n)<1e-8 else [math.floor(2*line)/2,math.ceil(2*line)/2]
    leg_pnl=[]
    for x in legs:
        margin=(hg-ag+x) if side=="home" else (ag-hg-x)
        leg_pnl.append(odds-1 if margin>1e-9 else -1 if margin < -1e-9 else 0)
    u=sum(leg_pnl)/len(leg_pnl)
    state=("full_win" if all(x>0 for x in leg_pnl) else "half_win" if any(x>0 for x in leg_pnl) else "push" if all(x==0 for x in leg_pnl) else "half_loss" if any(x==0 for x in leg_pnl) else "full_loss")
    return u,state

def main():
    paths=[json.loads(x) for x in gzip.open(PATHS,"rt",encoding="utf-8") if x.strip()]
    bets=[json.loads(x) for x in gzip.open(ORDERS,"rt",encoding="utf-8") if x.strip()]
    pred=[json.loads(x) for x in gzip.open(SELECTOR,"rt",encoding="utf-8") if x.strip()]
    summary=json.loads(RESULT.read_text())
    frozen={json.loads(x)["fid"] for x in open(FROZEN,encoding="utf-8") if x.strip()}
    pmap={x["fid"]:x for x in paths}
    assert len(pmap)==len(paths)==6967
    assert len(frozen)==10294 and h(FROZEN)=="6cc9c761548ba8b2dae7f4e50d77b0b90152229ea35fd1316161b3f27958f665"
    assert not (set(pmap)&frozen)
    assert len({x["fid"] for x in bets})==len(bets)==1271
    for b in bets:
        p=pmap[b["fid"]]
        assert b["group"] in (p.get("raw_group_hits") or {})
        assert p["raw_group_hits"][b["group"]]==b["side"]
        assert b["line"]==p["end_line"] and abs(b["price"]-p[f"{b['side']}_price"])<1e-10
        u,s=calc(float(p["end_line"]),b["side"],int(p["hg"]),int(p["ag"]),float(p[f"{b['side']}_price"]))
        assert abs(u-b["net_u"])<1e-9 and s==b["settlement"]
        assert not b.get("actual_receipt_claim",False)
    by=collections.defaultdict(lambda:[0,0.])
    for b in bets: by[int(b["year"])][0]+=1; by[int(b["year"])][1]+=b["net_u"]
    got={str(y):{"orders":v[0],"net_u":round(v[1],6)} for y,v in by.items()}
    want={y:{"orders":x["orders"],"net_u":x["net_u"]} for y,x in summary["exact_rule_union"]["by_year"].items()}
    assert got==want,(got,want)
    # Independently recompute the paired low-price side control for the exact same FIDs.
    fav_total=0.; fav_recent=0.
    for b in bets:
        p=pmap[b["fid"]]; side="home" if p["home_price"]<=p["away_price"] else "away"
        u,_=calc(float(p["end_line"]),side,int(p["hg"]),int(p["ag"]),float(p[f"{side}_price"]))
        fav_total+=u
        if int(b["year"])>=2024:fav_recent+=u
    assert round(fav_total,6)==summary["same_fid_lower_price_side_control"]["all_candidate_fids"]["net_u"]
    assert round(fav_recent,6)==summary["same_fid_lower_price_side_control"]["2024_2026"]["net_u"]
    # The selector records only groups whose training scores use earlier years.
    assert len({x["fid"] for x in pred})==len(pred)==122
    selected_by={y:collections.Counter() for y in (2024,2025,2026)}
    for x in pred:selected_by[int(x["year"])][x["group"]]+=1
    pred_year=collections.defaultdict(lambda:[0,0.])
    for x in pred:
        pred_year[int(x["year"])][0]+=1;pred_year[int(x["year"])][1]+=float(x["net_u"])
    for y,info in summary["prior_year_group_selector"]["by_test_year"].items():
        assert set(selected_by[int(y)])=={info["selected_group"]}
        assert pred_year[int(y)][0]==info["test"]["orders"]
        assert round(pred_year[int(y)][1],6)==info["test"]["net_u"]
    merged_n=len(frozen)+len(bets); merged_u=sum(float(x["pnl"]) for x in (json.loads(z) for z in open(FROZEN,encoding="utf-8") if z.strip()))+sum(x["net_u"] for x in bets)
    assert merged_n==summary["combined_frozen_eight"]["after_increment"]["all_years"]["orders"]
    assert round(merged_u,6)==summary["combined_frozen_eight"]["after_increment"]["all_years"]["net_u"]
    assert abs(sum(x["net_u"] for x in bets)-7.185)<1e-9
    assert abs(sum(x["net_u"] for x in bets if x["year"]>=2024)+2.515)<1e-9
    output={"pass":True,"complete_path_fids":len(paths),"frozen_fids":len(frozen),"frozen_overlap":0,"unique_incremental_orders":len(bets),"ah_settlements_recomputed":len(bets),"all_year_net_u":round(sum(x["net_u"] for x in bets),6),"2024_2026_net_u":round(sum(x["net_u"] for x in bets if x["year"]>=2024),6),"same_fid_favorite_net_u":round(fav_total,6),"same_fid_favorite_recent_net_u":round(fav_recent,6),"selector_orders_recomputed":len(pred),"selector_net_u_recomputed":round(sum(x["net_u"] for x in pred),6),"merged_orders":merged_n,"merged_net_u":round(merged_u,6),"input_sha256":{"paths":h(PATHS),"orders":h(ORDERS),"selector":h(SELECTOR),"summary":h(RESULT),"frozen":h(FROZEN)}}
    out=HERE/"cross_league_transfer_inference_verification_20261120.json"
    out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(output,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
