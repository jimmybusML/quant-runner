#!/usr/bin/env python3
"""Pair private M5 forward forecasts with strictly pre-kickoff source quotes.

Crown quotes take priority. TotalCorner default quotes are eligible only when
the fixture-market has no qualifying Crown quote. All row-level output stays
outside the public repository; this script emits a sanitized aggregate receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m5_forward_shadow_crown_pairing import dt, load_jsonl


def read_forecasts(path: Path):
    raw = path.read_bytes()
    rows = {}
    duplicates = set()
    for line in raw.decode().splitlines():
        try:
            row = json.loads(line)
            mid = str(row["match_id"])
            if mid in rows:
                duplicates.add(mid)
            rows[mid] = row
        except (json.JSONDecodeError, KeyError):
            continue
    for mid in duplicates:
        rows.pop(mid, None)
    return raw, rows, duplicates


def pair(forecast_path: Path, crown_index_path: Path, total_index_path: Path,
         output_path: Path):
    forecast_raw, forecasts, duplicate_forecasts = read_forecasts(forecast_path)
    crown_entries = load_jsonl(crown_index_path)
    total_entries = load_jsonl(total_index_path)
    crown_by_key = {}
    for row in crown_entries:
        if row.get("status") != "verified_fixture_response":
            continue
        mid = str(row.get("match_id") or "")
        asof = row.get("quote_event_asof_utc")
        crown_by_key[(mid, asof)] = row
    total_by_key = {}
    for row in total_entries:
        if row.get("status") != "verified_fixture_response":
            continue
        key = (str(row.get("match_id") or ""), row.get("prediction_asof_utc"),
               row.get("forecast_sha256"))
        total_by_key[key] = row
    forecast_sha = hashlib.sha256(forecast_raw).hexdigest()
    counts = Counter()
    selected = {}
    for mid, forecast in forecasts.items():
        if mid in duplicate_forecasts:
            continue
        asof = dt(forecast.get("prediction_asof_utc"))
        train_end = dt(forecast.get("train_end_utc"))
        kickoff = dt(forecast.get("kickoff_utc"))
        if not asof or not train_end or not kickoff or not train_end < asof < kickoff:
            counts["invalid_forecast_chronology"] += 1
            continue
        grid = (forecast.get("prediction") or {}).get("grid")
        if not isinstance(grid, list) or not grid:
            counts["missing_prediction_grid"] += 1
            continue
        total = total_by_key.get((mid, forecast.get("prediction_asof_utc"), forecast_sha))
        if total is None:
            counts["no_totalcorner_response"] += 1
            continue
        for market, key in (("AH", "selected_default_ah"), ("OU", "selected_default_ou")):
            crown = crown_by_key.get((mid, forecast.get("prediction_asof_utc")), {})
            if crown.get("ah_qualified" if market == "AH" else "ou_qualified"):
                counts[f"{market}_crown_preferred"] += 1
                continue
            quote = total.get(key)
            if not isinstance(quote, dict):
                counts[f"{market}_no_eligible_totalcorner_quote"] += 1
                continue
            event = dt(quote.get("quote_event_utc"))
            received = dt(total.get("captured_at_utc"))
            if not event or not received or not asof <= event <= received < kickoff:
                counts[f"{market}_time_order_rejected"] += 1
                continue
            fixture_market = (mid, market)
            if fixture_market in selected:
                counts[f"{market}_duplicate_fixture_market"] += 1
                continue
            selected[fixture_market] = {
                "match_id": mid, "league": forecast.get("league"),
                "home": forecast.get("home"), "away": forecast.get("away"),
                "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                "market": market, "source": "TotalCorner_default",
                "line": quote["line"], "prices": quote["prices"],
                "quote_event_utc": event.isoformat().replace("+00:00", "Z"),
                "quote_received_utc": received.isoformat().replace("+00:00", "Z"),
                "prediction_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                "train_end_utc": forecast.get("train_end_utc"),
                "score_grid": grid,
                "response_sha256": total.get("response_sha256"),
            }
            counts[f"{market}_paired_totalcorner_fixture_markets"] += 1

    output_path = output_path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if output_path == repo or repo in output_path.parents:
        raise ValueError("fixture-level source quote pairs must remain private")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_path.parent, 0o700)
    rows = sorted(selected.values(), key=lambda r: (r["kickoff_utc"], r["match_id"], r["market"]))
    raw = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                  for x in rows).encode()
    output_path.write_bytes(raw)
    by_market = Counter(row["market"] for row in rows)
    report = {
        "protocol": "M5_FORWARD_SOURCE_UNION_PAIRING_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "forecast_sha256": forecast_sha,
        "crown_index_sha256": hashlib.sha256(crown_index_path.read_bytes()).hexdigest(),
        "totalcorner_index_sha256": hashlib.sha256(total_index_path.read_bytes()).hexdigest(),
        "paired_fixture_markets": dict(by_market), "paired_rows": len(rows),
        "pair_sha256": hashlib.sha256(raw).hexdigest(), "audit_counts": dict(counts),
        "time_rule": "train_end_utc < prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc",
        "source_priority": "Crown per fixture-market; TotalCorner default only if Crown has no qualifying post-asof pre-kickoff quote.",
        "settlement_note": "Forward fixtures may remain unsettled. This pairing receipt is not ROI or settlement evidence.",
        "private_pairs_path": str(output_path),
    }
    receipt_path = output_path.with_suffix(output_path.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "paired_fixture_markets": dict(by_market), "paired_rows": len(rows),
                      "audit_counts": dict(counts), "pair_sha256": report["pair_sha256"]}, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--crown-index", type=Path, required=True)
    parser.add_argument("--totalcorner-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pair(args.forecasts, args.crown_index, args.totalcorner_index, args.output)


if __name__ == "__main__":
    main()
