#!/usr/bin/env python3
"""Capture Crown quotes for a frozen private M5 forward forecast cohort.

Uses the existing TotalCorner authorization path and rate-limited request
helper. Raw responses, IDs, quotes, and receipts stay in the private archive.
Run this collector without another TotalCorner API collector active so the
shared account rate limit is respected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import (
    API, atomic_write, ensure_private_destination, local_to_utc,
    request_json, token_value, utc_now,
)


def utc(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def valid_market_rows(rows, market, asof, kickoff, zone):
    valid = []
    if not isinstance(rows, list):
        return valid
    for row in rows:
        if not isinstance(row, list) or len(row) != 8:
            continue
        minute, raw_line, p1, p2, raw_time, _hg, _ag, closed = row
        if minute is not None or closed not in (0, "0", False):
            continue
        observed = local_to_utc(raw_time, zone)
        try:
            parts = [float(x.strip()) for x in str(raw_line).replace("/", ",").split(",")]
            prices = (float(p1), float(p2))
        except (TypeError, ValueError):
            continue
        if (not observed or observed < asof or observed >= kickoff or len(parts) not in (1, 2)
                or any(not math.isfinite(x) for x in parts + list(prices))
                or any(x <= 1 for x in prices)):
            continue
        line = sum(parts) / len(parts)
        if abs(line * 4 - round(line * 4)) > 1e-7:
            continue
        valid.append({"market": market, "line": line, "prices": prices,
                      "quote_event_utc": observed.isoformat().replace("+00:00", "Z")})
    return valid


def run(private_dir: Path, forecasts_path: Path, token_file: Path | None = None,
        source_timezone: str = "Asia/Shanghai", min_interval: float = 3.1, limit: int | None = None):
    if min_interval < 2.6:
        raise ValueError("min_interval must be at least 2.6 seconds")
    root = ensure_private_destination(private_dir)
    token = token_value(token_file)
    zone = ZoneInfo(source_timezone)
    forecasts = []
    for line in forecasts_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            asof, cutoff, kickoff = utc(row.get("prediction_asof_utc")), utc(row.get("train_end_utc")), utc(row.get("kickoff_utc"))
            if not asof or not cutoff or not kickoff or not cutoff < asof < kickoff:
                continue
            if kickoff <= datetime.now(timezone.utc):
                continue
            if not (row.get("prediction") or {}).get("grid"):
                continue
            forecasts.append((row, asof, kickoff))
        except Exception:
            continue
    forecasts.sort(key=lambda x: (x[2], str(x[0].get("match_id") or "")))
    if limit is not None:
        forecasts = forecasts[:max(0, limit)]
    out = root / "forward-shadow"
    raw_dir = out / "crown-responses"
    error_dir = out / "crown-errors"
    index_path = out / "crown-capture-index.jsonl"
    state = {"last_start": 0.0}
    counts = Counter()
    hashes = set()
    for forecast, asof, kickoff in forecasts:
        mid = str(forecast["match_id"])
        query = urllib.parse.urlencode({"bookmaker": "crown", "columns": "asianList,goalList"})
        url = f"{API}/match/bookmaker_odds/{urllib.parse.quote(mid, safe='')}?{query}"
        try:
            payload, response_meta, raw = request_json(url, token, min_interval, state)
            received = utc(response_meta.get("received_at_utc")) or datetime.now(timezone.utc)
            data = payload.get("data") if isinstance(payload, dict) else None
            matches = [m for m in data if isinstance(m, dict) and str(m.get("id") or "") == mid] if isinstance(data, list) else []
            if payload.get("success") != 1 or len(matches) != 1:
                entry = {"match_id": mid, "status": "identity_or_api_failure", "captured_at_utc": received.isoformat(),
                         "http_status": response_meta.get("http_status"), "error_code": (payload.get("error") or {}).get("code")}
                atomic_write(error_dir / f"{mid}-{received.strftime('%Y%m%dT%H%M%S%fZ')}.json",
                             (json.dumps(entry, sort_keys=True) + "\n").encode())
                counts["identity_or_api_failure"] += 1
                with index_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(entry, sort_keys=True) + "\n")
                continue
            match = matches[0]
            kickoff_source = local_to_utc(match.get("start"), zone)
            books = [b for b in match.get("bookmakers", []) if isinstance(b, dict) and b.get("slug") == "crown"]
            identity_ok = (match.get("l") == forecast.get("league") and match.get("h") == forecast.get("home")
                           and match.get("a") == forecast.get("away") and kickoff_source == kickoff)
            if not identity_ok or len(books) != 1:
                entry = {"match_id": mid, "status": "fixture_or_crown_identity_mismatch", "captured_at_utc": received.isoformat(),
                         "response_sha256": response_meta.get("response_sha256")}
                atomic_write(error_dir / f"{mid}-{received.strftime('%Y%m%dT%H%M%S%fZ')}.json",
                             (json.dumps(entry, sort_keys=True) + "\n").encode())
                counts["fixture_or_crown_identity_mismatch"] += 1
                with index_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(entry, sort_keys=True) + "\n")
                continue
            crown = books[0]
            ah = valid_market_rows(crown.get("asian_list"), "AH", asof, kickoff, zone)
            ou = valid_market_rows(crown.get("goal_list"), "OU", asof, kickoff, zone)
            raw_path = raw_dir / f"{mid}-{received.strftime('%Y%m%dT%H%M%S%fZ')}.json"
            atomic_write(raw_path, raw)
            entry = {"match_id": mid, "league": forecast.get("league"), "home": forecast.get("home"),
                     "away": forecast.get("away"), "status": "verified_fixture_response", "provider": "TotalCorner",
                     "source_bookmaker": "Crown", "source_endpoint": "/match/bookmaker_odds",
                     "captured_at_utc": received.isoformat().replace("+00:00", "Z"),
                     "quote_event_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                     "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                     "response_sha256": response_meta.get("response_sha256"),
                     "raw_response_relative_path": str(raw_path.relative_to(out)),
                     "ah_eligible_rows": ah, "ou_eligible_rows": ou,
                     "ah_qualified": bool(ah and received < kickoff), "ou_qualified": bool(ou and received < kickoff)}
            with index_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(entry, sort_keys=True) + "\n")
            hashes.add(str(entry["response_sha256"]))
            counts["verified_fixture_responses"] += 1
            counts["AH_qualified_fixture_markets"] += int(entry["ah_qualified"])
            counts["OU_qualified_fixture_markets"] += int(entry["ou_qualified"])
        except Exception as exc:
            # Never stringify exceptions that could carry a credential URL.
            entry = {"match_id": mid, "status": "transport_error", "error_type": type(exc).__name__,
                     "captured_at_utc": datetime.now(timezone.utc).isoformat()}
            with index_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(entry, sort_keys=True) + "\n")
            counts["transport_errors"] += 1
    receipt = {"protocol": "M5_FORWARD_CROWN_CAPTURE_RUN_V1",
               "generated_utc": utc_now(), "forecast_sha256": hashlib.sha256(forecasts_path.read_bytes()).hexdigest(),
               "attempted_fixtures": len(forecasts), "aggregate_counts": dict(counts),
               "response_hash_set_sha256": hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest(),
               "raw_quotes_and_fixture_rows_remain_private": True}
    receipt_path = out / f"crown-capture-receipt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    atomic_write(receipt_path, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"generated_utc": receipt["generated_utc"], "attempted_fixtures": len(forecasts),
                      "aggregate_counts": dict(counts), "response_hash_set_sha256": receipt["response_hash_set_sha256"]}, sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--min-interval", type=float, default=3.1)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.private_dir, args.forecasts, args.token_file, args.source_timezone, args.min_interval, args.limit)


if __name__ == "__main__":
    main()
