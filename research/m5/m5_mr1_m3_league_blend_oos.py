#!/usr/bin/env python3
"""Compare 2025-trained global and per-league M1/MR1/M3 blends on 2026 Crown OOS.

Uses the exact shared Crown contracts and frozen model forecasts. Every 2026
fixture remains in the denominator; a league without 2025 training rows uses
the global 2025 weights. Public output is aggregate-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from research.m5.m5_m1_mr1_m3_learned_blend_oos import (
    CATEGORIES, MARKETS, MODELS, SIDES, arrays, expected_returns, fit_roi_weights, fit_weights, instant,
    load_market_rows, read_rows,
)
from research.m5.m3_grid_crown_replay import legs_result, payout


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bootstrap_difference(local: np.ndarray, global_: np.ndarray, seed: int, reps: int = 10000):
    if len(local) != len(global_) or not len(local):
        raise ValueError("paired non-empty series required")
    diff = local - global_
    rng = np.random.default_rng(seed)
    means = np.empty(reps)
    chunk = 200
    for start in range(0, reps, chunk):
        size = min(chunk, reps - start)
        means[start:start + size] = diff[rng.integers(0, len(diff), size=(size, len(diff)))].mean(axis=1)
    return {
        "mean_roi_difference_pct_local_minus_global": round(float(diff.mean() * 100), 6),
        "bootstrap_95pct": [round(float(x), 6) for x in np.quantile(means, [.025, .975])],
        "repetitions": reps,
        "unit": "paired fixture-market bootstrap",
    }


def settle(rows, weights_by_league, league_by_id, global_weights, market):
    pnl = []
    categories = Counter()
    log_losses = []
    briers = []
    event_pnl = defaultdict(float)
    per_league = defaultdict(list)
    fallbacks = 0
    for row in rows:
        league = league_by_id[row["id"]]
        weights = weights_by_league.get(league)
        if weights is None:
            weights = global_weights
            fallbacks += 1
        side_probs = row["probabilities"]
        mixed = np.einsum("msk,m->sk", side_probs, weights)
        prices = row["prices"]
        ev = expected_returns(mixed, prices)
        side_index = int(np.argmax(ev))
        side = SIDES[market][side_index]
        legs, category = legs_result(market, side, row["line"], *row["actual"])
        value = payout(legs, float(prices[side_index]))
        actual_index = int(row["actual_category_by_side"][side_index])
        distribution = mixed[side_index]
        pnl.append(value)
        categories[category] += 1
        event_pnl[row["event_utc"]] += value
        log_losses.append(-math.log(max(float(distribution[actual_index]), 1e-15)))
        briers.append(float(np.square(distribution - np.eye(len(CATEGORIES))[actual_index]).sum()))
        per_league[league].append(value)
    n = len(rows)
    equity = peak = dd = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    p = np.asarray(pnl, dtype=float)
    return {
        "unique_fixture_markets": n,
        "simulated_bets": n,
        "settled_bets": n,
        "stake_units": n,
        "net_units": round(float(p.sum()), 6),
        "roi_pct": round(float(p.mean() * 100), 6),
        "max_drawdown_units_by_quote_event_time": round(dd, 6),
        "settlement_counts": {key: categories[key] for key in CATEGORIES},
        "settlement_log_loss": round(float(np.mean(log_losses)), 8),
        "settlement_brier": round(float(np.mean(briers)), 8),
        "quote_sources": {"Crown": n},
        "response_receipt_timing": {"post_kickoff": n},
        "global_weight_fallback_fixtures": fallbacks,
        "per_league": {
            league: {
                "fixtures": len(values), "net_units": round(float(np.sum(values)), 6),
                "roi_pct": round(float(np.mean(values) * 100), 6),
            }
            for league, values in sorted(per_league.items())
        },
        "_pnl": p,
    }


def run(m1_path: Path, mr1_path: Path, m3_path: Path, output: Path):
    m1_raw, m1 = read_rows(m1_path, ("match_id", "market"))
    mr1_raw, mr1 = read_rows(mr1_path, ("match_id", "market"))
    m3_raw, m3 = read_rows(m3_path, ("match_id",))
    markets = {}
    timing = Counter()
    for mi, market in enumerate(MARKETS):
        rows, audit = load_market_rows(market, m1, mr1, m3)
        expected_n = 9517
        if audit.get("post_kickoff_provider_receipt") != expected_n or audit.get("prefixture_quote_event") != expected_n:
            raise ValueError(f"unexpected chronology counts for {market}: {dict(audit)}")
        non_timing_audit = {key: value for key, value in audit.items()
                            if key not in {"post_kickoff_provider_receipt", "prefixture_quote_event"}}
        if non_timing_audit:
            raise ValueError(f"input pairing audit failed for {market}: {non_timing_audit}")
        train = [row for row in rows if row["year"] == "2025"]
        test = [row for row in rows if row["year"] == "2026"]
        if len(train) != 1005 or len(test) != 8512:
            raise ValueError(f"unexpected frozen split for {market}: {len(train)}/{len(test)}")
        if {r["id"] for r in train} & {r["id"] for r in test}:
            raise ValueError("train/test fixture leakage")
        league_by_id = {fid: row["league"] for (fid, row_market), row in mr1.items()
                        if row_market == market}
        grouped = defaultdict(list)
        for row in train:
            grouped[league_by_id[row["id"]]].append(row)
        global_weights, global_fit = fit_weights(train)
        global_roi_weights, global_roi_fit = fit_roi_weights(train)
        local_weights = {league: fit_weights(group)[0] for league, group in grouped.items()}
        local_roi_weights = {league: fit_roi_weights(group)[0] for league, group in grouped.items()}
        fitted = {
            "global_logloss": ({}, global_weights),
            "league_logloss": (local_weights, global_weights),
            "global_roi": ({}, global_roi_weights),
            "league_roi": (local_roi_weights, global_roi_weights),
        }
        strategy_metrics = {}
        for strat_idx, (strategy, (local, fallback)) in enumerate(fitted.items()):
            metrics = settle(test, local, league_by_id, fallback, market)
            strategy_metrics[strategy] = metrics
        comparisons = {}
        for local_name, base_name, seed_offset in (("league_logloss", "global_logloss", 0),
                                                    ("league_roi", "global_roi", 1)):
            local_pnl = strategy_metrics[local_name].pop("_pnl")
            global_pnl = strategy_metrics[base_name].pop("_pnl")
            comparisons[local_name + "_minus_" + base_name] = bootstrap_difference(
                local_pnl, global_pnl, seed=202611090 + mi * 10 + seed_offset)
        # Restore private arrays are not published; remove the remaining pooled PnL vectors.
        strategy_metrics["global_logloss"].pop("_pnl", None)
        strategy_metrics["global_roi"].pop("_pnl", None)
        markets[market] = {
            "training_2025_fixture_markets": len(train),
            "holdout_2026_fixture_markets": len(test),
            "training_test_fixture_ids_disjoint": True,
            "trained_leagues": len(grouped),
            "global_2025_logloss_weights": {name: round(float(w), 8)
                                            for name, w in zip(MODELS, global_weights)},
            "global_2025_roi_weights": {name: round(float(w), 8)
                                        for name, w in zip(MODELS, global_roi_weights)},
            "global_fit_training_log_loss": global_fit["training_log_loss"],
            "global_fit_training_roi_pct": global_roi_fit["training_roi_pct"],
            "strategies_2026": strategy_metrics,
            "paired_roi_differences": comparisons,
            "per_league_logloss_weights": {
                league: {name: round(float(w), 8) for name, w in zip(MODELS, weights)}
                for league, weights in sorted(local_weights.items())
            },
            "per_league_roi_weights": {
                league: {name: round(float(w), 8) for name, w in zip(MODELS, weights)}
                for league, weights in sorted(local_roi_weights.items())
            },
        }
        timing[f"{market}_2025_provider_receipt_post_kickoff"] = len(train)
        timing[f"{market}_2026_provider_receipt_post_kickoff"] = len(test)
    report = {
        "protocol": "M5_MR1_M3_LEAGUE_LOCAL_BLEND_2025_FIT_2026_OOS_V2",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha(Path(__file__)),
        "input_sha256": {
            "m1_prediction_trace": hashlib.sha256(m1_raw).hexdigest(),
            "mr1_prediction_trace": hashlib.sha256(mr1_raw).hexdigest(),
            "m3_predictions_and_crown_quotes": hashlib.sha256(m3_raw).hexdigest(),
        },
        "audit_counts": {},
        "provider_receipt_timing": dict(timing),
        "markets": markets,
        "limitations": [
            "Exploratory per-league weights are fit on the single 2025 training season and evaluated on 2026; 2026 has been examined in prior M5 work and is not an untouched final confirmation set.",
            "ROI-fit weights directly optimize the selected-side 1U return on 2025 and are especially vulnerable to overfitting; they are research diagnostics only.",
            "All 2026 rows are retained. Leagues without 2025 training rows use the global 2025 weights; this is model fallback, not fixture filtering.",
            "The strict common cohort is Crown-only and 9,517 fixture-markets per market, below the 10,000 target.",
            "All historical Crown API response receipts were post-kickoff; ROI is retrospective quote-event replay, not contemporaneously executable return.",
            "No production model, trade rule, Telegram, order flow, ledger, or gate was changed.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({market: {
        name: {"roi_pct": metrics["roi_pct"], "net_units": metrics["net_units"]}
        for name, metrics in result["strategies_2026"].items()
    } for market, result in markets.items()}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m1-trace", type=Path, required=True)
    parser.add_argument("--mr1-trace", type=Path, required=True)
    parser.add_argument("--m3-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.m1_trace, args.mr1_trace, args.m3_rows, args.output)


if __name__ == "__main__":
    main()
