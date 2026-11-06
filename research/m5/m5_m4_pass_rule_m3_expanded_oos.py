#!/usr/bin/env python3
"""Apply the existing M4 two-league Pass study as an exploratory M3 replay.

This does not turn M4 into a probability model or production gate. It applies
the already documented Japan J-League / Türkiye Super Lig exclusion to each
M3 model's expanded archive replay, with the same prices and outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from research.m5.m3_grid_crown_replay import legs_result, payout

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
MARKETS = ("AH", "OU")
PASS_LEAGUES = {"Japan J-League", "Türkiye Super Lig"}
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def ev(grid, market, side, line, price):
    total = 0.0
    for home, row in enumerate(grid):
        for away, prob in enumerate(row):
            legs, _ = legs_result(market, side, line, home, away)
            total += float(prob) * payout(legs, price)
    return total


def _group(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


def summarize(rows):
    pnl = math.fsum(x["pnl"] for x in rows)
    states = Counter(x["category"] for x in rows)
    by_time = defaultdict(float)
    for row in rows:
        by_time[row["event_utc"]] += row["pnl"]
    balance = peak = drawdown = 0.0
    for when in sorted(by_time):
        balance += by_time[when]
        peak = max(peak, balance)
        drawdown = max(drawdown, peak - balance)
    return {
        "unique_fixtures": len(rows), "simulated_bets": len(rows), "settled_bets": len(rows),
        "net_units": round(pnl, 6), "stake_units": len(rows),
        "roi_pct": round(100 * pnl / len(rows), 6) if rows else None,
        "settlement_counts": {c: states[c] for c in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "quote_sources": dict(Counter(x["source"] for x in rows)),
        "response_receipts": dict(Counter("pre_kickoff" if x["received_before_kickoff"] else "post_kickoff" for x in rows)),
        "by_utc_kickoff_year": {
            y: {"bets": len(group), "net_units": round(math.fsum(x["pnl"] for x in group), 6),
                "roi_pct": round(100 * math.fsum(x["pnl"] for x in group) / len(group), 6)}
            for y, group in sorted(_group(rows, "year").items())
        },
    }


def run(input_path: Path, report_path: Path):
    raw_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    base = {m: {model: [] for model in MODELS} for m in MARKETS}
    skipped = Counter()
    fixture_ids = {m: set() for m in MARKETS}
    with input_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            for market in MARKETS:
                quote = (row.get("quotes") or {}).get(market)
                if not quote:
                    skipped[f"missing_quote_{market}"] += 1
                    continue
                if not row.get("train_end_utc") < row.get("prediction_asof_utc") < row.get("kickoff_utc"):
                    skipped["invalid_prediction_chronology"] += 1
                    continue
                if not row.get("prediction_asof_utc") <= quote.get("event_utc") < row.get("kickoff_utc"):
                    skipped[f"invalid_quote_event_chronology_{market}"] += 1
                    continue
                fixture_ids[market].add(str(row["match_id"]))
                grid_map = row.get("model_score_grids") or {}
                for model in MODELS:
                    grid = grid_map.get(model)
                    if not grid:
                        skipped[f"missing_{model}_{market}"] += 1
                        continue
                    sides = ("home", "away") if market == "AH" else ("over", "under")
                    prices = quote["prices"]
                    evs = [ev(grid, market, side, float(quote["line"]), float(price))
                           for side, price in zip(sides, prices)]
                    idx = 0 if evs[0] >= evs[1] else 1
                    side, price = sides[idx], float(prices[idx])
                    legs, category = legs_result(market, side, float(quote["line"]),
                                                  int(row["actual_home_goals"]), int(row["actual_away_goals"]))
                    base[market][model].append({
                        "fixture_id": str(row["match_id"]), "league": row["league"],
                        "year": str(row["kickoff_utc"])[:4], "pnl": payout(legs, price),
                        "category": category, "event_utc": quote["event_utc"],
                        "source": quote["source"],
                        "received_before_kickoff": bool(quote["receipt_before_kickoff"]),
                    })

    markets = {}
    for market in MARKETS:
        markets[market] = {"common_fixture_count": len(fixture_ids[market]), "models": {}}
        for model, rows in base[market].items():
            kept = [x for x in rows if x["league"] not in PASS_LEAGUES]
            excluded = [x for x in rows if x["league"] in PASS_LEAGUES]
            markets[market]["models"][model] = {
                "all_M3_rows": summarize(rows),
                "M4_two_league_pass_exploratory": summarize(kept),
                "excluded_by_existing_M4_rule": summarize(excluded),
            }
    report = {
        "protocol": "M5_M4_EXISTING_PASS_RULE_ON_M3_EXPANDED_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_private_archive_sha256": raw_hash,
        "models": list(MODELS), "markets": markets,
        "excluded_leagues": sorted(PASS_LEAGUES),
        "method": "Recompute each existing M3 model's selected side on its exact M3-expanded archive quote and verified result; paired counterfactual removes Japan J-League and Türkiye Super Lig rows under the pre-existing M4 Pass research rule. One 1U per included fixture-market; no other filters or thresholds.",
        "limitations": [
            "M4 is a retrospective MR1-ledger league Pass study, not an independently trained prediction model.",
            "The two excluded leagues were selected after observing MR1 historical outcomes; applying that selected rule to this expanded archive is exploratory and not an untouched validation.",
            "Historical provider response receipts may be post-kickoff; simulated ROI does not establish executable prices.",
            "This research-only counterfactual does not modify any formal model or production gate.",
        ],
        "audit": {"skipped": dict(skipped), "fixture_id_counts": {m: len(ids) for m, ids in fixture_ids.items()}},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.input, args.report)
    print(json.dumps({m: {model: {
        "all": v["all_M3_rows"]["roi_pct"],
        "M4_pass": v["M4_two_league_pass_exploratory"]["roi_pct"],
        "n": v["M4_two_league_pass_exploratory"]["settled_bets"],
    } for model, v in report["markets"][m]["models"].items()} for m in MARKETS}, sort_keys=True))


if __name__ == "__main__":
    main()
