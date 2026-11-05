#!/usr/bin/env python3
"""Pair private M5 forward forecasts with independently received Crown quotes.

Only quote snapshots whose event time is on/after the M5 forecast as-of and
whose actual receipt is before kickoff are accepted. Match identity is checked
against the MR1 snapshot registry; MR1 predictions and ledgers are not read.
All fixture-level pairs and odds stay outside the public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from research.m5.crown_historical_capture import atomic_write, ensure_private_destination


def dt(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def run(forecast_path: Path, mr1_root: Path | None, output_path: Path, capture_index: Path | None = None):
    forecasts = {}
    for row in load_jsonl(forecast_path):
        mid = str(row.get("match_id") or "")
        if mid and mid not in forecasts:
            forecasts[mid] = row
    if mr1_root is not None:
        base = mr1_root / "data/prospective-market/shadow-v23"
        index_path, registry_path = base / "snapshot-index.jsonl", base / "fixtures.json"
        index_raw, registry_raw = index_path.read_bytes(), registry_path.read_bytes()
        registry = json.loads(registry_raw)
    else:
        base = None
        index_path = registry_path = None
        index_raw = registry_raw = b""
        registry = {}
    snapshots = {}
    counters = Counter()

    # M5's own TotalCorner -> Crown receipts are preferred when supplied.
    # These are raw-provider receipts for M5 forecasts, not MR1 predictions
    # or ledgers. Keep the MR1 snapshot path as a read-only alternate source.
    if capture_index is not None:
        for entry in load_jsonl(capture_index):
            mid = str(entry.get("match_id") or "")
            forecast = forecasts.get(mid)
            if not forecast:
                continue
            counters["m5_capture_index_matches"] += 1
            if entry.get("status") != "verified_fixture_response":
                counters["m5_capture_non_verified_entries"] += 1
                continue
            kickoff, asof = dt(forecast.get("kickoff_utc")), dt(forecast.get("prediction_asof_utc"))
            received = dt(entry.get("captured_at_utc"))
            if (not kickoff or not asof or not received or entry.get("source_bookmaker") != "Crown"
                    or entry.get("kickoff_utc") != forecast.get("kickoff_utc")
                    or received >= kickoff):
                counters["m5_capture_identity_or_time_mismatch"] += 1
                continue
            if entry.get("league") != forecast.get("league") or entry.get("home") != forecast.get("home") or entry.get("away") != forecast.get("away"):
                counters["m5_capture_identity_or_time_mismatch"] += 1
                continue
            if not asof <= received < kickoff:
                counters["m5_capture_receipt_outside_window"] += 1
                continue
            for market in ("AH", "OU"):
                for quote in entry.get("ah_eligible_rows" if market == "AH" else "ou_eligible_rows", []):
                    observed, line = dt(quote.get("quote_event_utc")), quote.get("line")
                    prices = quote.get("prices")
                    if (not observed or not asof <= observed <= received < kickoff
                            or not isinstance(prices, list) or len(prices) != 2):
                        continue
                    try:
                        line, prices = float(line), tuple(float(p) for p in prices)
                    except (TypeError, ValueError):
                        continue
                    if (not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                            or any(not math.isfinite(p) or p <= 1 for p in prices)):
                        continue
                    prediction = (forecast.get("prediction") or {}).get("grid")
                    if not isinstance(prediction, list) or not prediction:
                        counters["missing_score_grid"] += 1
                        continue
                    item = {"match_id": mid, "league": forecast["league"], "home": forecast["home"],
                            "away": forecast["away"], "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                            "market": market, "source": "Crown", "line": line, "prices": prices,
                            "quote_event_utc": observed.isoformat().replace("+00:00", "Z"),
                            "quote_received_utc": received.isoformat().replace("+00:00", "Z"),
                            "prediction_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                            "train_end_utc": forecast.get("train_end_utc"), "score_grid": prediction,
                            "response_sha256": entry.get("response_sha256")}
                    key = (mid, market)
                    previous = snapshots.get(key)
                    if previous is None or item["quote_event_utc"] > previous["quote_event_utc"]:
                        snapshots[key] = item
                    counters["m5_capture_eligible_market_rows"] += 1

    for entry in load_jsonl(index_path) if index_path is not None else []:
        mid = str(entry.get("match_id") or "")
        forecast = forecasts.get(mid)
        if not forecast:
            continue
        counters["forecast_fixture_index_matches"] += 1
        if entry.get("classification") != "SNAPSHOT_OK":
            counters["non_ok_snapshot_entries"] += 1
            continue
        path = base / str(entry.get("snapshot_path") or "")
        try:
            raw = path.read_bytes()
            snapshot = json.loads(raw)
        except Exception:
            counters["missing_or_invalid_snapshot"] += 1
            continue
        reg = registry.get(mid) or {}
        kickoff = dt(forecast.get("kickoff_utc"))
        asof = dt(forecast.get("prediction_asof_utc"))
        received = dt(snapshot.get("received_at"))
        if (not kickoff or not asof or snapshot.get("match_id") != mid or reg.get("match_id") != mid
                or any(reg.get(key) != forecast.get(key) for key in ("league", "home", "away"))
                or dt(snapshot.get("kickoff_at")) != kickoff or dt(reg.get("kickoff_at")) != kickoff):
            counters["identity_or_kickoff_mismatch"] += 1
            continue
        if not received or not asof <= received < kickoff:
            counters["receipt_outside_forecast_to_kickoff_window"] += 1
            continue
        for market in ("AH", "OU"):
            quote = snapshot.get(market) or {}
            observed = dt(quote.get("observed_at_utc") or quote.get("observed_at"))
            if not observed or not asof <= observed <= received < kickoff or quote.get("closed") is True:
                continue
            try:
                line = float(quote["line"])
                prices = ((float(quote["home_price"]), float(quote["away_price"])) if market == "AH"
                          else (float(quote["over_price"]), float(quote["under_price"])))
            except (KeyError, TypeError, ValueError):
                continue
            if (not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                    or any(not math.isfinite(p) or p <= 1 for p in prices)):
                continue
            prediction = (forecast.get("prediction") or {}).get("grid")
            if not isinstance(prediction, list) or not prediction:
                counters["missing_score_grid"] += 1
                continue
            item = {"match_id": mid, "league": forecast["league"], "home": forecast["home"],
                    "away": forecast["away"], "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                    "market": market, "source": "Crown", "line": line, "prices": prices,
                    "quote_event_utc": observed.isoformat().replace("+00:00", "Z"),
                    "quote_received_utc": received.isoformat().replace("+00:00", "Z"),
                    "prediction_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                    "train_end_utc": forecast.get("train_end_utc"),
                    "score_grid": prediction, "snapshot_sha256": hashlib.sha256(raw).hexdigest()}
            key = (mid, market)
            previous = snapshots.get(key)
            if previous is None or item["quote_event_utc"] > previous["quote_event_utc"]:
                snapshots[key] = item
    output_path = output_path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if output_path == repo or repo in output_path.parents:
        raise ValueError("fixture-level quote pairs must remain private")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_path.parent, 0o700)
    rows = sorted(snapshots.values(), key=lambda x: (x["kickoff_utc"], x["match_id"], x["market"]))
    raw = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                  for x in rows).encode()
    atomic_write(output_path, raw)
    counts = Counter(row["market"] for row in rows)
    receipt = {"protocol": "M5_FORWARD_CROWN_PAIRING_V1",
               "generated_utc": datetime.now(timezone.utc).isoformat(),
               "forecast_sha256": hashlib.sha256(forecast_path.read_bytes()).hexdigest(),
               "snapshot_index_sha256": hashlib.sha256(index_raw).hexdigest() if mr1_root is not None else None,
               "fixture_registry_sha256": hashlib.sha256(registry_raw).hexdigest() if mr1_root is not None else None,
               "unique_fixture_markets": dict(counts), "paired_rows": len(rows),
               "audit_counts": dict(counters), "pairs_sha256": hashlib.sha256(raw).hexdigest(),
               "pairs_path": str(output_path),
               "time_rule": "prediction_asof_utc <= quote_event_utc <= quote_received_utc < kickoff_utc",
               "scope_note": "Crown prices and actual receipt evidence; M5-only forecasts. No MR1 forecast, order, ledger or settlement is consumed. This is a forward shadow cohort and must not be labeled realized ROI before independent FT results arrive."}
    receipt_path = output_path.with_suffix(output_path.suffix + ".receipt.json")
    atomic_write(receipt_path, (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"generated_utc": receipt["generated_utc"], "paired_rows": len(rows),
                      "unique_fixture_markets": dict(counts), "audit_counts": dict(counters),
                      "pairs_sha256": receipt["pairs_sha256"]}, sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--mr1-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-index", type=Path)
    args = parser.parse_args()
    run(args.forecasts, args.mr1_root, args.output, args.capture_index)


if __name__ == "__main__":
    main()
