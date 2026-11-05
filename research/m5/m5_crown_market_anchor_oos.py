#!/usr/bin/env python3
"""M5/Crown market-probability anchor experiment on exact AH0 and OU2.5.

AH and OU fit independent convex weights by early quote-time log loss. The
later quote-time partition is held out for both proper scores and same-Crown
settlement ROI. This is research-only and adds no trading gate.
"""
from __future__ import annotations

import argparse
import hashlib
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

from research.m5.m5_crown_temperature_holdout import chronological_split, load_rows

WEIGHTS = tuple(i / 20 for i in range(21))
CATEGORIES = ("win", "push", "loss")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def observed_probs(row, market):
    grid = row["forecast"]["prediction"]["grid"]
    if market == "OU":
        over = sum(float(p) for h, rr in enumerate(grid) for a, p in enumerate(rr) if h + a > 2)
        return [over, 1.0 - over]
    home = draw = away = 0.0
    for h, rr in enumerate(grid):
        for a, p in enumerate(rr):
            if h > a:
                home += float(p)
            elif h == a:
                draw += float(p)
            else:
                away += float(p)
    return [home, draw, away]


def crown_anchor_probs(row, market, model_probs):
    inv = [1 / x for x in row["prices"]]
    if market == "OU":
        total = sum(inv)
        return [inv[0] / total, inv[1] / total]
    # AH0 prices identify the conditional home/away win split; DNB prices do
    # not identify draw mass, so the M5 draw probability is retained.
    total = sum(inv)
    conditional_home = inv[0] / total
    decisive_mass = model_probs[0] + model_probs[2]
    if decisive_mass <= 0:
        raise ValueError("AH0 model has no decisive probability mass")
    draw = model_probs[1]
    return [decisive_mass * conditional_home, draw,
            decisive_mass * (1 - conditional_home)]


def blend_probs(row, market, weight):
    model = observed_probs(row, market)
    crown = crown_anchor_probs(row, market, model)
    probs = [weight * x + (1 - weight) * y for x, y in zip(model, crown)]
    z = sum(probs)
    return [max(1e-12, x / z) for x in probs]


def outcome_label(row, market):
    h, a = int(row["ft"]["home_goals"]), int(row["ft"]["away_goals"])
    if market == "OU":
        return 0 if h + a > 2 else 1
    return 0 if h > a else 1 if h == a else 2


def logloss(probs, label):
    return -math.log(max(float(probs[label]), 1e-15))


def score_probs(rows, market, weight):
    labels = [outcome_label(r, market) for r in rows]
    ps = [blend_probs(r, market, weight) for r in rows]
    ll = sum(logloss(p, y) for p, y in zip(ps, labels)) / len(rows)
    onehot_brier = []
    for p, y in zip(ps, labels):
        onehot_brier.append(sum((x - (1 if i == y else 0)) ** 2 for i, x in enumerate(p)))
    brier = sum(onehot_brier) / len(rows)
    if market == "OU":
        brier /= 2  # Standard binary Brier single-event convention.
    return round(ll, 8), round(brier, 8)


def settle_selection(row, market, probs):
    prices = row["prices"]
    if market == "OU":
        evs = [probs[0] * (prices[0] - 1) - probs[1],
               probs[1] * (prices[1] - 1) - probs[0]]
        idx = 0 if evs[0] >= evs[1] else 1
        label = outcome_label(row, market)
        won = label == idx
        return {"ev": evs[idx], "units": prices[idx] - 1 if won else -1,
                "category": "win" if won else "loss"}
    evs = [probs[0] * (prices[0] - 1) - probs[2],
           probs[2] * (prices[1] - 1) - probs[0]]
    idx = 0 if evs[0] >= evs[1] else 1
    label = outcome_label(row, market)
    if label == 1:
        return {"ev": evs[idx], "units": 0.0, "category": "push"}
    won = (label == 0 and idx == 0) or (label == 2 and idx == 1)
    return {"ev": evs[idx], "units": prices[idx] - 1 if won else -1,
            "category": "win" if won else "loss"}


def summarize(rows, market, weight, seed):
    metrics = [settle_selection(row, market, blend_probs(row, market, weight)) for row in rows]
    n = len(rows)
    pnl = sum(x["units"] for x in metrics)
    counts = Counter(x["category"] for x in metrics)
    by_quote_time = defaultdict(float)
    for row, value in zip(rows, metrics):
        by_quote_time[row["observed"]] += value["units"]
    equity = peak = drawdown = 0.0
    for quote_time in sorted(by_quote_time):
        equity += by_quote_time[quote_time]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    values = [x["units"] for x in metrics]
    rng = random.Random(seed)
    boots = sorted(100 * sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    ll, brier = score_probs(rows, market, weight)
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
        "full_win": counts["win"], "half_win": 0,
        "full_loss": counts["loss"], "half_loss": 0,
        "push": counts["push"], "net_units": round(pnl, 6),
        "roi_pct": round(100 * pnl / n, 6),
        "max_drawdown_units_by_quote_time": round(drawdown, 6),
        "log_loss": ll, "brier": brier,
        "roi_fixture_bootstrap_95pct_interval": {
            "lower_2_5_pct": round(boots[249], 6),
            "upper_97_5_pct": round(boots[9749], 6),
            "resamples": 10000, "seed": seed,
        },
    }


