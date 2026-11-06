#!/usr/bin/env python3
"""Publish source-separated aggregate M5 ROI evidence from replay summaries.

The input summaries are kept private when they contain provider-level metadata.
This writer selects aggregate fields only and never exports fixture identities,
scores, prices, API responses, or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCENARIOS = (
    ("crown_only_baseline", "Crown_only", "baseline"),
    ("crown_only_recency", "Crown_only", "recency"),
    ("totalcorner_only_baseline", "TotalCorner_only", "baseline"),
    ("totalcorner_only_recency", "TotalCorner_only", "recency"),
    ("crown_first_union_baseline", "Crown_first_union", "baseline"),
    ("crown_first_union_recency", "Crown_first_union", "recency"),
)
MARKETS = ("AH", "OU")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def public_market_summary(report: dict, market: str) -> dict:
    row = report["markets"][market]
    return {
        "unique_fixture_markets": row["unique_fixtures"],
        "simulated_bets": row["simulated_bets"],
        "settled_bets": row["settled_bets"],
        "pending_bets": row["pending_bets"],
        "settlement_counts": {name: row["settlement_counts"][name]
                              for name in ("win", "half_win", "push", "half_loss", "loss")},
        "net_units": row["net_units"],
        "roi_pct": row["roi_pct"],
        "max_drawdown_units": row["max_drawdown_units_by_source_event_time"],
        "settlement_log_loss": row["settlement_log_loss"],
        "settlement_brier": row["settlement_brier"],
        "roi_bootstrap_95pct": row["roi_bootstrap_95pct"],
        "by_utc_kickoff_year": {
            year: {key: values.get(key) for key in ("fixtures", "net_units", "roi_pct")}
            for year, values in sorted(row["by_utc_kickoff_year"].items())
        },
        "source_fixture_markets": row["source_fixture_markets"],
        "quote_receipt_timing": row["quote_receipt_timing"],
        "utc_coverage": row["utc_coverage"],
    }


def build_report(inputs: dict[str, Path], generated_utc: str) -> dict:
    scenarios = {}
    for name, source_contract, model_variant in SCENARIOS:
        path = inputs[name]
        raw = path.read_bytes()
        source = json.loads(raw)
        policy = source.get("side_selection_policy")
        if policy is not None and policy != "higher_ev":
            raise ValueError(f"unexpected side-selection policy in {name}")
        input_hashes = source.get("input_hashes", {})
        scenarios[name] = {
            "model_variant": model_variant,
            "source_contract": source_contract,
            "generated_utc": source["generated_utc"],
            "input_report_sha256": sha(raw),
            "candidate_manifest_sha256": input_hashes.get("candidate_manifest_sha256", source.get("candidate_manifest_sha256")),
            "forecast_sha256": input_hashes.get("forecast_sha256", source.get("forecast_sha256")),
            "quote_response_hash_set_sha256": input_hashes.get("quote_response_hash_set_sha256", source.get("quote_response_hash_set_sha256")),
            "markets": {market: public_market_summary(source, market) for market in MARKETS},
        }
    return {
        "protocol": "M5_SOURCE_SEPARATED_PERFORMANCE_COMPARISON_V1",
        "generated_utc": generated_utc,
        "scenarios": scenarios,
        "roi_definition": "net_units / simulated_bets * 100; every simulated bet stakes 1U",
        "method": "AH and OU are independent. Each source-only replay uses that source alone; source-union replays select Crown first and TotalCorner default only for missing Crown fixture-markets, with no duplicate fixture-market. Each scenario selects the higher expected-return side from the frozen M5 goal model, with no additional threshold or filter.",
        "timing_limitations": "All included historical API response receipts were post-kickoff. Pre-kickoff quote event timestamps support retrospective event-time replay only and do not prove contemporaneous receipt or executable prices. The report separates Crown and TotalCorner and must not be described as live or formal betting performance.",
        "production_or_telegram_changes": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for name, _, _ in SCENARIOS:
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument("--generated-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = {name: getattr(args, name) for name, _, _ in SCENARIOS}
    report = build_report(inputs, args.generated_utc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "scenario_count": len(report["scenarios"]),
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
