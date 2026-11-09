#!/usr/bin/env python3
"""Fit settlement-probability temperatures on 2025, evaluate all 2026 rows.

The input is the private row-level Crown model-family replay. Public output is
aggregate only. Temperature is fit by 2025 settlement log loss, never by ROI;
all 2026 fixture-markets are retained and direction is recomputed at the same
Crown line and bilateral prices.
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

from research.m5.m5_line_conditional_settlement_calibration import (
    settlement_expected_return, temperature_adjust,
)

MODELS = ("M1", "MR1_V6", "M3_Poisson", "M3_Dixon_Coles", "M3_Bivariate_Poisson")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
REVERSE = {"win": "loss", "half_win": "half_loss", "push": "push",
           "half_loss": "half_win", "loss": "win"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fit_temperature(rows: list[dict]) -> tuple[float, bool]:
    if not rows:
        raise ValueError("empty 2025 calibration split")

    def objective(log_temperature: float) -> float:
        temperature = math.exp(log_temperature)
        return math.fsum(
            -math.log(max(temperature_adjust(row["distribution"], temperature)[row["category"]], 1e-15))
            for row in rows
        )

    low, high = math.log(0.25), math.log(4.0)
    result = minimize_scalar(objective, bounds=(low, high), method="bounded",
                             options={"xatol": 1e-9, "maxiter": 500})
    if not result.success or not math.isfinite(float(result.fun)):
        raise RuntimeError("temperature fit failed")
    boundary = min(abs(result.x - low), abs(result.x - high)) < 1e-5
    return math.exp(float(result.x)), bool(boundary)


def reverse_distribution(distribution: dict[str, float]) -> dict[str, float]:
    return {category: float(distribution[REVERSE[category]]) for category in CATEGORIES}


def evaluate(rows: list[dict], market: str, temperature: float) -> tuple[dict, list[float]]:
    if not rows:
        raise ValueError("empty evaluation split")
    sides = ("home", "away") if market == "AH" else ("over", "under")
    pnl_values, categories, log_losses, briers = [], Counter(), [], []
    by_event: dict[str, float] = defaultdict(float)
    for row in rows:
        chosen_side = str(row["side"]).lower()
        if chosen_side not in sides:
            raise ValueError("invalid archived side")
        source_index = sides.index(chosen_side)
        source_distribution = {key: float(value) for key, value in row["distribution"].items()}
        opposite = reverse_distribution(source_distribution)
        raw_options = [source_distribution if index == source_index else opposite for index in range(2)]
        options = [temperature_adjust(distribution, temperature) for distribution in raw_options]
        prices = [float(value) for value in row["prices"]]
        evs = [settlement_expected_return(distribution, price)
               for distribution, price in zip(options, prices)]
        selected_index = 0 if evs[0] >= evs[1] else 1
        actual = row["category"] if selected_index == source_index else REVERSE[row["category"]]
        price = prices[selected_index]
        pnl = {"win": price - 1.0, "half_win": (price - 1.0) / 2.0,
               "push": 0.0, "half_loss": -0.5, "loss": -1.0}[actual]
        pnl_values.append(pnl)
        categories[actual] += 1
        distribution = options[selected_index]
        log_losses.append(-math.log(max(distribution[actual], 1e-15)))
        briers.append(math.fsum((distribution[key] - float(key == actual)) ** 2 for key in CATEGORIES))
        by_event[row["quote_event_utc"]] += pnl
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    n = len(pnl_values)
    result = {
        "unique_fixture_markets": n,
        "simulated_bets": n,
        "settled_bets": n,
        "stake_units": n,
        "net_units": round(math.fsum(pnl_values), 6),
        "roi_pct": round(100 * math.fsum(pnl_values) / n, 6),
        "settlement_counts": {category: categories[category] for category in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "settlement_log_loss": round(math.fsum(log_losses) / n, 8),
        "settlement_brier": round(math.fsum(briers) / n, 8),
        "quote_source": "Crown",
        "response_receipt_timing": "post-kickoff; retrospective event-time replay",
    }
    return result, pnl_values


def bootstrap(values: list[float], seed: int, repetitions: int = 10000) -> dict:
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions)
    for start in range(0, repetitions, 200):
        size = min(200, repetitions - start)
        indices = rng.integers(0, len(array), size=(size, len(array)))
        means[start:start + size] = array[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975], method="linear")
    return {"method": "fixture percentile bootstrap, descriptive only",
            "repetitions": repetitions, "lower_95_roi_pct": round(100 * float(low), 6),
            "upper_95_roi_pct": round(100 * float(high), 6)}


def run(rows_path: Path, m1_path: Path, mr1_path: Path, m3_path: Path,
        family_report_path: Path, m5_replay_report_path: Path, output_path: Path) -> dict:
    repo = Path(__file__).resolve().parents[2]
    rows_path = rows_path.expanduser().resolve()
    if rows_path == repo or repo in rows_path.parents:
        raise ValueError("row-level model comparison input must remain outside the public repository")
    raw = rows_path.read_bytes()
    payload = json.loads(raw)
    result = {"protocol": "M5_MODEL_FAMILY_TEMPERATURE_2025_FIT_2026_HOLDOUT_V1",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "runner_sha256": sha(Path(__file__).resolve()),
              "input_sha256": {"private_model_family_rows": hashlib.sha256(raw).hexdigest(),
                               "model_family_comparison_report": sha(family_report_path),
                               "m5_crown_replay_report": sha(m5_replay_report_path),
                               "m1_trace": sha(m1_path), "mr1_trace": sha(mr1_path), "m3_grids": sha(m3_path)},
              "fit": {"period": "kickoff UTC year 2025", "target": "settlement-category log loss",
                      "temperature_bounds": [0.25, 4.0], "ROI_not_used_for_fit": True},
              "holdout": {"period": "kickoff UTC year 2026", "all_available_rows_retained": True,
                          "historical_receipts": "post-kickoff; retrospective event-time replay only"},
              "markets": {},
              "limitations": [
                  "The 2026 period has been examined in prior M5 research and is not an untouched confirmation set.",
                  "The exact M1/MR1/M3 archive intersection is below 10,000 per market; model-specific coverage is reported.",
                  "Historical Crown response receipts were post-kickoff; this is not contemporaneous execution ROI.",
                  "Temperature fitting changes probabilities only and introduces no fixture, league, price, time, or bet-count filter.",
              ]}
    seed = 202611090
    for market_index, market in enumerate(("AH", "OU")):
        result["markets"][market] = {}
        for model_index, model in enumerate(MODELS):
            rows = payload.get(market, {}).get(model)
            if not isinstance(rows, list):
                raise ValueError(f"missing rows: {market}/{model}")
            seen = set()
            train, test = [], []
            for row in rows:
                fixture_id = str(row["fixture_id"])
                if fixture_id in seen:
                    raise ValueError(f"duplicate fixture-market: {market}/{model}/{fixture_id}")
                seen.add(fixture_id)
                if row.get("market") != market or row.get("quote_event_utc", "") >= row.get("kickoff_utc", ""):
                    raise ValueError("market or quote/kickoff chronology mismatch")
                if row.get("category") not in CATEGORIES:
                    raise ValueError("invalid settlement category")
                year = row.get("kickoff_utc", "")[:4]
                if year == "2025":
                    train.append(row)
                elif year == "2026":
                    test.append(row)
            temperature, boundary = fit_temperature(train)
            raw_metrics, raw_pnl = evaluate(test, market, 1.0)
            calibrated_metrics, calibrated_pnl = evaluate(test, market, temperature)
            differences = [calibrated - baseline for calibrated, baseline in zip(calibrated_pnl, raw_pnl)]
            result["markets"][market][model] = {
                "training_fixture_markets_2025": len(train),
                "holdout_fixture_markets_2026": len(test),
                "fitted_temperature": round(temperature, 8),
                "temperature_fit_at_bound": bool(boundary),
                "raw_holdout": {**raw_metrics, "roi_bootstrap_95pct": bootstrap(raw_pnl, seed + market_index * 10 + model_index)},
                "calibrated_holdout": {**calibrated_metrics, "roi_bootstrap_95pct": bootstrap(calibrated_pnl, seed + 100 + market_index * 10 + model_index)},
                "paired_calibrated_minus_raw_roi_difference_bootstrap_95pct": bootstrap(
                    differences, seed + 200 + market_index * 10 + model_index),
            }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-model-family-rows", type=Path, required=True)
    parser.add_argument("--m1-trace", type=Path, required=True)
    parser.add_argument("--mr1-trace", type=Path, required=True)
    parser.add_argument("--m3-grids", type=Path, required=True)
    parser.add_argument("--model-family-report", type=Path, required=True)
    parser.add_argument("--m5-crown-replay-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_model_family_rows, args.m1_trace, args.mr1_trace,
                 args.m3_grids, args.model_family_report,
                 args.m5_crown_replay_report, args.output)
    print(json.dumps({market: {model: {
        "n": values["calibrated_holdout"]["settled_bets"],
        "temperature": values["fitted_temperature"],
        "raw_roi_pct": values["raw_holdout"]["roi_pct"],
        "calibrated_roi_pct": values["calibrated_holdout"]["roi_pct"],
        "paired_roi_difference_ci": values["paired_calibrated_minus_raw_roi_difference_bootstrap_95pct"],
    } for model, values in models.items()} for market, models in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
