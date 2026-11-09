#!/usr/bin/env python3
"""Sanitize an incremental M5 forward-settlement refresh.

The public report links an immutable capture/pairing receipt to a newer
verified settlement summary. Fixture identities, scores, odds, and raw
provider responses remain private.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MARKETS = ("AH", "OU")
OUTCOMES = ("win", "half_win", "push", "half_loss", "loss")
SOURCES = ("Crown", "TotalCorner_default")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_counts(value: dict) -> dict[str, int]:
    normalized = {source: int(value.get(source, 0)) for source in SOURCES}
    return {source: count for source, count in normalized.items() if count}


def build_receipt(capture_path: Path, previous_settlement_path: Path,
                  settlement_path: Path) -> dict:
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    previous = json.loads(previous_settlement_path.read_text(encoding="utf-8"))
    current = json.loads(settlement_path.read_text(encoding="utf-8"))
    if capture.get("protocol") != "M5_FORWARD_SHADOW_PUBLIC_CAPTURE_RECEIPT_V1":
        raise ValueError("unexpected public capture protocol")
    if previous.get("protocol") != "M5_FORWARD_SHADOW_SETTLEMENT_V1":
        raise ValueError("unexpected prior settlement protocol")
    if current.get("protocol") != "M5_FORWARD_SHADOW_SETTLEMENT_V1":
        raise ValueError("unexpected current settlement protocol")
    pair_sha = capture.get("pairing", {}).get("pair_sha256")
    if not pair_sha or previous.get("paired_input_sha256") != pair_sha:
        raise ValueError("previous settlement references another pairing")
    if current.get("paired_input_sha256") != pair_sha:
        raise ValueError("current settlement references another pairing")
    capture_integrity = capture.get("integrity", {})
    private_rows_published = capture_integrity.get("private_fixture_level_data_published",
                                                    capture_integrity.get("fixture_level_data_published"))
    if private_rows_published is not False:
        raise ValueError("capture does not affirm private row-level data")

    market_rows = {}
    for market in MARKETS:
        base_count = int(capture["pairing"]["paired_fixture_markets"].get(market, 0))
        paired_sources = source_counts(capture["pairing"]["source_fixture_markets_by_market"].get(market, {}))
        old = previous["markets"][market]
        row = current["markets"][market]
        if (row.get("unique_fixture_markets") != base_count
                or row.get("simulated_bets") != base_count
                or row.get("paired_source_fixture_markets") != paired_sources
                or row.get("settled_bets", 0) + row.get("pending_bets", 0) != base_count
                or sum(row.get("settlement_counts", {}).values()) != row.get("settled_bets")):
            raise ValueError(f"{market} settlement counts do not reconcile")
        previous_settled = int(old.get("settled_bets", 0))
        current_settled = int(row.get("settled_bets", 0))
        if current_settled < previous_settled:
            raise ValueError(f"{market} settlement count moved backwards")
        if row.get("pending_bets", 0) and row.get("roi_pct") is not None:
            raise ValueError(f"{market} full-cohort ROI must remain null while pending")
        counts = {outcome: int(row.get("settlement_counts", {}).get(outcome, 0))
                  for outcome in OUTCOMES}
        settled_sources = source_counts(row.get("settled_source_fixture_markets", {}))
        if sum(settled_sources.values()) != current_settled:
            raise ValueError(f"{market} source settlement counts do not reconcile")
        market_rows[market] = {
            "unique_fixture_markets": base_count,
            "simulated_bets": int(row["simulated_bets"]),
            "settled_bets": current_settled,
            "newly_verified_settlements_since_previous_receipt": current_settled - previous_settled,
            "pending_bets": int(row["pending_bets"]),
            "settlement_counts": counts,
            "paired_source_fixture_markets": paired_sources,
            "settled_source_fixture_markets": settled_sources,
            "net_units": float(row["net_units"]),
            "settled_roi_pct": float(row["realized_roi_on_settled_stake_pct"])
                if row.get("realized_roi_on_settled_stake_pct") is not None else None,
            "roi_pct": row.get("roi_pct"),
            "max_drawdown_units": row.get("max_drawdown_units_by_kickoff"),
        }

    return {
        "protocol": "M5_FORWARD_SHADOW_SETTLEMENT_REFRESH_PUBLIC_RECEIPT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capture_receipt_sha256": sha256(capture_path),
        "previous_settlement_receipt_sha256": sha256(previous_settlement_path),
        "settlement_receipt_sha256": sha256(settlement_path),
        "paired_input_sha256": pair_sha,
        "previous_settled_fixture_markets": previous.get("settled_fixture_markets"),
        "settled_fixture_markets": current.get("settled_fixture_markets"),
        "pending_fixture_markets": current.get("pending_fixture_markets"),
        "capture_counts": current.get("capture_counts", {}),
        "verified_result_response_hash_set_sha256": current.get("verified_result_response_hash_set_sha256"),
        "markets": market_rows,
        "integrity": {
            "same_immutable_pairing": True,
            "AH_and_OU_accounted_independently": True,
            "source_separated": True,
            "full_cohort_roi_null_while_pending": all(
                market_rows[m]["pending_bets"] == 0 or market_rows[m]["roi_pct"] is None
                for m in MARKETS),
            "fixture_level_data_published": False,
            "production_or_telegram_changes": False,
        },
        "timing": "FT results were received after kickoff and identity/UTC kickoff verified; this is a forward shadow settlement, not formal trading performance.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--previous-settlement", type=Path, required=True)
    parser.add_argument("--settlement", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_receipt(args.capture, args.previous_settlement, args.settlement)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "settled_fixture_markets": report["settled_fixture_markets"],
                      "pending_fixture_markets": report["pending_fixture_markets"],
                      "markets": report["markets"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
