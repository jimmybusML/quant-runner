#!/usr/bin/env python3
"""Research whether fitting a score-grid market residual by ROI generalizes.

AH and OU are optimized independently on the 2025 training slice. Every
eligible 2026 fixture-market remains in the holdout and is scored at 1U; this
is a model-parameter experiment, not an EV gate or a production rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_line_conditional_settlement_calibration import (
    build_rows, settlement_distribution, settlement_expected_return,
)
from research.m5.m5_market_residual_scoregrid_2025fit_2026holdout import (
    adjusted_grid, summarize,
)

MARKETS = ("AH", "OU")


def select_beta(search_values, objective):
    """Select highest training ROI; resolve ties toward the smallest tilt."""
    evaluated = [(float(objective(float(beta))), float(beta)) for beta in search_values]
    if not evaluated or any(not np.isfinite(score) for score, _ in evaluated):
        raise ValueError("beta search must have finite objective values")
    return sorted(evaluated, key=lambda item: (-item[0], abs(item[1]), item[1]))[0]


def roi_objective(rows, market: str, beta: float) -> float:
    sides = ("home", "away") if market == "AH" else ("over", "under")
    net = 0.0
    for row in rows:
        grid = adjusted_grid(row, market, beta)
        distributions = [settlement_distribution(grid, market, side, row["line"])
                         for side in sides]
        expected_returns = [settlement_expected_return(dist, price)
                            for dist, price in zip(distributions, row["prices"])]
        index = 0 if expected_returns[0] >= expected_returns[1] else 1
        legs, _ = legs_result(market, sides[index], row["line"], *row["score"])
        net += payout(legs, row["prices"][index])
    return 100.0 * net / len(rows) if rows else float("nan")


def run(private_dir: Path, output: Path, comparison_path: Path,
        source_timezone: str = "Asia/Shanghai") -> dict:
    samples, hashes, counts = build_rows(private_dir, source_timezone, None)
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    if comparison.get("input_hashes") != hashes:
        raise ValueError("comparison report input hashes do not match rebuilt cohort")

    beta_grid = np.linspace(-3.0, 3.0, 121)
    results = {}
    for index, market in enumerate(MARKETS):
        train, holdout = samples[2025][market], samples[2026][market]
        if not train or not holdout:
            raise ValueError(f"missing 2025 train or 2026 holdout rows for {market}")
        train_ids = {row["match_id"] for row in train}
        holdout_ids = {row["match_id"] for row in holdout}
        if train_ids & holdout_ids:
            raise ValueError(f"fixture identity leaked across {market} time split")

        objective = lambda beta: roi_objective(train, market, beta)
        training_roi, beta = select_beta(beta_grid, objective)
        prior = comparison["markets"][market]
        score_fit = prior["2026_holdout_results"]["pooled_2025"]
        seed = 20261170 + index
        results[market] = {
            "training_fixture_markets": len(train),
            "holdout_fixture_markets": len(holdout),
            "training_holdout_fixture_ids_disjoint": True,
            "roi_fit": {
                "parameter": "beta",
                "search_values": 121,
                "search_range": [-3.0, 3.0],
                "selected_beta": beta,
                "selection_objective": "2025 training ROI; no holdout outcomes used",
                "training_metrics": summarize(train, market, beta, seed),
                "holdout_metrics": summarize(holdout, market, beta, seed + 10),
            },
            "holdout_comparators": {
                "unadjusted_beta_zero": score_fit["baseline_beta_zero"],
                "beta_fit_on_2025_scoregrid_log_loss": {
                    "beta": score_fit["fitted_beta"],
                    "metrics": score_fit["market_residual"],
                },
            },
        }

    report = {
        "protocol": "M5_MARKET_RESIDUAL_ROI_FIT_2025_TRAIN_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "comparison_runner_sha256": hashlib.sha256(
            Path("research/m5/m5_market_residual_scoregrid_2025fit_2026holdout.py").read_bytes()
        ).hexdigest(),
        "input_hashes": hashes,
        "source_counts_by_market_year": dict(counts),
        "markets": results,
        "method": (
            "Separately select beta for AH and OU from a fixed 121-value grid using only "
            "2025 1U training ROI. The model applies an exponential score-grid tilt from "
            "the no-vig market residual, chooses the higher expected-return side for every "
            "eligible fixture-market, and evaluates all 2026 holdout rows without filters."
        ),
        "source_and_time_integrity": {
            "crown_and_totalcorner_default_distinct": True,
            "fixture_markets_deduplicated": True,
            "training_before_holdout_and_ids_disjoint": True,
            "market_source_rule": "Crown preferred per fixture-market; TotalCorner default fills missing Crown markets",
            "historical_provider_receipts": "post-kickoff; retrospective event-time replay, not executable ROI",
        },
        "limitations": [
            "This parameter search was selected after extensive inspection of the 2026 period; results are exploratory, not an untouched confirmation.",
            "The 2025 training slice is much smaller than the 2026 holdout and ROI selection is noisy.",
            "No fixture-level data is included in this report; no production change, EV gate, or market filter is made.",
        ],
        "fixture_level_data_published": False,
        "production_changes": False,
        "new_bet_gate_added": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.private_dir, args.output, args.comparison, args.source_timezone)
    print(json.dumps({market: {
        "n": rows["holdout_fixture_markets"],
        "beta": rows["roi_fit"]["selected_beta"],
        "training_roi_pct": rows["roi_fit"]["training_metrics"]["roi_pct"],
        "holdout_roi_pct": rows["roi_fit"]["holdout_metrics"]["roi_pct"],
        "baseline_holdout_roi_pct": rows["holdout_comparators"]["unadjusted_beta_zero"]["roi_pct"],
    } for market, rows in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
