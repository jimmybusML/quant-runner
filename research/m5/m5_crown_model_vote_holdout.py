#!/usr/bin/env python3
"""Chronological same-Crown holdout for a fixed M5/MR1 direction vote.

The 2-of-3 vote (M5 baseline, M5 recency, MR1 V6) and strict unanimous subset
are research candidates only. No vote rule is selected by ROI and neither is a
production betting rule. Private fixture rows are never written to the output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
from research.m5.m5_mr1_v6_same_crown_oos import build_common_quotes, dt, sha


def model_side(row: dict, name: str) -> str:
    market = row["market"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    if name == "MR1_V6":
        return str(row["v6_selected"]["side"])
    forecast = row["forecast"] if name == "M5_recency" else row["baseline_forecast"]
    grid = forecast["prediction"]["grid"]
    expected = [expected_return(grid, market, side, row["line"], price)
                for side, price in zip(sides, row["prices"])]
    return sides[0] if expected[0] >= expected[1] else sides[1]


def side_votes(row: dict) -> dict[str, str]:
    return {name: model_side(row, name) for name in ("M5_baseline", "M5_recency", "MR1_V6")}


def selections(rows: list[dict], strategy: str) -> list[tuple[dict, str]]:
    selected = []
    for row in rows:
        votes = side_votes(row)
        counts = Counter(votes.values())
        if strategy == "M5_baseline":
            side = votes["M5_baseline"]
        elif strategy == "M5_recency":
            side = votes["M5_recency"]
        elif strategy == "MR1_V6":
            side = votes["MR1_V6"]
        elif strategy == "majority_2_of_3":
            side = max(counts, key=counts.get)
        elif strategy == "unanimous_only":
            if len(counts) != 1:
                continue
            side = next(iter(counts))
        else:
            raise ValueError(strategy)
        selected.append((row, side))
    return selected


def score(selected: list[tuple[dict, str]], seed: int) -> dict:
    categories = Counter()
    bytime: dict[datetime, float] = defaultdict(float)
    pnl = []
    for row, side in selected:
        sides = ("home", "away") if row["market"] == "AH" else ("over", "under")
        price = row["prices"][sides.index(side)]
        hg = int(row["ft"]["home_goals"])
        ag = int(row["ft"]["away_goals"])
        legs, category = legs_result(row["market"], side, row["line"], hg, ag)
        units = payout(legs, price)
        categories[category] += 1
        bytime[row["observed"]] += units
        pnl.append(units)
    n = len(pnl)
    equity = peak = max_dd = 0.0
    for instant in sorted(bytime):
        equity += bytime[instant]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    rng = random.Random(seed)
    if n:
        bootstrap = sorted(100 * sum(pnl[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    else:
        bootstrap = []
    return {
        "simulated_bets": n,
        "settled_bets": n,
        "full_win": categories["win"],
        "half_win": categories["half_win"],
        "push": categories["push"],
        "half_loss": categories["half_loss"],
        "full_loss": categories["loss"],
        "net_units": round(sum(pnl), 6),
        "roi_pct": round(100 * sum(pnl) / n, 6) if n else None,
        "max_drawdown_by_quote_event_units": round(max_dd, 6) if n else None,
        "bootstrap_95pct_roi_interval": {
            "lower_2_5_pct": round(bootstrap[249], 6),
            "upper_97_5_pct": round(bootstrap[9749], 6),
            "resamples": 10000,
            "seed": seed,
        } if n else None,
    }


def run(mr1_root: Path, baseline_path: Path, candidate_path: Path, output: Path) -> dict:
    (chosen, counters, baseline_raw, candidate_raw, index_raw, registry_raw,
     record_hashes, snapshot_hashes, ft_hashes, baseline_n, candidate_n) = build_common_quotes(
        mr1_root, baseline_path, candidate_path
    )
    markets = {}
    for market in ("AH", "OU"):
        rows = sorted((row for (_, mkt), row in chosen.items() if mkt == market),
                      key=lambda row: (row["observed"], row["match_id"]))
        if not rows:
            markets[market] = {"unique_fixture_markets": 0, "strategies": {}}
            continue
        unique_times = sorted({row["observed"] for row in rows})
        cutoff = unique_times[int(len(unique_times) * 0.70)]
        early_quotes = [row for row in rows if row["observed"] < cutoff]
        late = [row for row in rows if row["observed"] >= cutoff]
        train = [row for row in early_quotes if dt(row["ft"].get("observed_at")) < cutoff]
        purged = [row for row in early_quotes if dt(row["ft"].get("observed_at")) >= cutoff]
        if not late or not train:
            raise RuntimeError(f"{market}: empty temporal train or holdout")
        if any(row["observed"] >= cutoff for row in train) or any(row["observed"] < cutoff for row in late):
            raise RuntimeError(f"{market}: quote-time split invariant failed")
        if any(dt(row["ft"].get("observed_at")) >= cutoff for row in train):
            raise RuntimeError(f"{market}: training FT receipt is not pre-holdout")
        strategies = {}
        for i, strategy in enumerate(("M5_baseline", "M5_recency", "MR1_V6", "majority_2_of_3", "unanimous_only")):
            train_rows = selections(train, strategy)
            test_rows = selections(late, strategy)
            strategies[strategy] = {
                "train": {"eligible_fixtures": len(train), **score(train_rows, 20261150 + i)},
                "later_holdout": {"eligible_fixture_universe": len(late), **score(test_rows, 20261160 + i)},
            }
        markets[market] = {
            "unique_fixture_markets": len(rows),
            "unique_quote_timestamps": len(unique_times),
            "chronological_cutoff_quote_utc": cutoff.isoformat().replace("+00:00", "Z"),
            "early_quote_fixtures": len(early_quotes),
            "training_fixtures_with_FT_received_before_cutoff": len(train),
            "purged_early_quotes_with_late_FT_receipt": len(purged),
            "later_holdout_fixtures": len(late),
            "train_and_holdout_fixture_ids_disjoint": not ({r["match_id"] for r in train} & {r["match_id"] for r in late}),
            "all_training_FT_receipts_precede_holdout": all(dt(r["ft"].get("observed_at")) < cutoff for r in train),
            "strategies": strategies,
        }

    report = {
        "protocol": "M5_CROWN_MODEL_DIRECTION_VOTE_CHRONOLOGICAL_HOLDOUT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": {
            "M5_baseline_forecasts": sha(baseline_raw),
            "M5_recency_forecasts": sha(candidate_raw),
            "MR1_snapshot_index": sha(index_raw),
            "MR1_fixture_registry": sha(registry_raw),
            "MR1_V6_records": sha("\n".join(sorted(record_hashes)).encode()),
            "verified_Crown_snapshots": sha("\n".join(sorted(snapshot_hashes)).encode()),
            "independent_FT_receipts": sha("\n".join(sorted(ft_hashes)).encode()),
        },
        "markets": markets,
        "validation_counts": dict(counters),
        "baseline_forecast_universe": baseline_n,
        "recency_forecast_universe": candidate_n,
        "crown_prices_used_only": True,
        "roi_used_for_candidate_or_cutoff_selection": False,
        "cutoff_method": "Within each market, sort unique verified Crown quote-event UTC instants and use the instant at the 70th percentile; all fixtures sharing the cutoff instant enter the later holdout. Early quotes whose independent FT receipt is not before the cutoff are purged from training.",
        "strategy_definition": "M5 baseline and recency each select their higher expected-return side at the exact Crown line/prices; MR1 V6 uses its source-verified saved selection on the exact same contract; majority_2_of_3 bets the side selected by at least two methods; unanimous_only bets only when all three methods agree. All bets are 1U and use quarter-line settlement.",
        "limitations": [
            "All observations are from the already researched 2026 Crown archive; this is retrospective repeated-use research, not an untouched independent test.",
            "The unanimity-only candidate is a research selection variable, not an approved formal rule or gate.",
            "The train window has no parameter fit; it is reported as context only. No rule was selected by train or holdout ROI.",
            "Coverage remains far below 10,000 unique Crown fixture-markets per market.",
            "M5 forecasts are retrospective UTC walk-forward hindcasts, not contemporaneously archived M5 deployment forecasts.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mr1-root", type=Path, required=True)
    parser.add_argument("--baseline-forecasts", type=Path, required=True)
    parser.add_argument("--candidate-forecasts", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results/m5_crown_model_vote_holdout.json")
    args = parser.parse_args()
    report = run(args.mr1_root, args.baseline_forecasts, args.candidate_forecasts, args.output)
    print(json.dumps({market: {"n": result["unique_fixture_markets"], "cutoff": result.get("chronological_cutoff_quote_utc"), "strategies": {name: value["later_holdout"] for name, value in result["strategies"].items()}} for market, result in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
