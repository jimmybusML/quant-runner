#!/usr/bin/env python3
"""Replay contemporaneous M3 score-grid forecasts on saved Crown main lines.

Inputs are public M3 research forecasts and a private, read-only MR1 Crown
snapshot archive. Output is aggregate-only. No production or network access.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
LEAGUE = {"England Premier League":"E0", "Germany Bundesliga I":"D1", "France Ligue 1":"F1",
          "Italy Serie A":"I1", "Spain La Liga":"SP1", "Belgium First Division A":"B1"}


def digest(b): return hashlib.sha256(b).hexdigest()

def norm(x):
    x = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", x)

def instant(x):
    try:
        d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError): return None

def money_line(x):
    parts = [float(p) for p in str(x).split(",")]
    if not (1 <= len(parts) <= 2 and all(math.isfinite(p) for p in parts)): raise ValueError
    value = sum(parts) / len(parts)
    if abs(value * 4 - round(value * 4)) > 1e-7: raise ValueError
    return value

def split_line(line):
    if abs(line * 2 - round(line * 2)) < 1e-8: return [line, line]
    low = math.floor(line * 2) / 2
    return [low, low + .5]

def legs_result(market, side, line, h, a):
    parts = split_line(line)
    out = []
    for part in parts:
        if market == "AH":
            margin = (h - a + part) if side == "home" else (a - h - part)
        else:
            margin = (h + a - part) if side == "over" else (part - h - a)
        out.append(1 if margin > 1e-9 else -1 if margin < -1e-9 else 0)
    s = sorted(out)
    category = ("win" if s == [1,1] else "half_win" if s == [0,1] else "loss" if s == [-1,-1]
                else "half_loss" if s == [-1,0] else "push" if s == [0,0] else "unknown")
    return out, category

def payout(legs, price): return sum(price - 1 if x == 1 else -1 if x == -1 else 0 for x in legs) / 2

def grid_distribution(grid, market, side, line):
    cats = Counter(); expected_by_price = {}
    for h, row in enumerate(grid):
        for a, prob in enumerate(row):
            _, cat = legs_result(market, side, line, h, a)
            cats[cat] += prob
    return cats

def expected_return(grid, market, side, line, price):
    ev = mass = 0.0
    for h, row in enumerate(grid):
        for a, p in enumerate(row):
            legs, _ = legs_result(market, side, line, h, a)
            ev += p * payout(legs, price); mass += p
    if abs(mass - 1) > 1e-7: raise ValueError("invalid goal grid mass")
    return ev / mass

def settle(grid, market, quote, score):
    fields = (("home_price", "away_price"), ("over_price", "under_price"))[market == "OU"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    evs = [expected_return(grid, market, side, quote["line"], quote["market"][field]) for side, field in zip(sides, fields)]
    side = sides[0] if evs[0] >= evs[1] else sides[1]
    price = quote["market"][fields[sides.index(side)]]
    legs, category = legs_result(market, side, quote["line"], *score)
    dist = grid_distribution(grid, market, side, quote["line"])
    return payout(legs, price), category, dist

def bootstrap(values, seed, reps=10000):
    if not values: return None
    rng = random.Random(seed); n = len(values)
    samples = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return {"method":"fixture percentile bootstrap, descriptive only", "repetitions":reps,
            "lower_95":round(samples[int(.025*(reps-1))],8), "upper_95":round(samples[int(.975*(reps-1))],8)}

def score(rows):
    if not rows: return None, None
    cats = ("win", "half_win", "push", "half_loss", "loss")
    ll, br = [], []
    for actual, probs in rows:
        y = cats.index(actual); ll.append(-math.log(max(probs[actual], 1e-15)))
        br.append(sum((probs[c] - (1.0 if c == actual else 0.0)) ** 2 for c in cats))
    return round(sum(ll)/len(ll),8), round(sum(br)/len(br),8)

def summarize(rows, seed):
    pnl = [r[0] for r in rows]; outcomes = Counter(r[1] for r in rows)
    bytime = defaultdict(float)
    for r in rows: bytime[r[2]] += r[0]
    equity = peak = dd = 0.0
    for t in sorted(bytime):
        equity += bytime[t]; peak = max(peak, equity); dd = max(dd, peak-equity)
    ll, br = score([(r[1],r[3]) for r in rows])
    return {"unique_fixtures":len(rows), "simulated_bets":len(rows), "settled_bets":len(rows),
            "pending_bets":0, "net_units":round(sum(pnl),6), "roi":round(sum(pnl)/len(pnl),8) if pnl else None,
            "settlement_counts":{x:outcomes[x] for x in ("win","half_win","loss","half_loss","push")},
            "max_drawdown_units_by_quote_timestamp":round(dd,6), "roi_bootstrap_95pct":bootstrap(pnl,seed),
            "settlement_log_loss":ll, "settlement_brier":br}

def analyze(mr1_root: Path, ledger: Path, m3_csv: Path, stack_path: Path):
    base = mr1_root / "data/prospective-market/shadow-v23"
    idx, regp = base/"snapshot-index.jsonl", base/"fixtures.json"
    idx_stat=(idx.stat().st_size,idx.stat().st_mtime_ns); idx_raw=idx.read_bytes()
    reg_stat=(regp.stat().st_size,regp.stat().st_mtime_ns); reg_raw=regp.read_bytes(); registry=json.loads(reg_raw)
    ledger_stat=(ledger.stat().st_size,ledger.stat().st_mtime_ns)
    pred_raw=m3_csv.read_bytes(); pred=defaultdict(dict)
    for row in csv.DictReader(pred_raw.decode("utf-8-sig").splitlines()):
        if row.get("prediction_status")!="predicted": continue
        key=(row.get("league"),str(row.get("match_date_utc") or "")[:10],norm(row.get("home_team")),norm(row.get("away_team")))
        if row.get("model") in MODELS: pred[key][row["model"]]=row
    stack_raw=stack_path.read_bytes(); stack=json.loads(stack_raw)
    weights={}
    for market,name in (("AH","1x2"),("OU","ou_over_2_5")):
        split=next(x for x in stack["markets"][name]["season_splits"] if x["test_season"]=="2627")
        weights[market]=split["walkforward_weights"]

    fixtures={}; bykey=defaultdict(list)
    for fid,f in registry.items():
        code=LEAGUE.get(str(f.get("league") or "")); kickoff=instant(f.get("kickoff_at"))
        if not code or not kickoff: continue
        key=(code,kickoff.date().isoformat(),norm(f.get("home")),norm(f.get("away")))
        fixtures[str(fid)]=(f,kickoff,key); bykey[key].append(str(fid))
    ledger_rows=defaultdict(lambda:defaultdict(list)); ledger_sha=[]; audit=Counter()
    for line in ledger.open(encoding="utf-8"):
        try:r=json.loads(line)
        except ValueError: audit["bad_ledger_json"]+=1; continue
        if r.get("protocol")!="M3_TOTALCORNER_FORWARD_FORECAST_V1": continue
        fid=str(r.get("totalcorner_match_id") or ""); entry=fixtures.get(fid)
        if not entry: continue
        f,kickoff,key=entry
        # The provider match ID plus exact teams anchors fixture identity. Its
        # source_fixture_date is the provider's calendar date, which can differ
        # from the registry's UTC kickoff date for late local kickoffs.
        if r.get("home_team")!=f.get("home") or r.get("away_team")!=f.get("away"):
            audit["provider_id_team_identity_mismatch"]+=1; continue
        if str(r.get("source_fixture_date") or "")[:10]!=kickoff.date().isoformat():
            audit["provider_local_date_differs_from_utc_date"]+=1
        model=str(r.get("model")); forecast_at=instant(r.get("forecasted_at_utc")); grid=r.get("score_probability_grid")
        if model not in MODELS or not forecast_at or forecast_at>=kickoff or not isinstance(grid,list):
            audit["bad_or_nonprematch_forecast"]+=1; continue
        try:
            width=len(grid[0]); mass=math.fsum(float(v) for row in grid for v in row)
            if not grid or width==0 or any(len(row)!=width for row in grid) or abs(mass-1)>1e-7: raise ValueError
            if any(not math.isfinite(float(v)) or float(v)<0 for row in grid for v in row): raise ValueError
        except (ValueError,TypeError,IndexError): audit["bad_grid"]+=1; continue
        canonical=json.dumps(grid,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
        if r.get("score_grid_sha256") and digest(canonical)!=r.get("score_grid_sha256"):
            audit["grid_hash_mismatch"]+=1;continue
        ledger_rows[fid][model].append({"at":forecast_at,"grid":grid,"hash":r.get("score_grid_sha256"),"run":r.get("run_id")})
        ledger_sha.append(digest(canonical))

    candidate_ids={fid for fid,models in ledger_rows.items() if set(models)==set(MODELS)}
    common_keys=set(pred)&set(bykey); collisions=sum(len(bykey[k])!=1 for k in common_keys)
    unique_common_keys={k for k in common_keys if len(bykey[k])==1}
    selected={}; snap_stats={}
    for line in idx_raw.decode("utf-8").splitlines():
        try:e=json.loads(line)
        except ValueError: audit["bad_index_json"]+=1; continue
        fid=str(e.get("match_id") or "")
        if fid not in candidate_ids:continue
        path=base/str(e.get("snapshot_path") or "")
        try:
            st=path.stat();snap_stats[path]=(st.st_size,st.st_mtime_ns);raw=path.read_bytes();s=json.loads(raw)
        except (OSError,ValueError):audit["unreadable_snapshot"]+=1;continue
        if (s.get("match_id")!=fid or s.get("source_bookmaker")!="crown" or s.get("source_bookmaker_verified") is not True
                or s.get("classification")!="SNAPSHOT_OK" or s.get("prematch_valid") is not True):continue
        received=instant(s.get("received_at"));kickoff=instant(s.get("kickoff_at"))
        if not received or not kickoff or received>=kickoff:audit["bad_quote_chronology"]+=1;continue
        for market in ("AH","OU"):
            q=s.get(market) or {}; fields=("home_price","away_price") if market=="AH" else ("over_price","under_price")
            try:
                line_value=money_line(q.get("line")); prices={k:float(q[k]) for k in fields}
            except (ValueError,TypeError,KeyError):continue
            if any(not math.isfinite(v) or v<=1 for v in prices.values()):continue
            observed=instant(q.get("observed_at_utc") or q.get("observed_at") or s.get("received_at"))
            if not observed or observed>=kickoff or observed>received:continue
            k=(fid,market); cand={"observed":observed,"received":received,"kickoff":kickoff,
                                 "line":line_value,"prices":prices,"sha":digest(raw)}
            if k not in selected or observed>selected[k]["observed"]:selected[k]=cand

    # Source M3 models were trained from completed M1-cache historical scores;
    # choose the latest full score grid available by each Crown capture time.
    all_events={m:defaultdict(list) for m in ("AH","OU")}; exact_match={m:defaultdict(list) for m in ("AH","OU")}
    for (fid,market),quote in selected.items():
        entry=fixtures[fid]; f,kickoff,key=entry
        m3rows=pred.get(key,{})
        if len(m3rows)!=3 or any(model not in ledger_rows[fid] for model in MODELS):continue
        if any(m3rows[x].get("actual_home_goals")!=next(iter(m3rows.values())).get("actual_home_goals")
               or m3rows[x].get("actual_away_goals")!=next(iter(m3rows.values())).get("actual_away_goals") for x in MODELS):
            audit["m3_result_disagreement"]+=1;continue
        try:score=(int(next(iter(m3rows.values()))["actual_home_goals"]),int(next(iter(m3rows.values()))["actual_away_goals"]))
        except (TypeError,ValueError,KeyError):continue
        chosen={}
        for model in MODELS:
            eligible=[r for r in ledger_rows[fid][model] if r["at"]<=quote["observed"]]
            if not eligible:break
            chosen[model]=max(eligible,key=lambda r:r["at"])
        if len(chosen)!=3: audit["no_all_model_forecast_before_quote"]+=1;continue
        grids={m:chosen[m]["grid"] for m in MODELS}
        blend_grid=[]
        h=len(grids[MODELS[0]]);w=len(grids[MODELS[0]][0])
        if any(len(g)!=h or len(g[0])!=w for g in grids.values()):audit["model_grid_shape_mismatch"]+=1;continue
        for i in range(h):blend_grid.append([sum(weights[market][m]*float(grids[m][i][j]) for m in MODELS) for j in range(w)])
        price_quote={"line":quote["line"],"market":quote["prices"]}
        for model,grid in list(grids.items())+[("m5_walkforward_blend",blend_grid)]:
            pnl,category,dist=settle(grid,market,price_quote,score)
            row=(pnl,category,quote["observed"],dist,key[0])
            all_events[market][model].append(row)
            exact_match[market][model].append(row) if key in unique_common_keys else None

    results={m:{model:summarize(rows,20261104+(0 if m=="AH" else 1)) for model,rows in groups.items()} for m,groups in all_events.items()}
    exact={m:{model:summarize(rows,20261144+(0 if m=="AH" else 1)) for model,rows in groups.items()} for m,groups in exact_match.items()}
    if (idx.stat().st_size,idx.stat().st_mtime_ns)!=idx_stat or (regp.stat().st_size,regp.stat().st_mtime_ns)!=reg_stat:
        raise RuntimeError("Crown archive changed during run")
    for path,st in snap_stats.items():
        if (path.stat().st_size,path.stat().st_mtime_ns)!=st:raise RuntimeError("Crown snapshot changed during run")
    if (ledger.stat().st_size,ledger.stat().st_mtime_ns)!=ledger_stat:raise RuntimeError("M3 ledger changed during run")
    quote_counts=Counter(m for _,m in selected)
    return {"protocol":"M5_M3_CONTEMPORANEOUS_GRID_CROWN_REPLAY_V1","generated_utc":datetime.now(timezone.utc).isoformat(),
        "m3_forward_ledger_sha256":digest(ledger.read_bytes()),"m3_oos_csv_sha256":digest(pred_raw),"m5_stack_report_sha256":digest(stack_raw),
        "crown_registry_sha256":digest(reg_raw),"crown_index_sha256":digest(idx_raw),
        "crown_selected_snapshot_hash_set_sha256":digest("\n".join(sorted({q["sha"] for q in selected.values()})).encode()),
        "score_grid_hash_set_sha256":digest("\n".join(sorted(set(ledger_sha))).encode()),
        "exact_join_candidate_fixtures":len(unique_common_keys),"exact_join_identity_collisions_excluded":collisions,
        "m3_forward_fixture_ids_with_all_three_models":len(candidate_ids),
        "crown_quote_fixtures_by_market":dict(quote_counts),"crown_fixture_market_with_quote_and_three_forecasts":{m:len(v.get("m5_walkforward_blend",[])) for m,v in all_events.items()},
        "crown_fixture_market_in_m3_season_oos_join":{m:len(v.get("m5_walkforward_blend",[])) for m,v in exact_match.items()},
        "weights_from_prior_m3_oos_seasons":weights,"snapshot_audit_counts":dict(audit),"markets":results,
        "exact_join_m3_oos_subset":exact,
        "method":"Use latest contemporaneous full M3 score grid per model available by the saved, verified Crown quote observation time; latest valid Crown market quote observed before kickoff; choose higher expected-return side without EV gate; one unit; Asian split-line settlement.",
        "limitations":["M3 grids were generated by the M3 penaltyblog method trained on completed rows of the read-only M1 historical score cache, not M1 predictions or parameters.",
          "M3 forecast source filter requires completed training match start before model run; forecasts are timestamped before kickoff. Full source cache rows are not copied to this report.",
          "M5 blend weights were learned on prior season-forward M3 probability results and transferred to this distinct contemporaneous cache-trained grid cohort; this transfer is exploratory.",
          "Model outcome scoring uses the M3 strict-season OOS result artifact; no non-Crown price is used.",
          "Private identifiers, team names, quotes, and grids are not published."],
        "production_modified":False,"telegram_write":False,"network_requests":0}

def main():
    p=argparse.ArgumentParser();p.add_argument('--mr1-root',type=Path,required=True);p.add_argument('--m3-ledger',type=Path,required=True);p.add_argument('--m3-csv',type=Path,required=True);p.add_argument('--stack-report',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=analyze(a.mr1_root,a.m3_ledger,a.m3_csv,a.stack_report);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({k:out[k] for k in ('generated_utc','exact_join_candidate_fixtures','m3_forward_fixture_ids_with_all_three_models','crown_quote_fixtures_by_market','crown_fixture_market_with_quote_and_three_forecasts','markets')},indent=2))

if __name__=='__main__':main()
