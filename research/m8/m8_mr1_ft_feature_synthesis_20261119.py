#!/usr/bin/env python3
"""Read-only synthesis of new MR1 Crown AH receipts and independent TotalCorner FT proofs."""
import collections,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"research/m8"
FTBASE=BASE/"mr1_m8_ft_evidence_20261119"
OUT=FTBASE/"verified_ft_feature_alignment.json"
FROZEN=Path("/Users/mac/QuantAsiaDesk/research-work/m8_foundation_20261115/historical_membership.jsonl")
FIX=Path("/Users/mac/QuantAsiaDesk/repos/mr1/data/prospective-market/shadow-v23/fixtures.json")
def main():
    old_leagues={str(json.loads(l).get("league")) for l in FROZEN.open() if l.strip()}
    fixtures=json.loads(FIX.read_text())
    original=[json.loads(l) for l in (BASE/"mr1_m8_ft_feature_audit_20261119/per_fixture.jsonl").open() if l.strip()]
    evidence={}
    p=FTBASE/"ft_query_evidence.jsonl"
    if p.exists():
        for l in p.open():
            row=json.loads(l);evidence[row["fid"]]=row
    out=[]
    for x in original:
        f=x["fid"];ev=evidence.get(f,{})
        state=ev.get("status") if x["kickoff_reached_asof"] else "not_started_at_audit_cutoff"
        has_prev_scope=str(fixtures[f].get("league_id")) in old_leagues
        out.append({**x,"league_id":fixtures[f].get("league_id"),
                    "league_id_seen_in_frozen_membership":has_prev_scope,
                    "ft_proof_status":state,
                    "ft_score":f'{ev["hg"]}-{ev["ag"]}' if state=="verified_ft" else None,
                    "ft_raw_sha256":ev.get("raw_sha256"),
                    "ft_observed_at_utc":ev.get("received_utc"),
                    "verified_settled_research_bet":False})
    counts=collections.Counter(x["ft_proof_status"] for x in out)
    league_hist=collections.Counter()
    for x in out:
        league_hist["prior_membership_league_id" if x["league_id_seen_in_frozen_membership"] else "outside_prior_membership_league_ids"]+=1
        if x["kickoff_reached_asof"]:
            league_hist["past_with_prior_league_id" if x["league_id_seen_in_frozen_membership"] else "past_outside_prior_league_ids"]+=1
    summary={"total_fids":len(out),"past_kickoff_at_audit":sum(x["kickoff_reached_asof"] for x in out),
             "future_at_audit":sum(not x["kickoff_reached_asof"] for x in out),
             "ft_status":dict(counts),"league_id_comparison":dict(league_hist),
             "ft_verified_by_match_view":counts["verified_ft"],
             "prior_m8_path_features_for_new_fids":0,
             "validated_new_m8_rule_signals":0,
             "new_trade_returns_calculated":False,
             "roi":"not_applicable",
             "caveats":["Past membership league IDs are a descriptive overlap, not a new allowed-league filter.",
                       "Old M8 historical path features do not include new FIDs. MR1 horizon samples do not reproduce the full event movement features.",
                       "Crown actual receipts are not a Telegram trade or evidence that the frozen eight would have selected the game.",
                       "Postgame FT must be matched to the same FID, teams and kickoff; raw SHA evidence remains on the Mac only."]}
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    with (FTBASE/"per_fixture_ft_alignment.jsonl").open("w") as f:
        for x in out:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
