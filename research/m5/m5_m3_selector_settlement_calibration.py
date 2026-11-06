#!/usr/bin/env python3
"""Prior-year settlement-probability calibration for the M3 model selector."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_penaltyblog_prior_year_selector import (
    CATEGORIES, MARKETS, MODELS, expected_return, outcome_distribution, select_model, summarize,
)


def temperature_adjust(distribution: dict[str, float], temperature: float) -> dict[str, float]:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive")
    values = {key: max(0.0, float(value)) ** (1.0 / temperature) for key, value in distribution.items()}
    total = math.fsum(values.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("calibration has zero probability mass")
    return {key: value / total for key, value in values.items()}


def selected_model_maps(rows_2025, cache):
    selections, global_losses = {}, {}
    for market in MARKETS:
        per_league = defaultdict(lambda: {model: [] for model in MODELS})
        global_scores = {model: [] for model in MODELS}
        for fixture in rows_2025:
            for model in MODELS:
                # Model selection uses proper scores from the model's expected-return side.
                sides = ("home", "away") if market == "AH" else ("over", "under")
                quote = fixture["quotes"][market]
                side_distributions = [outcome_distribution(fixture["model_score_grids"][model], market,
                    side, quote["line"], cache) for side in sides]
                evs = [expected_return(d, price) for d, price in zip(side_distributions, quote["prices"])]
                idx = 0 if evs[0] >= evs[1] else 1
                chosen = side_distributions[idx]
                actual_side = sides[idx]
                _, actual = legs_result(market, actual_side, quote["line"],
                    fixture["actual_home_goals"], fixture["actual_away_goals"])
                loss = -math.log(max(chosen[actual], 1e-15))
                per_league[fixture["league"]][model].append(loss)
                global_scores[model].append(loss)
        global_losses[market] = global_scores
        selections[market] = {league: select_model(scores, global_scores) for league, scores in per_league.items()}
        selections[market]["__fallback__"] = select_model({}, global_scores)
    return selections, global_losses


def bet(fixture, market, model, temperature, cache):
    quote = fixture["quotes"][market]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    raw = [outcome_distribution(fixture["model_score_grids"][model], market, side, quote["line"], cache)
           for side in sides]
    calibrated = [temperature_adjust(distribution, temperature) for distribution in raw]
    expected = [expected_return(distribution, price) for distribution, price in zip(calibrated, quote["prices"])]
    idx = 0 if expected[0] >= expected[1] else 1
    side, price, distribution = sides[idx], quote["prices"][idx], calibrated[idx]
    legs, actual = legs_result(market, side, quote["line"], fixture["actual_home_goals"], fixture["actual_away_goals"])
    actual_idx = CATEGORIES.index(actual)
    ll = -math.log(max(distribution[actual], 1e-15))
    brier = sum((distribution[c] - (1.0 if i == actual_idx else 0.0)) ** 2
                for i, c in enumerate(CATEGORIES))
    row = {"pnl": payout(legs, price), "category": actual, "distribution": distribution,
           "log_loss": ll, "brier": brier, "event_utc": quote["event_utc"],
           "kickoff_utc": fixture["kickoff_utc"], "source": quote["source"],
           "receipt_before_kickoff": quote["receipt_before_kickoff"]}
    return row


def metrics(rows):
    out = summarize(rows)
    out["settlement_log_loss"] = round(math.fsum(x["log_loss"] for x in rows) / len(rows), 8)
    out["settlement_brier"] = round(math.fsum(x["brier"] for x in rows) / len(rows), 8)
    return out


def validate_chronology(fixture: dict) -> None:
    train_end = datetime.fromisoformat(fixture["train_end_utc"].replace("Z", "+00:00"))
    asof = datetime.fromisoformat(fixture["prediction_asof_utc"].replace("Z", "+00:00"))
    kickoff = datetime.fromisoformat(fixture["kickoff_utc"].replace("Z", "+00:00"))
    if not train_end < asof < kickoff:
        raise ValueError("M3 forecast training/as-of/kickoff chronology failed")
    for market in MARKETS:
        quote = fixture["quotes"][market]
        event = datetime.fromisoformat(quote["event_utc"].replace("Z", "+00:00"))
        received = datetime.fromisoformat(quote["receipt_utc"].replace("Z", "+00:00"))
        if not asof <= event < kickoff or received < event or received < kickoff:
            raise ValueError("quote event/receipt chronology failed")


def run(private_predictions: Path, selector_report: Path, output: Path):
    raw_sha = hashlib.sha256()
    rows = {2025: [], 2026: []}
    with private_predictions.open("rb") as stream:
        for raw in stream:
            raw_sha.update(raw)
            if raw.strip():
                row = json.loads(raw)
                year = int(row["kickoff_utc"][:4])
                if year in rows:
                    validate_chronology(row)
                    rows[year].append(row)

    cache = {}
    selections, _ = selected_model_maps(rows[2025], cache)
    temperatures = [round(0.50 + i * 0.01, 2) for i in range(151)]
    market_output = {}
    for market in MARKETS:
        train_models = [selections[market].get(row["league"], selections[market]["__fallback__"]) for row in rows[2025]]
        test_models = [selections[market].get(row["league"], selections[market]["__fallback__"]) for row in rows[2026]]
        training_scores = {}
        for temperature in temperatures:
            candidate_rows = [bet(fixture, market, model, temperature, cache)
                              for fixture, model in zip(rows[2025], train_models)]
            training_scores[str(temperature)] = metrics(candidate_rows)["settlement_log_loss"]
        selected_temp = min(temperatures, key=lambda t: (training_scores[str(t)], abs(t - 1.0), t))
        raw_holdout = [bet(fixture, market, model, 1.0, cache)
                       for fixture, model in zip(rows[2026], test_models)]
        calibrated_holdout = [bet(fixture, market, model, selected_temp, cache)
                              for fixture, model in zip(rows[2026], test_models)]
        market_output[market] = {
            "selection_training_fixtures_2025": len(rows[2025]),
            "holdout_fixtures_2026": len(rows[2026]),
            "temperature_grid": {"min": temperatures[0], "max": temperatures[-1], "step": 0.01,
                                  "criterion": "lowest 2025 settlement log loss"},
            "selected_temperature": selected_temp,
            "training_log_loss_at_temperature_1": training_scores["1.0"],
            "training_log_loss_selected": training_scores[str(selected_temp)],
            "holdout_raw": metrics(raw_holdout),
            "holdout_calibrated": metrics(calibrated_holdout),
            "temperature_fit_uses_2026": False,
        }

    report = {
        "protocol": "M5_M3_PRIOR_YEAR_SETTLEMENT_TEMPERATURE_2025_FIT_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "private_forecasts_sha256": raw_sha.hexdigest(),
        "selector_report_sha256": hashlib.sha256(selector_report.read_bytes()).hexdigest(),
        "markets": market_output,
        "training_rule": "Model selection and temperature tuning use only 2025 OOS fixture results. The 2026 fixture set remains the untouched temporal holdout; one bet is retained per available fixture-market with no EV or confidence threshold.",
        "all_historical_receipts_post_kickoff": all(
            not fixture["quotes"][market]["receipt_before_kickoff"]
            for fixtures in rows.values() for fixture in fixtures for market in MARKETS),
        "forecast_and_quote_event_time_order_passed": True,
        "production_changes": False,
        "limitations": ["2026 holdout n=9,400 per market, below the 10,000 target.",
                        "Historical quote responses were received after kickoff; ROI is not executable performance.",
                        "A positive result would still require a future received-before-kickoff cohort."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-predictions", type=Path, required=True)
    parser.add_argument("--selector-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_predictions, args.selector_report, args.output)
    print(json.dumps({m: {"temperature": x["selected_temperature"],
                          "raw_roi": x["holdout_raw"]["roi_pct"],
                          "calibrated_roi": x["holdout_calibrated"]["roi_pct"],
                          "raw_log_loss": x["holdout_raw"]["settlement_log_loss"],
                          "calibrated_log_loss": x["holdout_calibrated"]["settlement_log_loss"]}
                      for m, x in report["markets"].items()}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
