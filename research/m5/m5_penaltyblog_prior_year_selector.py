#!/usr/bin/env python3
"""Research-only M3 model selection: 2025 probability score -> 2026 holdout.

For AH and OU independently, select the penaltyblog model with lowest 2025
settlement log loss per league, then apply that league/model choice to every
available 2026 fixture-market. Leagues without 2025 rows use the global 2025
lowest-log-loss model. No 2026 result is used in selection and no fixture is
filtered. This is analysis only; it does not alter M3 or any production path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m3_grid_crown_replay import legs_result, payout, split_line
from research.m5.m5_three_penaltyblog_expanded_oos import CATEGORIES

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
MARKETS = ("AH", "OU")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def settlement_masks(market: str, side: str, line: float, shape: tuple[int, int]):
    hg, ag = np.indices(shape)
    margins = []
    for part in split_line(float(line)):
        if market == "AH":
            margin = hg - ag + part if side == "home" else ag - hg - part
        else:
            margin = hg + ag - part if side == "over" else part - hg - ag
        margins.append(np.where(margin > 1e-9, 1, np.where(margin < -1e-9, -1, 0)))
    first, second = margins
    labels = np.select(
        [(first == 1) & (second == 1),
         ((first == 1) & (second == 0)) | ((first == 0) & (second == 1)),
         (first == 0) & (second == 0),
         ((first == -1) & (second == 0)) | ((first == 0) & (second == -1)),
         (first == -1) & (second == -1)],
        [0, 1, 2, 3, 4], default=-1)
    return {category: labels == idx for idx, category in enumerate(CATEGORIES)}


def outcome_distribution(grid, market: str, side: str, line: float, cache: dict):
    arr = np.asarray(grid, dtype=float)
    key = (market, side, float(line), arr.shape)
    if key not in cache:
        cache[key] = settlement_masks(market, side, line, arr.shape)
    return {category: float(arr[mask].sum()) for category, mask in cache[key].items()}


def expected_return(distribution: dict, price: float) -> float:
    return (distribution["win"] * (price - 1.0)
            + distribution["half_win"] * (price - 1.0) / 2.0
            - distribution["half_loss"] / 2.0 - distribution["loss"])


def select_model(training_scores: dict[str, list[float]], global_scores: dict[str, list[float]]) -> str:
    available = {name: float(np.mean(scores)) for name, scores in training_scores.items() if scores}
    if not available:
        available = {name: float(np.mean(scores)) for name, scores in global_scores.items() if scores}
    if not available:
        raise ValueError("no prior-year training score available for model selection")
    return min(MODELS, key=lambda name: (available.get(name, math.inf), MODELS.index(name)))


def make_bet(fixture: dict, market: str, model: str, cache: dict) -> dict:
    quote = fixture["quotes"][market]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    distributions = [outcome_distribution(fixture["model_score_grids"][model], market, side,
                                          quote["line"], cache) for side in sides]
    ev = [expected_return(dist, price) for dist, price in zip(distributions, quote["prices"])]
    index = 0 if ev[0] >= ev[1] else 1
    side, price, distribution = sides[index], quote["prices"][index], distributions[index]
    legs, actual = legs_result(market, side, quote["line"],
                               fixture["actual_home_goals"], fixture["actual_away_goals"])
    pnl = payout(legs, price)
    actual_index = CATEGORIES.index(actual)
    ll = -math.log(max(distribution[actual], 1e-15))
    brier = sum((distribution[c] - (1.0 if i == actual_index else 0.0)) ** 2
                for i, c in enumerate(CATEGORIES))
    return {"model": model, "league": fixture["league"], "year": fixture["kickoff_utc"][:4],
            "pnl": pnl, "category": actual, "distribution": distribution,
            "log_loss": ll, "brier": brier, "source": quote["source"],
            "event_utc": quote["event_utc"], "receipt_before_kickoff": quote["receipt_before_kickoff"]}


def summarize(rows: list[dict]) -> dict:
    outcomes = Counter(row["category"] for row in rows)
    pnl = math.fsum(row["pnl"] for row in rows)
    equity = peak = drawdown = 0.0
    by_event = defaultdict(float)
    for row in rows:
        by_event[row["event_utc"]] += row["pnl"]
    for when in sorted(by_event):
        equity += by_event[when]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {"fixtures": len(rows), "simulated_bets": len(rows), "settled_bets": len(rows),
            "net_units": round(pnl, 6), "roi_pct": round(100 * pnl / len(rows), 6) if rows else None,
            "settlement_counts": {c: outcomes[c] for c in CATEGORIES},
            "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
            "settlement_log_loss": round(math.fsum(r["log_loss"] for r in rows) / len(rows), 8) if rows else None,
            "settlement_brier": round(math.fsum(r["brier"] for r in rows) / len(rows), 8) if rows else None,
            "quote_source_fixture_markets": dict(Counter(r["source"] for r in rows)),
            "actual_response_receipt_timing": dict(Counter("pre_kickoff" if r["receipt_before_kickoff"] else "post_kickoff" for r in rows))}


def run(private_predictions: Path, source_report: Path, output: Path):
    private_raw_sha = hashlib.sha256()
    training = {market: defaultdict(lambda: {model: [] for model in MODELS}) for market in MARKETS}
    global_training = {market: {model: [] for model in MODELS} for market in MARKETS}
    raw_rows: dict[int, list[dict]] = {2025: [], 2026: []}
    cache = {}
    with private_predictions.open("rb") as stream:
        for raw_line in stream:
            private_raw_sha.update(raw_line)
            if not raw_line.strip():
                continue
            fixture = json.loads(raw_line)
            year = int(fixture["kickoff_utc"][:4])
            if year not in raw_rows:
                continue
            raw_rows[year].append(fixture)
            if year != 2025:
                continue
            for market in MARKETS:
                for model in MODELS:
                    bet = make_bet(fixture, market, model, cache)
                    training[market][fixture["league"]][model].append(bet["log_loss"])
                    global_training[market][model].append(bet["log_loss"])

    selections = {}
    holdout = {market: [] for market in MARKETS}
    fixed = {market: {model: [] for model in MODELS} for market in MARKETS}
    selection_counts = {market: Counter() for market in MARKETS}
    leagues_per_model = {market: {model: set() for model in MODELS} for market in MARKETS}
    for market in MARKETS:
        selections[market] = {}
        global_model = select_model({}, global_training[market])
        for league, score_map in training[market].items():
            selections[market][league] = select_model(score_map, global_training[market])
        selections[market]["__fallback__"] = global_model
        for fixture in raw_rows[2026]:
            league = fixture["league"]
            selected_model = selections[market].get(league, global_model)
            selected_bet = make_bet(fixture, market, selected_model, cache)
            holdout[market].append(selected_bet)
            selection_counts[market][selected_model] += 1
            leagues_per_model[market][selected_model].add(league)
            for model in MODELS:
                fixed[market][model].append(make_bet(fixture, market, model, cache))

    market_results = {}
    for market in MARKETS:
        market_results[market] = {
            "selection_method": "Per league, select lowest 2025 OOS settlement log loss; if a league has no 2025 predictions, use the global lowest-2025-log-loss model. Apply to all 2026 fixtures without exclusions.",
            "selection_training_fixtures": len(raw_rows[2025]),
            "holdout_fixtures": len(raw_rows[2026]),
            "selected_model_by_league": {"global_fallback": selections[market]["__fallback__"],
                "league_count_by_selected_model": {model: len(leagues_per_model[market][model]) for model in MODELS},
                "fixture_count_by_selected_model": {model: selection_counts[market][model] for model in MODELS}},
            "selected_by_league_holdout": summarize(holdout[market]),
            "fixed_model_same_holdout": {model: summarize(rows) for model, rows in fixed[market].items()},
        }

    source = json.loads(source_report.read_text(encoding="utf-8"))
    report = {"protocol": "M5_M3_PENALTYBLOG_2025_SCORE_SELECTOR_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "private_forecast_sha256": private_raw_sha.hexdigest(),
        "source_m3_run_report_sha256": hashlib.sha256(source_report.read_bytes()).hexdigest(),
        "candidate_manifest_sha256": source["candidate_manifest_sha256"],
        "models": list(MODELS), "markets": market_results,
        "selection_data_is_strict_oos": True,
        "holdout_2026_not_used_for_selection": True,
        "holdout_scope_boundary": "All 2026 fixture-markets with complete three-model OOS forecasts and a valid selected source quote; no post-hoc outcome or league exclusions.",
        "all_historical_response_receipts_post_kickoff": True,
        "interpretation": "Research-only, retrospective event-time results. The 2026 holdout is below the separate 10,000-match threshold; this experiment cannot satisfy the M5 acceptance target even if its ROI were positive.",
        "production_changes": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-predictions", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_predictions, args.source_report, args.output)
    print(json.dumps({market: {"selector": data["selected_by_league_holdout"],
                              "fixed": {m: r["roi_pct"] for m, r in data["fixed_model_same_holdout"].items()},
                              "selected_models": data["selected_model_by_league"]}
                      for market, data in report["markets"].items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
