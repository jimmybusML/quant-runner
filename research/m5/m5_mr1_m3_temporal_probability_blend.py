#!/usr/bin/env python3
"""Train simple MR1/M3 probability blends on 2025, score 2026 on the same Crown cohort.

The private inputs contain fixture-level predictions and prices. Only aggregate
metrics and input hashes are written to the public report.
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

from research.m5.m3_grid_crown_replay import grid_distribution, legs_result, payout

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
MR1_CATEGORY_KEY = {"win": "full_win", "half_win": "half_win", "push": "push",
                    "half_loss": "half_loss", "loss": "full_loss"}
INVERSE = {"win": "loss", "half_win": "half_loss", "push": "push",
           "half_loss": "half_win", "loss": "win"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_m3(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = str(row["match_id"])
        if key in rows:
            raise ValueError("duplicate M3 fixture")
        rows[key] = row
    return raw, rows


def read_mr1(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["match_id"]), row["market"])
        if key in rows:
            raise ValueError("duplicate MR1 fixture-market")
        rows[key] = row
    return raw, rows


def normalize(probs: dict) -> dict:
    out = {c: float(probs.get(c, 0.0)) for c in CATEGORIES}
    if any(not math.isfinite(v) or v < -1e-10 for v in out.values()):
        raise ValueError("invalid settlement probabilities")
    total = sum(out.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError("settlement probabilities do not sum to one")
    return {c: max(0.0, v) / total for c, v in out.items()}


def mr1_distribution(row: dict) -> dict:
    return normalize({c: float(row["probabilities"][MR1_CATEGORY_KEY[c]]) for c in CATEGORIES})


def side_distribution(distribution: dict, selected_side: str, side: str) -> dict:
    if selected_side == side:
        return dict(distribution)
    return {c: float(distribution[INVERSE[c]]) for c in CATEGORIES}


def blend(left: dict, right: dict, mr1_weight: float) -> dict:
    p = {c: (1.0 - mr1_weight) * left[c] + mr1_weight * right[c] for c in CATEGORIES}
    return normalize(p)


def ev_from_distribution(probs: dict, price: float) -> float:
    return (probs["win"] + 0.5 * probs["half_win"]) * (price - 1.0) \
        - probs["loss"] - 0.5 * probs["half_loss"]


def score_sample(item: dict, model: str, weight: float) -> dict:
    market, line = item["market"], item["line"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    m3_probs = item["m3_probabilities"][model]
    mr1_probs = item["mr1_probabilities"]
    quote_prices = item["prices"]
    candidates = []
    for idx, side in enumerate(sides):
        mp = m3_probs[side]
        rp = side_distribution(mr1_probs, item["mr1_side"], side)
        probs = blend(mp, rp, weight)
        candidates.append((ev_from_distribution(probs, quote_prices[idx]), idx, side, probs))
    _, idx, side, probs = max(candidates, key=lambda x: (x[0], -x[1]))
    legs, actual = legs_result(market, side, line, item["home_goals"], item["away_goals"])
    return {"pnl": payout(legs, quote_prices[idx]), "category": actual,
            "probabilities": probs, "event_utc": item["event_utc"],
            "kickoff_utc": item["kickoff_utc"], "side": side}


def log_loss(rows: list[dict]) -> float:
    return -sum(math.log(max(r["probabilities"][r["category"]], 1e-15)) for r in rows) / len(rows)


def brier(rows: list[dict]) -> float:
    return sum(sum((r["probabilities"][c] - (1.0 if c == r["category"] else 0.0)) ** 2
                   for c in CATEGORIES) for r in rows) / len(rows)


def summarize(rows: list[dict], seed: int) -> dict:
    n = len(rows)
    net = math.fsum(r["pnl"] for r in rows)
    counts = Counter(r["category"] for r in rows)
    event_net = defaultdict(float)
    for row in rows:
        event_net[row["event_utc"]] += row["pnl"]
    equity = peak = max_dd = 0.0
    for event in sorted(event_net):
        equity += event_net[event]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    if n:
        values = np.asarray([r["pnl"] for r in rows], dtype=np.float64)
        rng = np.random.default_rng(seed)
        reps, chunk = 2000, 100
        bootstrap = np.concatenate([
            values[rng.integers(0, n, size=(min(chunk, reps - start), n))].mean(axis=1)
            for start in range(0, reps, chunk)
        ])
    else:
        bootstrap = np.asarray([])
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "net_units": round(net, 6),
        "roi_pct": round(100.0 * net / n, 6) if n else None,
        "settlement_counts": {c: counts[c] for c in ("win", "half_win", "push", "half_loss", "loss")},
        "max_drawdown_units_by_quote_event_time": round(max_dd, 6),
        "settlement_log_loss": round(log_loss(rows), 8) if rows else None,
        "settlement_brier": round(brier(rows), 8) if rows else None,
        "roi_bootstrap_95pct": {"lower_95_pct": round(100 * float(np.quantile(bootstrap, .025)), 6),
                                 "upper_95_pct": round(100 * float(np.quantile(bootstrap, .975)), 6),
                                 "method": "fixture percentile bootstrap, descriptive only",
                                 "repetitions": 2000} if bootstrap.size else None,
    }


def load_cohort(m3_path: Path, mr1_path: Path) -> tuple[dict, dict]:
    m3_raw, m3 = read_m3(m3_path)
    mr1_raw, mr1 = read_mr1(mr1_path)
    common_ids = {fid for fid in m3 if all((fid, market) in mr1 for market in MARKETS)}
    if not common_ids:
        raise ValueError("empty M3/MR1 common cohort")
    per_market = {m: [] for m in MARKETS}
    audit = Counter()
    for fid in sorted(common_ids):
        f = m3[fid]
        train_end = datetime.fromisoformat(f["train_end_utc"].replace("Z", "+00:00"))
        asof = datetime.fromisoformat(f["prediction_asof_utc"].replace("Z", "+00:00"))
        kickoff = datetime.fromisoformat(f["kickoff_utc"].replace("Z", "+00:00"))
        if not train_end < asof < kickoff:
            raise ValueError("M3 forecast chronology failure")
        for market in MARKETS:
            mr = mr1[(fid, market)]
            q = f["quotes"][market]
            if q.get("source") != "Crown":
                raise ValueError("common model cohort is not Crown-only")
            line = float(q["line"])
            if abs(float(mr["line"]) - line) > 1e-8:
                raise ValueError("M3/MR1 contract line mismatch")
            if mr["event_utc"] != q["event_utc"]:
                raise ValueError("M3/MR1 quote event mismatch")
            quote_sides = ("home", "away") if market == "AH" else ("over", "under")
            if mr["side"] not in quote_sides or abs(
                    float(mr["price"]) - float(q["prices"][quote_sides.index(mr["side"])])
            ) > 1e-8:
                raise ValueError("MR1 selected price differs from shared Crown quote")
            event = datetime.fromisoformat(q["event_utc"].replace("Z", "+00:00"))
            receipt = datetime.fromisoformat(q["receipt_utc"].replace("Z", "+00:00"))
            mr_receipt = datetime.fromisoformat(mr["receipt_utc"].replace("Z", "+00:00"))
            mr_kickoff = datetime.fromisoformat(mr["kickoff_utc"].replace("Z", "+00:00"))
            if mr_kickoff != kickoff or mr_receipt < event:
                raise ValueError("MR1 receipt/kickoff chronology mismatch")
            if not asof <= event < kickoff or receipt < event:
                raise ValueError("invalid Crown event/receipt chronology")
            grids = f["model_score_grids"]
            sides = quote_sides
            m3_distributions = {}
            for model in MODELS:
                grid = grids[model]
                m3_distributions[model] = {
                    side: normalize(grid_distribution(grid, market, side, line)) for side in sides}
            mr_probs = mr1_distribution(mr)
            h, a = int(f["actual_home_goals"]), int(f["actual_away_goals"])
            per_market[market].append({
                "match_id": fid, "market": market, "line": line,
                "prices": [float(x) for x in q["prices"]], "event_utc": q["event_utc"],
                "receipt_utc": q["receipt_utc"], "kickoff_utc": f["kickoff_utc"],
                "year": str(kickoff.year), "home_goals": h, "away_goals": a,
                "m3_probabilities": m3_distributions, "mr1_probabilities": mr_probs,
                "mr1_side": mr["side"], "mr1_pnl": float(mr["pnl"]),
                "mr1_category": mr["category"],
            })
            audit["m3_post_kickoff_receipts"] += int(receipt >= kickoff)
            audit["mr1_post_kickoff_receipts"] += int(mr_receipt >= kickoff)
            audit["pre_kickoff_event_quotes"] += int(event < kickoff)
    return {"AH": per_market["AH"], "OU": per_market["OU"]}, {
        "unique_common_fixtures": len(common_ids), "audit": dict(audit),
        "m3_sha256": hashlib.sha256(m3_raw).hexdigest(),
        "mr1_trace_sha256": hashlib.sha256(mr1_raw).hexdigest(),
    }


def fit_weight(rows: list[dict], model: str) -> tuple[float, float]:
    if not rows:
        raise ValueError("empty training partition")
    candidates = []
    for i in range(101):
        weight = i / 100.0
        scored = [score_sample(row, model, weight) for row in rows]
        candidates.append((log_loss(scored), weight))
    return min(candidates, key=lambda x: (x[0], x[1]))[1], min(candidates)[0]


def run(m3_path: Path, mr1_path: Path, output: Path) -> dict:
    cohort, meta = load_cohort(m3_path, mr1_path)
    results = {}
    for market in MARKETS:
        rows = cohort[market]
        train = [r for r in rows if r["year"] == "2025"]
        test = [r for r in rows if r["year"] == "2026"]
        if not train or not test:
            raise ValueError("required 2025/2026 temporal split missing")
        model_results = {}
        candidates = ("mr1_v6", *MODELS, *(f"equal_mr1_{m3}" for m3 in MODELS),
                      *(f"train_logloss_mr1_{m3}" for m3 in MODELS))
        for name in candidates:
            if name == "mr1_v6":
                alpha = 1.0
                train_rows = [{"pnl": r["mr1_pnl"], "category": r["mr1_category"],
                               "probabilities": r["mr1_probabilities"], "event_utc": r["event_utc"],
                               "kickoff_utc": r["kickoff_utc"]} for r in train]
                test_rows = [{"pnl": r["mr1_pnl"], "category": r["mr1_category"],
                              "probabilities": r["mr1_probabilities"], "event_utc": r["event_utc"],
                              "kickoff_utc": r["kickoff_utc"]} for r in test]
            elif name in MODELS:
                alpha = 0.0
                train_rows = [score_sample(r, name, alpha) for r in train]
                test_rows = [score_sample(r, name, alpha) for r in test]
            else:
                m3_model = next(model for model in MODELS if name.endswith("_" + model))
                if name.startswith("equal_mr1_"):
                    alpha = 0.5
                    train_ll = None
                else:
                    alpha, train_ll = fit_weight(train, m3_model)
                train_rows = [score_sample(r, m3_model, alpha) for r in train]
                test_rows = [score_sample(r, m3_model, alpha) for r in test]
            entry = {"mr1_probability_weight": round(alpha, 4),
                     "training_2025": summarize(train_rows, 20261106),
                     "holdout_2026": summarize(test_rows, 20261107)}
            if name.startswith("train_logloss_"):
                entry["weight_selection"] = {"method": "grid search 0.00..1.00 by 0.01 minimizing 2025 settlement-category log loss",
                                              "training_log_loss": round(float(train_ll), 8)}
            model_results[name] = entry
        results[market] = {
            "train_fixture_markets": len(train), "train_year_utc": "2025",
            "holdout_fixture_markets": len(test), "holdout_year_utc": "2026",
            "train_test_fixture_ids_disjoint": not bool({r["match_id"] for r in train} & {r["match_id"] for r in test}),
            "holdout_receipt_timing": "all provider receipts post-kickoff; event-time retrospective only",
            "models": model_results,
        }
    report = {
        "protocol": "M5_MR1_M3_2025_TRAIN_2026_HOLDOUT_PROBABILITY_BLEND_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha(Path(__file__)),
        "input_sha256": {"m3_forecasts": meta["m3_sha256"], "mr1_same_cohort_trace": meta["mr1_trace_sha256"]},
        "common_fixture_count": meta["unique_common_fixtures"],
        "audit": meta["audit"], "markets": results,
        "method": "On the identical Crown AH/OU quote and outcome cohort, derive each M3 model's five-state contract distribution from its pre-kickoff score grid; convert the frozen MR1 V6 selected-side distribution to the same side and line; form convex mixtures, select the higher expected-return side at the shared two prices, and settle one unit. Equal blend uses a fixed 0.5 MR1 weight. A separate MR1 weight is selected only on 2025 by settlement-category log loss (0.01 grid), then frozen for 2026. No EV floor or sample filter is used.",
        "limitations": [
            "This is a retrospective event-time replay: Crown response receipts were post-kickoff even though quote events preceded kickoff.",
            "2026 has been viewed in prior M5 research; the temporal split prevents direct training leakage but this is not a newly untouched final holdout.",
            "A blend's training weight optimizes categorical probability log loss, not ROI; holdout ROI is reported without selection or thresholding.",
            "M1 is not included because its saved prediction coverage does not overlap this full cohort; M4 remains a Pass rule, not a predictor.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--m3-private", type=Path, required=True)
    p.add_argument("--mr1-trace-private", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = run(a.m3_private, a.mr1_trace_private, a.output)
    print(json.dumps({m: {k: {"alpha": v["mr1_probability_weight"],
        "test_roi_pct": v["holdout_2026"]["roi_pct"],
        "test_brier": v["holdout_2026"]["settlement_brier"]} for k, v in x["models"].items()}
        for m, x in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
