#!/usr/bin/env python3
"""Select a side-direction diagnostic per league on 2025 and test on 2026.

This research-only, all-fixture policy compares the predeclared higher-model-EV,
market favorite, and market underdog directions. Leagues with fewer than 20
2025 training fixtures fall back to higher-model-EV. The rule never filters
2026 fixtures and does not alter any production strategy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


POLICIES = {
    "higher_ev": "m5_source_union_league_year_diagnostic_20261106.json",
    "favorite": "m5_source_union_favorite_league_year_diagnostic_20261106.json",
    "underdog": "m5_source_union_underdog_league_year_diagnostic_20261106.json",
}
MIN_TRAIN_FIXTURES = 20


def read(path: Path):
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build(paths: dict[str, Path]):
    reports, hashes = {}, {}
    for policy, path in paths.items():
        reports[policy], hashes[policy] = read(path)
    markets = {}
    for market in ("AH", "OU"):
        base = reports["higher_ev"]["markets"][market]
        yearly = {
            policy: report["markets"][market]["descriptive_splits_no_filter_applied"][
                "by_league_and_utc_kickoff_year"]
            for policy, report in reports.items()
        }
        leagues = sorted({key.rsplit(" | ", 1)[0] for key in yearly["higher_ev"]
                          if key.endswith(" | 2026")})
        chosen, training = {}, {}
        for league in leagues:
            key = f"{league} | 2025"
            rows = {policy: groups.get(key) for policy, groups in yearly.items()}
            counts = {x["fixtures"] for x in rows.values() if x is not None}
            if len(counts) > 1:
                raise ValueError(f"different 2025 fixture counts across side policies: {league}")
            n = next(iter(counts), 0)
            if n >= MIN_TRAIN_FIXTURES:
                selected = max(("higher_ev", "favorite", "underdog"),
                               key=lambda p: rows[p]["roi_pct"] if rows[p] else float("-inf"))
            else:
                selected = "higher_ev"
            chosen[league] = selected
            training[league] = {"fixtures": n, "selected_policy": selected,
                                "training_roi_pct_by_policy": {
                                    p: (rows[p]["roi_pct"] if rows[p] else None)
                                    for p in ("higher_ev", "favorite", "underdog")}}

        total_n = 0
        total_net = 0.0
        category_totals = Counter()
        policy_counts = Counter()
        market_source = base["descriptive_splits_no_filter_applied"][
            "by_source_and_utc_kickoff_year"]
        train_n = base["by_utc_kickoff_year"].get("2025", {}).get("fixtures", 0)
        for league, policy in chosen.items():
            row = yearly[policy].get(f"{league} | 2026")
            if row is None:
                raise ValueError(f"missing 2026 result for {market}/{league}/{policy}")
            total_n += row["fixtures"]
            total_net += row["net_units"]
            policy_counts[policy] += row["fixtures"]
            for category, count in row["settlement_counts"].items():
                category_totals[category] += count
        source_counts = {
            source: row["fixtures"]
            for key, row in market_source.items()
            for source, year in [key.rsplit(" | ", 1)] if year == "2026"
        }
        primary_n = base["by_utc_kickoff_year"].get("2026", {}).get("fixtures", 0)
        if total_n != primary_n:
            raise ValueError(f"league aggregates do not cover unique 2026 sample: {total_n} != {primary_n}")
        markets[market] = {
            "training_year": 2025,
            "training_unique_fixtures": train_n,
            "holdout_year": 2026,
            "holdout_unique_fixtures": total_n,
            "simulated_bets": total_n,
            "settled_bets": total_n,
            "source_fixture_markets": source_counts,
            "settlement_counts": {k: category_totals[k] for k in
                                  ("win", "half_win", "push", "half_loss", "loss")},
            "net_units": round(total_net, 6),
            "roi_pct": round(100 * total_net / total_n, 6) if total_n else None,
            "base_policy_2026_roi_pct": base["by_utc_kickoff_year"]["2026"]["roi_pct"],
            "policy_fixture_counts": dict(policy_counts),
            "minimum_training_fixtures_for_direction_selection": MIN_TRAIN_FIXTURES,
            "leagues": training,
            "limitations": [
                "This is a retrospective source-event-time replay; selected historical API receipts were post-kickoff.",
                "League policy selection uses 2025 settlement ROI on small per-league cohorts and has substantial selection bias.",
                "2026 was held out from selection; results are not contemporaneously executable or production validated.",
                "No fixtures are filtered; each unique fixture contributes one 1U bet in the holdout.",
            ],
        }
    return {
        "protocol": "M5_LEAGUE_DIRECTION_2025_TRAIN_2026_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_report_sha256": hashes,
        "selection_rule": "For each market and league, select the highest 2025 ROI among higher model EV, market favorite, and market underdog if training n>=20; otherwise use higher model EV. Freeze for 2026. This is research-only and places one bet on every valid 2026 fixture.",
        "markets": markets,
        "no_production_changes": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).resolve().parent / "results")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {policy: args.results_dir / name for policy, name in POLICIES.items()}
    report = build(paths)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "markets": {m: {k: v[k] for k in ("training_unique_fixtures",
                          "holdout_unique_fixtures", "roi_pct", "base_policy_2026_roi_pct",
                          "policy_fixture_counts", "source_fixture_markets", "settlement_counts")}
                                  for m, v in report["markets"].items()},
                      "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
