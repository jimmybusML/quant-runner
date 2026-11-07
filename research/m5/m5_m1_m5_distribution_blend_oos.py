#!/usr/bin/env python3
"""Evaluate an M1/M5 distribution blend on 2025-train / 2026-holdout.

M1 contributes only when its saved prediction matches the exact M5
fixture-market quote contract and outcome. Missing M1 forecasts fall back to
M5, so the full M5 cohort remains intact. The mixing weight is fit separately
for AH/OU by 2025 settlement log loss, never by 2026 ROI.
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

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_line_conditional_settlement_calibration import (
    build_rows, settlement_distribution, settlement_expected_return,
)

MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def instant(value):
    from datetime import datetime
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def opposite_distribution(dist: dict[str, float]) -> dict[str, float]:
    """Reverse win/loss and half-win/half-loss for the opposing side."""
    return {"win": float(dist.get("loss", 0.0)),
            "half_win": float(dist.get("half_loss", 0.0)),
            "push": float(dist.get("push", 0.0)),
            "half_loss": float(dist.get("half_win", 0.0)),
            "loss": float(dist.get("win", 0.0))}


def blend_distribution(m5: dict[str, float], m1: dict[str, float], alpha: float):
    if not math.isfinite(alpha) or alpha < 0 or alpha > 1:
        raise ValueError("alpha must be in [0, 1]")
    out = {category: (1.0 - alpha) * float(m5.get(category, 0.0))
           + alpha * float(m1.get(category, 0.0)) for category in CATEGORIES}
    total = math.fsum(out.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("invalid blend distribution")
    return {category: value / total for category, value in out.items()}


def validate_m1_match(row: dict, m1: dict, kickoff_utc: str | None = None) -> str | None:
    """Return mismatch reason, or None when identity and quote contract match."""
    if m1 is None:
        return "missing_m1_row"
    try:
        if instant(row["event_utc"]) != instant(m1["event_utc"]):
            return "quote_event_mismatch"
        kickoff_utc = kickoff_utc or row.get("kickoff_utc")
        if kickoff_utc is None or instant(kickoff_utc) != instant(m1["kickoff_utc"]):
            return "kickoff_mismatch"
        if abs(float(row["line"]) - float(m1["line"])) > 1e-8:
            return "line_mismatch"
        if row["source"] != m1["source"]:
            return "source_mismatch"
        if any(abs(float(a) - float(b)) > 1e-8 for a, b in zip(row["prices"], m1["prices"])):
            return "price_pair_mismatch"
        if str(m1["actual_home_goals"]) != str(row["score"][0]) or str(m1["actual_away_goals"]) != str(row["score"][1]):
            return "score_mismatch"
        if instant(m1["prediction_asof_utc"]) > instant(row["event_utc"]):
            return "m1_asof_after_quote_event"
        if instant(m1["prediction_asof_utc"]) >= instant(kickoff_utc):
            return "m1_asof_not_pregame"
        return None
    except (KeyError, TypeError, ValueError):
        return "invalid_m1_contract"


def m5_both_side_distributions(row: dict, market: str):
    sides = SIDES[market]
    return [settlement_distribution(row["grid"], market, side, row["line"]) for side in sides]


def m1_both_side_distributions(m1: dict, market: str):
    selected_side = str(m1.get("m1_side", "")).lower()
    sides = SIDES[market]
    if selected_side not in sides:
        return None
    selected = {category: float(m1.get("m1_distribution", {}).get(category, 0.0))
                for category in CATEGORIES}
    total = math.fsum(selected.values())
    if not math.isfinite(total) or total <= 0:
        return None
    selected = {category: value / total for category, value in selected.items()}
    opposite = opposite_distribution(selected)
    return [selected if side == selected_side else opposite for side in sides]


def row_with_distributions(row: dict, market: str, m1: dict | None, alpha: float):
    sides = SIDES[market]
    m5_dists = m5_both_side_distributions(row, market)
    m1_dists = m1_both_side_distributions(m1, market) if m1 is not None else None
    if m1_dists is None:
        alpha = 0.0
    dists = [blend_distribution(m5, m1d, alpha) if m1_dists else m5
             for m5, m1d in zip(m5_dists, (m1_dists or m5_dists))]
    expected = [settlement_expected_return(dist, price)
                for dist, price in zip(dists, row["prices"])]
    index = 0 if expected[0] >= expected[1] else 1
    actual = legs_result(market, sides[index], row["line"], *row["score"])[1]
    legs, _ = legs_result(market, sides[index], row["line"], *row["score"])
    return {"distribution": dists[index], "side": sides[index], "actual": actual,
            "pnl": payout(legs, row["prices"][index]), "source": row["source"],
            "event_utc": instant(row["event_utc"]).isoformat(),
            "receipt_timing": row.get("receipt_timing", "unknown"),
            "m1_used": m1_dists is not None}


def score_rows(rows, market: str, m1_by_key: dict, alpha: float):
    return [row_with_distributions(row, market, m1_by_key.get((str(row["match_id"]), market)), alpha)
            for row in rows]


def mean_log_loss(rows):
    return math.fsum(-math.log(max(row["distribution"].get(row["actual"], 0.0), 1e-15))
                     for row in rows) / len(rows)


def summarize(rows, seed: int):
    n = len(rows)
    categories = Counter(row["actual"] for row in rows)
    pnl = [float(row["pnl"]) for row in rows]
    net = math.fsum(pnl)
    event_pnl = defaultdict(float)
    for row in rows:
        event_pnl[row["event_utc"]] += row["pnl"]
    equity = peak = drawdown = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    logloss = mean_log_loss(rows)
    brier = math.fsum(math.fsum((row["distribution"].get(cat, 0.0) - float(row["actual"] == cat)) ** 2
                                for cat in CATEGORIES) for row in rows) / n
    rng = random.Random(seed)
    boot = sorted(sum(pnl[rng.randrange(n)] for _ in range(n)) / n for _ in range(5000))
    return {"unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
            "stake_units": n, "net_units": round(net, 6),
            "roi_pct": round(100 * net / n, 6),
            "settlement_counts": {cat: categories[cat] for cat in CATEGORIES},
            "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
            "settlement_log_loss": round(logloss, 8), "settlement_brier": round(brier, 8),
            "roi_bootstrap_95pct": {"method": "fixture percentile bootstrap, descriptive only",
                                    "repetitions": 5000,
                                    "lower_95_roi_pct": round(100 * boot[int(.025 * 4999)], 6),
                                    "upper_95_roi_pct": round(100 * boot[int(.975 * 4999)], 6)},
            "source_fixture_markets": dict(Counter(row["source"] for row in rows)),
            "m1_forecasts_used": sum(bool(row["m1_used"]) for row in rows),
            "m1_forecasts_fallback_to_m5": sum(not row["m1_used"] for row in rows)}


def run(private_dir: Path, m1_trace_path: Path, output: Path, source_timezone="Asia/Shanghai"):
    samples, hashes, counts = build_rows(private_dir, source_timezone, None)
    m1_by_key = {}
    with m1_trace_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                key = (str(row["match_id"]), str(row["market"]))
                if key in m1_by_key:
                    raise ValueError("duplicate M1 fixture-market")
                m1_by_key[key] = row

    manifest = json.loads((private_dir / "candidate-manifest.json").read_text(encoding="utf-8"))
    kickoff_by_id = {str(row["match_id"]): row["kickoff_utc"] for row in manifest["rows"]}
    mismatches = Counter()
    used_by_market = {market: Counter() for market in MARKETS}
    valid_m1_by_key = {}
    for market in MARKETS:
        for year in (2025, 2026):
            for row in samples[year][market]:
                m1 = m1_by_key.get((str(row["match_id"]), market))
                mismatch = validate_m1_match(row, m1, kickoff_by_id.get(str(row["match_id"])))
                if mismatch is None:
                    used_by_market[market][year] += 1
                    valid_m1_by_key[(str(row["match_id"]), market)] = m1
                else:
                    mismatches[f"{market}_{year}_{mismatch}"] += 1

    alpha_grid = np.linspace(0.0, 1.0, 21)
    results = {}
    for market_index, market in enumerate(MARKETS):
        train, holdout = samples[2025][market], samples[2026][market]
        train_ids = {str(row["match_id"]) for row in train}
        holdout_ids = {str(row["match_id"]) for row in holdout}
        if train_ids & holdout_ids:
            raise RuntimeError(f"{market} fixture ids leak across temporal split")
        train_variants = []
        for alpha in alpha_grid:
            scored = score_rows(train, market, valid_m1_by_key, float(alpha))
            train_variants.append((mean_log_loss(scored), float(alpha), scored))
        best_ll, alpha, train_rows = min(train_variants, key=lambda item: (item[0], item[1]))
        holdout_rows = score_rows(holdout, market, valid_m1_by_key, alpha)
        m5_only_rows = score_rows(holdout, market, valid_m1_by_key, 0.0)
        m1_max_fallback_rows = score_rows(holdout, market, valid_m1_by_key, 1.0)
        results[market] = {
            "training_fixture_markets": len(train), "holdout_fixture_markets": len(holdout),
            "training_holdout_fixture_ids_disjoint": True,
            "m1_exact_contract_matches_by_year": {"2025": used_by_market[market][2025],
                                                   "2026": used_by_market[market][2026]},
            "selected_m1_weight_alpha": alpha,
            "training_selected_log_loss": round(best_ll, 8),
            "training_metrics": summarize(train_rows, 20261180 + market_index),
            "holdout_metrics": summarize(holdout_rows, 20261190 + market_index),
            "holdout_comparators": {
                "m5_only_alpha_zero": summarize(m5_only_rows, 20261200 + market_index),
                "m1_max_weight_with_m5_fallback": summarize(m1_max_fallback_rows, 20261210 + market_index),
            },
        }

    report = {
        "protocol": "M5_M1_DISTRIBUTION_BLEND_2025_TRAIN_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha_file(Path(__file__)),
        "m1_trace_sha256": sha_file(m1_trace_path),
        "m5_input_hashes": hashes,
        "source_counts_by_market_year": dict(counts),
        "m1_contract_mismatch_counts": dict(mismatches),
        "markets": results,
        "method": (
            "For each side, combine M1 and M5 settlement-category distributions with a "
            "market-specific alpha chosen from 21 equally spaced weights by 2025 selected-side "
            "settlement log loss. The model chooses the higher expected-return side on every "
            "fixture-market. If exact M1 quote-contract data are absent, alpha is set to zero "
            "for that row so M5 still predicts and every holdout row remains included."
        ),
        "source_and_time_integrity": {
            "crown_and_totalcorner_default_distinct": True,
            "fixture_markets_deduplicated": True,
            "training_before_holdout_and_ids_disjoint": True,
            "m1_quote_match_requires_exact_source_event_line_prices_kickoff_and_score": True,
            "m1_forecast_asof_before_quote_event_and_kickoff": True,
            "historical_api_receipts": "post-kickoff; retrospective event-time ROI, not executable ROI",
        },
        "limitations": [
            "The 2025 training sample is smaller than the 2026 holdout and alpha is selected on previously examined M5 archive data.",
            "The 2026 holdout has been examined in previous model studies; this is exploratory, not an untouched confirmatory test.",
            "All provider API receipts in this historical cohort were post-kickoff.",
            "No fixture-level rows or odds are published; no production model, bet gate, or formal trading route is changed.",
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
    parser.add_argument("--m1-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.private_dir, args.m1_trace, args.output, args.source_timezone)
    print(json.dumps({market: {"train_n": rows["training_fixture_markets"],
                              "holdout_n": rows["holdout_fixture_markets"],
                              "m1_matches": rows["m1_exact_contract_matches_by_year"],
                              "alpha": rows["selected_m1_weight_alpha"],
                              "holdout_roi_pct": rows["holdout_metrics"]["roi_pct"],
                              "m5_only_roi_pct": rows["holdout_comparators"]["m5_only_alpha_zero"]["roi_pct"]}
                     for market, rows in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
