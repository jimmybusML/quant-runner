#!/usr/bin/env python3
"""Compare MR1 V6 and the three M3 grids on the exact same Crown cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from research.m5.m3_grid_crown_replay import (
    expected_return, grid_distribution, legs_result, payout,
)

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")
PROB_KEY = {"win": "full_win", "half_win": "half_win", "push": "push", "half_loss": "half_loss", "loss": "full_loss"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(rows):
    n = len(rows)
    pnl = math.fsum(float(x["pnl"]) for x in rows)
    counts = Counter(x["category"] for x in rows)
    ll = brier = 0.0
    for row in rows:
        probs = row["probabilities"]
        ll -= math.log(max(float(probs.get(row["category"], 0.0)), 1e-15))
        brier += math.fsum((float(probs.get(c, 0.0)) - (1.0 if c == row["category"] else 0.0)) ** 2 for c in CATEGORIES)
    by_event = defaultdict(float)
    for row in rows:
        by_event[row["event_utc"]] += float(row["pnl"])
    equity = peak = max_dd = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    by_year = {}
    for year in sorted({x["year"] for x in rows}):
        group = [x for x in rows if x["year"] == year]
        net = math.fsum(float(x["pnl"]) for x in group)
        by_year[year] = {"bets": len(group), "net_units": round(net, 6), "roi_pct": round(100 * net / len(group), 6)}
    return {
        "unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "net_units": round(pnl, 6), "roi_pct": round(100 * pnl / n, 6) if n else None,
        "settlement_counts": {c: counts[c] for c in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(max_dd, 6),
        "settlement_log_loss": round(ll / n, 8) if n else None,
        "settlement_brier": round(brier / n, 8) if n else None,
        "quote_sources": dict(Counter(x["source"] for x in rows)),
        "response_receipts": dict(Counter("pre_kickoff" if x["receipt"] < x["kickoff"] else "post_kickoff" for x in rows)),
        "by_utc_kickoff_year": by_year,
    }


def run(m3_path: Path, trace_path: Path, output_path: Path):
    forecasts = {}
    for line in m3_path.open(encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            fid = str(row["match_id"])
            if fid in forecasts:
                raise ValueError("duplicate M3 fixture identity")
            forecasts[fid] = row
    mr1 = {}
    for line in trace_path.open(encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["match_id"]), row["market"])
        if key in mr1:
            raise ValueError("duplicate MR1 fixture-market")
        mr1[key] = row

    common_ids = {fid for fid in forecasts if all((fid, market) in mr1 for market in MARKETS)}
    if len(common_ids) != 9517:
        raise ValueError(f"unexpected paired cohort size: {len(common_ids)}")
    results = {market: {name: [] for name in (*MODELS, "mr1_v6")} for market in MARKETS}
    for fid in sorted(common_ids):
        forecast = forecasts[fid]
        home, away = int(forecast["actual_home_goals"]), int(forecast["actual_away_goals"])
        for market in MARKETS:
            quote = forecast["quotes"][market]
            if quote.get("source") != "Crown":
                raise ValueError("paired cohort is not Crown-only")
            line = float(quote["line"])
            sides = ("home", "away") if market == "AH" else ("over", "under")
            for model in MODELS:
                grid = forecast["model_score_grids"][model]
                expected = [expected_return(grid, market, side, line, price)
                            for side, price in zip(sides, quote["prices"])]
                idx = 0 if expected[0] >= expected[1] else 1
                side, price = sides[idx], float(quote["prices"][idx])
                legs, category = legs_result(market, side, line, home, away)
                probs = grid_distribution(grid, market, side, line)
                results[market][model].append({
                    "pnl": payout(legs, price), "category": category, "probabilities": probs,
                    "event_utc": quote["event_utc"], "receipt": quote["receipt_utc"],
                    "kickoff": forecast["kickoff_utc"], "year": str(forecast["kickoff_utc"])[:4],
                    "source": quote["source"], "side": side,
                })
            baseline = mr1[(fid, market)]
            if abs(float(baseline["line"]) - line) > 1e-8:
                raise ValueError("MR1 and M3 contract line mismatch")
            # The V6 output trace stores the selected side and full five-state distribution.
            results[market]["mr1_v6"].append({
                "pnl": float(baseline["pnl"]), "category": baseline["category"],
                "probabilities": {c: float(baseline["probabilities"][PROB_KEY[c]]) for c in CATEGORIES},
                "event_utc": baseline["event_utc"],
                "receipt": baseline["receipt_utc"], "kickoff": baseline["kickoff_utc"],
                "year": str(baseline["year"]), "source": "Crown", "side": baseline["side"],
            })

    report_markets = {}
    for market in MARKETS:
        rows_by_model = results[market]
        report_markets[market] = {
            "unique_common_fixtures": len(common_ids),
            "models": {name: summarize(rows) for name, rows in rows_by_model.items()},
            "side_agreement_pct_vs_mr1": {
                model: round(100 * sum(a["side"] == b["side"] for a, b in zip(rows_by_model[model], rows_by_model["mr1_v6"])) / len(common_ids), 6)
                for model in MODELS
            },
        }
    report = {
        "protocol": "M5_MR1_V6_VS_M3_THREE_MODELS_SAME_CROWN_COHORT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "M3_private_forecasts_sha256": sha(m3_path), "MR1_private_trace_sha256": sha(trace_path),
        "unique_common_fixtures": len(common_ids), "markets": report_markets,
        "method": "M3 Poisson, Dixon-Coles, and Bivariate Poisson score grids and actual MR1 V6 selected outputs are scored on identical Crown AH/OU lines, prices, and verified outcomes for the exact common fixture IDs; one 1U per fixture-market, same Asian settlement.",
        "limitations": [
            "All Crown provider response receipts were post-kickoff; ROI is retrospective event-time simulation, not executable historical ROI.",
            "Cohort requires M3 OOS prediction plus Crown AH/OU and Crown 1X2 inputs, so it is smaller than the full M3 source-union rerun.",
            "M1 has no archived predictions on most of this cohort; M4 is a Pass rule, not a prediction model, and neither is presented as a model on this paired cohort.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3-private", type=Path, required=True)
    parser.add_argument("--mr1-trace-private", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.m3_private, args.mr1_trace_private, args.output)
    print(json.dumps({m: {name: summary["roi_pct"] for name, summary in data["models"].items()}
                      for m, data in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
