#!/usr/bin/env python3
"""Fit source-aware market-residual tilts on 2025, evaluate 2026 OOS.

The M5 score grid is tilted along goal difference (AH) or total goals (OU)
according to the difference between de-vig market probability and M5's own
settlement probability at the exact quoted line. A single coefficient per
market/source is fit by exact-score log loss on 2025 only. The 2026 cohort is
kept intact and evaluated at the same event-time quote; no row filter/gate.
Fixture-level inputs and provider responses remain in the private archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_line_conditional_settlement_calibration import (
    CATEGORIES, build_rows, settlement_distribution, settlement_expected_return,
)

MARKETS = ("AH", "OU")


def logit(p: float) -> float:
    p = min(1.0 - 1e-12, max(1e-12, float(p)))
    return math.log(p / (1.0 - p))


def market_residual(row: dict, market: str) -> float:
    sides = ("home", "away") if market == "AH" else ("over", "under")
    base = [settlement_distribution(row["grid"], market, side, row["line"]) for side in sides]
    # Reciprocal-price normalization removes the two-way overround.
    inv = [1.0 / float(price) for price in row["prices"]]
    market_p0 = inv[0] / (inv[0] + inv[1])
    # For integer Asian lines, push mass is excluded; half settlements count
    # half toward each side. This yields the market/model comparable cover rate.
    p0 = base[0]["win"] + 0.5 * base[0]["half_win"]
    p1 = base[0]["loss"] + 0.5 * base[0]["half_loss"]
    model_p0 = p0 / (p0 + p1) if p0 + p1 > 0 else 0.5
    return logit(market_p0) - logit(model_p0)


def tilt_grid(grid: list[list[float]], market: str, residual: float, beta: float) -> list[list[float]]:
    if not math.isfinite(beta) or not math.isfinite(residual):
        raise ValueError("non-finite residual tilt")
    logs = []
    for home, values in enumerate(grid):
        row_logs = []
        for away, probability in enumerate(values):
            p = float(probability)
            if p < 0 or not math.isfinite(p):
                raise ValueError("invalid score-grid probability")
            coordinate = home - away if market == "AH" else home + away
            row_logs.append(math.log(max(p, 1e-300)) + beta * residual * coordinate)
        logs.append(row_logs)
    maximum = max(value for row in logs for value in row)
    weights = [[math.exp(value - maximum) for value in row] for row in logs]
    mass = math.fsum(value for row in weights for value in row)
    if not mass or not math.isfinite(mass):
        raise ValueError("invalid tilted score-grid mass")
    return [[value / mass for value in row] for row in weights]


def adjusted_grid(row: dict, market: str, beta: float) -> list[list[float]]:
    return tilt_grid(row["grid"], market, market_residual(row, market), beta)


def score_grid_nll(rows: list[dict], market: str, beta: float) -> float:
    losses = []
    for row in rows:
        grid = adjusted_grid(row, market, beta)
        home, away = row["score"]
        if home >= len(grid) or away >= len(grid[home]):
            raise ValueError("actual score outside model grid")
        losses.append(-math.log(max(grid[home][away], 1e-15)))
    return math.fsum(losses) / len(losses)


def fit_beta(rows: list[dict], market: str) -> dict:
    if len(rows) < 20:
        raise ValueError("at least 20 training rows required")
    fit = minimize_scalar(lambda b: score_grid_nll(rows, market, float(b)),
                          bounds=(-3.0, 3.0), method="bounded",
                          options={"xatol": 1e-6, "maxiter": 300})
    if not fit.success or not math.isfinite(float(fit.fun)):
        raise RuntimeError("market-residual coefficient fit failed")
    return {"training_rows": len(rows), "beta": float(fit.x),
            "training_scoregrid_log_loss_baseline": round(score_grid_nll(rows, market, 0.0), 8),
            "training_scoregrid_log_loss_fitted": round(float(fit.fun), 8),
            "fit_objective": "exact score negative log likelihood; ROI not used",
            "coefficient_at_search_boundary": abs(abs(float(fit.x)) - 3.0) < 1e-3}


def summarize(rows: list[dict], market: str, beta: float, seed: int) -> dict:
    if not rows:
        return {"unique_fixture_markets": 0, "roi_pct": None}
    sides = ("home", "away") if market == "AH" else ("over", "under")
    decisions = []
    category_counts = Counter()
    score_losses, briers = [], []
    by_event = defaultdict(float)
    for row in rows:
        grid = adjusted_grid(row, market, beta)
        distributions = [settlement_distribution(grid, market, side, row["line"]) for side in sides]
        evs = [settlement_expected_return(dist, float(price))
               for dist, price in zip(distributions, row["prices"])]
        index = 0 if evs[0] >= evs[1] else 1
        side = sides[index]
        actual = legs_result(market, side, row["line"], *row["score"])[1]
        pnl = payout(legs_result(market, side, row["line"], *row["score"])[0], row["prices"][index])
        dist = distributions[index]
        category_counts[actual] += 1
        score_losses.append(-math.log(max(float(dist[actual]), 1e-15)))
        briers.append(math.fsum((float(dist[c]) - float(c == actual)) ** 2 for c in CATEGORIES))
        by_event[row["event_utc"]] += pnl
        decisions.append({"pnl": pnl, "source": row["source"], "category": actual})
    n = len(decisions)
    net = math.fsum(x["pnl"] for x in decisions)
    equity = peak = max_dd = 0.0
    for when in sorted(by_event):
        equity += by_event[when]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    rng = np.random.default_rng(seed)
    pnl = np.asarray([x["pnl"] for x in decisions], dtype=float)
    boot = []
    for start in range(0, 1000, 100):
        indexes = rng.integers(0, n, size=(100, n))
        boot.extend((100.0 * pnl[indexes].mean(axis=1)).tolist())
    boot.sort()
    source_split = {}
    for source in sorted({x["source"] for x in decisions}):
        values = [x["pnl"] for x in decisions if x["source"] == source]
        source_split[source] = {"unique_fixture_markets": len(values),
                                "net_units": round(math.fsum(values), 6),
                                "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n,
        "settlement_counts": {category: category_counts[category] for category in CATEGORIES},
        "net_units": round(net, 6), "roi_pct": round(100 * net / n, 6),
        "max_drawdown_units_by_quote_event_time": round(max_dd, 6),
        "settlement_log_loss": round(math.fsum(score_losses) / n, 8),
        "settlement_brier": round(math.fsum(briers) / n, 8),
        "roi_bootstrap_95pct": {"lower": round(boot[24], 6), "upper": round(boot[974], 6),
                                "resamples": 1000, "seed": seed},
        "source_fixture_markets": dict(sorted(Counter(x["source"] for x in decisions).items())),
        "source_split_roi": source_split,
        "one_bet_per_fixture_market_no_filter": True,
    }


def run(private_dir: Path, output: Path, source_timezone: str, forecast_path: Path | None = None) -> dict:
    samples, hashes, counts = build_rows(private_dir, source_timezone, forecast_path)
    result = {}
    for market in MARKETS:
        train = samples[2025][market]
        test = samples[2026][market]
        if not train or not test:
            raise ValueError(f"missing 2025 training or 2026 holdout rows for {market}")
        if len({r["match_id"] for r in train} & {r["match_id"] for r in test}):
            raise RuntimeError("fixture identity leaked between train and holdout")
        betas = {"pooled_2025": fit_beta(train, market)}
        for source in ("Crown", "TotalCorner_default"):
            source_rows = [r for r in train if r["source"] == source]
            if len(source_rows) >= 20:
                betas[f"{source}_2025"] = fit_beta(source_rows, market)
        test_results = {}
        for name, params in betas.items():
            beta = params["beta"]
            test_results[name] = {
                "fitted_beta": beta,
                "baseline_beta_zero": summarize(test, market, 0.0, 20261110),
                "market_residual": summarize(test, market, beta, 20261111),
                "training_rows_by_source": dict(Counter(r["source"] for r in
                    (train if name == "pooled_2025" else
                     [r for r in train if r["source"] == name.removesuffix("_2025")])))
            }
        result[market] = {
            "training_utc_kickoff_year": 2025,
            "holdout_utc_kickoff_year": 2026,
            "training_unique_fixture_markets": len(train),
            "holdout_unique_fixture_markets": len(test),
            "training_and_holdout_fixture_ids_disjoint": True,
            "training_2025_coefficients": betas,
            "2026_holdout_results": test_results,
        }
    report = {
        "protocol": "M5_MARKET_RESIDUAL_SCOREGRID_2025_FIT_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_hashes": hashes,
        "training_holdout_source_counts": dict(counts),
        "markets": result,
        "method": "Fit one market-specific residual coefficient, and optional source-specific coefficients, on 2025 exact-score log loss. Adjust the M5 score grid by exponential tilt along goal difference (AH) or total goals (OU), using the logit difference between no-vig two-way price probability and M5 settlement probability at that exact line. In 2026, choose the higher expected-return side for every eligible fixture-market at the same source quote and stake one unit; no filters or ROI gates.",
        "source_and_time_integrity": {
            "Crown_and_TotalCorner_default_are_distinct": True,
            "source_priority": "Crown per fixture-market; TotalCorner default only when no eligible Crown quote exists",
            "fixture_markets_deduplicated": True,
            "forecast_train_end_before_asof_before_quote_event_before_kickoff": True,
            "api_receipt_timing": "All selected historical provider receipts were post-kickoff; ROI is event-time retrospective, not pregame receipt-verified or executable ROI.",
            "AH_and_OU_fit_and_report_separately": True,
        },
        "limitations": [
            "2026 has been examined in earlier M5 research; this is a new method on a previously explored temporal holdout, not an untouched confirmatory test.",
            "The method assumes no-vig two-way Asian odds provide an approximate side probability after excluding push mass; quarter-line half settlements remain represented exactly in the score grid.",
            "TotalCorner-only 2026 coverage is smaller than 10,000; the pooled Crown-first union is the only 2026 holdout meeting the per-market sample target.",
        ],
        "fixture_level_data_published": False,
        "production_changes": False,
        "new_bet_gate_added": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--forecast-path", type=Path)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_dir, args.output, args.source_timezone, args.forecast_path)
    print(json.dumps({market: {"training": item["training_unique_fixture_markets"],
                              "holdout": item["holdout_unique_fixture_markets"],
                              "models": item["2026_holdout_results"]}
                      for market, item in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
