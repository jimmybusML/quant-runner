#!/usr/bin/env python3
"""Describe M5 baseline results by UTC kickoff quarter and actual quote source.

All eligible rows are retained. This is a diagnostic partition only; it does
not create selection rules or alter model/side selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_line_conditional_settlement_calibration import (
    build_rows, settlement_distribution, settlement_expected_return,
)

MARKETS = ("AH", "OU")
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"unique_fixture_markets": 0, "simulated_bets": 0, "settled_bets": 0,
                "stake_units": 0, "net_units": 0.0, "roi_pct": None,
                "settlement_counts": {category: 0 for category in CATEGORIES}}
    pnl = [float(row["pnl"]) for row in rows]
    counts = Counter(row["category"] for row in rows)
    event_pnl = defaultdict(float)
    for row in rows:
        event_pnl[row["event_utc"]] += float(row["pnl"])
    equity = peak = drawdown = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    ll = math.fsum(-math.log(max(float(row["distribution"].get(row["category"], 0.0)), 1e-15))
                   for row in rows) / n
    brier = math.fsum(
        sum((float(row["distribution"].get(category, 0.0))
             - float(row["category"] == category)) ** 2 for category in CATEGORIES)
        for row in rows) / n
    return {"unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
            "stake_units": n, "net_units": round(math.fsum(pnl), 6),
            "roi_pct": round(100 * math.fsum(pnl) / n, 6),
            "settlement_counts": {category: counts[category] for category in CATEGORIES},
            "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
            "settlement_log_loss": round(ll, 8), "settlement_brier": round(brier, 8),
            "quote_sources": dict(sorted(Counter(row["source"] for row in rows).items())),
            "quote_receipt_timing": dict(sorted(Counter(row["receipt_timing"] for row in rows).items()))}


def build_diagnostic(samples: dict, hashes: dict, kickoff_by_id: dict[str, str]) -> dict:
    output = {}
    for market in MARKETS:
        all_rows = []
        partitions = defaultdict(list)
        seen = set()
        for year in sorted(samples):
            for row in samples[year][market]:
                key = (str(row["match_id"]), market)
                if key in seen:
                    raise ValueError("duplicate fixture-market in source union")
                seen.add(key)
                sides = SIDES[market]
                distributions = [settlement_distribution(row["grid"], market, side, row["line"])
                                 for side in sides]
                returns = [settlement_expected_return(dist, price)
                           for dist, price in zip(distributions, row["prices"])]
                idx = 0 if returns[0] >= returns[1] else 1
                side = sides[idx]
                _, category = legs_result(market, side, row["line"], *row["score"])
                legs, _ = legs_result(market, side, row["line"], *row["score"])
                kickoff_value = kickoff_by_id[str(row["match_id"])]
                kickoff = datetime.fromisoformat(str(kickoff_value).replace("Z", "+00:00"))
                quarter = (kickoff.month - 1) // 3 + 1
                scored = {"pnl": payout(legs, row["prices"][idx]), "category": category,
                          "distribution": distributions[idx], "event_utc": row["event_utc"],
                          "source": row["source"], "receipt_timing": row["receipt_timing"]}
                all_rows.append(scored)
                partitions[(str(year), f"Q{quarter}")].append(scored)
                partitions[(str(year), f"Q{quarter}", row["source"])].append(scored)
        report = {"all_years": summarize(all_rows), "by_utc_year_quarter": {},
                  "by_utc_year_quarter_and_source": {}}
        for key, rows in sorted(partitions.items()):
            if len(key) == 2:
                report["by_utc_year_quarter"][f"{key[0]}-{key[1]}"] = summarize(rows)
            else:
                report["by_utc_year_quarter_and_source"][f"{key[0]}-{key[1]}|{key[2]}"] = summarize(rows)
        output[market] = report
    runner_path = Path(__file__).resolve()
    return {"protocol": "M5_BASELINE_UTC_QUARTER_AND_SOURCE_DIAGNOSTIC_V1",
            "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "runner_sha256": hashlib.sha256(runner_path.read_bytes()).hexdigest(),
            "input_hashes": hashes, "markets": output,
            "method": "Re-score every eligible M5 score grid at the exact saved source-union line and prices; select the higher expected-return side, stake 1U, settle actual Asian contract. Partition only after scoring by UTC kickoff quarter and recorded source. No rows are dropped and no thresholds or gates are added.",
            "limitations": ["Historical source receipts were retrieved post-kickoff; ROI is retrospective event-time simulation.",
                            "Quarter/source partitions are descriptive and are not evidence to add production filters.",
                            "2026 has been repeatedly inspected and is not a fresh confirmatory holdout."],
            "fixture_level_data_published": False}


def run(private_dir: Path, output: Path, source_timezone="Asia/Shanghai"):
    samples, hashes, _ = build_rows(private_dir, source_timezone, None)
    manifest = json.loads((private_dir / "candidate-manifest.json").read_text(encoding="utf-8"))
    kickoff_by_id = {str(row["match_id"]): row["kickoff_utc"] for row in manifest["rows"]}
    report = build_diagnostic(samples, hashes, kickoff_by_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.private_dir, args.output, args.source_timezone)
    print(json.dumps({market: {"n": value["all_years"]["unique_fixture_markets"],
                              "roi_pct": value["all_years"]["roi_pct"],
                              "quarters": {key: row["roi_pct"] for key, row in value["by_utc_year_quarter"].items()}}
                     for market, value in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
