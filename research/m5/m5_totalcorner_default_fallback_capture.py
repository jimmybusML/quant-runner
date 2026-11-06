#!/usr/bin/env python3
"""Capture TotalCorner default AH/OU only where Crown is unavailable.

Historical responses and candidate identities remain in a private directory.
This collector is separate from the Crown-only collector and labels the source
as TotalCorner default (not Crown). It only considers forecast candidates for
which a Crown response has already been processed, so the two feeds can be
joined with per-market Crown-first precedence without double counting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import (
    API, atomic_write, ensure_private_destination, local_to_utc,
    request_json, save_json, token_value, utc_now,
)


def utc(value: str | None) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def valid_rows(rows: object, asof: datetime, kickoff: datetime, zone: ZoneInfo) -> list[dict]:
    valid = []
    if not isinstance(rows, list):
        return valid
    for row in rows:
        # TotalCorner's older /match/odds archive can return the first seven
        # documented columns and omit the newer home/away-score + closed
        # fields. Those rows remain usable only when their own minute field
        # proves they are pre-kickoff; never infer a missing closed flag.
        if not isinstance(row, list) or len(row) < 7:
            continue
        minute, raw_line, first_price, second_price, raw_time = row[:5]
        if minute not in (None, "", 0, "0"):
            continue
        if len(row) >= 8 and row[7] not in (0, "0", False):
            continue
        observed = local_to_utc(raw_time, zone)
        if not observed or observed < asof or observed >= kickoff:
            continue
        try:
            parts = [float(part.strip()) for part in str(raw_line).replace("/", ",").split(",")]
            prices = (float(first_price), float(second_price))
        except (TypeError, ValueError):
            continue
        if (len(parts) not in (1, 2) or any(not math.isfinite(x) for x in parts + list(prices))
                or any(price <= 1 for price in prices)):
            continue
        line = sum(parts) / len(parts)
        if abs(line * 4 - round(line * 4)) > 1e-8:
            continue
        if len(parts) == 2 and abs(abs(parts[0] - parts[1]) - 0.5) > 1e-8:
            continue
        valid.append({"observed": observed, "line": line})
    return valid


def response_match(payload: dict, fixture: dict, zone: ZoneInfo) -> dict | None:
    data = payload.get("data")
    matches = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
    exact = [row for row in matches if isinstance(row, dict) and str(row.get("id") or "") == fixture["match_id"]]
    if len(exact) != 1:
        return None
    row = exact[0]
    if (row.get("h") != fixture["home"] or row.get("a") != fixture["away"]
            or row.get("l") != fixture["league"]):
        return None
    kick = local_to_utc(row.get("start"), zone)
    expected = utc(fixture["kickoff_utc"])
    try:
        has_score = row.get("hg") is not None and row.get("ag") is not None
        score = (int(row.get("hg")), int(row.get("ag"))) if has_score else None
    except (TypeError, ValueError):
        return None
    if (not kick or kick != expected
            or (score is not None and score != (fixture["home_goals"], fixture["away_goals"]))):
        return None
    return row


def load_forecast_metadata(path: Path) -> dict[str, dict]:
    result = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                row = json.loads(line)
                result[str(row["match_id"])] = {key: row.get(key) for key in
                    ("league", "home", "away", "kickoff", "prediction_asof_utc", "train_end_utc")}
            except Exception:
                continue
    return result


def crown_rows(path: Path, match_id: str) -> dict[str, list]:
    if not path.exists():
        return {"AH": [], "OU": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload.get("data") or []
        matches = [row for row in data if isinstance(row, dict) and str(row.get("id") or "") == match_id]
        if len(matches) != 1:
            return {"AH": [], "OU": []}
        books = [row for row in matches[0].get("bookmakers", []) if isinstance(row, dict) and row.get("slug") == "crown"]
        if len(books) != 1:
            return {"AH": [], "OU": []}
        return {"AH": books[0].get("asian_list") or [], "OU": books[0].get("goal_list") or []}
    except Exception:
        return {"AH": [], "OU": []}


def valid_crown_set(rows: dict[str, list], asof: datetime, kickoff: datetime, zone: ZoneInfo) -> dict[str, bool]:
    return {market: bool(valid_rows(rows.get("AH" if market == "AH" else "OU"), asof, kickoff, zone))
            for market in ("AH", "OU")}


def run(args) -> dict:
    out = ensure_private_destination(args.private_dir)
    token = token_value(args.token_file)
    zone = ZoneInfo(args.source_timezone)
    progress_path = out / "quote-progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if not progress.get("finished_utc"):
            raise RuntimeError("Crown capture is still active or has no final checkpoint; wait before TotalCorner fallback.")

    manifest_path = out / "candidate-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    candidates = manifest.get("rows") or []
    forecast_path = out / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecasts = load_forecast_metadata(forecast_path)
    index_path = out / "crown-response-index.jsonl"
    processed_ids = set()
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            try:
                processed_ids.add(str(json.loads(line).get("match_id") or ""))
            except Exception:
                continue
    response_dir = out / "crown-responses"
    if response_dir.exists():
        processed_ids.update(p.stem for p in response_dir.glob("*.json"))
    if not processed_ids:
        raise RuntimeError("No completed Crown capture candidates are available to source-fallback.")

    fallback_dir = out / "totalcorner-default-responses"
    fallback_index_path = out / "totalcorner-default-index.jsonl"
    error_dir = out / "totalcorner-default-errors"
    prior_index = {}
    if fallback_index_path.exists():
        for line in fallback_index_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
                if entry.get("status") != "transport_error":
                    prior_index[str(entry.get("match_id") or "")] = entry
            except Exception:
                continue

    # Count source-priority coverage already secured. Per market, Crown wins;
    # TotalCorner may fill only when its Crown row is absent at/after M5 as-of.
    market_counts = {"AH": {"crown": 0, "totalcorner_default": 0},
                     "OU": {"crown": 0, "totalcorner_default": 0}}
    candidate_by_id = {str(row.get("match_id") or ""): row for row in candidates}
    for mid in processed_ids:
        fixture = candidate_by_id.get(mid)
        forecast = forecasts.get(mid)
        if not fixture or not forecast:
            continue
        asof, kickoff = utc(forecast.get("prediction_asof_utc")), utc(forecast.get("kickoff"))
        if not asof or not kickoff or utc(forecast.get("train_end_utc")) is None or utc(forecast["train_end_utc"]) >= asof:
            continue
        crown_valid = valid_crown_set(crown_rows(out / "crown-responses" / f"{mid}.json", mid), asof, kickoff, zone)
        total_entry = prior_index.get(mid) or {}
        for market in ("AH", "OU"):
            if crown_valid[market]:
                market_counts[market]["crown"] += 1
            elif total_entry.get(f"{market.lower()}_valid_prematch_rows", 0) > 0:
                market_counts[market]["totalcorner_default"] += 1

    state = {"last_start": 0.0}
    attempted = 0
    for fixture in candidates:
        if args.max_requests is not None and attempted >= args.max_requests:
            break
        mid = str(fixture.get("match_id") or "")
        if mid not in processed_ids or mid in prior_index:
            continue
        forecast = forecasts.get(mid)
        if not forecast:
            continue
        asof, kickoff = utc(forecast.get("prediction_asof_utc")), utc(forecast.get("kickoff"))
        train_end = utc(forecast.get("train_end_utc"))
        if not asof or not kickoff or not train_end or train_end >= asof or asof >= kickoff:
            continue
        crown_valid = valid_crown_set(crown_rows(out / "crown-responses" / f"{mid}.json", mid), asof, kickoff, zone)
        missing = [market for market in ("AH", "OU") if not crown_valid[market]
                   and market_counts[market]["crown"] + market_counts[market]["totalcorner_default"] < args.target_market_fixtures]
        if not missing:
            continue
        url = f"{API}/match/odds/{urllib.parse.quote(mid, safe='')}?" + urllib.parse.urlencode({"columns": "asianList,goalList"})
        try:
            payload, receipt, raw_body = request_json(url, token, args.min_interval, state)
            attempted += 1
            match = response_match(payload, fixture, zone) if payload.get("success") == 1 else None
            if match is None:
                entry = {"match_id": mid, "captured_at_utc": utc_now(), "provider": "TotalCorner",
                         "source_endpoint": "/match/odds", "source_bookmaker": "totalcorner_default_NOT_CROWN",
                         "status": "identity_or_api_validation_failed", "response_sha256": receipt.get("response_sha256"),
                         "ah_valid_prematch_rows": 0, "ou_valid_prematch_rows": 0}
                save_json(error_dir / f"{mid}.json", entry)
                with fallback_index_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry, sort_keys=True) + "\n")
                prior_index[mid] = entry
            else:
                ah = valid_rows(match.get("asian_list"), asof, kickoff, zone)
                ou = valid_rows(match.get("goal_list"), asof, kickoff, zone)
                atomic_write(fallback_dir / f"{mid}.json", raw_body)
                entry = {"match_id": mid, "captured_at_utc": utc_now(), "provider": "TotalCorner",
                         "source_endpoint": "/match/odds", "source_bookmaker": "totalcorner_default_NOT_CROWN",
                         "status": "verified_fixture_response", "response_sha256": receipt.get("response_sha256"),
                         "ah_valid_prematch_rows": len(ah), "ou_valid_prematch_rows": len(ou)}
                with fallback_index_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(entry, sort_keys=True) + "\n")
                prior_index[mid] = entry
                for market, eligible in (("AH", ah), ("OU", ou)):
                    if not crown_valid[market] and eligible:
                        market_counts[market]["totalcorner_default"] += 1
        except Exception as exc:
            attempted += 1
            entry = {"match_id": mid, "captured_at_utc": utc_now(), "provider": "TotalCorner",
                     "source_endpoint": "/match/odds", "source_bookmaker": "totalcorner_default_NOT_CROWN",
                     "status": "transport_error", "error_type": type(exc).__name__,
                     "ah_valid_prematch_rows": 0, "ou_valid_prematch_rows": 0}
            save_json(error_dir / f"{mid}.json", entry)
            with fallback_index_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
        if attempted and attempted % 100 == 0:
            summary = {"protocol": "M5_TOTALCORNER_DEFAULT_FALLBACK_PROGRESS_V1", "updated_utc": utc_now(),
                       "candidate_manifest_sha256": digest(manifest_raw), "processed_crown_candidates": len(processed_ids),
                       "attempted_totalcorner_requests": attempted, "source_priority_market_counts": market_counts}
            save_json(out / "totalcorner-default-progress.json", summary)
            print(json.dumps(summary, sort_keys=True), flush=True)
        if all(market_counts[m]["crown"] + market_counts[m]["totalcorner_default"] >= args.target_market_fixtures
               for m in ("AH", "OU")):
            break

    summary = {"protocol": "M5_TOTALCORNER_DEFAULT_FALLBACK_SUMMARY_V1", "finished_utc": utc_now(),
               "candidate_manifest_sha256": digest(manifest_raw), "processed_crown_candidates": len(processed_ids),
               "attempted_totalcorner_requests": attempted, "source_priority_market_counts": market_counts,
               "source_note": "Crown was selected first per fixture-market; TotalCorner /match/odds default values were only eligible to fill missing Crown markets. All raw responses remain private."}
    save_json(out / "totalcorner-default-progress.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--min-interval", type=float, default=3.1)
    parser.add_argument("--target-market-fixtures", type=int, default=10000)
    parser.add_argument("--max-requests", type=int,
                        help="optional per-invocation request cap; rerunning resumes from private indexes")
    args = parser.parse_args()
    if args.min_interval < 2.6:
        raise SystemExit("min-interval must be at least 2.6 seconds")
    if args.max_requests is not None and args.max_requests < 1:
        raise SystemExit("max-requests must be positive")
    run(args)


if __name__ == "__main__":
    main()

