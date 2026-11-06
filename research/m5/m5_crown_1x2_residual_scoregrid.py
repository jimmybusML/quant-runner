#!/usr/bin/env python3
"""Use event-time Crown 1X2 as a residual feature for M5 AH/OU grids.

Per market, fit one scalar on 2025 Crown rows by exact-score log loss. Apply
the result to every 2026 Crown-first/TOTAL-default row: adjust the score grid
when a qualifying post-asof pre-kickoff Crown 1X2 exists; otherwise retain the
M5 grid. All fixture data remain private, and each market keeps every row.
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
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import minimize_scalar

from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc
from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
from research.m5.m5_line_conditional_settlement_calibration import (
    CATEGORIES, build_rows, settlement_distribution,
)
from research.m5.m5_source_union_replay import read_jsonl

MARKETS = ("AH", "OU")
RESULTS = ("home", "draw", "away")


def instant(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def select_crown_1x2(raw_path: Path, match_id: str, forecast: dict, zone: ZoneInfo,
                     receipt_utc: datetime | None):
    """Return the latest qualifying Crown 1X2 probabilities and source time."""
    try:
        payload = json.loads(raw_path.read_bytes())
        data = payload.get("data")
        rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        exact = [r for r in rows if isinstance(r, dict) and str(r.get("id") or "") == match_id]
        if payload.get("success") != 1 or len(exact) != 1:
            return None
        row = exact[0]
        kickoff = instant(forecast.get("kickoff"))
        asof = instant(forecast.get("prediction_asof_utc"))
        if ((row.get("h"), row.get("a"), row.get("l")) !=
                (forecast.get("home"), forecast.get("away"), forecast.get("league"))
                or local_to_utc(row.get("start"), zone) != kickoff or not kickoff or not asof
                or not receipt_utc):
            return None
        books = [b for b in row.get("bookmakers", [])
                 if isinstance(b, dict) and b.get("slug") == "crown"]
        if len(books) != 1:
            return None
        candidates = []
        odds = books[0].get("odds") or {}
        for label in ("open", "close"):
            quote = odds.get(label) or {}
            event = local_to_utc(quote.get("time"), zone)
            try:
                prices = tuple(float(quote[key]) for key in RESULTS)
            except (KeyError, TypeError, ValueError):
                continue
            if (event and asof <= event < kickoff and event <= receipt_utc
                    and all(math.isfinite(p) and p > 1 for p in prices)):
                inverse = [1.0 / p for p in prices]
                total = math.fsum(inverse)
                candidates.append((event, [p / total for p in inverse], label))
        if not candidates:
            return None
        event, probabilities, label = max(candidates, key=lambda x: x[0])
        return {"event_utc": event, "receipt_utc": receipt_utc,
                "receipt_timing": "pre_kickoff" if receipt_utc < kickoff else "post_kickoff",
                "probabilities": probabilities, "field": label}
    except Exception:
        return None


def model_result_probs(grid):
    p = [0.0, 0.0, 0.0]
    for home, row in enumerate(grid):
        for away, mass in enumerate(row):
            p[0 if home > away else 1 if home == away else 2] += float(mass)
    total = math.fsum(p)
    return [max(v / total, 1e-15) for v in p]


def residual_vector(grid, market_probs):
    base = model_result_probs(grid)
    target = [max(float(x), 1e-15) for x in market_probs]
    target_total = math.fsum(target)
    target = [x / target_total for x in target]
    return [math.log(target[i] / base[i]) for i in range(3)]


def tilt_grid(grid, residual, beta):
    logs = []
    for home, row in enumerate(grid):
        values = []
        for away, probability in enumerate(row):
            result_idx = 0 if home > away else 1 if home == away else 2
            values.append(math.log(max(float(probability), 1e-300)) + beta * residual[result_idx])
        logs.append(values)
    peak = max(x for row in logs for x in row)
    weights = [[math.exp(x - peak) for x in row] for row in logs]
    total = math.fsum(x for row in weights for x in row)
    if not total or not math.isfinite(total):
        raise ValueError("invalid tilted score grid")
    return [[x / total for x in row] for row in weights]


def fit_beta(rows):
    if len(rows) < 20:
        raise ValueError("insufficient Crown 1X2 training rows")
    def nll(beta):
        losses = []
        for row in rows:
            grid = tilt_grid(row["grid"], residual_vector(row["grid"], row["market_1x2"]), float(beta))
            home, away = row["score"]
            losses.append(-math.log(max(grid[home][away], 1e-15)))
        return math.fsum(losses) / len(losses)
    fitted = minimize_scalar(nll, bounds=(-2.0, 2.0), method="bounded",
                             options={"xatol": 1e-6, "maxiter": 300})
    if not fitted.success or not math.isfinite(float(fitted.fun)):
        raise RuntimeError("Crown 1X2 residual fit failed")
    return {"training_rows": len(rows), "beta": float(fitted.x),
            "baseline_exact_score_log_loss": round(nll(0.0), 8),
            "fitted_exact_score_log_loss": round(float(fitted.fun), 8),
            "fit_objective": "2025 exact-score negative log likelihood; not ROI",
            "at_search_boundary": abs(abs(float(fitted.x)) - 2.0) < 1e-3}


def evaluate(rows, market, beta, market_probs_by_id, seed):
    sides = ("home", "away") if market == "AH" else ("over", "under")
    counts = Counter()
    by_source = defaultdict(list)
    event_pnl = defaultdict(float)
    selected_rows = []
    ll, brier = [], []
    for row in rows:
        market_quote = market_probs_by_id.get(row["match_id"])
        grid = row["grid"]
        if market_quote:
            grid = tilt_grid(grid, residual_vector(grid, market_quote["probabilities"]), beta)
        distributions = [settlement_distribution(grid, market, side, row["line"]) for side in sides]
        ev = [expected_return(grid, market, side, row["line"], price)
              for side, price in zip(sides, row["prices"])]
        index = 0 if ev[0] >= ev[1] else 1
        legs, category = legs_result(market, sides[index], row["line"], *row["score"])
        pnl = payout(legs, row["prices"][index])
        distribution = distributions[index]
        counts[category] += 1
        ll.append(-math.log(max(float(distribution[category]), 1e-15)))
        brier.append(math.fsum((float(distribution[c]) - float(c == category)) ** 2 for c in CATEGORIES))
        by_source[row["source"]].append(pnl)
        event_pnl[row["event_utc"]] += pnl
        selected_rows.append(pnl)
    n = len(rows)
    net = math.fsum(selected_rows)
    equity = peak = dd = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    rng = random.Random(seed)
    boot = sorted(100 * math.fsum(selected_rows[rng.randrange(n)] for _ in range(n)) / n
                  for _ in range(3000))
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "settlement_counts": {c: counts[c] for c in CATEGORIES},
        "net_units": round(net, 6), "roi_pct": round(100 * net / n, 6),
        "max_drawdown_units_by_quote_event_time": round(dd, 6),
        "settlement_log_loss": round(math.fsum(ll) / n, 8),
        "settlement_brier": round(math.fsum(brier) / n, 8),
        "roi_bootstrap_95pct": {"lower": round(boot[74], 6), "upper": round(boot[2924], 6),
                                "resamples": 3000, "seed": seed},
        "source_fixture_markets": {k: len(v) for k, v in sorted(by_source.items())},
        "source_split_roi": {k: {"n": len(v), "net_units": round(math.fsum(v), 6),
                                 "roi_pct": round(100 * math.fsum(v) / len(v), 6)}
                             for k, v in sorted(by_source.items())},
    }


def run(private_dir: Path, output: Path, source_timezone="Asia/Shanghai", forecast_path=None):
    samples, input_hashes, _ = build_rows(private_dir, source_timezone, forecast_path)
    root = ensure_private_destination(private_dir)
    forecast_file = forecast_path or root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecast_bytes = forecast_file.read_bytes()
    forecasts = {}
    for line in forecast_bytes.decode().splitlines():
        try:
            r = json.loads(line)
            forecasts[str(r["match_id"])] = r
        except Exception:
            continue
    zone = ZoneInfo(source_timezone)
    crown_index = {str(x.get("match_id")): x for x in read_jsonl(root / "crown-response-index.jsonl")}
    quote_probs, quote_times, response_hashes = {}, {}, set()
    for mid, forecast in forecasts.items():
        path = root / "crown-responses" / f"{mid}.json"
        if not path.exists():
            continue
        receipt = instant(crown_index.get(mid, {}).get("captured_at_utc"))
        quote = select_crown_1x2(path, mid, forecast, zone, receipt)
        if quote:
            quote_probs[mid] = quote
            quote_times[mid] = quote["event_utc"]
            response_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())

    results = {}
    for market in MARKETS:
        training_ids = {r["match_id"] for r in samples[2025][market]}
        holdout_ids = {r["match_id"] for r in samples[2026][market]}
        if training_ids & holdout_ids:
            raise RuntimeError(f"fixture identity leaked between years for {market}")
        train_rows = []
        for row in samples[2025][market]:
            if row["source"] != "Crown" or row["match_id"] not in quote_probs:
                continue
            q = quote_probs[row["match_id"]]
            train_rows.append({**row, "market_1x2": q["probabilities"]})
        if not train_rows:
            raise ValueError(f"no 2025 qualifying Crown 1X2 training rows for {market}")
        fitted = fit_beta(train_rows)
        test = samples[2026][market]
        evaluated_quote_map = {r["match_id"]: quote_probs[r["match_id"]]
                               for r in test if r["source"] == "Crown" and r["match_id"] in quote_probs}
        if any(not instant(r["event_utc"]) or r["match_id"] not in quote_times
               for r in train_rows):
            raise RuntimeError("missing event-time proof for fitted Crown 1X2 row")
        train_receipts = Counter(quote_probs[r["match_id"]]["receipt_timing"] for r in train_rows)
        holdout_receipts = Counter(quote_probs[mid]["receipt_timing"] for mid in evaluated_quote_map)
        results[market] = {
            "training_utc_year": 2025, "holdout_utc_year": 2026,
            "training_crown_rows_with_qualifying_1x2": len(train_rows),
            "holdout_fixture_markets": len(test),
            "training_holdout_fixture_ids_disjoint": True,
            "holdout_crown_rows_with_qualifying_1x2": len(evaluated_quote_map),
            "holdout_crown_rows_without_qualifying_1x2_using_baseline_grid": sum(
                r["source"] == "Crown" and r["match_id"] not in evaluated_quote_map for r in test),
            "holdout_totalcorner_rows_without_1x2_using_baseline_grid": sum(
                r["source"] == "TotalCorner_default" for r in test),
            "qualifying_1x2_response_receipt_timing": {
                "2025_training": dict(sorted(train_receipts.items())),
                "2026_holdout": dict(sorted(holdout_receipts.items())),
            },
            "fitted_2025": fitted,
            "2026_baseline": evaluate(test, market, 0.0, {}, 20261112),
            "2026_crown_1x2_residual_plus_baseline_fallback": evaluate(
                test, market, fitted["beta"], evaluated_quote_map, 20261113),
        }

    report = {
        "protocol": "M5_CROWN_1X2_RESIDUAL_SCOREGRID_2025_FIT_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_hashes": {**input_hashes,
                         "crown_1x2_response_hash_set_sha256": hashlib.sha256(
                             "\n".join(sorted(response_hashes)).encode()).hexdigest()},
        "markets": results,
        "method": "Fit one AH-specific and one OU-specific scalar on 2025 Crown 1X2 rows by exact-score log loss: exponentially tilt the M5 grid by log(de-vig Crown 1X2 probability / M5 result probability). On 2026, use the latest open/close Crown 1X2 quote whose local event time converts to UTC after M5 forecast-asof and before kickoff; apply the correction to every qualifying Crown-priced AH/OU row, and retain the base M5 grid on rows without qualifying 1X2 (including TotalCorner default). One bet per fixture-market, no filters or ROI gates.",
        "source_and_time_integrity": {
            "Crown_only_1x2_feature": True,
            "TotalCorner_default_used_as_1x2": False,
            "Crown_and_TotalCorner_lines_keep_distinct_sources": True,
            "AH_and_OU_fit_separately": True,
            "source_priority_per_market": "Crown first; TotalCorner default only if Crown market quote absent",
            "qualifying_1x2_time": "forecast_asof_utc <= Crown odds.open/close event time < kickoff_utc",
            "response_receipt_limitation": "Each 1X2 receipt is verified not earlier than its quote event; historical Crown API receipts were post-kickoff, so only quote event time is pre-kickoff. ROI is retrospective event-time simulation, not receipt-verified executable ROI.",
            "holdout_fixture_ids_disjoint_from_training": all(
                value["training_holdout_fixture_ids_disjoint"] for value in results.values()),
        },
        "limitations": [
            "2026 was previously inspected in M5 research and is not an untouched confirmatory sample.",
            "The model only has a Crown 1X2 feature on Crown rows; TotalCorner default rows and rows with no qualifying 1X2 retain the base M5 grid but remain in the full union denominator.",
            "The M5 1X2 feature is a de-vig Crown line, not MR1 forecast reuse; no MR1 predictions, orders, ledger or parameters are inputs.",
        ],
        "fixture_level_data_published": False,
        "production_changes": False,
        "new_bet_gate_added": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--forecast-path", type=Path)
    p.add_argument("--source-timezone", default="Asia/Shanghai")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = run(a.private_dir, a.output, a.source_timezone, a.forecast_path)
    print(json.dumps({m: {"training": v["training_crown_rows_with_qualifying_1x2"],
                          "holdout": v["holdout_fixture_markets"],
                          "baseline_roi": v["2026_baseline"]["roi_pct"],
                          "model_roi": v["2026_crown_1x2_residual_plus_baseline_fallback"]["roi_pct"]}
                      for m, v in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
