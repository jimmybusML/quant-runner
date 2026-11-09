#!/usr/bin/env python3
"""Publish descriptive loss-driver splits for the frozen M5 Crown replay.

This is an aggregate-only diagnostic. It does not fit a model, select a
strategy, filter fixtures, or create a trading rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"unique_fixture_markets": 0, "simulated_bets": 0,
                "settled_bets": 0, "stake_units": 0, "net_units": 0,
                "roi_pct": None, "settlement_counts": {c: 0 for c in CATEGORIES},
                "settlement_log_loss": None, "settlement_brier": None,
                "max_drawdown_units_by_quote_event_time": None}
    pnl = [float(row["pnl_units"]) for row in rows]
    net = math.fsum(pnl)
    counts = Counter(row["settlement"] for row in rows)
    log_loss = brier = 0.0
    event_pnl = defaultdict(float)
    for row in rows:
        dist, actual = row["settlement_distribution"], row["settlement"]
        log_loss -= math.log(max(float(dist.get(actual, 0)), 1e-15))
        brier += math.fsum((float(dist.get(c, 0)) - (c == actual)) ** 2 for c in CATEGORIES)
        event_pnl[row["quote_event_utc"]] += float(row["pnl_units"])
    equity = peak = drawdown = 0.0
    for event in sorted(event_pnl):
        equity += event_pnl[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "net_units": round(net, 6),
        "roi_pct": round(100 * net / n, 6),
        "settlement_counts": {c: counts[c] for c in CATEGORIES},
        "settlement_log_loss": round(log_loss / n, 8),
        "settlement_brier": round(brier / n, 8),
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
    }


def grouped(rows: list[dict], key_fn) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)
    return {str(key): summary(value) for key, value in sorted(groups.items(), key=lambda x: str(x[0]))}


def lead_bucket(hours: float) -> str:
    # Descriptive bins only. They do not filter or alter the scored cohort.
    if hours <= 1:
        return "<=1h"
    if hours <= 6:
        return "1-6h"
    if hours <= 24:
        return "6-24h"
    return ">24h"


def run(private_rows_path: Path, source_report_path: Path, output_path: Path) -> dict:
    source = json.loads(source_report_path.read_text())
    rows = [json.loads(line) for line in private_rows_path.read_text().splitlines() if line.strip()]
    seen = set()
    by_market = {market: [] for market in ("AH", "OU")}
    for row in rows:
        market = row["market"]
        if market not in by_market:
            raise ValueError("unexpected market")
        key = (str(row["fixture_id"]), market)
        if key in seen:
            raise ValueError("duplicate fixture-market")
        seen.add(key)
        kickoff = datetime.fromisoformat(row["kickoff_utc"].replace("Z", "+00:00"))
        asof = datetime.fromisoformat(row["prediction_asof_utc"].replace("Z", "+00:00"))
        train_end = datetime.fromisoformat(row["train_end_utc"].replace("Z", "+00:00"))
        event = datetime.fromisoformat(row["quote_event_utc"].replace("Z", "+00:00"))
        received = datetime.fromisoformat(row["quote_received_utc"].replace("Z", "+00:00"))
        if not train_end < asof <= event < kickoff or received < event:
            raise ValueError("published-row chronology mismatch")
        if row.get("quote_received_pre_kickoff") is not False:
            raise ValueError("expected explicitly retrospective receipt")
        by_market[market].append(row)

    markets = {}
    for market, market_rows in by_market.items():
        published = source["markets"][market]
        actual = summary(market_rows)
        for key in ("unique_fixture_markets", "simulated_bets", "settled_bets",
                    "stake_units", "net_units", "roi_pct", "settlement_counts",
                    "settlement_log_loss", "settlement_brier"):
            expected = published[key]
            if isinstance(expected, float):
                if abs(actual[key] - expected) > 1e-6:
                    raise ValueError(f"source aggregate mismatch: {market} {key}")
            elif actual[key] != expected:
                raise ValueError(f"source aggregate mismatch: {market} {key}")
        def lead(row):
            k = datetime.fromisoformat(row["kickoff_utc"].replace("Z", "+00:00"))
            q = datetime.fromisoformat(row["quote_event_utc"].replace("Z", "+00:00"))
            return lead_bucket((k - q).total_seconds() / 3600)
        def hour(row):
            return row["kickoff_utc"][11:13] + "Z"
        markets[market] = {
            "overall": actual,
            "by_quote_kind": grouped(market_rows, lambda r: r["quote_kind"]),
            "by_utc_kickoff_hour": grouped(market_rows, hour),
            "by_quote_lead_to_kickoff": grouped(market_rows, lead),
            "by_utc_kickoff_year": grouped(market_rows, lambda r: r["kickoff_utc"][:4]),
            "by_league": grouped(market_rows, lambda r: r["league"]),
        }
    report = {
        "protocol": "M5_CROWN_SUMMARY_LOSS_DRIVER_DIAGNOSTIC_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha(Path(__file__)),
        "source_summary_report_sha256": sha(source_report_path),
        "private_replay_rows_sha256": sha(private_rows_path),
        "source_forecast_sha256": source["forecast_sha256"],
        "source_candidate_manifest_sha256": source["candidate_manifest_sha256"],
        "source_response_hash_set_sha256": source["response_hash_set_sha256"],
        "markets": markets,
        "method": "Descriptive disjoint splits of the already scored Crown summary cohort. No rows are removed and no split defines a strategy or trading gate.",
        "limitations": [
            "Historical Crown responses were received after kickoff; these are event-time retrospective outcomes, not executable returns.",
            "Split results are exploratory and not corrected for multiple comparisons; no subgroup is selected as a trading rule.",
            "This diagnostic covers the existing M5 score-grid forecasts, not M1, MR1, M3, or M4 refits.",
            "All market-specific rows reconcile to the source report; fixture-level IDs, prices, scores, and probabilities are not published.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-rows", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.private_rows, args.source_report, args.output)
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "markets": {m: {"n": x["overall"]["unique_fixture_markets"],
                                      "roi_pct": x["overall"]["roi_pct"],
                                      "league_count": len(x["by_league"])}
                                  for m, x in report["markets"].items()},
                      "private_replay_rows_sha256": report["private_replay_rows_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
