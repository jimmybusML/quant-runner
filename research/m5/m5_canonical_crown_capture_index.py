#!/usr/bin/env python3
"""Normalize the local Crown cache into an M5 forward-quote index.

The shared Mac collector remains the sole network client. This adapter verifies
its live/summary SQLite receipts and raw hashes, then exposes Crown AH and OU
open/close rows to the existing M5 source-union pairing runner. Fixture-level
output must remain outside the public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE_TZ = ZoneInfo("Asia/Shanghai")


def instant(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace(" ", "T").replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SOURCE_TZ)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def zulu(dt):
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def quote_rows(book, market, asof, received, kickoff):
    source_key, price_keys = (("asian", ("home", "away")) if market == "AH"
                              else ("goal", ("over", "under")))
    rows = []
    for kind in ("open", "close"):
        quote = (book.get(source_key) or {}).get(kind)
        if not isinstance(quote, dict):
            continue
        event = instant(quote.get("time"))
        try:
            line = float(quote["line"])
            prices = [float(quote[key]) for key in price_keys]
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if (not event or not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                or any(not math.isfinite(p) or p <= 1 for p in prices)
                or not asof <= event <= received < kickoff):
            continue
        rows.append({"quote_event_utc": zulu(event), "line": line, "prices": prices,
                     "quote_kind": kind})
    return rows


def build_index(forecast_path: Path, database: Path, output_path: Path):
    forecast_raw = forecast_path.read_bytes()
    forecasts = {}
    duplicates = set()
    for line in forecast_raw.decode().splitlines():
        try:
            row = json.loads(line)
            fid = str(row["match_id"])
            if fid in forecasts:
                duplicates.add(fid)
            forecasts[fid] = row
        except (ValueError, KeyError, TypeError):
            continue
    cx = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    captures = cx.execute("""SELECT fixture_id,response_received_at_utc,source_file,
        response_sha256,kickoff_at_utc,prospective_observation
        FROM capture WHERE capture_mode='live' AND data_layer='summary'
        ORDER BY response_received_at_utc""").fetchall()
    stats = Counter()
    chosen = {}
    for capture in captures:
        fid = str(capture["fixture_id"])
        forecast = forecasts.get(fid)
        if not forecast or fid in duplicates:
            stats["no_unique_forecast"] += 1
            continue
        try:
            raw_bytes = Path(capture["source_file"]).read_bytes()
            if hashlib.sha256(raw_bytes).hexdigest() != capture["response_sha256"]:
                stats["response_hash_mismatch"] += 1
                continue
            raw = json.loads(raw_bytes)
        except (OSError, ValueError, TypeError):
            stats["missing_or_invalid_raw_response"] += 1
            continue
        data = raw.get("data") if isinstance(raw, dict) else None
        match = data[0] if isinstance(data, list) and len(data) == 1 else data if isinstance(data, dict) else None
        if raw.get("success") not in (1, True, "1") or not isinstance(match, dict):
            stats["invalid_api_response"] += 1
            continue
        if str(match.get("id")) != fid:
            stats["fixture_id_mismatch"] += 1
            continue
        kickoff = instant(forecast.get("kickoff_utc"))
        response_kickoff = instant(match.get("start"))
        asof = instant(forecast.get("prediction_asof_utc"))
        received = instant(capture["response_received_at_utc"])
        if (not kickoff or not asof or not received or response_kickoff != kickoff
                or instant(capture["kickoff_at_utc"]) != kickoff
                or any(match.get(key) != forecast.get(field)
                       for key, field in (("h", "home"), ("a", "away"), ("l", "league")))
                or not asof < kickoff or received >= kickoff or not capture["prospective_observation"]):
            stats["identity_or_time_mismatch"] += 1
            continue
        book = next((b for b in match.get("bookmakers", [])
                     if str(b.get("slug", "")).lower() == "crown"), None)
        if not isinstance(book, dict):
            stats["no_crown_book"] += 1
            continue
        ah = quote_rows(book, "AH", asof, received, kickoff)
        ou = quote_rows(book, "OU", asof, received, kickoff)
        entry = {
            "status": "verified_fixture_response", "match_id": fid,
            "source_bookmaker": "Crown", "captured_at_utc": zulu(received),
            "quote_event_asof_utc": forecast["prediction_asof_utc"],
            "kickoff_utc": forecast["kickoff_utc"], "league": forecast["league"],
            "home": forecast["home"], "away": forecast["away"],
            "response_sha256": capture["response_sha256"],
            "ah_qualified": bool(ah), "ou_qualified": bool(ou),
            "ah_eligible_rows": ah, "ou_eligible_rows": ou,
        }
        old = chosen.get(fid)
        if old is None or entry["captured_at_utc"] > old["captured_at_utc"]:
            chosen[fid] = entry
        stats["verified_live_fixture_responses"] += 1
        stats["AH_quote_rows"] += len(ah)
        stats["OU_quote_rows"] += len(ou)
    cx.close()
    output_path = output_path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if output_path == repo or repo in output_path.parents:
        raise ValueError("fixture-level capture index must remain private")
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_path.parent, 0o700)
    rows = sorted(chosen.values(), key=lambda x: (x["captured_at_utc"], x["match_id"]))
    encoded = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                      for row in rows).encode()
    tmp = output_path.with_name(output_path.name + ".tmp")
    tmp.write_bytes(encoded)
    os.chmod(tmp, 0o600)
    os.replace(tmp, output_path)
    report = {"generated_utc": zulu(datetime.now(timezone.utc)),
              "forecast_sha256": hashlib.sha256(forecast_raw).hexdigest(),
              "capture_index_sha256": hashlib.sha256(encoded).hexdigest(),
              "verified_live_fixture_responses": len(rows),
              "AH_eligible_fixture_markets": sum(bool(x["ah_eligible_rows"]) for x in rows),
              "OU_eligible_fixture_markets": sum(bool(x["ou_eligible_rows"]) for x in rows),
              "audit_counts": dict(stats), "time_rule": "forecast_asof <= quote_event <= response_received < kickoff",
              "capture_mode": "live", "source": "Crown"}
    print(json.dumps(report, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_index(args.forecasts, args.database, args.output)


if __name__ == "__main__":
    main()
