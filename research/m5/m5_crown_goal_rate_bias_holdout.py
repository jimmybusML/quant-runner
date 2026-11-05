#!/usr/bin/env python3
"""Outcome-safe global home/away goal-rate bias correction on Crown holdout.

Fits two multiplicative Poisson intercept corrections by maximum likelihood
using only unique training fixtures whose FT receipt predates a quote-time
cutoff. Applies the fixed correction to later M5 score grids and evaluates
AH/OU separately on the exact same verified Crown lines, prices, and FT.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
from research.m5.m5_mr1_v6_same_crown_oos import build_common_quotes, dt, sha


def forecast_for(row: dict, name: str) -> dict:
    return row["forecast"] if name == "M5_recency" else row["baseline_forecast"]


def fit_goal_rate_factors(rows: list[dict], name: str) -> dict:
    unique = {}
    for row in rows:
        unique.setdefault(row["match_id"], row)
    sum_home_goals = sum_away_goals = sum_home_lambda = sum_away_lambda = 0.0
    for row in unique.values():
        forecast = forecast_for(row, name)
        pred = forecast["prediction"]
        sum_home_goals += int(row["ft"]["home_goals"])
        sum_away_goals += int(row["ft"]["away_goals"])
        sum_home_lambda += float(pred["lambda_home"])
        sum_away_lambda += float(pred["lambda_away"])
    if not unique or sum_home_lambda <= 0 or sum_away_lambda <= 0:
        raise ValueError("invalid goal-rate calibration training sample")
    # For independent Poisson intercept multipliers, these are the exact
    # maximum-likelihood estimates: total observed goals / total predicted μ.
    return {
        "unique_training_fixtures": len(unique),
        "home_rate_multiplier": sum_home_goals / sum_home_lambda,
        "away_rate_multiplier": sum_away_goals / sum_away_lambda,
        "training_home_goals": int(sum_home_goals),
        "training_away_goals": int(sum_away_goals),
    }


def adjusted_grid(row: dict, name: str, factors: dict) -> list[list[float]]:
    forecast = forecast_for(row, name)
    grid = forecast["prediction"]["grid"]
    log_home = math.log(factors["home_rate_multiplier"])
    log_away = math.log(factors["away_rate_multiplier"])
    logp = []
    maximum = -math.inf
    for home, line in enumerate(grid):
        out = []
        for away, probability in enumerate(line):
            value = math.log(max(float(probability), 1e-300)) + home * log_home + away * log_away
            maximum = max(maximum, value)
            out.append(value)
        logp.append(out)
    weights = [[math.exp(value - maximum) for value in line] for line in logp]
    total = sum(sum(line) for line in weights)
    return [[value / total for value in line] for line in weights]


def evaluate_one(row: dict, name: str, grid: list[list[float]]) -> dict:
    market = row["market"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    ev = [expected_return(grid, market, side, row["line"], price)
          for side, price in zip(sides, row["prices"])]
    index = 0 if ev[0] >= ev[1] else 1
    side = sides[index]
    goals = (int(row["ft"]["home_goals"]), int(row["ft"]["away_goals"]))
    legs, category = legs_result(market, side, row["line"], *goals)
    units = payout(legs, row["prices"][index])

    categories = ("win", "half_win", "push", "half_loss", "loss")
    distribution = Counter()
    for home, probrow in enumerate(grid):
        for away, probability in enumerate(probrow):
            _, predicted_category = legs_result(market, side, row["line"], home, away)
            distribution[predicted_category] += probability
    actual_index = categories.index(category)
    probabilities = [distribution[key] for key in categories]
    log_loss = -math.log(max(probabilities[actual_index], 1e-15))
    brier = sum((p - (1.0 if i == actual_index else 0.0)) ** 2 for i, p in enumerate(probabilities))
    return {"units": units, "category": category, "ev": ev[index],
            "settlement_log_loss": log_loss, "settlement_brier": brier}


def summarize(rows: list[dict], name: str, factors: dict | None, seed: int) -> dict:
    scored = []
    for row in rows:
        forecast = forecast_for(row, name)
        grid = forecast["prediction"]["grid"] if factors is None else adjusted_grid(row, name, factors)
        scored.append((row, evaluate_one(row, name, grid)))
    n = len(scored)
    outcomes = Counter(result["category"] for _, result in scored)
    pnl_by_time: dict[datetime, float] = defaultdict(float)
    for row, result in scored:
        pnl_by_time[row["observed"]] += result["units"]
    equity = peak = max_dd = 0.0
    for instant in sorted(pnl_by_time):
        equity += pnl_by_time[instant]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    pnl = [result["units"] for _, result in scored]
    rng = random.Random(seed)
    boot = sorted(100 * sum(pnl[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)) if n else []
    return {
        "unique_fixture_markets": n,
        "simulated_bets": n,
        "settled_bets": n,
        "full_win": outcomes["win"],
        "half_win": outcomes["half_win"],
        "push": outcomes["push"],
        "half_loss": outcomes["half_loss"],
        "full_loss": outcomes["loss"],
        "net_units": round(sum(pnl), 6),
        "roi_pct": round(100 * sum(pnl) / n, 6) if n else None,
        "max_drawdown_by_quote_event_units": round(max_dd, 6) if n else None,
        "settlement_log_loss": round(sum(result["settlement_log_loss"] for _, result in scored) / n, 8) if n else None,
        "settlement_brier": round(sum(result["settlement_brier"] for _, result in scored) / n, 8) if n else None,
        "mean_selected_model_ev_pct": round(100 * sum(result["ev"] for _, result in scored) / n, 6) if n else None,
        "bootstrap_95pct_roi_interval": {
            "lower_2_5_pct": round(boot[249], 6),
            "upper_97_5_pct": round(boot[9749], 6),
            "resamples": 10000,
            "seed": seed,
        } if n else None,
    }


def run(mr1_root: Path, baseline_path: Path, candidate_path: Path, output: Path) -> dict:
    (chosen, counters, baseline_raw, candidate_raw, index_raw, registry_raw,
     record_hashes, snapshot_hashes, ft_hashes, baseline_n, candidate_n) = build_common_quotes(
        mr1_root, baseline_path, candidate_path
    )
    markets = {}
    for market in ("AH", "OU"):
        rows = sorted((row for (_, mkt), row in chosen.items() if mkt == market),
                      key=lambda row: (row["observed"], row["match_id"]))
        if not rows:
            markets[market] = {"status": "no_verified_quotes"}
            continue
        times = sorted({row["observed"] for row in rows})
        cutoff = times[int(len(times) * 0.70)]
        early = [row for row in rows if row["observed"] < cutoff]
        train = [row for row in early if dt(row["ft"].get("observed_at")) < cutoff]
        purged = [row for row in early if dt(row["ft"].get("observed_at")) >= cutoff]
        test = [row for row in rows if row["observed"] >= cutoff]
        train_ids = {row["match_id"] for row in train}
        test_ids = {row["match_id"] for row in test}
        if not train or not test or train_ids & test_ids:
            raise RuntimeError(f"{market}: invalid train/test partition")
        if any(dt(row["ft"].get("observed_at")) >= cutoff for row in train):
            raise RuntimeError(f"{market}: training FT receipt crosses holdout boundary")
        model_outputs = {}
        for i, name in enumerate(("M5_baseline", "M5_recency")):
            factors = fit_goal_rate_factors(train, name)
            model_outputs[name] = {
                "training_fixture_count": factors["unique_training_fixtures"],
                "training_FT_received_before_cutoff": True,
                "estimated_global_home_rate_multiplier": round(factors["home_rate_multiplier"], 8),
                "estimated_global_away_rate_multiplier": round(factors["away_rate_multiplier"], 8),
                "raw_later_holdout": summarize(test, name, None, 20261170 + i),
                "calibrated_later_holdout": summarize(test, name, factors, 20261180 + i),
            }
        markets[market] = {
            "unique_verified_fixture_markets": len(rows),
            "unique_quote_timestamps": len(times),
            "quote_time_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "early_quote_fixtures": len(early),
            "training_unique_fixtures": len(train_ids),
            "purged_early_quotes_late_FT_receipt": len(purged),
            "later_holdout_fixtures": len(test),
            "train_holdout_fixture_ids_disjoint": not bool(train_ids & test_ids),
            "all_training_FT_receipts_precede_cutoff": True,
            "models": model_outputs,
        }
    report = {
        "protocol": "M5_CROWN_GLOBAL_GOAL_RATE_BIAS_CORRECTION_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {
            "M5_baseline_forecasts": sha(baseline_raw),
            "M5_recency_forecasts": sha(candidate_raw),
            "MR1_snapshot_index": sha(index_raw),
            "MR1_fixture_registry": sha(registry_raw),
            "MR1_V6_records": sha("\n".join(sorted(record_hashes)).encode()),
            "verified_Crown_snapshots": sha("\n".join(sorted(snapshot_hashes)).encode()),
            "independent_FT_receipts": sha("\n".join(sorted(ft_hashes)).encode()),
        },
        "forecast_universe": {"baseline": baseline_n, "recency": candidate_n},
        "markets": markets,
        "validation_counts": dict(counters),
        "crown_prices_used_only": True,
        "roi_used_for_parameter_selection": False,
        "parameter_method": "Per market and model, estimate separate global home/away Poisson rate multipliers as sum(actual goals)/sum(unadjusted predicted λ) on unique early fixture identities. This is the exact two-intercept maximum-likelihood fit for Poisson counts. Apply score-grid exponential tilting by exp(home_goals*log(home_multiplier)+away_goals*log(away_multiplier)), then renormalize. No ROI tuning or gates.",
        "cutoff_method": "Within each market, chronological 70th percentile of distinct verified Crown quote-event UTC timestamps; all matches at the cutoff timestamp enter holdout. Purge early quotes whose separate FT receipt is not before cutoff.",
        "limitations": [
            "This 2026 Crown cohort was used in earlier M5 studies; chronological holdout is not pristine untouched validation.",
            "This estimates only two global scoring-rate offsets and does not model league-specific or market-specific drift.",
            "AH and OU are evaluated separately on 870 unique fixture-markets each; these are Crown ROI samples, not the 10,000-fixture objective.",
            "M5 forecasts are retrospective UTC walk-forward hindcasts, not contemporaneously archived M5 deployment predictions.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mr1-root", type=Path, required=True)
    parser.add_argument("--baseline-forecasts", type=Path, required=True)
    parser.add_argument("--candidate-forecasts", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results/m5_crown_goal_rate_bias_holdout.json")
    args = parser.parse_args()
    report = run(args.mr1_root, args.baseline_forecasts, args.candidate_forecasts, args.output)
    print(json.dumps({m: {"n": x["unique_verified_fixture_markets"], "train": x["training_unique_fixtures"], "holdout": x["later_holdout_fixtures"], "models": {name: {"raw_roi": metrics["raw_later_holdout"]["roi_pct"], "calibrated_roi": metrics["calibrated_later_holdout"]["roi_pct"], "home_factor": metrics["estimated_global_home_rate_multiplier"], "away_factor": metrics["estimated_global_away_rate_multiplier"]} for name, metrics in x["models"].items()}} for m, x in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