def fit_weight(rows, market):
    candidates = []
    labels = [outcome_label(r, market) for r in rows]
    for w in WEIGHTS:
        loss = sum(logloss(blend_probs(r, market, w), y) for r, y in zip(rows, labels)) / len(rows)
        candidates.append((loss, -w, w))
    best_loss, _, best_weight = min(candidates)
    return best_weight, best_loss, {str(w): round(loss, 8) for loss, _, w in candidates}


def run(mr1_root: Path, forecasts: Path, output: Path):
    all_rows, forecast_raw, index_raw, registry_raw = load_rows(mr1_root, forecasts)
    snapshots = sorted({r["snapshot_sha256"] for rs in all_rows.values() for r in rs})
    receipts = sorted({r["ft_sha256"] for rs in all_rows.values() for r in rs})
    results = {}
    for market, contract in (("AH", 0.0), ("OU", 2.5)):
        events = [r for r in all_rows[market] if abs(r["line"] - contract) < 1e-9]
        if len(events) < 20:
            results[market] = {"contract": contract, "status": "insufficient_contract_sample", "unique_fixtures": len(events)}
            continue
        train, test, cutoff, purged = chronological_split(events)
        if len(train) < 10 or len(test) < 10:
            results[market] = {"contract": contract, "status": "insufficient_temporal_split",
                               "train": len(train), "test": len(test), "purged": purged}
            continue
        if any(r["ft_observed"] >= cutoff for r in train):
            raise RuntimeError("training FT receipt crosses the holdout quote boundary")
        if any(r["observed"] < cutoff for r in test):
            raise RuntimeError("quote-time holdout contains pre-cutoff quote")
        fitted_weight, train_loss, train_curve = fit_weight(train, market)
        results[market] = {
            "contract": contract,
            "source_verified_unique_contract_fixtures": len(events),
            "train_fixtures_with_FT_received_before_holdout_quote": len(train),
            "purged_pre_cutoff_fixtures_without_pre_holdout_FT": purged,
            "untouched_later_quote_time_holdout_fixtures": len(test),
            "quote_time_cutoff_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "fitted_M5_weight_selected_by_train_log_loss": fitted_weight,
            "train_log_loss_at_fitted_weight": round(train_loss, 8),
            "train_log_loss_by_candidate_weight": train_curve,
            "candidate_definitions": {
                "M5_only": "M5 probability distribution; weight 1.0",
                "Crown_anchor": "No-vig Crown price probabilities; AH0 keeps M5 draw mass because DNB prices do not identify draw probability",
                "fitted_blend": "Convex mixture of M5 and Crown-anchor probabilities; weight fitted on early-period log loss only",
            },
            "holdout_same_Crown_contract": {
                "M5_only": summarize(test, market, 1.0, 20261101),
                "Crown_anchor": summarize(test, market, 0.0, 20261102),
                "fitted_blend": summarize(test, market, fitted_weight, 20261103),
            },
            "roi_used_to_select_weight": False,
            "new_bet_gate_added": False,
        }
    report = {
        "protocol": "M5_CROWN_MARKET_ANCHORED_AH0_OU25_TIME_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_sha256": sha(forecast_raw),
        "MR1_snapshot_index_sha256": sha(index_raw),
        "MR1_fixture_registry_sha256": sha(registry_raw),
        "verified_Crown_snapshot_count": len(snapshots),
        "verified_Crown_snapshot_hash_set_sha256": sha("\n".join(snapshots).encode()),
        "verified_FT_receipt_count": len(receipts),
        "verified_FT_receipt_hash_set_sha256": sha("\n".join(receipts).encode()),
        "markets": results,
        "method": "Exact verified MR1 Crown receipt quotes and separate post-kickoff FT. One unique fixture per selected contract. Train-only convex weight selection minimizes settlement outcome log loss; holdout ROI uses same Crown prices, one 1U selection per fixture and Asian settlement. AH and OU fit separately. No threshold or filter is selected.",
        "limitations": [
            "Only exact AH0 (DNB) and OU2.5 contracts are included in this candidate test; it does not generalize to other lines.",
            "AH0 Crown prices identify the conditional decisive home/away split but not draw probability; the anchor retains the M5 draw mass.",
            "The quote-time holdout is a small 2026 period that was previously explored in other M5 analyses; it is not an untouched independent validation sample.",
            "The overall Crown-priced sample remains below 10,000 fixtures per market.",
        ],
        "crown_prices_used_only": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({m: {"unique": x.get("source_verified_unique_contract_fixtures"),
                          "train": x.get("train_fixtures_with_FT_received_before_holdout_quote"),
                          "test": x.get("untouched_later_quote_time_holdout_fixtures"),
                          "fit_weight": x.get("fitted_M5_weight_selected_by_train_log_loss"),
                          "holdout": x.get("holdout_same_Crown_contract")}
                      for m, x in results.items()}, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--forecasts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.mr1_root, a.forecasts, a.output)


if __name__ == "__main__":
    main()
