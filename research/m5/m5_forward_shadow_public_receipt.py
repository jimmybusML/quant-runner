#!/usr/bin/env python3
"""Sanitize a private M5 forward capture/pairing into a public receipt.

The public artifact contains aggregate counts and input hashes only. Raw
fixture identities, predictions, lines, prices, and provider responses stay
outside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def instant(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_receipt(forecast_path: Path, forecast_meta_path: Path,
                  crown_capture_path: Path, pair_path: Path,
                  pair_meta_path: Path, totalcorner_capture_path: Path | None = None,
                  settlement_path: Path | None = None) -> dict:
    forecast_meta = json.loads(forecast_meta_path.read_text(encoding="utf-8"))
    crown_capture = json.loads(crown_capture_path.read_text(encoding="utf-8"))
    totalcorner_capture = (json.loads(totalcorner_capture_path.read_text(encoding="utf-8"))
                           if totalcorner_capture_path else None)
    settlement = (json.loads(settlement_path.read_text(encoding="utf-8"))
                  if settlement_path else None)
    pair_meta = json.loads(pair_meta_path.read_text(encoding="utf-8"))
    forecast_raw = forecast_path.read_bytes()
    pair_raw = pair_path.read_bytes()
    forecast_hash = hashlib.sha256(forecast_raw).hexdigest()
    pair_hash = hashlib.sha256(pair_raw).hexdigest()
    if forecast_hash != forecast_meta.get("forecast_sha256"):
        raise ValueError("forecast hash does not match its receipt")
    if forecast_hash != pair_meta.get("forecast_sha256"):
        raise ValueError("pairing receipt references another forecast batch")
    if pair_hash != pair_meta.get("pair_sha256"):
        raise ValueError("pair hash does not match its receipt")
    if (crown_capture.get("forecast_sha256")
            and crown_capture.get("forecast_sha256") != forecast_hash):
        raise ValueError("Crown capture receipt references another forecast batch")
    if totalcorner_capture and totalcorner_capture.get("forecast_sha256") != forecast_hash:
        raise ValueError("TotalCorner capture receipt references another forecast batch")
    if settlement:
        if settlement.get("protocol") != "M5_FORWARD_SHADOW_SETTLEMENT_V1":
            raise ValueError("unexpected settlement receipt protocol")
        if settlement.get("paired_input_sha256") != pair_hash:
            raise ValueError("settlement receipt references another pair batch")

    forecast_rows = []
    fixture_ids = set()
    for line in forecast_raw.decode("utf-8").splitlines():
        row = json.loads(line)
        mid = str(row.get("match_id") or "")
        if not mid or mid in fixture_ids:
            raise ValueError("missing or duplicate forecast fixture identity")
        fixture_ids.add(mid)
        forecast_rows.append(row)

    market_counts = Counter()
    source_counts = {"AH": Counter(), "OU": Counter()}
    min_kickoff = max_kickoff = None
    seen = set()
    for line in pair_raw.decode("utf-8").splitlines():
        row = json.loads(line)
        mid, market, source = str(row.get("match_id") or ""), row.get("market"), row.get("source")
        key = (mid, market)
        if not mid or market not in ("AH", "OU") or source not in ("Crown", "TotalCorner_default"):
            raise ValueError("invalid private pair row")
        if key in seen:
            raise ValueError("duplicate fixture-market in pair file")
        seen.add(key)
        train_end = instant(row.get("train_end_utc"))
        asof = instant(row.get("prediction_asof_utc"))
        event = instant(row.get("quote_event_utc"))
        received = instant(row.get("quote_received_utc"))
        kickoff = instant(row.get("kickoff_utc"))
        if not (train_end and asof and event and received and kickoff
                and train_end < asof <= event <= received < kickoff):
            raise ValueError("forward pair violates train/asof/quote/receipt/kickoff chronology")
        market_counts[market] += 1
        source_counts[market][source] += 1
        min_kickoff = kickoff if min_kickoff is None else min(min_kickoff, kickoff)
        max_kickoff = kickoff if max_kickoff is None else max(max_kickoff, kickoff)

    paired = dict(market_counts)
    if paired != pair_meta.get("paired_fixture_markets"):
        raise ValueError("pair market counts differ from private pairing receipt")
    if len(seen) != pair_meta.get("paired_rows"):
        raise ValueError("pair row count differs from private pairing receipt")
    if settlement:
        if (settlement.get("settled_fixture_markets", 0)
                + settlement.get("pending_fixture_markets", 0) != len(seen)):
            raise ValueError("settlement fixture-market counts differ from pair batch")
        for market in ("AH", "OU"):
            result = settlement["markets"][market]
            if not (result["unique_fixture_markets"] == result["simulated_bets"]
                    and result["settled_bets"] + result["pending_bets"] == result["simulated_bets"]
                    and sum(result["settlement_counts"].values()) == result["settled_bets"]
                    and result["paired_source_fixture_markets"]
                    == dict(source_counts[market])):
                raise ValueError(f"{market} settlement counts do not reconcile")
            if result["pending_bets"] and result["roi_pct"] is not None:
                raise ValueError(f"{market} incomplete settlement cannot have full-cohort ROI")
    per_market = {}
    for market in ("AH", "OU"):
        count = market_counts[market]
        per_market[market] = {
            "unique_fixture_markets": count,
            "source_fixture_markets": dict(sorted(source_counts[market].items())),
            "receipt_timing": ("no paired receipts" if count == 0
                                else "all paired receipts were before kickoff"),
            "settled_fixture_markets": 0,
            "fixture_markets_pending_settlement_verification": count,
            "net_units": None,
            "roi_pct": None,
            "max_drawdown_units": None,
        }
    chronology_start = min_kickoff.isoformat().replace("+00:00", "Z") if min_kickoff else None
    chronology_end = max_kickoff.isoformat().replace("+00:00", "Z") if max_kickoff else None
    receipt = {
        "protocol": "M5_FORWARD_SHADOW_PUBLIC_CAPTURE_RECEIPT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sanitizer_sha256": sha256(Path(__file__)),
        "forecast_generated_utc": forecast_meta.get("generated_utc"),
        "crown_capture_generated_utc": crown_capture.get("generated_utc"),
        "pairing_generated_utc": pair_meta.get("generated_utc"),
        "forecast_fixture_count": len(forecast_rows),
        "forecast_sha256": forecast_hash,
        "forecast_receipt_sha256": sha256(forecast_meta_path),
        "crown_capture_receipt_sha256": sha256(crown_capture_path),
        "pair_receipt_sha256": sha256(pair_meta_path),
        "crown_capture": {
            "attempted_fixtures": crown_capture.get("attempted_fixtures"),
            "aggregate_counts": crown_capture.get("aggregate_counts", {}),
            "response_hash_set_sha256": crown_capture.get("response_hash_set_sha256"),
        },
        "paired_fixture_markets": len(seen),
        "paired_fixture_markets_by_market": dict(sorted(market_counts.items())),
        "pairing_audit_counts": pair_meta.get("audit_counts", {}),
        "markets": per_market,
        "kickoff_coverage_utc": [chronology_start, chronology_end],
        "pair_sha256": pair_hash,
        "crown_index_sha256": pair_meta.get("crown_index_sha256"),
        "totalcorner_index_sha256": pair_meta.get("totalcorner_index_sha256"),
        "integrity": {
            "all_fixture_markets_unique": True,
            "source_separated": True,
            "train_end_before_asof_before_or_at_quote_before_or_at_receipt_before_kickoff": True,
            "private_fixture_level_data_published": False,
            "settlement_performed": settlement is not None,
        },
        "limitations": [
            ("This is a prediction/quote pairing receipt, not a simulated wager or ROI result."
             if not settlement else
             "The paired cohort settlement has pending fixture-markets; full-cohort ROI remains null."),
            "AH and OU paired samples are reported independently and remain below 10,000.",
            "Crown is preferred per fixture-market; TotalCorner default only fills missing Crown markets.",
            "Raw fixture identities, score grids, lines, prices and API responses remain private.",
        ],
    }
    if totalcorner_capture:
        receipt["totalcorner_capture"] = {
            "generated_utc": totalcorner_capture.get("generated_utc"),
            "attempted_fixtures": totalcorner_capture.get("attempted_fixtures"),
            "forecast_candidate_fixtures": totalcorner_capture.get("forecast_candidate_fixtures"),
            "aggregate_counts": totalcorner_capture.get("aggregate_counts", {}),
            "response_hash_set_sha256": totalcorner_capture.get("response_hash_set_sha256"),
            "source_rule": totalcorner_capture.get("source_rule"),
        }
    if settlement:
        settlement_metrics = (
            "unique_fixture_markets", "simulated_bets", "settled_bets", "pending_bets",
            "settlement_counts", "settled_stake_units", "total_stake_units", "net_units",
            "roi_pct", "realized_roi_on_settled_stake_pct", "max_drawdown_units_by_kickoff",
            "paired_source_fixture_markets", "settled_source_fixture_markets")
        receipt["settlement"] = {
            "generated_utc": settlement.get("generated_utc"),
            "fixture_count": settlement.get("fixture_count"),
            "settled_fixture_markets": settlement.get("settled_fixture_markets"),
            "pending_fixture_markets": settlement.get("pending_fixture_markets"),
            "capture_counts": settlement.get("capture_counts", {}),
            "markets": {market: {key: settlement["markets"][market][key]
                                 for key in settlement_metrics}
                        for market in ("AH", "OU")},
            "paired_input_sha256": settlement.get("paired_input_sha256"),
            "verified_result_response_hash_set_sha256": settlement.get(
                "verified_result_response_hash_set_sha256"),
            "timing": settlement.get("timing"),
            "production_or_telegram_changes": False,
        }
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--forecast-meta", type=Path, required=True)
    parser.add_argument("--crown-capture", type=Path, required=True)
    parser.add_argument("--totalcorner-capture", type=Path)
    parser.add_argument("--settlement-input", type=Path)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--pair-meta", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_receipt(args.forecasts, args.forecast_meta, args.crown_capture,
                           args.pairs, args.pair_meta, args.totalcorner_capture,
                           args.settlement_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "paired_fixture_markets_by_market": report["paired_fixture_markets_by_market"],
                      "source_fixture_markets": {m: report["markets"][m]["source_fixture_markets"]
                                                 for m in ("AH", "OU")},
                      "crown_capture": report["crown_capture"]["aggregate_counts"],
                      "pair_sha256": report["pair_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
