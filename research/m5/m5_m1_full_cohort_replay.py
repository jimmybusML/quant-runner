#!/usr/bin/env python3
"""Run the archived M1 model on the complete M3 expanded OOS cohort.

This local research runner reads private M5 scores/quote snapshots and a
read-only M1 source checkout. It writes aggregate-only results. M1 model
parameters are frozen at their recorded 2024-06-01 cutoff; dynamic team fits
use each UTC-year's pre-cutoff results with M1's documented two-day
retrospective availability buffer. No production entrypoint is called.
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

MARKETS = {"AH": "全场让球", "OU": "全场大小球"}
SIDES = {"AH": ("HOME", "AWAY"), "OU": ("OVER", "UNDER")}
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def instant(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)


def legs_result(market, side, line, home, away):
    q = float(line) * 4
    if not math.isfinite(q) or abs(q - round(q)) > 1e-8:
        raise ValueError("non-quarter line")
    q = int(round(q))
    # The shared M3 settlement contract represents a whole/half line as two
    # identical legs so that the common half-stake payout routine returns the
    # full win/loss amount; quarter lines split across adjacent half lines.
    legs = (q, q) if q % 2 == 0 else (q - 1, q + 1)
    out = []
    for leg in legs:
        if market == "AH":
            if side == "HOME":
                signed = 4 * (home - away) + leg
            else:
                # The input line is the home-side handicap. The away contract
                # is its exact opposite, as in the M3 historical settlement.
                signed = 4 * (away - home) - leg
        else:
            total = home + away
            signed = 4 * total - leg if side == "OVER" else leg - 4 * total
        out.append(1 if signed > 0 else -1 if signed < 0 else 0)
    ordered = sorted(out)
    category = ("win" if ordered == [1, 1] else "half_win" if ordered == [0, 1]
                else "loss" if ordered == [-1, -1] else "half_loss" if ordered == [-1, 0]
                else "push")
    return out, category


def payout(legs, decimal_price):
    return sum(decimal_price - 1 if x == 1 else -1 if x == -1 else 0 for x in legs) / 2


def summarize(rows, seed):
    n = len(rows)
    pnl = [float(row["pnl"]) for row in rows]
    categories = Counter(row["category"] for row in rows)
    per_event = defaultdict(float)
    for row in rows:
        per_event[row["event_utc"]] += row["pnl"]
    equity = peak = drawdown = 0.0
    for event in sorted(per_event):
        equity += per_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    ll = brier = 0.0
    if n:
        for row in rows:
            dist = row["distribution"]
            actual = row["category"]
            ll -= math.log(max(float(dist.get(actual, 0.0)), 1e-15))
            brier += sum((float(dist.get(cat, 0.0)) - (cat == actual)) ** 2 for cat in CATEGORIES)
        ll /= n
        brier /= n
    rng = random.Random(seed)
    bootstrap = None
    if n:
        samples = sorted(sum(pnl[rng.randrange(n)] for _ in range(n)) / n for _ in range(5000))
        bootstrap = {"method": "fixture percentile bootstrap, descriptive only", "repetitions": 5000,
                     "lower_95_roi_pct": round(100 * samples[int(.025 * 4999)], 6),
                     "upper_95_roi_pct": round(100 * samples[int(.975 * 4999)], 6)}
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n, "stake_units": n,
        "net_units": round(sum(pnl), 6), "roi_pct": round(100 * sum(pnl) / n, 6) if n else None,
        "settlement_counts": {cat: categories[cat] for cat in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6) if n else None,
        "settlement_log_loss": round(ll, 8) if n else None,
        "settlement_brier": round(brier, 8) if n else None,
        "roi_bootstrap_95pct": bootstrap,
        "quote_sources": dict(Counter(row["source"] for row in rows)),
        "response_receipt_timing": dict(Counter("pre_kickoff" if row["receipt_before_kickoff"] else "post_kickoff" for row in rows)),
    }


def run(private_dir: Path, m1_repo: Path, m3_rows_path: Path, output: Path, private_trace: Path):
    repo_root = Path(__file__).resolve().parents[2]
    trace_resolved = private_trace.expanduser().resolve()
    if trace_resolved == repo_root or repo_root in trace_resolved.parents:
        raise ValueError("fixture-level M1 trace must remain outside the public repository")
    sys.path.insert(0, str(m1_repo.resolve()))
    from m1_current import fit_dynamic, joint_grid

    manifest_path = private_dir / "candidate-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    scores = {str(r["match_id"]): r for r in manifest["rows"]
              if r.get("home_goals") is not None and r.get("away_goals") is not None}
    params_path = m1_repo / "m1_parameters.json"
    params_raw = params_path.read_bytes()
    calibration = json.loads(params_raw)
    if calibration.get("model_family") != "M1" or calibration.get("calibration_cutoff_exclusive") != "2024-06-01":
        raise ValueError("unexpected M1 parameter snapshot")

    m3_rows = []
    with m3_rows_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                m3_rows.append(json.loads(line))
    if len({str(r["match_id"]) for r in m3_rows}) != len(m3_rows):
        raise ValueError("duplicate fixture in M3 comparison cohort")

    by_league = defaultdict(list)
    for row in scores.values():
        kickoff = instant(row["kickoff_utc"])
        by_league[str(row["league"])].append({**row, "_kickoff": kickoff})
    for league in by_league:
        by_league[league].sort(key=lambda r: (r["_kickoff"], str(r["match_id"])))

    predictions = {}
    fit_audit = {}
    failures = Counter()
    grouped = defaultdict(list)
    for row in m3_rows:
        kickoff = instant(row["kickoff_utc"])
        asof = instant(row["prediction_asof_utc"])
        if not asof < kickoff:
            failures["invalid_target_chronology"] += 1
            continue
        source = scores.get(str(row["match_id"]))
        if not source or (source["league"], source["home"], source["away"], source["kickoff_utc"],
                          int(source["home_goals"]), int(source["away_goals"])) != (
                          row["league"], row["home"], row["away"], row["kickoff_utc"],
                          int(row["actual_home_goals"]), int(row["actual_away_goals"])):
            failures["target_identity_or_score_mismatch"] += 1
            continue
        grouped[(str(row["league"]), asof)].append(row)

    for (league, asof), targets in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        histories = by_league.get(league, [])
        history = [dict(home=r["home"], away=r["away"], home_goals=int(r["home_goals"]),
                        away_goals=int(r["away_goals"]), date=r["_kickoff"].date().isoformat(),
                        match_time=r["kickoff_utc"], status="FT", competition=league)
                   for r in histories if r["_kickoff"] < asof]
        if not history:
            failures["no_prior_training_rows"] += len(targets)
            continue
        try:
            state = fit_dynamic(history, league, asof.isoformat(), retrospective=True,
                                shrinkage_prior=calibration["shrinkage_prior"])
        except Exception as exc:
            failures[f"dynamic_fit_{type(exc).__name__}"] += len(targets)
            continue
        fit_audit[f"{league}|{asof.date().isoformat()}"] = {
            "target_fixtures": len(targets), "history_rows_used": state.diagnostics["history_rows"],
            "history_max_date": state.diagnostics["history_max_date"],
            "fit_before_utc": asof.isoformat().replace("+00:00", "Z"),
            "retrospective_two_day_availability_buffer": True,
        }
        for row in targets:
            fixture = scores[str(row["match_id"])]
            base = state.predict(row["home"], row["away"], False)
            try:
                grid, _ = joint_grid(base, league, calibration)
                predictions[str(row["match_id"])] = grid.tolist()
            except Exception as exc:
                failures[f"grid_{type(exc).__name__}"] += 1

    scored = {market: [] for market in MARKETS}
    trace_rows = []
    year_source_counts = {market: defaultdict(list) for market in MARKETS}
    row_ids = set()
    for row in m3_rows:
        mid = str(row["match_id"])
        if mid not in predictions:
            continue
        if mid in row_ids:
            raise ValueError("duplicate scored fixture")
        row_ids.add(mid)
        grid = predictions[mid]
        kickoff = instant(row["kickoff_utc"])
        for market, short in MARKETS.items():
            quote = row.get("quotes", {}).get(market)
            if not quote:
                continue
            event = instant(quote["event_utc"])
            if not event < kickoff:
                failures["quote_event_not_pregame"] += 1
                continue
            source = scores[mid]
            home_score, away_score = int(source["home_goals"]), int(source["away_goals"])
            first, second = SIDES[market]
            prices = [float(x) for x in quote["prices"]]
            if len(prices) != 2 or any(not math.isfinite(p) or p <= 1 for p in prices):
                failures["invalid_quote_prices"] += 1
                continue
            hk = [p - 1 for p in prices]
            from m1_market_calculation import evaluate_side
            line = float(quote["line"])
            line2 = -line if market == "AH" else line
            sides = [evaluate_side(grid, short, first, line, hk[0]),
                     evaluate_side(grid, short, second, line2, hk[1])]
            chosen = 0 if sides[0]["ev"] >= sides[1]["ev"] else 1
            side = (first, second)[chosen]
            legs, category = legs_result(market, side, line, home_score, away_score)
            receipt = instant(quote["receipt_utc"])
            state_names = {"FULL_WIN": "win", "HALF_WIN": "half_win", "PUSH": "push",
                           "HALF_LOSS": "half_loss", "FULL_LOSS": "loss"}
            result = {"pnl": payout(legs, prices[chosen]), "category": category,
                      "distribution": {state_names[k]: v for k, v in sides[chosen]["states"].items()},
                      "event_utc": event.isoformat(),
                      "source": quote["source"], "receipt_before_kickoff": bool(quote["receipt_before_kickoff"]),
                      "year": kickoff.year}
            scored[market].append(result)
            year_source_counts[market][(kickoff.year, quote["source"])].append(result)
            trace_rows.append({"match_id": mid, "market": market, "league": row["league"],
                               "kickoff_utc": row["kickoff_utc"], "prediction_asof_utc": row["prediction_asof_utc"],
                               "source": quote["source"], "event_utc": quote["event_utc"],
                               "receipt_utc": quote["receipt_utc"], "receipt_before_kickoff": quote["receipt_before_kickoff"],
                               "line": line, "prices": prices, "m1_side": side,
                               "m1_selected_decimal_price": prices[chosen],
                               "actual_home_goals": home_score, "actual_away_goals": away_score,
                               "m1_category": category, "m1_pnl": result["pnl"],
                               "m1_distribution": result["distribution"]})

    markets = {}
    for idx, (market, rows) in enumerate(scored.items()):
        markets[market] = {"all_years": summarize(rows, 202611070 + idx),
                           "by_utc_kickoff_year": {}, "by_quote_source": {}}
        for year in sorted({r["year"] for r in rows}):
            markets[market]["by_utc_kickoff_year"][str(year)] = summarize(
                [r for r in rows if r["year"] == year], 202611170 + idx + year)
        for source in sorted({r["source"] for r in rows}):
            markets[market]["by_quote_source"][source] = summarize(
                [r for r in rows if r["source"] == source], 202611270 + idx)

    private_trace = trace_resolved
    private_trace.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_trace.write_text("".join(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n" for r in trace_rows))
    private_trace.chmod(0o600)
    report = {
        "protocol": "M5_M1_ARCHIVED_CORE_FULL_M3_COHORT_UTC_YEAR_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_data_sha256": {"candidate_manifest": hashlib.sha256(manifest_raw).hexdigest(),
                               "public_runner": sha_file(Path(__file__).resolve()),
                               "m3_quote_and_identity_rows": sha_file(m3_rows_path),
                               "m1_current_module": sha_file(m1_repo / "m1_current.py"),
                               "m1_market_calculation_module": sha_file(m1_repo / "m1_market_calculation.py"),
                               "m1_parameters": hashlib.sha256(params_raw).hexdigest(),
                               "m1_private_prediction_trace": sha_file(private_trace)},
        "m1_model_method": calibration["method"],
        "m1_calibration_cutoff_exclusive": calibration["calibration_cutoff_exclusive"],
        "m1_static_shrinkage_prior_fit_before": calibration["shrinkage_prior"]["fit_before"],
        "cohort_unique_fixtures_with_m1_predictions": len(predictions),
        "time_order": "M1 dynamic team fits use only same-league final scores whose UTC calendar date is at least two days before each UTC-year forecast as-of. Frozen M1 calibration and shrinkage prior cutoffs precede every forecast as-of.",
        "quote_policy": "Use the exact Crown-first / TotalCorner-default source, line, and decimal prices paired to the M3 cohort; model side is selected by the larger M1 expected return. Each market is settled independently at 1U per fixture-market.",
        "limitations": ["Historical provider response receipt times were after kickoff in the source archive, so reported ROI is retrospective replay rather than executable ROI.",
                        "M1's documented two-day date-only availability buffer is an explicit reconstruction assumption because historical result ingestion timestamps are not available for the complete cohort.",
                        "M1 calibration parameters are the archived frozen snapshot with 2024-06-01 exclusive cutoff; they are applied unchanged to both 2025 and 2026 test folds."],
        "markets": markets,
        "fold_count": len(fit_audit),
        "audit_counts": dict(failures),
        "fit_audit_sha256": hashlib.sha256(json.dumps(fit_audit, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"], "cohort_unique_fixtures_with_m1_predictions": len(predictions),
                      "markets": {k: v["all_years"] for k, v in markets.items()}, "audit_counts": dict(failures)}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--m1-repo", type=Path, required=True)
    parser.add_argument("--m3-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-trace", type=Path, required=True)
    args = parser.parse_args()
    run(args.private_dir, args.m1_repo, args.m3_rows, args.output, args.private_trace)


if __name__ == "__main__":
    main()
