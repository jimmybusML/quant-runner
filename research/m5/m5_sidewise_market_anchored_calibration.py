#!/usr/bin/env python3
"""Fit a two-sided multinomial calibration layer on 2025, evaluate 2026.

Input is the private, exact-line M1/MR1/M3 Crown comparison archive. For each
fixture, each side becomes a training example with its own reversed settlement
distribution and label. Hyperparameter selection uses only the latest 25% of
2025 fixture dates and settlement log loss. Every 2026 fixture is retained;
the model chooses the higher calibrated expected-return side with no threshold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
REVERSE = {"win": "loss", "half_win": "half_loss", "push": "push",
           "half_loss": "half_win", "loss": "win"}
MODELS = ("M1", "MR1_V6", "M3_Poisson", "M3_Dixon_Coles", "M3_Bivariate_Poisson")
MARKETS = ("AH", "OU")
C_GRID = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
EPSILON = 1e-8


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def reverse_distribution(distribution: dict[str, float]) -> dict[str, float]:
    return {category: float(distribution[REVERSE[category]]) for category in CATEGORIES}


def make_features(distribution: dict[str, float], price: float,
                  opposing_price: float, line: float) -> np.ndarray:
    probs = np.asarray([float(distribution[c]) for c in CATEGORIES], dtype=float)
    if (not np.isfinite(probs).all() or np.any(probs < -1e-9)
            or abs(float(probs.sum()) - 1.0) > 1e-6):
        raise ValueError("invalid settlement probability vector")
    if not (math.isfinite(price) and math.isfinite(opposing_price)
            and price > 1.0 and opposing_price > 1.0 and math.isfinite(line)):
        raise ValueError("invalid price or line")
    return np.r_[np.log(np.maximum(probs, EPSILON)), math.log(price),
                 math.log(opposing_price), line]


def two_sided_rows(rows: list[dict], market: str):
    sides = ("home", "away") if market == "AH" else ("over", "under")
    output = []
    for row in rows:
        original_side = row["side"]
        if original_side not in sides:
            raise ValueError("invalid selected side")
        chosen = sides.index(original_side)
        dist = {key: float(row["distribution"][key]) for key in CATEGORIES}
        opposite = reverse_distribution(dist)
        prices = [float(x) for x in row["prices"]]
        if len(prices) != 2:
            raise ValueError("expected both Crown prices")
        actual = row["category"]
        if actual not in CATEGORIES:
            raise ValueError("invalid actual settlement category")
        for index, side in enumerate(sides):
            side_dist = dist if index == chosen else opposite
            category = actual if index == chosen else REVERSE[actual]
            features = make_features(side_dist, prices[index], prices[1-index], float(row["line"]))
            output.append({"fixture_id": str(row["fixture_id"]), "kickoff_utc": row["kickoff_utc"],
                           "features": features, "category": category,
                           "side": side, "price": prices[index]})
    return output


def scale_features(train_x: np.ndarray, *others: np.ndarray):
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1e-10] = 1.0
    return [(x - mean) / scale for x in (train_x, *others)]


def fit_softmax(x: np.ndarray, labels: list[str], c_value: float):
    """L2-regularized multinomial logistic model with fixed five classes."""
    y = np.asarray([CATEGORIES.index(label) for label in labels], dtype=int)
    n, width = x.shape
    target = np.eye(len(CATEGORIES))[y]
    regularization = 1.0 / c_value

    def objective(flat):
        weights = flat[:width * len(CATEGORIES)].reshape(width, len(CATEGORIES))
        intercept = flat[width * len(CATEGORIES):]
        logits = x @ weights + intercept
        log_probs = logits - logsumexp(logits, axis=1, keepdims=True)
        probs = np.exp(log_probs)
        loss = -float(log_probs[np.arange(n), y].mean()) + 0.5 * regularization * float((weights ** 2).sum()) / n
        grad_weights = x.T @ (probs - target) / n + regularization * weights / n
        grad_intercept = (probs - target).mean(axis=0)
        gradient = np.r_[grad_weights.ravel(), grad_intercept]
        return loss, gradient

    result = minimize(objective, np.zeros(width * len(CATEGORIES) + len(CATEGORIES)),
                      method="L-BFGS-B", jac=True, options={"maxiter": 2000, "ftol": 1e-12})
    if not result.success or not np.isfinite(result.fun):
        raise RuntimeError("multinomial calibration fit failed")
    return result.x[:width * len(CATEGORIES)].reshape(width, len(CATEGORIES)), result.x[width * len(CATEGORIES):]


def predict_softmax(params, x: np.ndarray) -> np.ndarray:
    weights, intercept = params
    return softmax(x @ weights + intercept, axis=1)


def fit_select_c(train_rows: list[dict], market: str):
    fixtures = sorted({row["fixture_id"]: row["kickoff_utc"] for row in train_rows}.items(),
                      key=lambda item: (item[1], item[0]))
    if len(fixtures) < 40:
        raise ValueError("not enough 2025 fixture dates for chronological calibration split")
    cut = max(1, min(len(fixtures) - 1, int(math.floor(len(fixtures) * 0.75))))
    fit_ids = {fixture_id for fixture_id, _ in fixtures[:cut]}
    val_ids = {fixture_id for fixture_id, _ in fixtures[cut:]}
    assert not fit_ids & val_ids
    all_sides = two_sided_rows(train_rows, market)
    fit = [row for row in all_sides if row["fixture_id"] in fit_ids]
    validation = [row for row in all_sides if row["fixture_id"] in val_ids]
    x_fit = np.stack([r["features"] for r in fit])
    x_val = np.stack([r["features"] for r in validation])
    x_fit, x_val = scale_features(x_fit, x_val)
    y_fit = [r["category"] for r in fit]
    y_val = [r["category"] for r in validation]
    candidates = []
    for c_value in C_GRID:
        estimator = fit_softmax(x_fit, y_fit, c_value)
        probabilities = predict_softmax(estimator, x_val)
        labels_index = np.asarray([CATEGORIES.index(label) for label in y_val], dtype=int)
        loss = float(-np.log(np.maximum(probabilities[np.arange(len(y_val)), labels_index], EPSILON)).mean())
        candidates.append((loss, c_value))
    best_loss, best_c = min(candidates)
    metadata = {"2025_fixtures": len(fixtures), "inner_fit_fixtures": len(fit_ids),
                "inner_validation_fixtures": len(val_ids), "inner_fit_two_side_rows": len(fit),
                "inner_validation_two_side_rows": len(validation), "selected_C_by_validation_log_loss": best_c,
                "validation_log_loss": round(best_loss, 8),
                "validation_log_loss_by_C": {str(c_value): round(loss, 8)
                                             for loss, c_value in candidates},
                "validation_dates": [fixtures[cut][1], fixtures[-1][1]]}
    return metadata


def fit_full(rows: list[dict], market: str, c_value: float):
    examples = two_sided_rows(rows, market)
    x = np.stack([r["features"] for r in examples])
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-10] = 1.0
    model = fit_softmax((x-mean)/scale, [r["category"] for r in examples], c_value)
    return model, mean, scale


def ev(distribution: dict[str, float], price: float) -> float:
    return (distribution["win"] * (price - 1.0)
            + distribution["half_win"] * (price - 1.0) / 2.0
            - distribution["half_loss"] / 2.0 - distribution["loss"])


def roi_metrics(pnls: list[float], categories: list[str], ll: list[float], brier: list[float],
                seed: int) -> dict:
    n = len(pnls)
    if not n:
        raise ValueError("empty holdout")
    rng = np.random.default_rng(seed)
    values = np.asarray(pnls, dtype=float)
    means = np.empty(10000)
    for start in range(0, len(means), 200):
        size = min(200, len(means) - start)
        means[start:start+size] = rng.choice(values, size=(size, n), replace=True).mean(axis=1)
    counts = {category: categories.count(category) for category in CATEGORIES}
    total = math.fsum(pnls)
    equity = peak = dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {"fixture_markets": n, "simulated_bets": n, "settled_bets": n, "stake_units": n,
            "settlement_counts": counts, "net_units": round(total, 6),
            "roi_pct": round(100 * total / n, 6),
            "max_drawdown_units_in_quote_event_order": round(dd, 6),
            "roi_bootstrap_95pct": {"lower_95_roi_pct": round(100 * float(np.quantile(means, .025)), 6),
                                    "upper_95_roi_pct": round(100 * float(np.quantile(means, .975)), 6),
                                    "repetitions": len(means), "method": "fixture bootstrap"},
            "settlement_log_loss": round(math.fsum(ll) / n, 8),
            "settlement_brier": round(math.fsum(brier) / n, 8)}


def paired_roi_difference_bootstrap(calibrated: list[float], baseline: list[float], seed: int) -> dict:
    if len(calibrated) != len(baseline) or not calibrated:
        raise ValueError("paired ROI series must have same nonzero length")
    differences = np.asarray(calibrated, dtype=float) - np.asarray(baseline, dtype=float)
    rng = np.random.default_rng(seed)
    samples = np.empty(10000)
    for start in range(0, len(samples), 200):
        size = min(200, len(samples) - start)
        idx = rng.integers(0, len(differences), size=(size, len(differences)))
        samples[start:start+size] = differences[idx].mean(axis=1)
    low, high = np.quantile(samples, [0.025, 0.975])
    return {"lower_95_difference_pp": round(100 * float(low), 6),
            "upper_95_difference_pp": round(100 * float(high), 6),
            "method": "paired fixture bootstrap", "repetitions": len(samples)}


def score_holdout(rows: list[dict], market: str, model, mean: np.ndarray, scale: np.ndarray,
                  seed: int) -> tuple[dict, list[float]]:
    sides = ("home", "away") if market == "AH" else ("over", "under")
    pnls, categories, losses, briers = [], [], [], []
    for row in sorted(rows, key=lambda r: (r["quote_event_utc"], r["fixture_id"])):
        examples = two_sided_rows([row], market)
        x = np.stack([r["features"] for r in examples])
        raw_proba = predict_softmax(model, (x-mean)/scale)
        calibrated = []
        for probs in raw_proba:
            dist = {category: float(value) for category, value in zip(CATEGORIES, probs)}
            calibrated.append(dist)
        prices = [float(x) for x in row["prices"]]
        selected = 0 if ev(calibrated[0], prices[0]) >= ev(calibrated[1], prices[1]) else 1
        original_side_idx = sides.index(row["side"])
        actual = row["category"] if selected == original_side_idx else REVERSE[row["category"]]
        price = prices[selected]
        pnl = {"win": price-1, "half_win": (price-1)/2, "push": 0.0,
               "half_loss": -0.5, "loss": -1.0}[actual]
        p = max(calibrated[selected][actual], EPSILON)
        losses.append(-math.log(p))
        briers.append(math.fsum((calibrated[selected][category] - float(category == actual))**2
                                for category in CATEGORIES))
        categories.append(actual)
        pnls.append(pnl)
    return roi_metrics(pnls, categories, losses, briers, seed), pnls


def baseline_metrics(rows: list[dict], seed: int) -> tuple[dict, list[float]]:
    pnls, categories, ll, brier = [], [], [], []
    for row in sorted(rows, key=lambda r: (r["quote_event_utc"], r["fixture_id"])):
        category = row["category"]
        distribution = row["distribution"]
        pnls.append(float(row["pnl"]))
        categories.append(category)
        ll.append(-math.log(max(float(distribution[category]), EPSILON)))
        brier.append(math.fsum((float(distribution[c]) - float(c == category))**2 for c in CATEGORIES))
    return roi_metrics(pnls, categories, ll, brier, seed), pnls


def run(private_rows: Path, comparison_report: Path, output: Path) -> dict:
    private_rows = private_rows.resolve()
    raw = private_rows.read_bytes()
    payload = json.loads(raw)
    report = {"protocol": "M5_SIDEWISE_MARKET_ANCHORED_CALIBRATION_2025FIT_2026HOLDOUT_V1",
              "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "inputs": {"private_model_family_rows_sha256": sha_bytes(raw),
                         "comparison_report_sha256": sha_file(comparison_report),
                         "runner_sha256": sha_file(Path(__file__))},
              "source": "Crown canonical quote-event archive; historical receipts post-kickoff",
              "fit_protocol": {"fit_year": 2025, "outer_holdout_year": 2026,
                               "calibrator": "multinomial logistic on log five-category probabilities, log both decimal prices, and line",
                               "hyperparameter_selection": "chronological first 75% / last 25% of 2025 fixture dates, minimizing settlement-category log loss",
                               "c_grid": list(C_GRID), "roi_not_used_for_fit": True,
                               "all_holdout_fixture_markets_retained": True,
                               "one_side_selected_by_higher_calibrated_expected_return_no_threshold": True},
              "markets": {},
              "limitations": ["2026 has been examined in prior M5 work and is development holdout, not untouched confirmation.",
                              "Historical quote response receipts are post-kickoff; ROI is retrospective event-time simulation.",
                              "M1 and MR1 rows require exact archived line match; model-specific sample counts differ.",
                              "Calibration and model research do not alter production strategy or add bet, league, price, or time gates."]}
    for market_idx, market in enumerate(MARKETS):
        report["markets"][market] = {}
        for model_idx, model_name in enumerate(MODELS):
            rows = payload.get(market, {}).get(model_name)
            if not isinstance(rows, list):
                raise ValueError(f"missing {market}/{model_name}")
            train, test = [], []
            seen = set()
            for row in rows:
                fid = str(row["fixture_id"])
                if fid in seen or row.get("market") != market:
                    raise ValueError("duplicate fixture-market or market mismatch")
                seen.add(fid)
                event = datetime.fromisoformat(row["quote_event_utc"].replace("Z", "+00:00"))
                kickoff = datetime.fromisoformat(row["kickoff_utc"].replace("Z", "+00:00"))
                if not event < kickoff:
                    raise ValueError("quote event must precede kickoff")
                year = kickoff.year
                if year == 2025:
                    train.append(row)
                elif year == 2026:
                    test.append(row)
            if not train or not test:
                raise ValueError(f"missing 2025 fit or 2026 test rows: {market}/{model_name}")
            selection = fit_select_c(train, market)
            c_value = selection["selected_C_by_validation_log_loss"]
            model, mean, scale = fit_full(train, market, c_value)
            for row in train:
                if datetime.fromisoformat(row["kickoff_utc"].replace("Z", "+00:00")).year >= 2026:
                    raise AssertionError("target year leaked into training")
            baseline, baseline_pnl = baseline_metrics(test, 202611090 + market_idx*20 + model_idx)
            calibrated, calibrated_pnl = score_holdout(
                test, market, model, mean, scale, 202612090 + market_idx*20 + model_idx)
            report["markets"][market][model_name] = {
                "train_fixture_markets_2025": len(train), "holdout_fixture_markets_2026": len(test),
                "inner_hyperparameter_selection": selection,
                "baseline_raw_model": baseline,
                "market_anchored_calibrator": calibrated,
                "paired_roi_difference_calibrated_minus_raw": paired_roi_difference_bootstrap(
                    calibrated_pnl, baseline_pnl, 202613090 + market_idx*20 + model_idx),
            }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-model-family-rows", type=Path, required=True)
    parser.add_argument("--comparison-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_model_family_rows, args.comparison_report, args.output)
    print(json.dumps({market: {name: {"n": row["holdout_fixture_markets_2026"],
                                           "raw_roi_pct": row["baseline_raw_model"]["roi_pct"],
                                           "calibrated_roi_pct": row["market_anchored_calibrator"]["roi_pct"]}
                            for name, row in models.items()} for market, models in report["markets"].items()},
                     sort_keys=True))


if __name__ == "__main__":
    main()
