#!/usr/bin/env python3
"""Audit two chronological recency-model OOS cohorts from sanitized aggregates.

This does not tune weights or use Crown P&L. It checks that the per-league
baseline/candidate score deltas aggregate to each year's published totals and
summarizes whether league score changes persist across consecutive OOS years.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

METRICS = {
    "AH_1X2_log_loss": "ah_1x2_log_loss",
    "AH_1X2_brier": "ah_1x2_brier",
    "OU_O2_5_log_loss": "ou_o25_log_loss",
    "OU_O2_5_brier": "ou_o25_brier",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize_year(year: str, report: dict) -> dict:
    leagues = report["by_league"]
    if len(leagues) != 51:
        raise ValueError(f"{year}: expected the frozen 51-league scope, got {len(leagues)}")
    n = sum(int(row["candidate"]["unique_fixtures"]) for row in leagues.values())
    if n != int(report["unique_fixture_count"]):
        raise ValueError(f"{year}: league fixture counts do not match OOS total")
    folds = report["fold_receipts"]
    if len(folds) != 51 or int(report["fold_count"]) != 51:
        raise ValueError(f"{year}: expected one chronological fold per frozen league")
    cutoff = datetime(int(year), 1, 1, tzinfo=timezone.utc)
    for fold in folds:
        train_disjoint = fold.get("final_fit_train_ids_disjoint_from_target", fold.get("final_fit_train_ids_disjoint_from_2026_target"))
        if not train_disjoint:
            raise ValueError(f"{year}: training and target fixture identities overlap")
        train_end = datetime.fromisoformat(str(fold["training_end_utc"]).replace("Z", "+00:00"))
        if train_end.tzinfo is None or train_end.astimezone(timezone.utc) >= cutoff:
            raise ValueError(f"{year}: training cutoff is not before the target UTC year")
        validation_disjoint = fold.get("validation_ids_disjoint_from_target", fold.get("2025_validation_ids_disjoint_from_2026_target"))
        if not validation_disjoint:
            raise ValueError(f"{year}: validation and target identities overlap")

    metrics = {}
    for public_name, key in METRICS.items():
        baseline = report["baseline_same_fixture_oos"][key]
        candidate = report["candidate_oos"][key]
        weighted_delta = sum(
            int(row["candidate"]["unique_fixtures"])
            * (float(row["candidate"][key]) - float(row["baseline"][key]))
            for row in leagues.values()
        ) / n
        # Per-league aggregates are rounded to 15 digits; allow only rounding
        # noise when reconciling their weighted mean to the full-row receipt.
        observed_delta = float(candidate) - float(baseline)
        if abs(weighted_delta - observed_delta) > 2e-8:
            raise ValueError(f"{year} {public_name}: league deltas fail aggregate reconciliation")
        improved = sum(float(x["candidate"][key]) < float(x["baseline"][key]) for x in leagues.values())
        worsened = sum(float(x["candidate"][key]) > float(x["baseline"][key]) for x in leagues.values())
        metrics[public_name] = {
            "baseline": baseline,
            "candidate": candidate,
            "candidate_minus_baseline": observed_delta,
            "league_weighted_delta_reconciled": weighted_delta,
            "leagues_improved": improved,
            "leagues_worsened": worsened,
            "fixtures": n,
        }
    return {
        "unique_oos_fixtures": n,
        "leagues": len(leagues),
        "folds": report["fold_count"],
        "chronological_fold_guards_passed": True,
        "validation_year": str(int(year) - 1),
        "time_isolation": report["time_isolation"],
        "metrics": metrics,
    }


def run(input_dir: Path, output: Path) -> dict:
    reports = {}
    hashes = {}
    for year in ("2025", "2026"):
        path = input_dir / f"m5_goal_model_recency_{year}_oos.json"
        reports[year] = json.loads(path.read_text(encoding="utf-8"))
        hashes[year] = sha(path)
    if reports["2025"]["candidate_manifest_sha256"] != reports["2026"]["candidate_manifest_sha256"]:
        raise ValueError("the two OOS years do not use the same frozen candidate manifest")
    if reports["2025"]["baseline_forecast_sha256"] != reports["2026"]["baseline_forecast_sha256"]:
        raise ValueError("the two reports do not share the same baseline forecast source")
    if set(reports["2025"]["by_league"]) != set(reports["2026"]["by_league"]):
        raise ValueError("league scope differs between the OOS years")

    years = {year: summarize_year(year, report) for year, report in reports.items()}
    persistence = {}
    for name, key in METRICS.items():
        both_improved = both_worsened = reversed_sign = 0
        for league in reports["2025"]["by_league"]:
            deltas = [
                float(reports[year]["by_league"][league]["candidate"][key])
                - float(reports[year]["by_league"][league]["baseline"][key])
                for year in ("2025", "2026")
            ]
            both_improved += deltas[0] < 0 and deltas[1] < 0
            both_worsened += deltas[0] > 0 and deltas[1] > 0
            reversed_sign += (deltas[0] < 0 < deltas[1]) or (deltas[1] < 0 < deltas[0])
        persistence[name] = {
            "both_years_improved": both_improved,
            "both_years_worsened": both_worsened,
            "direction_reversed": reversed_sign,
            "leagues": 51,
        }

    result = {
        "protocol": "M5_RECENCY_TWO_YEAR_OOS_STABILITY_AUDIT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_receipt_sha256": hashes,
        "manifest_sha256": reports["2025"]["candidate_manifest_sha256"],
        "frozen_scope_complete_historical_universe": False,
        "years": years,
        "cross_year_league_persistence": persistence,
        "roi": None,
        "crown_prices_used": False,
        "limitations": [
            "These are forecast proper scores, not Crown-priced AH/OU ROI.",
            "The 2025 and 2026 OOS identities are in different UTC calendar years and are not duplicated across these cohorts.",
            "The schedule manifest covers the fixed 51-league scope only partially.",
            "Only per-league aggregate scores are available here; no fixture-level bootstrap is inferred.",
            "Cross-year league persistence is descriptive and does not define a league filter.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results/m5_recency_two_year_stability.json")
    args = parser.parse_args()
    result = run(args.input_dir, args.output)
    print(json.dumps({"output": str(args.output), "years": result["years"], "persistence": result["cross_year_league_persistence"]}, sort_keys=True))


if __name__ == "__main__":
    main()
