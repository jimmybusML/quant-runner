#!/usr/bin/env python3
"""Time-separated descriptive calibration of M5 expected returns at Crown prices.

Train-period quantiles define descriptive EV bins. The later quote-time holdout
is reported without selecting a trading filter or changing the M5 strategy.
Only aggregate metrics and source hashes are written to the public artifact.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m5_crown_temperature_holdout import evaluate, load_rows


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def summarize(metrics, seed=20261105):
    n = len(metrics)
    if not n:
        return {"fixtures": 0, "simulated_bets": 0, "settled_bets": 0,
                "net_units": 0.0, "roi_pct": None, "mean_predicted_ev_pct": None,
                "roi_fixture_bootstrap_95pct_interval": None, "settlements": {}}
    values = [x["units"] for x in metrics]
    rng = random.Random(seed)
    samples = sorted(100 * sum(values[rng.randrange(n)] for _ in range(n)) / n
                     for _ in range(10000))
    counts = Counter(x["category"] for x in metrics)
    net = sum(values)
    return {
        "fixtures": n,
        "simulated_bets": n,
        "settled_bets": n,
        "net_units": round(net, 6),
        "roi_pct": round(net * 100 / n, 6),
        "mean_predicted_ev_pct": round(100 * sum(x["ev"] for x in metrics) / n, 6),
        "roi_minus_mean_predicted_ev_percentage_points": round(100 * net / n - 100 * sum(x["ev"] for x in metrics) / n, 6),
        "settlements": {k: counts[k] for k in ("win", "half_win", "push", "half_loss", "loss")},
        "roi_fixture_bootstrap_95pct_interval": {
            "lower_2_5_pct": round(samples[249], 6),
            "upper_97_5_pct": round(samples[9749], 6),
            "resamples": 10000,
            "seed": seed,
        },
    }


def evaluate_lower_model_ev_side(row):
    """Fixed diagnostic comparator: settle the side with lower M5 EV."""
    from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
    market = row["market"]
    grid = row["forecast"]["prediction"]["grid"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    evs = [expected_return(grid, market, side, row["line"], price)
           for side, price in zip(sides, row["prices"])]
    idx = 0 if evs[0] < evs[1] else 1
    goals = (int(row["ft"]["home_goals"]), int(row["ft"]["away_goals"]))
    legs, category = legs_result(market, sides[idx], row["line"], *goals)
    return {"ev": evs[idx], "units": payout(legs, row["prices"][idx]), "category": category}


def run(mr1_root: Path, forecasts: Path, output: Path):
    rows_by_market, forecast_raw, index_raw, registry_raw = load_rows(mr1_root, forecasts)
    snapshot_hashes = sorted({row["snapshot_sha256"] for rows in rows_by_market.values() for row in rows})
    ft_hashes = sorted({row["ft_sha256"] for rows in rows_by_market.values() for row in rows})
    report_markets = {}
    for market, events in rows_by_market.items():
        if len(events) < 10:
            report_markets[market] = {"status": "insufficient_quotes", "source_verified_quotes": len(events)}
            continue
        train, test, cutoff, purged = __import__(
            "research.m5.m5_crown_temperature_holdout", fromlist=["chronological_split"]
        ).chronological_split(events)
        train_evs = sorted(evaluate(row, 1.0)["ev"] for row in train)
        if len(train_evs) < 4 or not test:
            report_markets[market] = {"status": "insufficient_temporal_holdout", "train": len(train), "test": len(test)}
            continue
        # Frozen quartile cut points are estimated from the early train period only.
        cuts = [train_evs[min(len(train_evs) - 1, math.ceil(q * len(train_evs) / 4) - 1)]
                for q in (1, 2, 3)]
        grouped = {i: [] for i in range(1, 5)}
        for row in test:
            metric = evaluate(row, 1.0)
            group = bisect.bisect_right(cuts, metric["ev"]) + 1
            grouped[group].append(metric)
        populated = {str(i): summarize(group, 20261105 + i)
                     for i, group in grouped.items() if group}
        test_metrics = [evaluate(row, 1.0) for row in test]
        lower_ev_metrics = [evaluate_lower_model_ev_side(row) for row in test]
        report_markets[market] = {
            "source_verified_unique_fixture_markets": len(events),
            "train_fixtures_with_FT_received_before_holdout_quote": len(train),
            "pre_cutoff_rows_purged_for_late_FT_receipt": purged,
            "untouched_later_quote_time_holdout_fixtures": len(test),
            "quote_time_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "holdout_quote_time_range_utc": [test[0]["observed"].isoformat().replace("+00:00", "Z"),
                                              test[-1]["observed"].isoformat().replace("+00:00", "Z")],
            "bin_cutpoints_frozen_from_training_period": True,
            "bin_definition": "Train-period quartiles of the M5 model's larger of the two Crown-price expected returns; tied cut values may create empty or unequal bins. Descriptive only.",
            "holdout_all_fixture_baseline": summarize(test_metrics, 20261104),
            "holdout_lower_M5_EV_side_diagnostic": summarize(lower_ev_metrics, 20261103),
            "holdout_by_training_EV_quartile": populated,
            "roi_gate_or_selection_rule_added": False,
        }
    report = {
        "protocol": "M5_MR1_CROWN_EV_TIME_SPLIT_CALIBRATION_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_sha256": sha(forecast_raw),
        "MR1_snapshot_index_sha256": sha(index_raw),
        "MR1_fixture_registry_sha256": sha(registry_raw),
        "verified_Crown_snapshot_count": len(snapshot_hashes),
        "verified_Crown_snapshot_hash_set_sha256": sha("\n".join(snapshot_hashes).encode()),
        "verified_FT_receipt_count": len(ft_hashes),
        "verified_FT_receipt_hash_set_sha256": sha("\n".join(ft_hashes).encode()),
        "markets": report_markets,
        "method": "Using exact MR1 verified Crown receipts and separate post-kickoff FT, one latest quote per fixture-market. Early-period train outcomes must have been received before the holdout quote boundary. Train-period expected-return quartiles are frozen and evaluated on the later quote-time holdout. No threshold is selected or applied.",
        "limitations": [
            "The verified Crown sample is short and concentrated in one recent period; bins are not strategy tests or evidence of cross-season stability.",
            "Some training-quantile cut points tie, yielding empty or unequal holdout groups.",
            "The model expected return uses the M5 full-score probability grid and the quoted Crown line/price; the realized ROI is noisy and the bootstrap interval is descriptive.",
            "Public artifact contains aggregate counts, metrics, and hashes only.",
        ],
        "crown_prices_used_only": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({m: {k: v for k, v in d.items() if k in (
        "source_verified_unique_fixture_markets", "train_fixtures_with_FT_received_before_holdout_quote",
        "pre_cutoff_rows_purged_for_late_FT_receipt", "untouched_later_quote_time_holdout_fixtures",
        "holdout_all_fixture_baseline", "holdout_by_training_EV_quartile")}
        for m, d in report_markets.items()}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mr1-root", type=Path, required=True)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.mr1_root, args.forecasts, args.output)


if __name__ == "__main__":
    main()
