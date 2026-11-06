#!/usr/bin/env python3
"""Capture TotalCorner default AH/OU as a source-distinct M5 forward fallback.

The cohort and model forecasts are M5-only and remain private. Crown is
preferred per fixture-market; TOTAL is retained only when no qualifying Crown
quote exists. Source-event and actual receipt timestamps are checked
independently. This collector never records settlement, ROI, or production
actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import (
    API, atomic_write, ensure_private_destination, local_to_utc, request_json,
    token_value, utc_now,
)
from research.m5.m5_forward_shadow_crown_capture import utc as parse_utc
from research.m5.m3_grid_crown_replay import split_line


def totalcorner_rows(rows, asof, kickoff, zone):
    valid = []
    if not isinstance(rows, list):
        return valid
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue
        minute, raw_line, p1, p2, raw_time = row[:5]
        if minute not in (None, "", 0, "0"):
            continue
        if len(row) >= 8 and row[7] not in (0, "0", False):
            continue
        event = local_to_utc(raw_time, zone)
        if not event or event < asof or event >= kickoff:
            continue
        try:
            parts = [float(x.strip()) for x in str(raw_line).replace("/", ",").split(",")]
            prices = (float(p1), float(p2))
            line = sum(parts) / len(parts)
            split_line(line)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if (len(parts) not in (1, 2) or abs(line * 4 - round(line * 4)) > 1e-8
                or any(not math.isfinite(x) for x in parts + list(prices))
                or any(p <= 1 for p in prices)
                or (len(parts) == 2 and abs(abs(parts[0] - parts[1]) - .5) > 1e-8)):
            continue
        valid.append({"line": line, "prices": prices,
                      "quote_event_utc": event.isoformat().replace("+00:00", "Z")})
    return sorted(valid, key=lambda x: x["quote_event_utc"])


def load_jsonl(path):
    rows = []
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def run(private_dir: Path, forecasts_path: Path, source_timezone="Asia/Shanghai",
        min_interval=3.1, limit=None):
    if min_interval < 2.6:
        raise ValueError("min_interval must be at least 2.6 seconds")
    root = ensure_private_destination(private_dir)
    token = token_value(None)
    zone = ZoneInfo(source_timezone)
    raw_forecasts = forecasts_path.read_bytes()
    forecasts = []
    for line in raw_forecasts.decode().splitlines():
        try:
            row = json.loads(line)
            asof = parse_utc(row.get("prediction_asof_utc"))
            train_end = parse_utc(row.get("train_end_utc"))
            kickoff = parse_utc(row.get("kickoff_utc"))
            if (not asof or not train_end or not kickoff or not train_end < asof < kickoff
                    or kickoff <= datetime.now(timezone.utc)
                    or not (row.get("prediction") or {}).get("grid")):
                continue
            forecasts.append((row, asof, kickoff))
        except Exception:
            continue
    forecasts.sort(key=lambda x: (x[2], str(x[0].get("match_id") or "")))
    if limit is not None:
        forecasts = forecasts[:max(0, limit)]

    out = root / "forward-shadow"
    raw_dir = out / "totalcorner-default-responses"
    errors_dir = out / "totalcorner-default-errors"
    index_path = out / "totalcorner-default-capture-index.jsonl"
    run_id = hashlib.sha256(raw_forecasts).hexdigest()
    prior = {(str(x.get("forecast_sha256")), str(x.get("match_id")))
             for x in load_jsonl(index_path)}

    crown_by_id = {}
    for item in load_jsonl(out / "crown-capture-index.jsonl"):
        if item.get("status") == "verified_fixture_response":
            mid = str(item.get("match_id") or "")
            crown_by_id.setdefault(mid, []).append(item)

    state = {"last_start": 0.0}
    counts = Counter()
    response_hashes = set()
    for forecast, asof, kickoff in forecasts:
        mid = str(forecast.get("match_id") or "")
        if not mid or (run_id, mid) in prior:
            counts["already_captured"] += 1
            continue
        latest_crown = next((x for x in reversed(crown_by_id.get(mid, []))
                             if x.get("quote_event_asof_utc") == forecast.get("prediction_asof_utc")), {})
        crown_ah = bool(latest_crown.get("ah_qualified"))
        crown_ou = bool(latest_crown.get("ou_qualified"))
        url = f"{API}/match/odds/{urllib.parse.quote(mid, safe='')}?" + urllib.parse.urlencode(
            {"columns": "asianList,goalList"})
        try:
            counts["request_attempts"] += 1
            payload, meta, raw = request_json(url, token, min_interval, state)
            received = parse_utc(meta.get("received_at_utc")) or datetime.now(timezone.utc)
            data = payload.get("data") if isinstance(payload, dict) else None
            data_rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            matches = [x for x in data_rows if isinstance(x, dict) and str(x.get("id") or "") == mid]
            exact = matches[0] if len(matches) == 1 else None
            identity_ok = (payload.get("success") == 1 and exact is not None
                           and exact.get("h") == forecast.get("home")
                           and exact.get("a") == forecast.get("away")
                           and exact.get("l") == forecast.get("league")
                           and local_to_utc(exact.get("start"), zone) == kickoff)
            if not identity_ok:
                entry = {"status": "fixture_or_api_identity_mismatch", "provider": "TotalCorner",
                         "match_id": mid, "forecast_sha256": run_id,
                         "captured_at_utc": received.isoformat().replace("+00:00", "Z")}
                atomic_write(errors_dir / f"{mid}-{received.strftime('%Y%m%dT%H%M%S%fZ')}.json",
                             (json.dumps(entry, sort_keys=True) + "\n").encode())
                with index_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry, sort_keys=True) + "\n")
                counts["fixture_or_api_identity_mismatch"] += 1
                continue

            ah_rows = totalcorner_rows(exact.get("asian_list"), asof, kickoff, zone)
            ou_rows = totalcorner_rows(exact.get("goal_list"), asof, kickoff, zone)
            receipt_before_kickoff = received < kickoff
            selected_ah = ah_rows[-1] if ah_rows and not crown_ah and receipt_before_kickoff else None
            selected_ou = ou_rows[-1] if ou_rows and not crown_ou and receipt_before_kickoff else None
            raw_path = raw_dir / f"{mid}-{received.strftime('%Y%m%dT%H%M%S%fZ')}.json"
            atomic_write(raw_path, raw)
            entry = {
                "status": "verified_fixture_response", "provider": "TotalCorner",
                "source_bookmaker": "totalcorner_default_NOT_CROWN",
                "source_endpoint": "/match/odds", "match_id": mid,
                "league": forecast.get("league"), "home": forecast.get("home"),
                "away": forecast.get("away"),
                "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                "prediction_asof_utc": asof.isoformat().replace("+00:00", "Z"),
                "captured_at_utc": received.isoformat().replace("+00:00", "Z"),
                "response_sha256": meta.get("response_sha256"), "forecast_sha256": run_id,
                "raw_response_relative_path": str(raw_path.relative_to(out)),
                "crown_qualified_ah": crown_ah, "crown_qualified_ou": crown_ou,
                "ah_eligible_rows": ah_rows, "ou_eligible_rows": ou_rows,
                "selected_default_ah": selected_ah, "selected_default_ou": selected_ou,
            }
            with index_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
            counts["verified_fixture_responses"] += 1
            counts["AH_default_qualified_fixture_markets"] += int(selected_ah is not None)
            counts["OU_default_qualified_fixture_markets"] += int(selected_ou is not None)
            counts["crown_preferred_AH_skips"] += int(crown_ah)
            counts["crown_preferred_OU_skips"] += int(crown_ou)
            response_hashes.add(str(meta.get("response_sha256") or hashlib.sha256(raw).hexdigest()))
        except Exception as exc:
            received = datetime.now(timezone.utc)
            entry = {"status": "transport_error", "provider": "TotalCorner",
                     "match_id": mid, "forecast_sha256": run_id,
                     "error_type": type(exc).__name__,
                     "captured_at_utc": received.isoformat().replace("+00:00", "Z")}
            with index_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
            counts["transport_errors"] += 1

    receipt = {
        "protocol": "M5_FORWARD_TOTALCORNER_DEFAULT_CAPTURE_V1",
        "generated_utc": utc_now(), "forecast_sha256": run_id,
        "attempted_fixtures": counts["request_attempts"],
        "forecast_candidate_fixtures": len(forecasts), "aggregate_counts": dict(counts),
        "response_hash_set_sha256": hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest(),
        "raw_quotes_and_fixture_rows_remain_private": True,
        "source_rule": "Crown is preferred per fixture-market; TotalCorner default is selected only when Crown has no qualifying post-asof pre-kickoff quote.",
    }
    receipt_path = out / f"totalcorner-default-capture-receipt-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    atomic_write(receipt_path, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"generated_utc": receipt["generated_utc"],
                      "attempted_fixtures": counts["request_attempts"],
                      "forecast_candidate_fixtures": len(forecasts), "aggregate_counts": dict(counts),
                      "response_hash_set_sha256": receipt["response_hash_set_sha256"]}, sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--min-interval", type=float, default=3.1)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.private_dir, args.forecasts, args.source_timezone, args.min_interval, args.limit)


if __name__ == "__main__":
    main()
