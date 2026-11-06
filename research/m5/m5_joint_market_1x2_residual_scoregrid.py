#!/usr/bin/env python3
"""Joint Crown 1X2 and Asian-line residual score-grid experiment.

Fit AH and OU independently on 2025 exact-score NLL, then evaluate the full
2026 Crown-first/TotalCorner-default temporal holdout. Missing Crown 1X2
features contribute zero residual while the fixture-market stays in sample.
No ROI-based fitting, gates, or fixture filters are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import minimize

from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc
from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_crown_1x2_residual_scoregrid import (
    RESULTS, instant, residual_vector, select_crown_1x2, tilt_grid as tilt_1x2,
)
from research.m5.m5_line_conditional_settlement_calibration import (
    CATEGORIES, build_rows, settlement_distribution,
)
from research.m5.m5_market_residual_scoregrid_2025fit_2026holdout import (
    market_residual, tilt_grid as tilt_market,
)
from research.m5.m5_source_union_replay import read_jsonl

MARKETS = ("AH", "OU")


def _combined_grid(row, market, residuals, beta_market, beta_1x2):
    grid = tilt_market(row["grid"], market, residuals["market"], beta_market)
    if residuals["1x2"] is None:
        return grid
    return tilt_1x2(grid, residuals["1x2"], beta_1x2)


def _nll(rows, market, feature_map, params):
    beta_market, beta_1x2 = map(float, params)
    losses = []
    for row in rows:
        grid = _combined_grid(row, market, feature_map[row["match_id"]], beta_market, beta_1x2)
        home, away = row["score"]
        losses.append(-math.log(max(float(grid[home][away]), 1e-15)))
    return math.fsum(losses) / len(losses)


def fit_joint(rows, market, feature_map):
    if len(rows) < 20:
        raise ValueError(f"insufficient {market} training rows")
    bounds = ((-3.0, 3.0), (-2.0, 2.0))
    starts = ((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (-1.0, -1.0))
    candidates = []
    for initial in starts:
        fit = minimize(lambda x: _nll(rows, market, feature_map, x), np.asarray(initial),
                       method="L-BFGS-B", bounds=bounds,
                       options={"ftol": 1e-12, "gtol": 1e-8, "maxiter": 1000})
        if fit.success and math.isfinite(float(fit.fun)):
            candidates.append(fit)
    if not candidates:
        raise RuntimeError(f"{market} joint coefficient fit failed")
    fit = min(candidates, key=lambda x: float(x.fun))
    result = {"beta_market_line": float(fit.x[0]), "beta_crown_1x2": float(fit.x[1]),
              "training_rows": len(rows), "training_rows_with_1x2": sum(
                  feature_map[r["match_id"]]["1x2"] is not None for r in rows),
              "training_exact_score_nll_baseline": round(_nll(rows, market, feature_map, (0, 0)), 8),
              "training_exact_score_nll_joint_fit": round(float(fit.fun), 8),
              "training_fit_objective": "exact-score negative log likelihood; not ROI",
              "fit_at_search_boundary": (abs(abs(float(fit.x[0])) - 3.0) < 1e-3
                                           or abs(abs(float(fit.x[1])) - 2.0) < 1e-3)}
    # Separately fit each already-studied component on the same training rows.
    single_market = minimize(lambda x: _nll(rows, market, feature_map, (float(x[0]), 0.0)),
                             np.array([0.0]), method="L-BFGS-B", bounds=(bounds[0],),
                             options={"ftol": 1e-12, "maxiter": 1000})
    only_1x2 = minimize(lambda x: _nll(rows, market, feature_map, (0.0, float(x[0]))),
                        np.array([0.0]), method="L-BFGS-B", bounds=(bounds[1],),
                        options={"ftol": 1e-12, "maxiter": 1000})
    result["market_only_beta"] = float(single_market.x[0])
    result["1x2_only_beta"] = float(only_1x2.x[0])
    return result


def evaluate(rows, market, feature_map, params, seed):
    sides = ("home", "away") if market == "AH" else ("over", "under")
    counts, pnl_values, score_losses, briers = Counter(), [], [], []
    by_source, by_event = defaultdict(list), defaultdict(float)
    for row in rows:
        grid = _combined_grid(row, market, feature_map[row["match_id"]], *params)
        distributions = [settlement_distribution(grid, market, side, row["line"]) for side in sides]
        # Expected return is computed from the complete win/half/push/loss masses.
        returns = []
        for distribution, price in zip(distributions, row["prices"]):
            returns.append(math.fsum(distribution[c] * payoff for c, payoff in zip(
                CATEGORIES, (price - 1.0, (price - 1.0) / 2.0, 0.0, -0.5, -1.0))))
        index = 0 if returns[0] >= returns[1] else 1
        side = sides[index]
        legs, category = legs_result(market, side, row["line"], *row["score"])
        pnl = payout(legs, row["prices"][index])
        counts[category] += 1
        pnl_values.append(pnl)
        by_source[row["source"]].append(pnl)
        by_event[row["event_utc"]] += pnl
        distribution = distributions[index]
        score_losses.append(-math.log(max(float(distribution[category]), 1e-15)))
        briers.append(math.fsum((float(distribution[c]) - float(c == category)) ** 2
                                for c in CATEGORIES))
    n = len(rows)
    if n == 0:
        raise ValueError("empty evaluation cohort")
    net = math.fsum(pnl_values)
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    rng = np.random.default_rng(seed)
    pnl_array = np.asarray(pnl_values, dtype=float)
    boot = np.concatenate([100 * pnl_array[rng.integers(0, n, size=(100, n))].mean(axis=1)
                           for _ in range(30)])
    boot.sort()
    return {"unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
            "stake_units": n, "settlement_counts": {c: counts[c] for c in CATEGORIES},
            "net_units": round(net, 6), "roi_pct": round(100 * net / n, 6),
            "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
            "settlement_log_loss": round(math.fsum(score_losses) / n, 8),
            "settlement_brier": round(math.fsum(briers) / n, 8),
            "roi_bootstrap_95pct": {"lower": round(float(boot[74]), 6),
                                    "upper": round(float(boot[2924]), 6),
                                    "resamples": 3000, "seed": seed},
            "source_fixture_markets": dict(sorted(Counter(r["source"] for r in rows).items())),
            "source_split_roi": {source: {"n": len(values),
                "net_units": round(math.fsum(values), 6),
                "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
                for source, values in sorted(by_source.items())},
            "one_bet_per_fixture_market_no_filter": True}


def run(private_dir: Path, output: Path, source_timezone="Asia/Shanghai", forecast_path=None):
    samples, input_hashes, _ = build_rows(private_dir, source_timezone, forecast_path)
    root = ensure_private_destination(private_dir)
    forecast_file = forecast_path or root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecasts = {}
    for line in forecast_file.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    crown_index = {str(r.get("match_id")): r for r in read_jsonl(root / "crown-response-index.jsonl")}
    zone = ZoneInfo(source_timezone)
    quote_probs, quote_hashes = {}, set()
    for mid, forecast in forecasts.items():
        path = root / "crown-responses" / f"{mid}.json"
        if not path.exists():
            continue
        receipt = instant(crown_index.get(mid, {}).get("captured_at_utc"))
        quote = select_crown_1x2(path, mid, forecast, zone, receipt)
        if quote:
            quote_probs[mid] = quote
            quote_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())

    results = {}
    for market in MARKETS:
        train, test = samples[2025][market], samples[2026][market]
        train_ids = {r["match_id"] for r in train}
        test_ids = {r["match_id"] for r in test}
        if train_ids & test_ids:
            raise RuntimeError(f"{market} train/holdout fixture overlap")
        features = {}
        for row in train + test:
            quote = quote_probs.get(row["match_id"]) if row["source"] == "Crown" else None
            features[row["match_id"]] = {
                "market": market_residual(row, market),
                "1x2": residual_vector(row["grid"], quote["probabilities"]) if quote else None,
            }
        fitted = fit_joint(train, market, features)
        fitted_joint = (fitted["beta_market_line"], fitted["beta_crown_1x2"])
        fitted_market = (fitted["market_only_beta"], 0.0)
        fitted_1x2 = (0.0, fitted["1x2_only_beta"])
        results[market] = {
            "training_utc_kickoff_year": 2025, "holdout_utc_kickoff_year": 2026,
            "training_fixture_markets": len(train), "holdout_fixture_markets": len(test),
            "training_and_holdout_fixture_ids_disjoint": True,
            "holdout_source_counts": dict(Counter(r["source"] for r in test)),
            "training_quote_receipt_timing": dict(Counter(r["receipt_timing"] for r in train)),
            "holdout_quote_receipt_timing": dict(Counter(r["receipt_timing"] for r in test)),
            "holdout_rows_with_crown_1x2_feature": sum(features[r["match_id"]]["1x2"] is not None for r in test),
            "holdout_rows_retaining_baseline_1x2_component": sum(features[r["match_id"]]["1x2"] is None for r in test),
            "training_1x2_receipt_timing": dict(Counter(
                quote_probs[r["match_id"]]["receipt_timing"] for r in train
                if r["source"] == "Crown" and r["match_id"] in quote_probs)),
            "holdout_1x2_receipt_timing": dict(Counter(
                quote_probs[r["match_id"]]["receipt_timing"] for r in test
                if r["source"] == "Crown" and r["match_id"] in quote_probs)),
            "fitted_2025": fitted,
            "2026_holdout": {
                "baseline": evaluate(test, market, features, (0.0, 0.0), 20261120),
                "market_line_residual_only": evaluate(test, market, features, fitted_market, 20261121),
                "crown_1x2_residual_only": evaluate(test, market, features, fitted_1x2, 20261122),
                "joint_market_line_plus_crown_1x2": evaluate(test, market, features, fitted_joint, 20261123),
            },
        }
    report = {
        "protocol": "M5_JOINT_MARKET_AND_CROWN_1X2_RESIDUAL_2025_FIT_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_hashes": {**input_hashes, "crown_1x2_response_hash_set_sha256": hashlib.sha256(
            "\n".join(sorted(quote_hashes)).encode()).hexdigest()},
        "markets": results,
        "method": "Fit market-line and Crown 1X2 residual coefficients jointly by 2025 exact-score NLL, separately for AH and OU. Apply each feature only when available; missing 1X2 retains the market-line/base grid. Compare baseline and single-feature fits on the identical full 2026 holdout; choose the higher expected-return side per fixture-market at one unit, no filters or gates.",
        "source_and_time_integrity": {
            "price_source_priority": "Crown per fixture-market; TotalCorner default only when no eligible Crown market quote exists",
            "Crown_and_TotalCorner_kept_distinct": True,
            "TotalCorner_used_as_1x2_feature": False,
            "forecast_train_end_before_asof_before_quote_event_before_kickoff": True,
            "train_holdout_fixture_ids_disjoint": True,
            "historical_provider_receipts": "All selected historical receipts were post-kickoff; ROI is retrospective event-time replay, not receipt-verified executable return.",
            "AH_and_OU_fitted_and_reported_separately": True,
        },
        "limitations": ["2026 was inspected in prior M5 work and is not an untouched confirmatory holdout.",
                        "The joint model adds two train-fitted coefficients and may overfit; independent future forward results are required.",
                        "Retrospective quote event times do not prove that prices were received before kickoff."],
        "fixture_level_data_published": False, "production_changes": False, "new_bet_gate_added": False,
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
    print(json.dumps({m: {"training": v["training_fixture_markets"],
                          "holdout": v["holdout_fixture_markets"],
                          "fitted": v["fitted_2025"],
                          "results": {k: x["roi_pct"] for k, x in v["2026_holdout"].items()}}
                      for m, v in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
