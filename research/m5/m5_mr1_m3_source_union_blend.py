#!/usr/bin/env python3
"""Replay fixed MR1/M3 probability blends over the complete M3-quoted cohort.

The public receipt contains aggregate metrics only. Fixture-level forecasts,
quotes, outcomes, and identifiers remain in the authorized private archive.
MR1 is blended only when its frozen trace matches the exact M3 quote contract;
otherwise the independently generated M3 forecast is used unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m3_grid_crown_replay import grid_distribution, legs_result, payout
from research.m5.m5_mr1_m3_temporal_probability_blend import (
    CATEGORIES, MODELS, blend, ev_from_distribution, mr1_distribution,
    normalize, side_distribution, summarize,
)

MARKETS = ("AH", "OU")
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> tuple[bytes, list[dict]]:
    raw = path.read_bytes()
    return raw, [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def summarize_partition(rows: list[dict], seed: int) -> dict:
    result = summarize(rows, seed)
    result["quote_sources"] = dict(sorted(Counter(row["source"] for row in rows).items()))
    result["response_receipt_timing"] = dict(sorted(Counter(
        "pre_kickoff" if instant(row["receipt_utc"]) < instant(row["kickoff_utc"])
        else "post_kickoff" for row in rows).items()))
    return result


def run(m3_path: Path, mr1_path: Path, output_path: Path, weight: float = 0.5) -> dict:
    if not 0 <= weight <= 1:
        raise ValueError("blend weight must be between zero and one")
    m3_raw, m3_rows = read_jsonl(m3_path)
    mr1_raw, mr1_rows = read_jsonl(mr1_path)
    m3_by_id = {}
    for row in m3_rows:
        fid = str(row["match_id"])
        if fid in m3_by_id:
            raise ValueError("duplicate M3 fixture identity")
        m3_by_id[fid] = row
    mr1_by_key = {}
    for row in mr1_rows:
        key = (str(row["match_id"]), str(row["market"]))
        if key in mr1_by_key:
            raise ValueError("duplicate MR1 fixture-market identity")
        mr1_by_key[key] = row

    reports = {}
    market_fixture_ids = {}
    total_market_counts = {}
    for market in MARKETS:
        sides = SIDES[market]
        strategy_rows = {strategy: {model: [] for model in MODELS}
                         for strategy in ("M3_only", "MR1_M3_fixed_blend_with_M3_fallback")}
        counts = Counter()
        seen_market_ids = set()
        for fid, fixture in sorted(m3_by_id.items()):
            quote = fixture.get("quotes", {}).get(market)
            if not quote:
                continue
            if fid in seen_market_ids:
                raise ValueError("duplicate fixture-market in M3 quoted cohort")
            seen_market_ids.add(fid)
            kickoff = instant(fixture["kickoff_utc"])
            train_end = instant(fixture["train_end_utc"])
            asof = instant(fixture["prediction_asof_utc"])
            event = instant(quote["event_utc"])
            receipt = instant(quote["receipt_utc"])
            if not train_end < asof < kickoff or not asof <= event < kickoff or receipt < event:
                raise ValueError("M3 forecast/quote chronology violation")
            if int(fixture["year"]) != kickoff.year:
                raise ValueError("stored target year differs from UTC kickoff year")
            market_fixture_ids.setdefault(market, set()).add(fid)
            prices = tuple(float(value) for value in quote["prices"])
            line = float(quote["line"])
            mr1 = mr1_by_key.get((fid, market))
            compatible = False
            if mr1:
                compatible = (
                    quote.get("source") == "Crown"
                    and mr1.get("league") == fixture.get("league")
                    and mr1.get("kickoff_utc") == fixture.get("kickoff_utc")
                    and abs(float(mr1["line"]) - line) < 1e-8
                    and mr1.get("event_utc") == quote.get("event_utc")
                    and mr1.get("side") in sides
                    and abs(float(mr1["price"]) - prices[sides.index(mr1["side"])]) < 1e-8
                    and instant(mr1["receipt_utc"]) >= event
                )
                if not compatible:
                    counts["MR1_present_but_quote_or_identity_mismatch"] += 1
            counts["MR1_exact_quote_fixture_markets"] += int(compatible)
            counts["M3_fallback_fixture_markets"] += int(not compatible)
            counts[f"source_{quote['source']}"] += 1
            actual_home, actual_away = int(fixture["actual_home_goals"]), int(fixture["actual_away_goals"])
            for model_index, model in enumerate(MODELS):
                grid = fixture["model_score_grids"][model]
                m3_probs = {side: normalize(grid_distribution(grid, market, side, line)) for side in sides}
                mr_probs = mr1_distribution(mr1) if compatible else None
                candidates = {strategy: [] for strategy in strategy_rows}
                for side_index, side in enumerate(sides):
                    base_probs = m3_probs[side]
                    mixed_probs = (blend(base_probs, side_distribution(mr_probs, mr1["side"], side), weight)
                                   if compatible else base_probs)
                    candidates["M3_only"].append((ev_from_distribution(base_probs, prices[side_index]),
                                                  side_index, side, base_probs))
                    candidates["MR1_M3_fixed_blend_with_M3_fallback"].append(
                        (ev_from_distribution(mixed_probs, prices[side_index]), side_index, side, mixed_probs))
                for strategy, options in candidates.items():
                    _, side_index, side, probs = max(options, key=lambda item: (item[0], -item[1]))
                    legs, category = legs_result(market, side, line, actual_home, actual_away)
                    pnl = payout(legs, prices[side_index])
                    strategy_rows[strategy][model].append({
                        "pnl": pnl, "category": category, "probabilities": probs,
                        "event_utc": quote["event_utc"], "kickoff_utc": fixture["kickoff_utc"],
                        "receipt_utc": quote["receipt_utc"], "source": quote["source"],
                        "year": str(kickoff.year),
                    })
        total_market_counts[market] = len(seen_market_ids)
        reports[market] = {
            "unique_m3_quoted_fixtures": len(seen_market_ids),
            "mr1_exact_quote_fixture_markets": counts["MR1_exact_quote_fixture_markets"],
            "m3_fallback_fixture_markets": counts["M3_fallback_fixture_markets"],
            "quote_sources": {source.removeprefix("source_"): counts[source]
                              for source in sorted(counts) if source.startswith("source_")},
            "models": {},
        }
        for model_index, model in enumerate(MODELS):
            reports[market]["models"][model] = {}
            for strategy_index, strategy in enumerate(strategy_rows):
                rows = strategy_rows[strategy][model]
                base_seed = 20261106 + model_index * 101 + strategy_index * 17 + (0 if market == "AH" else 1)
                entry = {"all_years": summarize_partition(rows, base_seed), "by_utc_kickoff_year": {}}
                for year in sorted({row["year"] for row in rows}):
                    entry["by_utc_kickoff_year"][year] = summarize_partition(
                        [row for row in rows if row["year"] == year], base_seed + int(year))
                reports[market]["models"][model][strategy] = entry

    if total_market_counts["AH"] != total_market_counts["OU"]:
        raise ValueError("AH and OU fixture universe differs; report them separately")
    if market_fixture_ids["AH"] != market_fixture_ids["OU"]:
        raise ValueError("AH and OU quoted fixture identities are not aligned")
    result = {
        "protocol": "M5_MR1_M3_FIXED_BLEND_COMPLETE_M3_QUOTED_COHORT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "For each market and M3 model, compare M3-only with a fixed probability blend; use MR1 only when its exact line, quote event, selected side price, fixture identity, and kickoff match the M3 Crown contract. Otherwise retain M3 unchanged. One 1U simulated bet per fixture-market, side selected by higher model expected return; no threshold or result-based filtering.",
        "blend_weight_mr1": weight,
        "candidate_status": "exploratory; equal blend has already been examined on the overlapping 2026 MR1/M3 cohort, so these metrics are not a fresh untouched holdout",
        "data_scope": "M3 strict UTC-year-forward score grids and Crown-first/TotalCorner-default historical quote archive; 2025 and 2026 quote-matched fixtures only",
        "input_sha256": {"m3_private_forecasts": hashlib.sha256(m3_raw).hexdigest(),
                         "mr1_private_trace": hashlib.sha256(mr1_raw).hexdigest()},
        "runner_sha256": sha(Path(__file__).resolve()),
        "quote_receipts": "Provider response receipt timestamps are reported separately; this archive was retrieved retrospectively after kickoff.",
        "time_order_passed": True,
        "AH_OU_fixture_id_sets_equal": True,
        "markets": reports,
        "limitations": [
            "The fixed 50/50 candidate reuses an already explored blend and is not confirmatory evidence.",
            "Every M3 fixture is counted once per market; MR1-missing fixtures use M3 probabilities without dropping rows.",
            "Historical API response receipts occurred after kickoff, so the simulated ROI is not executable or realized betting performance.",
            "M1 does not have compatible saved forecasts across this cohort; M4 is a historical MR1-based Pass rule, not an independent probability model.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3-forecasts", type=Path, required=True)
    parser.add_argument("--mr1-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mr1-weight", type=float, default=0.5)
    args = parser.parse_args()
    result = run(args.m3_forecasts, args.mr1_trace, args.output, args.mr1_weight)
    print(json.dumps({"generated_utc": result["generated_utc"],
                      "markets": {market: {"unique_m3_quoted_fixtures": value["unique_m3_quoted_fixtures"],
                                           "mr1_exact_quote_fixture_markets": value["mr1_exact_quote_fixture_markets"],
                                           "models": {model: {strategy: row["all_years"]["roi_pct"]
                                                              for strategy, row in strategies.items()}
                                                       for model, strategies in value["models"].items()}}
                                 for market, value in result["markets"].items()}},
                     sort_keys=True))


if __name__ == "__main__":
    main()
