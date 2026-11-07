#!/usr/bin/env python3
"""Audit same-fixture Crown/TotalCorner historical quote overlap.

The receipt is aggregate-only. It compares provider quote events on the same
fixture and market when both are available after the model as-of, without
selecting a provider for wagering or computing a provider-specific ROI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import local_to_utc
from research.m5.m5_line_conditional_settlement_calibration import instant
from research.m5.m5_source_union_replay import event_rows, fixture_row, raw_event

MARKETS = ("AH", "OU")
INDEX_FIELD = {"AH": "ah_valid_prematch_rows", "OU": "ou_valid_prematch_rows"}


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def summarize_pairs(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "same_fixture_market_quote_pairs": n,
        "same_contract_line_pairs": sum(bool(row["same_line"]) for row in rows),
        "same_event_timestamp_pairs": sum(row["event_gap_seconds"] == 0 for row in rows),
        "event_times_within_60_seconds": sum(row["event_gap_seconds"] <= 60 for row in rows),
        "prices_both_sides_within_0_01": sum(bool(row["prices_close"]) for row in rows),
        "median_absolute_event_time_gap_seconds": (
            float(sorted(row["event_gap_seconds"] for row in rows)[n // 2]) if n else None),
        "mean_max_side_price_difference": (
            round(math.fsum(row["max_side_price_difference"] for row in rows) / n, 6) if n else None),
        "both_event_times_pregame": sum(bool(row["both_pregame"]) for row in rows),
        "both_provider_receipts_post_kickoff": sum(bool(row["both_receipts_post_kickoff"]) for row in rows),
    }


def run(private_dir: Path, output: Path, source_timezone: str = "Asia/Shanghai") -> dict:
    zone = ZoneInfo(source_timezone)
    manifest_path = private_dir / "candidate-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}

    index_raw = {}
    indexes = {}
    duplicate_index_rows = Counter()
    for source, filename in (("Crown", "crown-response-index.jsonl"),
                             ("TotalCorner_default", "totalcorner-default-index.jsonl")):
        path = private_dir / filename
        raw = path.read_bytes()
        index_raw[source] = raw
        index = {}
        for line in raw.decode("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                mid = str(row.get("match_id") or "")
                if mid in index:
                    duplicate_index_rows[source] += 1
                    old_time = str(index[mid].get("captured_at_utc") or "")
                    new_time = str(row.get("captured_at_utc") or "")
                    if new_time >= old_time:
                        index[mid] = row
                else:
                    index[mid] = row
        indexes[source] = index

    all_overlap_ids = set()
    for market in MARKETS:
        field = INDEX_FIELD[market]
        all_overlap_ids |= ({mid for mid, row in indexes["Crown"].items() if int(row.get(field, 0) or 0) > 0}
                            & {mid for mid, row in indexes["TotalCorner_default"].items()
                               if int(row.get(field, 0) or 0) > 0})
    forecast_path = private_dir / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecasts = {}
    forecast_digest = hashlib.sha256()
    with forecast_path.open("rb") as stream:
        for line in stream:
            forecast_digest.update(line)
            if line.strip():
                row = json.loads(line)
                mid = str(row.get("match_id") or "")
                if mid in all_overlap_ids:
                    if mid in forecasts:
                        raise ValueError("duplicate M5 forecast fixture identity")
                    forecasts[mid] = row

    response_hashes = set()
    paired = {market: defaultdict(list) for market in MARKETS}
    q3_index_overlap = {market: 0 for market in MARKETS}
    for market in MARKETS:
        field = INDEX_FIELD[market]
        crown_ids = {mid for mid, row in indexes["Crown"].items()
                     if int(row.get(field, 0) or 0) > 0}
        total_ids = {mid for mid, row in indexes["TotalCorner_default"].items()
                     if int(row.get(field, 0) or 0) > 0}
        overlap = crown_ids & total_ids
        q3_index_overlap[market] = sum(
            1 for mid in overlap
            if (fixtures.get(mid, {}).get("kickoff_utc", "")[:7]
                in ("2026-07", "2026-08", "2026-09")))

        for mid in overlap:
            fixture = fixtures.get(mid)
            if not fixture:
                continue
            forecast = forecasts.get(mid)
            if not forecast:
                continue
            asof, kickoff = instant(forecast.get("prediction_asof_utc")), instant(forecast.get("kickoff"))
            train_end = instant(forecast.get("train_end_utc"))
            if not (asof and kickoff and train_end and train_end < asof < kickoff):
                continue
            valid = {}
            response_rows = {}
            receipts = {}
            for source, folder in (("Crown", "crown-responses"),
                                   ("TotalCorner_default", "totalcorner-default-responses")):
                path = private_dir / folder / f"{mid}.json"
                if not path.is_file():
                    break
                raw = path.read_bytes()
                payload = json.loads(raw)
                provider_row = fixture_row(payload, mid)
                if not provider_row:
                    break
                if (provider_row.get("h"), provider_row.get("a"), provider_row.get("l")) != (
                        fixture.get("home"), fixture.get("away"), fixture.get("league")):
                    break
                response_kickoff = local_to_utc(provider_row.get("start"), zone)
                if response_kickoff != kickoff:
                    break
                if source == "Crown":
                    books = [b for b in provider_row.get("bookmakers", [])
                             if isinstance(b, dict) and b.get("slug") == "crown"]
                    if len(books) != 1:
                        break
                chosen = raw_event(event_rows(provider_row, market,
                                             "crown" if source == "Crown" else "totalcorner"),
                                   market, asof, kickoff, zone)
                if not chosen:
                    break
                valid[source] = chosen
                response_rows[source] = raw
                receipts[source] = instant(indexes[source][mid].get("captured_at_utc"))
            if len(valid) != 2:
                continue
            crown_quote, total_quote = valid["Crown"], valid["TotalCorner_default"]
            event_gap = abs((crown_quote[0] - total_quote[0]).total_seconds())
            max_price_diff = max(abs(a - b) for a, b in zip(crown_quote[2], total_quote[2]))
            receipts_post = bool(receipts["Crown"] and receipts["TotalCorner_default"]
                                 and receipts["Crown"] >= kickoff and receipts["TotalCorner_default"] >= kickoff)
            qkey = f"{kickoff.year}-Q{(kickoff.month - 1) // 3 + 1}"
            paired[market][qkey].append({
                "same_line": abs(crown_quote[1] - total_quote[1]) <= 1e-8,
                "event_gap_seconds": event_gap,
                "prices_close": max_price_diff <= 0.01,
                "max_side_price_difference": max_price_diff,
                "both_pregame": crown_quote[0] < kickoff and total_quote[0] < kickoff,
                "both_receipts_post_kickoff": receipts_post,
            })
            for raw in response_rows.values():
                response_hashes.add(sha_bytes(raw))
    if all_overlap_ids and not forecasts:
        raise RuntimeError("forecast overlap rows were not loaded")
    markets_report = {}
    for market in MARKETS:
        field = INDEX_FIELD[market]
        crown_ids = {mid for mid, row in indexes["Crown"].items() if int(row.get(field, 0) or 0) > 0}
        total_ids = {mid for mid, row in indexes["TotalCorner_default"].items()
                     if int(row.get(field, 0) or 0) > 0}
        market_overlap = crown_ids & total_ids
        q3_ids = {mid for mid in market_overlap if fixtures.get(mid, {}).get("kickoff_utc", "")[:7]
                  in ("2026-07", "2026-08", "2026-09")}
        all_pairs = [row for rows in paired[market].values() for row in rows]
        markets_report[market] = {
            "index_fixture_overlap": len(market_overlap),
            "Q3_index_fixture_overlap": len(q3_ids),
            "Q3_M5_asof_valid_quote_pairs": len(paired[market].get("2026-Q3", [])),
            "all_years": summarize_pairs(all_pairs),
            "by_utc_year_quarter": {key: summarize_pairs(rows)
                                    for key, rows in sorted(paired[market].items())},
        }
    report = {
        "protocol": "M5_CROWN_TOTALCORNER_SAME_FIXTURE_QUOTE_OVERLAP_AUDIT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runner_sha256": sha_bytes(Path(__file__).resolve().read_bytes()),
        "input_sha256": {
            "candidate_manifest": sha_bytes(manifest_raw),
            "m5_forecasts": forecast_digest.hexdigest(),
            "Crown_response_index": sha_bytes(index_raw["Crown"]),
            "TotalCorner_response_index": sha_bytes(index_raw["TotalCorner_default"]),
            "overlap_raw_response_hash_set": sha_bytes("\n".join(sorted(response_hashes)).encode()),
        },
        "duplicate_response_index_rows_collapsed_to_latest_receipt": dict(duplicate_index_rows),
        "markets": markets_report,
        "method": "Intersect provider indexes with at least one pre-kickoff quote row, then revalidate exact M5 forecast identity, UTC kickoff, train_end < prediction_asof < kickoff, and each provider's market quote event within [prediction_asof, kickoff). Compare source events only on exact fixture-market overlap.",
        "limitations": [
            "This is quote overlap/price diagnostic only; no provider-specific ROI is calculated because paired source quotes have different event times and coverage is very small.",
            "Provider responses were retrieved after kickoff even when quote event times were pre-kickoff.",
            "The existing TotalCorner collector fills Crown gaps; absent same-fixture pairs reflect capture design and are not evidence that provider prices are equal.",
            "No provider-switching rule or trade gate is proposed.",
        ],
        "fixture_level_data_published": False,
    }
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
    print(json.dumps({market: {"Q3_index_overlap": report["markets"][market]["Q3_index_fixture_overlap"],
                              "paired_quotes": report["markets"][market]["all_years"]["same_fixture_market_quote_pairs"]}
                     for market in MARKETS}, sort_keys=True))


if __name__ == "__main__":
    main()
