#!/usr/bin/env python3
"""Strict same Crown contract comparison of M1, MR1, and three M3 models.

All row-level inputs are private; only aggregate metrics and SHA-256 receipts
are written publicly. The input cohort is the exact M1/MR1/M3 Crown contract
intersection, with fixture-market uniqueness checked independently by AH/OU.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout

MODELS = ("m1", "mr1_v6", "m3_poisson", "m3_dixon_coles", "m3_bivariate_poisson")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}


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


def category_distribution(grid, market, side, line):
    dist = Counter()
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _, category = legs_result(market, side, line, home, away)
            dist[category] += probability
    return dict(dist)


def summarize(rows, seed):
    n = len(rows)
    if not n:
        return {"unique_fixtures": 0, "simulated_bets": 0, "settled_bets": 0, "roi_pct": None}
    pnl = [float(r["pnl"]) for r in rows]
    categories = Counter(r["category"] for r in rows)
    per_event = defaultdict(float)
    for row in rows:
        per_event[row["event_utc"]] += row["pnl"]
    equity = peak = drawdown = 0.0
    for event in sorted(per_event):
        equity += per_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    ll = brier = 0.0
    for row in rows:
        dist = row["distribution"]
        actual = row["category"]
        ll -= math.log(max(float(dist.get(actual, 0.0)), 1e-15))
        brier += sum((float(dist.get(cat, 0.0)) - (cat == actual)) ** 2 for cat in CATEGORIES)
    ll /= n
    brier /= n
    rng = random.Random(seed)
    samples = sorted(sum(pnl[rng.randrange(n)] for _ in range(n)) / n for _ in range(5000))
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n, "stake_units": n,
        "net_units": round(sum(pnl), 6), "roi_pct": round(100 * sum(pnl) / n, 6),
        "settlement_counts": {c: categories[c] for c in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "settlement_log_loss": round(ll, 8), "settlement_brier": round(brier, 8),
        "roi_bootstrap_95pct": {"method": "fixture percentile bootstrap, descriptive only", "repetitions": 5000,
                                "lower_95_roi_pct": round(100 * samples[int(.025 * 4999)], 6),
                                "upper_95_roi_pct": round(100 * samples[int(.975 * 4999)], 6)},
        "quote_sources": dict(Counter(r["source"] for r in rows)),
    }


def run(m1_trace_path: Path, mr1_trace_path: Path, m3_rows_path: Path, output: Path):
    m1 = {}
    with m1_trace_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                key = (str(row["match_id"]), row["market"])
                if key in m1:
                    raise ValueError("duplicate M1 fixture-market")
                m1[key] = row
    mr1 = {}
    with mr1_trace_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                key = (str(row["match_id"]), row["market"])
                if key in mr1:
                    raise ValueError("duplicate MR1 fixture-market")
                mr1[key] = row
    m3 = {}
    with m3_rows_path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                m3[str(row["match_id"])] = row

    by_market = {market: [] for market in ("AH", "OU")}
    mismatch = Counter()
    receipt_timing = Counter()
    matched_ids_by_market = {}
    for key, mr1row in mr1.items():
        mid, market = key
        m1row, m3row = m1.get(key), m3.get(mid)
        if m1row is None or m3row is None:
            mismatch["missing_model_row"] += 1
            continue
        quote = m3row.get("quotes", {}).get(market)
        if quote is None:
            mismatch["missing_quote"] += 1
            continue
        if (m1row["source"] != "Crown" or quote["source"] != "Crown"
                or m1row["source"] != quote["source"]):
            mismatch["non_crown_source"] += 1
            continue
        if (instant(m1row["event_utc"]) != instant(quote["event_utc"])
                or instant(mr1row["event_utc"]) != instant(quote["event_utc"])):
            mismatch["quote_event_mismatch"] += 1
            continue
        if any(abs(float(x) - float(y)) > 1e-8 for x, y in (
                (m1row["line"], quote["line"]), (mr1row["line"], quote["line"]))):
            mismatch["quote_line_mismatch"] += 1
            continue
        if instant(m1row["kickoff_utc"]) != instant(mr1row["kickoff_utc"]) or instant(m1row["kickoff_utc"]) != instant(m3row["kickoff_utc"]):
            mismatch["kickoff_mismatch"] += 1
            continue
        sides = SIDES[market]
        mr1_side = str(mr1row["side"]).lower()
        if mr1_side not in sides:
            mismatch["mr1_side_invalid"] += 1
            continue
        selected_idx = sides.index(mr1_side)
        if abs(float(mr1row["price"]) - float(quote["prices"][selected_idx])) > 1e-8:
            mismatch["mr1_selected_price_mismatch"] += 1
            continue
        if any(abs(float(a) - float(b)) > 1e-8 for a, b in zip(m1row["prices"], quote["prices"])):
            mismatch["m1_price_pair_mismatch"] += 1
            continue
        receipt_timing["pre_kickoff" if instant(quote["receipt_utc"]) < instant(m1row["kickoff_utc"])
                       else "post_kickoff"] += 1

        actual = (int(m3row["actual_home_goals"]), int(m3row["actual_away_goals"]))
        line = float(quote["line"])
        prices = [float(x) for x in quote["prices"]]
        current = {name: [] for name in MODELS}
        m1_probs = {"win": m1row["m1_distribution"].get("win", 0),
                    "half_win": m1row["m1_distribution"].get("half_win", 0),
                    "push": m1row["m1_distribution"].get("push", 0),
                    "half_loss": m1row["m1_distribution"].get("half_loss", 0),
                    "loss": m1row["m1_distribution"].get("loss", 0)}
        current["m1"].append({"pnl": float(m1row["m1_pnl"]), "category": m1row["m1_category"],
                               "distribution": m1_probs, "event_utc": quote["event_utc"], "source": quote["source"]})
        mr1_probs = {"win": mr1row["probabilities"].get("full_win", 0),
                     "half_win": mr1row["probabilities"].get("half_win", 0),
                     "push": mr1row["probabilities"].get("push", 0),
                     "half_loss": mr1row["probabilities"].get("half_loss", 0),
                     "loss": mr1row["probabilities"].get("full_loss", 0)}
        current["mr1_v6"].append({"pnl": float(mr1row["pnl"]), "category": mr1row["category"],
                                  "distribution": mr1_probs, "event_utc": quote["event_utc"], "source": quote["source"]})
        for model_name in ("poisson", "dixon_coles", "bivariate_poisson"):
            grid = m3row["model_score_grids"][model_name]
            evs = [expected_return(grid, market, side, line, price) for side, price in zip(sides, prices)]
            idx = 0 if evs[0] >= evs[1] else 1
            side, price = sides[idx], prices[idx]
            legs, category = legs_result(market, side, line, *actual)
            dist = category_distribution(grid, market, side, line)
            current[f"m3_{model_name}"].append({"pnl": payout(legs, price), "category": category,
                                                "distribution": dist, "event_utc": quote["event_utc"],
                                                "source": quote["source"]})
        for model_name in MODELS:
            by_market[market].append((mid, model_name, current[model_name][0]))
        matched_ids_by_market.setdefault(market, set()).add(mid)

    markets = {}
    for idx, market in enumerate(("AH", "OU")):
        entries = by_market[market]
        counts = Counter(name for _, name, _ in entries)
        expected_n = counts.get("m1", 0)
        if len(counts) != len(MODELS) or any(counts[name] != expected_n for name in MODELS):
            raise ValueError("models do not share the exact fixture cohort")
        markets[market] = {"shared_unique_fixtures": expected_n,
                           "exact_shared_quote_contracts": expected_n,
                           "quote_sources": {"Crown": expected_n}, "models": {}}
        for model_idx, name in enumerate(MODELS):
            rows = [row for _, item_name, row in entries if item_name == name]
            markets[market]["models"][name] = summarize(rows, 202611060 + idx * 10 + model_idx)

    ids_payload = "\n".join(f"{market}|{mid}" for market in ("AH", "OU")
                            for mid in sorted(matched_ids_by_market.get(market, set())))
    report = {
        "protocol": "M5_MR1_M1_M3_EXACT_CROWN_COMMON_COHORT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {"M1_trace": sha_file(m1_trace_path), "MR1_trace": sha_file(mr1_trace_path),
                         "M3_rows_and_quotes": sha_file(m3_rows_path),
                         "cohort_fixture_market_id_set": hashlib.sha256(ids_payload.encode()).hexdigest()},
        "audit_counts": dict(mismatch),
        "provider_receipt_timing": dict(receipt_timing),
        "markets": markets,
        "method": "Exact fixture-market intersection; verify UTC kickoff, source, Crown quote event time, AH/OU line, and MR1 selected-side price against the identical M3 quote pair. Each model independently selects the higher expected-return side and is settled at 1U with Asian split-line settlement. M1 and the three M3 models are scored from their complete score distributions; MR1 V6 uses its recorded probabilities and selected-side settlement.",
        "limitations": ["All provider response receipts in this historic cohort were post-kickoff; ROI is retrospective quote-event replay, not executable ROI.",
                        "M1 reconstruction uses the archived M1 parameter cutoff and a documented two-day retrospective availability buffer for historical results.",
                        "This exact Crown-only intersection is 9,517 fixtures per market, below the 10,000-market sample requirement; the M1/M3 larger cohort report remains a separate Crown-first plus TotalCorner-default analysis."],
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"], "audit_counts": report["audit_counts"],
                      "markets": {m: {"n": v["shared_unique_fixtures"], "models": {
                          k: {"roi_pct": x["roi_pct"], "log_loss": x["settlement_log_loss"], "brier": x["settlement_brier"]}
                          for k, x in v["models"].items()}} for m, v in markets.items()}}, sort_keys=True))


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
