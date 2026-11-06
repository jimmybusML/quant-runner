#!/usr/bin/env python3
"""Research-only per-market, line-conditioned settlement calibration.

Fits a global temperature and regularized quarter-line temperatures using
2025 M5 OOS forecasts, then evaluates all available 2026 fixture-markets.
Every eligible 2026 market remains in the holdout; calibration changes only
the settlement-probability distribution and never filters fixtures.
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

from scipy.optimize import minimize_scalar

from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc
from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_source_union_replay import (
    event_rows, fixture_row, instant, raw_event, read_jsonl,
)

MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def temperature_adjust(distribution: dict[str, float], temperature: float) -> dict[str, float]:
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("invalid settlement temperature")
    powered = {key: max(0.0, float(distribution.get(key, 0.0))) ** (1.0 / temperature)
               for key in CATEGORIES}
    total = math.fsum(powered.values())
    if total <= 0 or not math.isfinite(total):
        raise ValueError("invalid probability mass")
    return {key: value / total for key, value in powered.items()}


def settlement_distribution(grid, market, side, line):
    result = Counter()
    mass = math.fsum(float(p) for row in grid for p in row)
    if not math.isfinite(mass) or mass <= 0:
        raise ValueError("invalid score-grid mass")
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _, category = legs_result(market, side, line, home, away)
            result[category] += float(probability) / mass
    return {category: float(result.get(category, 0.0)) for category in CATEGORIES}


def settlement_expected_return(distribution, price):
    payoffs = {"win": price - 1.0, "half_win": (price - 1.0) / 2.0,
               "push": 0.0, "half_loss": -0.5, "loss": -1.0}
    return math.fsum(float(distribution.get(category, 0.0)) * payoffs[category]
                     for category in CATEGORIES)


def fit_temperature(rows, shrinkage: float = 25.0) -> float:
    """Fit NLL temperature; per-line fits shrink log-temperature to global."""
    if not rows:
        raise ValueError("empty calibration sample")
    labels = [row["actual"] for row in rows]
    distributions = [row["distribution"] for row in rows]
    global_target = math.log(rows[0].get("global_temperature", 1.0))

    def objective(log_temperature):
        temperature = math.exp(log_temperature)
        losses = []
        for distribution, label in zip(distributions, labels):
            adjusted = temperature_adjust(distribution, temperature)
            losses.append(-math.log(max(adjusted[label], 1e-15)))
        penalty = 0.5 * shrinkage * (log_temperature - global_target) ** 2
        return math.fsum(losses) + penalty

    fit = minimize_scalar(objective, bounds=(math.log(0.25), math.log(4.0)),
                          method="bounded", options={"xatol": 1e-9, "maxiter": 500})
    if not fit.success or not math.isfinite(float(fit.fun)):
        raise RuntimeError("temperature calibration failed")
    return math.exp(float(fit.x))


def metrics(rows):
    counts = Counter(row["actual"] for row in rows)
    n = len(rows)
    net = math.fsum(row["pnl"] for row in rows)
    equity = peak = drawdown = 0.0
    by_event = defaultdict(float)
    for row in rows:
        by_event[row["event_utc"]] += row["pnl"]
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    log_losses, briers = [], []
    for row in rows:
        probabilities = row["distribution"]
        log_losses.append(-math.log(max(probabilities[row["actual"]], 1e-15)))
        briers.append(math.fsum((probabilities[c] - float(c == row["actual"])) ** 2
                                for c in CATEGORIES))
    return {"unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
            "settlement_counts": {c: counts[c] for c in CATEGORIES},
            "net_units": round(net, 6), "roi_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_units_by_quote_event_time": round(drawdown, 6) if n else None,
            "settlement_log_loss": round(math.fsum(log_losses) / n, 8) if n else None,
            "settlement_brier": round(math.fsum(briers) / n, 8) if n else None,
            "source_fixture_markets": dict(sorted(Counter(r["source"] for r in rows).items())),
            "receipt_timing": dict(sorted(Counter(r["receipt_timing"] for r in rows).items()))}


def choose_side(row, market, temperature):
    sides = ("home", "away") if market == "AH" else ("over", "under")
    distributions = [settlement_distribution(row["grid"], market, side, row["line"])
                     for side in sides]
    adjusted = [temperature_adjust(d, temperature) for d in distributions]
    evs = [settlement_expected_return(d, price) for d, price in zip(adjusted, row["prices"])]
    index = 0 if evs[0] >= evs[1] else 1
    side = sides[index]
    legs, actual = legs_result(market, side, row["line"], *row["score"])
    return {"actual": actual, "pnl": payout(legs, row["prices"][index]),
            "distribution": adjusted[index], "source": row["source"],
            "receipt_timing": row["receipt_timing"], "event_utc": row["event_utc"]}


def build_rows(private_dir: Path, source_timezone: str, forecast_path: Path | None):
    root = ensure_private_destination(private_dir)
    zone = ZoneInfo(source_timezone)
    manifest_raw = (root / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    path = forecast_path or root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecast_raw = path.read_bytes()
    forecasts = {}
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    crown_index = {str(r.get("match_id")): r for r in read_jsonl(root / "crown-response-index.jsonl")}
    total_index = {str(r.get("match_id")): r for r in read_jsonl(root / "totalcorner-default-index.jsonl")
                   if r.get("status") == "verified_fixture_response"}
    samples = {year: {market: [] for market in MARKETS} for year in (2025, 2026)}
    hashes, counts = set(), Counter()
    for fixture in manifest.get("rows", []):
        mid = str(fixture.get("match_id") or "")
        forecast = forecasts.get(mid)
        if not forecast:
            continue
        kickoff = instant(forecast.get("kickoff"))
        if not kickoff or kickoff.year not in samples:
            continue
        asof, train_end = instant(forecast.get("prediction_asof_utc")), instant(forecast.get("train_end_utc"))
        if not asof or not train_end or not train_end < asof < kickoff:
            counts["invalid_forecast_chronology"] += 1
            continue
        identity = (forecast.get("league"), forecast.get("home"), forecast.get("away"),
                    forecast.get("kickoff"), forecast.get("home_goals"), forecast.get("away_goals"))
        expected_identity = (fixture.get("league"), fixture.get("home"), fixture.get("away"),
                             fixture.get("kickoff_utc"), fixture.get("home_goals"), fixture.get("away_goals"))
        if identity != expected_identity:
            counts["forecast_fixture_identity_mismatch"] += 1
            continue
        grid = (forecast.get("prediction") or {}).get("grid")
        if not isinstance(grid, list) or not grid:
            counts["missing_score_grid"] += 1
            continue
        score = (int(fixture["home_goals"]), int(fixture["away_goals"]))
        for market in MARKETS:
            selected = source = receipt = response_hash = None
            crown_path = root / "crown-responses" / f"{mid}.json"
            if crown_path.exists():
                try:
                    raw = crown_path.read_bytes()
                    payload = json.loads(raw)
                    row = fixture_row(payload, mid)
                    if (payload.get("success") == 1 and row
                            and (row.get("h"), row.get("a"), row.get("l"))
                            == (fixture["home"], fixture["away"], fixture["league"])
                            and local_to_utc(row.get("start"), zone) == kickoff
                            and (int(row.get("hg")), int(row.get("ag"))) == score):
                        selected = raw_event(event_rows(row, market, "crown"), market, asof, kickoff, zone)
                        if selected:
                            source = "Crown"
                            receipt = instant(crown_index.get(mid, {}).get("captured_at_utc"))
                            response_hash = hashlib.sha256(raw).hexdigest()
                except Exception:
                    counts["invalid_crown_response"] += 1
            if selected is None:
                total_path = root / "totalcorner-default-responses" / f"{mid}.json"
                entry = total_index.get(mid)
                if total_path.exists() and entry:
                    try:
                        raw = total_path.read_bytes()
                        payload = json.loads(raw)
                        row = fixture_row(payload, mid)
                        score_ok = row and ((row.get("hg") is None and row.get("ag") is None)
                                           or (int(row.get("hg")), int(row.get("ag"))) == score)
                        if (payload.get("success") == 1 and row and score_ok
                                and (row.get("h"), row.get("a"), row.get("l"))
                                == (fixture["home"], fixture["away"], fixture["league"])
                                and local_to_utc(row.get("start"), zone) == kickoff):
                            selected = raw_event(event_rows(row, market, "totalcorner"), market, asof, kickoff, zone)
                            if selected:
                                source = "TotalCorner_default"
                                receipt = instant(entry.get("captured_at_utc"))
                                response_hash = hashlib.sha256(raw).hexdigest()
                    except Exception:
                        counts["invalid_totalcorner_response"] += 1
            if not selected:
                continue
            event, line, prices = selected
            if receipt is None or receipt < event or not asof <= event < kickoff:
                counts["invalid_quote_chronology"] += 1
                continue
            receipt_timing = "pre_kickoff" if receipt < kickoff else "post_kickoff"
            samples[kickoff.year][market].append({"match_id": mid, "league": fixture.get("league"),
                "line": float(line), "prices": tuple(map(float, prices)), "event_utc": event,
                "receipt_timing": receipt_timing, "source": source, "grid": grid, "score": score})
            hashes.add(response_hash)
            counts[f"{kickoff.year}_{market}_{source}"] += 1
    return samples, {"manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
                     "forecast_sha256": hashlib.sha256(forecast_raw).hexdigest(),
                     "quote_response_hash_set_sha256": hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()}, counts


def fit_and_evaluate(samples, shrinkage=25.0):
    output = {}
    for market in MARKETS:
        training, holdout = samples[2025][market], samples[2026][market]
        if not training or not holdout:
            raise ValueError(f"missing temporal sample for {market}")
        distributions = []
        for row in training:
            sides = ("home", "away") if market == "AH" else ("over", "under")
            options = [settlement_distribution(row["grid"], market, side, row["line"]) for side in sides]
            evs = [settlement_expected_return(d, p) for d, p in zip(options, row["prices"])]
            idx = 0 if evs[0] >= evs[1] else 1
            legs, actual = legs_result(market, sides[idx], row["line"], *row["score"])
            distributions.append({"distribution": options[idx], "actual": actual})
        global_temperature = fit_temperature(distributions, shrinkage=0.0)
        by_line = defaultdict(list)
        # Fit on the exact quarter-line key seen in the 2025 training sample.
        for sample, calibrated_row in zip(training, distributions):
            calibrated_row["global_temperature"] = global_temperature
            by_line[round(sample["line"] * 4) / 4].append(calibrated_row)
        line_temperatures = {key: fit_temperature(rows, shrinkage=shrinkage)
                             for key, rows in by_line.items()}
        training_raw, training_global, training_line = [], [], []
        for row in training:
            training_raw.append(choose_side(row, market, 1.0))
            training_global.append(choose_side(row, market, global_temperature))
            key = round(row["line"] * 4) / 4
            training_line.append(choose_side(row, market, line_temperatures[key]))
        raw_rows, global_rows, line_rows = [], [], []
        for row in holdout:
            raw_rows.append(choose_side(row, market, 1.0))
            global_rows.append(choose_side(row, market, global_temperature))
            key = round(row["line"] * 4) / 4
            line_rows.append(choose_side(row, market, line_temperatures.get(key, global_temperature)))
        output[market] = {"training_fixture_markets_2025": len(training),
            "holdout_fixture_markets_2026": len(holdout),
            "global_temperature_fit_on_2025_log_loss": round(global_temperature, 8),
            "per_quarter_line_temperature_shrinkage_strength": shrinkage,
            "quarter_line_groups_fit": len(line_temperatures),
            "holdout_lines_without_2025_group": sum(round(r["line"]*4)/4 not in line_temperatures for r in holdout),
            "training_2025_resubstitution_diagnostic": {
                "raw_unadjusted": metrics(training_raw),
                "global_temperature": metrics(training_global),
                "line_conditioned_shrunk_temperature": metrics(training_line)},
            "raw_unadjusted": metrics(raw_rows), "global_temperature": metrics(global_rows),
            "line_conditioned_shrunk_temperature": metrics(line_rows),
            "holdout_results_used_in_fit": False}
    return output


def run(args):
    samples, hashes, counts = build_rows(args.private_dir, args.source_timezone, args.forecast_path)
    market_results = fit_and_evaluate(samples, args.shrinkage)
    report = {"protocol": "M5_LINE_CONDITIONAL_SETTLEMENT_CALIBRATION_2025_FIT_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_hashes": hashes, "training_year": 2025, "holdout_year": 2026,
        "training_and_holdout_counts_by_source": dict(counts), "markets": market_results,
        "method": "For each market, select the higher expected-return side on each 2025 OOS fixture. Fit a global settlement-category temperature by 2025 log loss, then fit exact quarter-line temperatures with an L2 shrinkage penalty on log-temperature toward the global fit. Evaluate all available 2026 OOS fixture-markets without filtering. One unit per fixture-market.",
        "receipt_timing": "All historical API receipts are reported after kickoff; ROI is event-time retrospective and not executable performance.",
        "temporal_isolation_verified": True, "fixture_level_data_published": False,
        "production_changes": False,
        "limitations": ["This is an exploratory calibration model; no threshold, league filter, or fixture exclusion is applied.",
                        "2026 holdout is the only evaluation year and should not be reused to tune shrinkage.",
                        "Historical post-kickoff receipts do not establish executable Crown or TotalCorner ROI."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"], "markets": market_results,
                      "input_hashes": hashes, "counts": dict(counts)}, ensure_ascii=False, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--forecast-path", type=Path)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--shrinkage", type=float, default=25.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.shrinkage < 0 or not math.isfinite(args.shrinkage):
        parser.error("--shrinkage must be finite and non-negative")
    run(args)


if __name__ == "__main__":
    main()
