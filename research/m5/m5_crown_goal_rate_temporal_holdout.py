#!/usr/bin/env python3
"""Temporal holdout for outcome-fitted M5 goal-rate calibration on Crown.

Fits separate home/away goal-rate multipliers from M5 score grids and actual
scores before a fixed UTC cutoff. It then evaluates the unchanged side choice
rule on later Crown source-event quotes. No ROI thresholds or row filters are
used. Raw fixture data must remain in a private directory.
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

from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc
from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout, bootstrap, score
from research.m5.m5_source_union_replay import event_rows, fixture_row, raw_event


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def normalize_grid(grid):
    if not isinstance(grid, list) or not grid:
        return None
    try:
        values = [[float(v) for v in row] for row in grid]
        mass = math.fsum(v for row in values for v in row)
        if (not math.isfinite(mass) or mass <= 0
                or any(not math.isfinite(v) or v < 0 for row in values for v in row)
                or abs(mass - 1.0) > 1e-7):
            return None
        return values
    except (TypeError, ValueError):
        return None


def tilt_grid(grid, home_factor, away_factor):
    log_home, log_away = math.log(home_factor), math.log(away_factor)
    log_weights = []
    maximum = -math.inf
    for home, row in enumerate(grid):
        out = []
        for away, probability in enumerate(row):
            value = math.log(max(probability, 1e-300)) + home * log_home + away * log_away
            maximum = max(maximum, value)
            out.append(value)
        log_weights.append(out)
    weights = [[math.exp(value - maximum) for value in row] for row in log_weights]
    total = math.fsum(value for row in weights for value in row)
    return [[value / total for value in row] for row in weights]


def market_distribution(grid, market, side, line):
    result = defaultdict(float)
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _, category = legs_result(market, side, line, home, away)
            result[category] += probability
    return result


def evaluate(market, rows, calibration, seed):
    categories = ("win", "half_win", "push", "half_loss", "loss")
    sides = ("home", "away") if market == "AH" else ("over", "under")
    outcomes = Counter()
    pnl_rows = []
    scores = []
    for row in rows:
        grid = row["grid"] if calibration is None else tilt_grid(row["grid"], *calibration)
        evs = [expected_return(grid, market, side, row["line"], price)
               for side, price in zip(sides, row["prices"])]
        side_idx = 0 if evs[0] >= evs[1] else 1
        side = sides[side_idx]
        legs, category = legs_result(market, side, row["line"], *row["actual"])
        pnl = payout(legs, row["prices"][side_idx])
        distribution = market_distribution(grid, market, side, row["line"])
        ll = -math.log(max(distribution[category], 1e-15))
        brier = math.fsum((distribution[c] - (1.0 if c == category else 0.0)) ** 2
                          for c in categories)
        outcomes[category] += 1
        scores.append((ll, brier))
        pnl_rows.append({"pnl": pnl, "event": row["quote_event"], "match_id": row["match_id"]})

    by_event = defaultdict(float)
    for row in pnl_rows:
        by_event[row["event"]] += row["pnl"]
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    values = [row["pnl"] for row in pnl_rows]
    net = math.fsum(values)
    n = len(values)
    boot = bootstrap(values, seed) if n else None
    if boot:
        boot = {**boot, "lower_95": round(100 * boot["lower_95"], 6),
                "upper_95": round(100 * boot["upper_95"], 6), "units": "percent"}
    ll, br = score([]) if not scores else (math.fsum(x[0] for x in scores) / n,
                                          math.fsum(x[1] for x in scores) / n)
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n, "pending_bets": 0,
        "settlement_counts": {c: outcomes[c] for c in categories},
        "net_units": round(net, 6), "total_stake_units": n,
        "roi_pct": round(100 * net / n, 6) if n else None,
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6) if n else None,
        "roi_bootstrap_95pct": boot,
        "settlement_log_loss": round(ll, 8) if n else None,
        "settlement_brier": round(br, 8) if n else None,
        "source_fixture_markets": {"Crown": n},
    }


def fit_rate_factors(rows):
    # Each fixture occurs once per market; deduplicate defensively.
    unique = {}
    for row in rows:
        unique.setdefault(row["match_id"], row)
    actual_home = math.fsum(row["actual"][0] for row in unique.values())
    actual_away = math.fsum(row["actual"][1] for row in unique.values())
    pred_home = math.fsum(
        home * probability
        for row in unique.values()
        for home, gridrow in enumerate(row["grid"])
        for probability in gridrow
    )
    pred_away = math.fsum(
        away * probability
        for row in unique.values()
        for gridrow in row["grid"]
        for away, probability in enumerate(gridrow)
    )
    if not unique or pred_home <= 0 or pred_away <= 0 or actual_home <= 0 or actual_away <= 0:
        raise ValueError("training data cannot estimate finite goal-rate multipliers")
    return {
        "training_unique_fixtures": len(unique),
        "training_actual_home_goals": int(actual_home),
        "training_actual_away_goals": int(actual_away),
        "training_predicted_home_goals": round(pred_home, 8),
        "training_predicted_away_goals": round(pred_away, 8),
        "home_rate_multiplier": actual_home / pred_home,
        "away_rate_multiplier": actual_away / pred_away,
    }


def run(private_path: Path, output: Path, cutoff: str, source_timezone: str):
    root = ensure_private_destination(private_path)
    zone = ZoneInfo(source_timezone)
    split = instant(cutoff + "T00:00:00Z")
    if split is None:
        raise ValueError("cutoff must be an ISO UTC date")
    manifest_raw = (root / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    forecast_path = root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecast_raw = forecast_path.read_bytes()
    forecasts = {}
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    candidate_by_id = {str(r.get("match_id")): r for r in manifest.get("rows", [])}
    receipt_by_id = {}
    index_path = root / "crown-response-index.jsonl"
    for line in index_path.read_text(encoding="utf-8").splitlines() if index_path.exists() else []:
        try:
            receipt_by_id[str(json.loads(line).get("match_id"))] = json.loads(line)
        except Exception:
            continue

    markets = {m: {} for m in ("AH", "OU")}
    counters = Counter()
    hashes = set()
    for mid, forecast in forecasts.items():
        fixture = candidate_by_id.get(mid)
        if not fixture:
            continue
        train_end = instant(forecast.get("train_end_utc"))
        asof = instant(forecast.get("prediction_asof_utc"))
        kickoff = instant(forecast.get("kickoff"))
        if not train_end or not asof or not kickoff or not (train_end < asof < kickoff):
            counters["invalid_forecast_chronology"] += 1
            continue
        if (forecast.get("league"), forecast.get("home"), forecast.get("away"), forecast.get("kickoff"),
                forecast.get("home_goals"), forecast.get("away_goals")) != (
                fixture.get("league"), fixture.get("home"), fixture.get("away"), fixture.get("kickoff_utc"),
                fixture.get("home_goals"), fixture.get("away_goals")):
            counters["fixture_identity_or_score_mismatch"] += 1
            continue
        score_actual = (int(fixture["home_goals"]), int(fixture["away_goals"]))
        grid = normalize_grid((forecast.get("prediction") or {}).get("grid"))
        if grid is None:
            counters["invalid_score_grid"] += 1
            continue
        if sum(map(len, grid)) < 1:
            continue
        raw_path = root / "crown-responses" / f"{mid}.json"
        if not raw_path.exists():
            continue
        try:
            raw = raw_path.read_bytes()
            payload = json.loads(raw)
            provider = fixture_row(payload, mid)
            if (payload.get("success") != 1 or not provider
                    or provider.get("h") != fixture["home"] or provider.get("a") != fixture["away"]
                    or provider.get("l") != fixture["league"]):
                counters["invalid_crown_identity"] += 1
                continue
            if local_to_utc(provider.get("start"), zone) != kickoff or (
                    int(provider.get("hg")), int(provider.get("ag"))) != score_actual:
                counters["crown_score_or_kickoff_mismatch"] += 1
                continue
            receipt = instant(receipt_by_id.get(mid, {}).get("captured_at_utc"))
            if receipt is None:
                counters["missing_receipt_timestamp"] += 1
                continue
            input_hash = hashlib.sha256(raw).hexdigest()
            for market in ("AH", "OU"):
                selected = raw_event(event_rows(provider, market, "crown"), market, asof, kickoff, zone)
                if not selected:
                    continue
                observed, line, prices = selected
                if receipt < observed:
                    counters["receipt_before_source_event"] += 1
                    continue
                record = {"match_id": mid, "grid": grid, "actual": score_actual,
                          "line": line, "prices": prices, "quote_event": observed,
                          "kickoff": kickoff, "receipt": receipt, "league": fixture.get("league")}
                row_market = markets[market]
                target = "train" if kickoff < split else "holdout"
                row_market.setdefault(target, {})[mid] = record
                input_hashes = hashes
                input_hashes.add(input_hash)
                if receipt < kickoff:
                    counters["receipt_before_kickoff_" + market] += 1
                else:
                    counters["receipt_after_kickoff_" + market] += 1
        except Exception:
            counters["invalid_crown_response"] += 1

    report_markets = {}
    for idx, market in enumerate(("AH", "OU")):
        training = list(markets[market].get("train", {}).values())
        holdout = list(markets[market].get("holdout", {}).values())
        if not training or not holdout:
            report_markets[market] = {"status": "insufficient_temporal_rows",
                                      "training_fixture_markets": len(training),
                                      "holdout_fixture_markets": len(holdout)}
            continue
        factors = fit_rate_factors(training)
        report_markets[market] = {
            "cutoff_utc": cutoff + "T00:00:00Z",
            "training_unique_fixture_markets": len(training),
            "holdout_unique_fixture_markets": len(holdout),
            "training_fixture_ids_disjoint_from_holdout": not bool(
                {r["match_id"] for r in training} & {r["match_id"] for r in holdout}),
            "training_kickoff_range_utc": [min(r["kickoff"].isoformat() for r in training),
                                           max(r["kickoff"].isoformat() for r in training)],
            "holdout_kickoff_range_utc": [min(r["kickoff"].isoformat() for r in holdout),
                                          max(r["kickoff"].isoformat() for r in holdout)],
            "parameter_fit": {**factors,
                "method": "separate Poisson log-rate intercept MLE from prior-period actual goals / prior-period score-grid expected goals; no ROI optimization"},
            "raw_holdout": evaluate(market, holdout, None, 20261160 + idx),
            "calibrated_holdout": evaluate(market, holdout,
                (factors["home_rate_multiplier"], factors["away_rate_multiplier"]), 20261170 + idx),
            "source": "Crown only; one latest eligible source-event quote per fixture-market",
            "timing": {"holdout_quote_event_between_prediction_asof_and_kickoff": True,
                       "all_api_receipts_after_kickoff": all(r["receipt"] >= r["kickoff"] for r in holdout),
                       "holdout_receipts_before_kickoff": sum(r["receipt"] < r["kickoff"] for r in holdout)},
        }

    report = {
        "protocol": "M5_CROWN_GOAL_RATE_TEMPORAL_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_start_utc": cutoff + "T00:00:00Z",
        "input_hashes": {"candidate_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                         "forecast_sha256": hashlib.sha256(forecast_raw).hexdigest(),
                         "crown_response_hash_set_sha256": hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()},
        "candidate_fixtures": len(candidate_by_id), "forecast_rows": len(forecasts),
        "markets": report_markets, "audit_counts": dict(counters),
        "strategy_definition": "Each fixture-market selects the side with the greater expected return from the corresponding score grid and the latest valid source-time Crown line/prices. Same rule before and after calibration; one unit stake; no EV cutoff, source mixing, or filters.",
        "limits": ["Historical Crown responses are fetched after fixtures; source-event timestamps support retrospective event-time evaluation, not contemporaneous receipt or executable ROI.",
                   "The 2026 temporal holdout is a research holdout, not a pristine preregistered independent era.",
                   "Calibration is a single global home/away goal-rate tilt per market, fitted only on fixtures before the UTC cutoff; no ROI is used to choose parameters."],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"], "markets": report_markets,
                      "audit_counts": report["audit_counts"]}, ensure_ascii=False, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--holdout-start", default="2026-09-01")
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    run(args.private_dir, args.output, args.holdout_start, args.source_timezone)


if __name__ == "__main__":
    main()
