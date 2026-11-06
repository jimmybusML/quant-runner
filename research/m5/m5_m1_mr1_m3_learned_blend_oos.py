#!/usr/bin/env python3
"""Learn M1/MR1/M3 probability ensemble weights on 2025, hold out 2026.

All model predictions, quote pairs, and results are read from private files.
The public output is aggregate only. AH and OU weights are fit independently;
no match filters, ROI thresholds, or trade-count gates are introduced.
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
from scipy.optimize import minimize

from research.m5.m3_grid_crown_replay import grid_distribution, legs_result, payout

MODELS = ("m1", "mr1_v6", "m3_poisson", "m3_dixon_coles", "m3_bivariate_poisson")
M3_MODELS = {"m3_poisson": "poisson", "m3_dixon_coles": "dixon_coles",
             "m3_bivariate_poisson": "bivariate_poisson"}
MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}
INVERSE = {"win": "loss", "half_win": "half_loss", "push": "push",
           "half_loss": "half_win", "loss": "win"}
MR1_CATEGORY_KEY = {"win": "full_win", "half_win": "half_win", "push": "push",
                    "half_loss": "half_loss", "loss": "full_loss"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instant(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def read_rows(path: Path, key_fields: tuple[str, ...]):
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = tuple(str(row[field]) for field in key_fields)
        if key in rows:
            raise ValueError(f"duplicate private input key: {key_fields}")
        rows[key] = row
    return raw, rows


def normalize(values):
    out = np.asarray(values, dtype=np.float64)
    if out.shape[-1] != len(CATEGORIES) or not np.all(np.isfinite(out)) or np.any(out < -1e-10):
        raise ValueError("invalid settlement probability vector")
    total = out.sum(axis=-1, keepdims=True)
    if np.any(np.abs(total - 1.0) > 1e-6):
        raise ValueError("settlement probabilities do not sum to one")
    return np.maximum(out, 0.0) / total


def invert_distribution(values):
    """Map a five-state Asian settlement distribution to the opposite side."""
    values = normalize(values)
    return normalize(values[..., [4, 3, 2, 1, 0]])


def category_index(market, side, line, home_goals, away_goals):
    _, category = legs_result(market, side, line, home_goals, away_goals)
    return CATEGORIES.index(category)


def load_market_rows(market, m1, mr1, m3):
    sides = SIDES[market]
    fixtures = []
    audit = Counter()
    for key in sorted(mr1):
        fid, row_market = key
        if row_market != market:
            continue
        m1row = m1.get((fid, market))
        f = m3.get((fid,))
        if not m1row or not f:
            audit["missing_prediction_row"] += 1
            continue
        q = f.get("quotes", {}).get(market)
        if not q or q.get("source") != "Crown" or m1row.get("source") != "Crown":
            audit["source_or_quote_mismatch"] += 1
            continue
        if (instant(q["event_utc"]) != instant(m1row["event_utc"])
                or instant(q["event_utc"]) != instant(mr1[key]["event_utc"])):
            audit["quote_event_mismatch"] += 1
            continue
        if any(abs(float(a) - float(b)) > 1e-8 for a, b in (
                (q["line"], m1row["line"]), (q["line"], mr1[key]["line"]))):
            audit["quote_line_mismatch"] += 1
            continue
        if instant(f["kickoff_utc"]) != instant(m1row["kickoff_utc"]) \
                or instant(f["kickoff_utc"]) != instant(mr1[key]["kickoff_utc"]):
            audit["kickoff_mismatch"] += 1
            continue
        asof = instant(m1row["prediction_asof_utc"])
        kickoff = instant(f["kickoff_utc"])
        event = instant(q["event_utc"])
        if not (asof < kickoff and asof <= event < kickoff):
            audit["prediction_quote_chronology_mismatch"] += 1
            continue
        mr = mr1[key]
        if mr["side"] not in sides or abs(
                float(mr["price"]) - float(q["prices"][sides.index(mr["side"])])
        ) > 1e-8:
            audit["mr1_selected_price_mismatch"] += 1
            continue
        if any(abs(float(a) - float(b)) > 1e-8 for a, b in zip(m1row["prices"], q["prices"])):
            audit["m1_price_pair_mismatch"] += 1
            continue

        side_probs = np.zeros((len(MODELS), 2, len(CATEGORIES)), dtype=np.float64)
        m1_selected = m1row["m1_side"].lower()
        if m1_selected not in sides:
            audit["m1_side_invalid"] += 1
            continue
        raw_m1 = np.asarray([float(m1row["m1_distribution"][c]) for c in CATEGORIES])
        mr1_probs = np.asarray([float(mr["probabilities"][MR1_CATEGORY_KEY[c]]) for c in CATEGORIES])
        for idx, side in enumerate(sides):
            side_probs[0, idx] = raw_m1 if side == m1_selected else invert_distribution(raw_m1)
            side_probs[1, idx] = mr1_probs if side == mr["side"] else invert_distribution(mr1_probs)
        grid_models = f["model_score_grids"]
        for model_idx, model_name in enumerate(MODELS[2:], start=2):
            grid = grid_models[M3_MODELS[model_name]]
            for side_idx, side in enumerate(sides):
                dist = grid_distribution(grid, market, side, float(q["line"]))
                side_probs[model_idx, side_idx] = [float(dist[c]) for c in CATEGORIES]
        side_probs = normalize(side_probs)
        actual = (int(f["actual_home_goals"]), int(f["actual_away_goals"]))
        actual_idx = np.asarray([category_index(market, side, float(q["line"]), *actual)
                                 for side in sides], dtype=np.int64)
        fixtures.append({
            "id": fid, "market": market, "year": str(kickoff.year), "probabilities": side_probs,
            "actual_category_by_side": actual_idx, "prices": np.asarray(q["prices"], dtype=np.float64),
            "line": float(q["line"]), "actual": actual, "event_utc": q["event_utc"],
            "kickoff_utc": f["kickoff_utc"], "source": q["source"],
            "receipt_before_kickoff": bool(q["receipt_before_kickoff"]),
        })
        audit["post_kickoff_provider_receipt"] += int(instant(q["receipt_utc"]) >= kickoff)
        audit["prefixture_quote_event"] += int(event < kickoff)
    return fixtures, audit


def arrays(rows):
    probs = np.stack([r["probabilities"] for r in rows])  # rows x models x sides x categories
    prices = np.stack([r["prices"] for r in rows])
    actual = np.stack([r["actual_category_by_side"] for r in rows])
    return probs, prices, actual


def expected_returns(blended, prices):
    win = blended[..., 0]
    half_win = blended[..., 1]
    half_loss = blended[..., 3]
    loss = blended[..., 4]
    return (win + .5 * half_win) * (prices - 1.0) - loss - .5 * half_loss


def score_weights(weights, prob_tensor, prices, actual_indices):
    mixed = np.einsum("nmsk,m->nsk", prob_tensor, weights)
    ev = expected_returns(mixed, prices)
    chosen = np.argmax(ev, axis=1)
    rows = np.arange(len(chosen))
    dist = mixed[rows, chosen, :]
    actual = actual_indices[rows, chosen]
    ll = -np.log(np.maximum(dist[rows, actual], 1e-15)).mean()
    return float(ll), chosen, dist, actual


def fit_weights(train):
    probs, prices, actual = arrays(train)
    def objective(w):
        return score_weights(w, probs, prices, actual)[0]
    starts = [np.full(len(MODELS), 1 / len(MODELS))]
    starts.extend(np.eye(len(MODELS)))
    starts.extend([
        np.asarray([.5, .5, 0, 0, 0]),
        np.asarray([.5, 0, .5, 0, 0]),
        np.asarray([.5, 0, 0, .5, 0]),
        np.asarray([.5, 0, 0, 0, .5]),
    ])
    best = None
    diagnostics = []
    for start in starts:
        result = minimize(objective, start, method="SLSQP",
                          bounds=[(0.0, 1.0)] * len(MODELS),
                          constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0)}],
                          options={"maxiter": 250, "ftol": 1e-10})
        candidate = np.clip(result.x, 0.0, 1.0)
        candidate /= candidate.sum()
        loss = objective(candidate)
        diagnostics.append({"optimizer_success": bool(result.success),
                            "iterations": int(result.nit), "training_log_loss": round(loss, 8)})
        if best is None or loss < best[0]:
            best = (loss, candidate)
    return best[1], {"training_log_loss": round(best[0], 8),
                     "multistart_count": len(starts), "optimizer_runs": diagnostics}


def fit_roi_weights(train):
    probs, prices, _ = arrays(train)
    actual_returns = np.empty((len(train), 2), dtype=np.float64)
    for i, row in enumerate(train):
        for side_idx, side in enumerate(SIDES[row["market"]]):
            legs, _ = legs_result(row["market"], side, row["line"], *row["actual"])
            actual_returns[i, side_idx] = payout(legs, float(row["prices"][side_idx]))

    def objective(w):
        mixed = np.einsum("nmsk,m->nsk", probs, w)
        chosen = np.argmax(expected_returns(mixed, prices), axis=1)
        return -float(actual_returns[np.arange(len(chosen)), chosen].mean())

    starts = [np.full(len(MODELS), 1 / len(MODELS))]
    starts.extend(np.eye(len(MODELS)))
    starts.extend([np.asarray([.5, .5, 0, 0, 0]), np.asarray([.5, 0, .5, 0, 0]),
                   np.asarray([.5, 0, 0, .5, 0]), np.asarray([.5, 0, 0, 0, .5])])
    best = None
    diagnostics = []
    for start in starts:
        result = minimize(objective, start, method="SLSQP", bounds=[(0.0, 1.0)] * len(MODELS),
                          constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0)}],
                          options={"maxiter": 250, "ftol": 1e-10})
        candidate = np.clip(result.x, 0.0, 1.0)
        candidate /= candidate.sum()
        roi = -objective(candidate)
        diagnostics.append({"optimizer_success": bool(result.success), "iterations": int(result.nit),
                            "training_roi_pct": round(100 * roi, 6)})
        if best is None or roi > best[0]:
            best = (roi, candidate)
    return best[1], {"training_roi_pct": round(100 * best[0], 6),
                     "multistart_count": len(starts), "optimizer_runs": diagnostics}


def summarize(rows, weights, seed):
    probs, prices, actual_indices = arrays(rows)
    ll, chosen, distributions, actual_categories = score_weights(weights, probs, prices, actual_indices)
    pnl = []
    categories = Counter()
    event_pnl = defaultdict(float)
    for idx, row in enumerate(rows):
        side_index = int(chosen[idx])
        side = SIDES[row["market"]][side_index]
        legs, category = legs_result(row["market"], side, row["line"], *row["actual"])
        value = payout(legs, float(row["prices"][side_index]))
        pnl.append(value)
        categories[category] += 1
        event_pnl[row["event_utc"]] += value
        if CATEGORIES.index(category) != int(actual_categories[idx]):
            raise AssertionError("actual settlement index mismatch")
    n = len(rows)
    equity = peak = drawdown = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    brier = np.square(distributions - np.eye(len(CATEGORIES))[actual_categories]).sum(axis=1).mean()
    rng = np.random.default_rng(seed)
    values = np.asarray(pnl, dtype=np.float64)
    reps, chunk = 5000, 100
    boot = np.concatenate([
        values[rng.integers(0, n, size=(min(chunk, reps - start), n))].mean(axis=1)
        for start in range(0, reps, chunk)
    ])
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n, "stake_units": n,
        "net_units": round(math.fsum(pnl), 6), "roi_pct": round(100 * math.fsum(pnl) / n, 6),
        "settlement_counts": {c: categories[c] for c in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "settlement_log_loss": round(ll, 8), "settlement_brier": round(float(brier), 8),
        "roi_bootstrap_95pct": {"method": "fixture percentile bootstrap, descriptive only",
                                "repetitions": reps,
                                "lower_95_roi_pct": round(100 * float(np.quantile(boot, .025)), 6),
                                "upper_95_roi_pct": round(100 * float(np.quantile(boot, .975)), 6)},
        "quote_sources": dict(Counter(r["source"] for r in rows)),
        "provider_receipt_timing": dict(Counter(
            "pre_kickoff" if r["receipt_before_kickoff"] else "post_kickoff" for r in rows)),
    }


def run(m1_trace_path: Path, mr1_trace_path: Path, m3_rows_path: Path, output: Path):
    m1_raw, m1 = read_rows(m1_trace_path, ("match_id", "market"))
    mr1_raw, mr1 = read_rows(mr1_trace_path, ("match_id", "market"))
    m3_raw, m3 = read_rows(m3_rows_path, ("match_id",))
    report_markets = {}
    audit_total = Counter()
    timing_total = Counter()
    for market_idx, market in enumerate(MARKETS):
        rows, audit = load_market_rows(market, m1, mr1, m3)
        for key, value in audit.items():
            if key in {"post_kickoff_provider_receipt", "prefixture_quote_event"}:
                timing_total[f"{market}_{key}"] += value
            else:
                audit_total[f"{market}_{key}"] += value
        train = [r for r in rows if r["year"] == "2025"]
        test = [r for r in rows if r["year"] == "2026"]
        if len(train) != 1005 or len(test) != 8512:
            raise ValueError(f"unexpected temporal partition for {market}: {len(train)}/{len(test)}")
        fitted, fit_audit = fit_weights(train)
        weights = {name: round(float(value), 8) for name, value in zip(MODELS, fitted)}
        roi_fitted, roi_fit_audit = fit_roi_weights(train)
        strategies = {
            "trained_2025_logloss_weights": fitted,
            "trained_2025_roi_weights": roi_fitted,
            "equal_weight": np.full(len(MODELS), 1 / len(MODELS)),
            **{f"single_{name}": np.eye(len(MODELS))[i] for i, name in enumerate(MODELS)},
        }
        entries = {}
        for strat_idx, (name, strategy_weights) in enumerate(strategies.items()):
            train_report = summarize(train, strategy_weights, 202611060 + market_idx * 31 + strat_idx)
            test_report = summarize(test, strategy_weights, 202611160 + market_idx * 31 + strat_idx)
            entries[name] = {"weights": {k: round(float(v), 8) for k, v in zip(MODELS, strategy_weights)},
                             "training_2025": train_report, "holdout_2026": test_report}
        report_markets[market] = {
            "training_fixture_markets_2025": len(train), "holdout_fixture_markets_2026": len(test),
            "training_test_fixture_ids_disjoint": not bool({r["id"] for r in train} & {r["id"] for r in test}),
            "learned_weights": weights, "weight_fit": fit_audit,
            "roi_learned_weights": {name: round(float(value), 8) for name, value in zip(MODELS, roi_fitted)},
            "roi_weight_fit": roi_fit_audit, "strategies": entries,
            "all_holdout_sources": {"Crown": len(test)},
        }
    if audit_total:
        raise ValueError(f"identity/quote audit failures: {dict(audit_total)}")
    report = {
        "protocol": "M5_M1_MR1_M3_2025_LOGLOSS_TRAIN_2026_OOS_BLEND_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha(Path(__file__)),
        "input_sha256": {"m1_prediction_trace": hashlib.sha256(m1_raw).hexdigest(),
                         "mr1_prediction_trace": hashlib.sha256(mr1_raw).hexdigest(),
                         "m3_predictions_and_crown_quotes": hashlib.sha256(m3_raw).hexdigest()},
        "common_unique_fixtures_per_market": 9517,
        "audit_counts": dict(audit_total),
        "timing_counts": dict(timing_total),
        "markets": report_markets,
        "method": "Fit independent AH/OU five-model convex probability weights by 2025 mean settlement-category log loss with multistart SLSQP; freeze weights and evaluate 2026. Each model contributes probabilities for both sides of the exact same pregame Crown contract; MR1/M1 recorded-side distributions are inverted by the Asian settlement symmetry when necessary. The blended model selects the side with higher expected net return from the recorded two prices, one unit per fixture-market, without an EV threshold or fixture selection. Equal-weight and single-model baselines use the identical 2026 holdout.",
        "limitations": [
            "All exact same-cohort markets are Crown; MR1 coverage limits this comparison to 9,517 per market, below the 10,000 target.",
            "Historical Crown response receipts were post-kickoff despite pre-kickoff quote event times; ROI is retrospective event-time replay, not executable ROI.",
            "2026 was inspected in earlier M5 experiments, so it is chronological OOS for these frozen weights but not an untouched final confirmation set.",
            "M1 reconstruction uses its frozen parameter snapshot and the documented two-day retrospective availability buffer; actual per-result ingestion timestamps are unavailable for the full cohort.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({m: {
        "learned_weights": v["learned_weights"],
        "holdout_2026": {name: {"roi_pct": row["holdout_2026"]["roi_pct"],
                               "log_loss": row["holdout_2026"]["settlement_log_loss"],
                               "brier": row["holdout_2026"]["settlement_brier"]}
                         for name, row in v["strategies"].items()}
    } for m, v in report_markets.items()}, sort_keys=True))


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
