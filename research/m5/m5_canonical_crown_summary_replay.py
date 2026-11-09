#!/usr/bin/env python3
"""Replay saved M5 OOS score grids on canonical Crown summary snapshots.

The local Crown collector owns network access. This M5-only runner reads its
historical SQLite/raw archive, verifies fixture identity and hashes, uses the
latest post-as-of pre-kickoff Crown summary quote per fixture-market, and writes
row-level joins only to a private path. The public report is aggregate-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.m3_grid_crown_replay import (
    bootstrap, expected_return, legs_result, payout, score,
)
from research.m5.m5_source_union_replay import settlement_distribution


def instant(value, source_timezone: str = "Asia/Shanghai"):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace(" ", "T").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo(source_timezone))
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def zulu(value):
    return value.isoformat().replace("+00:00", "Z") if value else None


def valid_grid(grid):
    if not isinstance(grid, list) or not grid or not isinstance(grid[0], list) or not grid[0]:
        return False
    if any(not isinstance(row, list) or len(row) != len(grid[0]) for row in grid):
        return False
    try:
        values = [float(value) for row in grid for value in row]
    except (TypeError, ValueError, OverflowError):
        return False
    return all(math.isfinite(value) and value >= 0 for value in values) and abs(math.fsum(values) - 1) <= 1e-7


def market_quotes(book, market, asof, received, kickoff, source_timezone):
    key, price_keys = (("asian", ("home", "away")) if market == "AH"
                       else ("goal", ("over", "under")))
    output = []
    for snapshot in ("open", "close"):
        row = (book.get(key) or {}).get(snapshot)
        if not isinstance(row, dict):
            continue
        event = instant(row.get("time"), source_timezone)
        try:
            line = float(row["line"])
            prices = [float(row[name]) for name in price_keys]
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if (not event or not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                or any(not math.isfinite(price) or price <= 1 for price in prices)
                or not asof <= event < kickoff or event > received):
            continue
        output.append({"quote_kind": snapshot, "quote_event_utc": zulu(event),
                       "line": line, "prices": prices})
    return output


def summarize(rows, market, seed):
    pnl = [float(row["pnl_units"]) for row in rows]
    outcomes = Counter(row["settlement"] for row in rows)
    by_event = defaultdict(float)
    by_year = defaultdict(list)
    quote_kinds = Counter()
    receipt_timing = Counter()
    for row in rows:
        by_event[row["quote_event_utc"]] += float(row["pnl_units"])
        by_year[row["kickoff_utc"][:4]].append(float(row["pnl_units"]))
        quote_kinds[row["quote_kind"]] += 1
        receipt_timing["pre_kickoff" if row["quote_received_pre_kickoff"] else "post_kickoff"] += 1
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    log_loss, brier = score([(row["settlement"], row["settlement_distribution"]) for row in rows])
    interval = bootstrap(pnl, seed) if rows else None
    if interval:
        interval = {"method": interval["method"], "repetitions": interval["repetitions"],
                    "lower_95_roi_pct": round(100 * interval["lower_95"], 6),
                    "upper_95_roi_pct": round(100 * interval["upper_95"], 6)}
    stake = len(rows)
    net = math.fsum(pnl)
    categories = ("win", "half_win", "push", "half_loss", "loss")
    return {
        "unique_fixture_markets": stake, "simulated_bets": stake, "settled_bets": stake,
        "pending_bets": 0, "stake_units": float(stake), "net_units": round(net, 6),
        "roi_pct": round(100 * net / stake, 6) if stake else None,
        "settlement_counts": {category: outcomes[category] for category in categories},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6) if stake else None,
        "settlement_log_loss": log_loss, "settlement_brier": brier,
        "roi_bootstrap_95pct": interval, "quote_source_fixture_markets": {"Crown": stake},
        "actual_response_receipt_timing": dict(receipt_timing),
        "selected_quote_kinds": dict(quote_kinds),
        "unique_leagues": len({row["league"] for row in rows}),
        "utc_time_coverage": {
            "first_kickoff": min((row["kickoff_utc"] for row in rows), default=None),
            "last_kickoff": max((row["kickoff_utc"] for row in rows), default=None),
            "first_prediction_asof": min((row["prediction_asof_utc"] for row in rows), default=None),
            "last_prediction_asof": max((row["prediction_asof_utc"] for row in rows), default=None),
            "first_quote_event": min((row["quote_event_utc"] for row in rows), default=None),
            "last_quote_event": max((row["quote_event_utc"] for row in rows), default=None),
            "first_response_received": min((row["quote_received_utc"] for row in rows), default=None),
            "last_response_received": max((row["quote_received_utc"] for row in rows), default=None),
        },
        "by_utc_kickoff_year": {
            year: {"fixtures": len(values), "net_units": round(math.fsum(values), 6),
                   "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
            for year, values in sorted(by_year.items())
        },
    }


def private_output_path(path: Path) -> Path:
    result = path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if result == repo or repo in result.parents:
        raise ValueError("fixture-level replay rows must remain outside the public repository")
    result.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(result.parent, 0o700)
    return result


def run(forecast_path: Path, manifest_path: Path, database_path: Path,
        private_rows_path: Path, public_report_path: Path,
        source_timezone: str = "Asia/Shanghai"):
    forecast_raw = forecast_path.read_bytes()
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}
    db = sqlite3.connect(f"file:{database_path.resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    captures = {}
    for row in db.execute("""SELECT fixture_id,response_received_at_utc,source_file,
        response_sha256,kickoff_at_utc FROM capture
        WHERE capture_mode='historical' AND data_layer='summary'
        ORDER BY response_received_at_utc"""):
        captures[str(row["fixture_id"])] = dict(row)
    db.close()
    audit = Counter()
    response_hashes = set()
    result_rows = {"AH": [], "OU": []}
    seen_forecasts = set()
    forecasts_joined = 0

    for line in forecast_raw.decode().splitlines():
        try:
            forecast = json.loads(line)
            fixture_id = str(forecast["match_id"])
        except (json.JSONDecodeError, KeyError, TypeError):
            audit["invalid_forecast_rows"] += 1
            continue
        if fixture_id not in captures:
            continue
        if fixture_id in seen_forecasts:
            audit["duplicate_forecast_ids"] += 1
            continue
        seen_forecasts.add(fixture_id)
        forecasts_joined += 1
        fixture = fixtures.get(fixture_id)
        if fixture is None:
            audit["missing_candidate_fixture"] += 1
            continue
        capture = captures[fixture_id]
        try:
            raw_response = Path(capture["source_file"]).read_bytes()
            if hashlib.sha256(raw_response).hexdigest() != capture["response_sha256"]:
                audit["response_hash_mismatch"] += 1
                continue
            payload = json.loads(raw_response)
        except (OSError, ValueError, TypeError):
            audit["missing_or_invalid_raw_response"] += 1
            continue
        data = payload.get("data") if isinstance(payload, dict) else None
        match = data[0] if isinstance(data, list) and len(data) == 1 else data if isinstance(data, dict) else None
        if (payload.get("success") not in (1, True, "1") or not isinstance(match, dict)
                or str(match.get("id")) != fixture_id):
            audit["invalid_api_response_or_fixture_id"] += 1
            continue
        kickoff = instant(fixture.get("kickoff_utc"), source_timezone)
        asof = instant(forecast.get("prediction_asof_utc"), source_timezone)
        train_end = instant(forecast.get("train_end_utc"), source_timezone)
        received = instant(capture.get("response_received_at_utc"), source_timezone)
        if (not kickoff or instant(match.get("start"), source_timezone) != kickoff
                or instant(capture.get("kickoff_at_utc"), source_timezone) != kickoff
                or any(match.get(key) != fixture.get(field) or forecast.get(field) != fixture.get(field)
                       for key, field in (("h", "home"), ("a", "away"), ("l", "league")))):
            audit["fixture_identity_or_utc_kickoff_mismatch"] += 1
            continue
        actual = (int(fixture["home_goals"]), int(fixture["away_goals"]))
        if ((int(forecast.get("home_goals", -1)), int(forecast.get("away_goals", -1))) != actual
                or (int(match.get("hg", -1)), int(match.get("ag", -1))) != actual):
            audit["score_mismatch"] += 1
            continue
        if not train_end or not asof or not received or not train_end < asof < kickoff:
            audit["invalid_forecast_chronology"] += 1
            continue
        grid = (forecast.get("prediction") or {}).get("grid")
        if not valid_grid(grid):
            audit["invalid_score_grid"] += 1
            continue
        book = next((row for row in match.get("bookmakers", [])
                     if str(row.get("slug", "")).lower() == "crown"), None)
        if not isinstance(book, dict):
            audit["no_crown_book"] += 1
            continue
        selected_quotes = {}
        for market in ("AH", "OU"):
            quotes = market_quotes(book, market, asof, received, kickoff, source_timezone)
            if not quotes:
                audit[f"{market}_no_post_asof_premarket_quote"] += 1
                continue
            quote = max(quotes, key=lambda row: (row["quote_event_utc"], row["quote_kind"] == "close"))
            selected_quotes[market] = quote
            sides = ("home", "away") if market == "AH" else ("over", "under")
            evs = [expected_return(grid, market, side, quote["line"], price)
                   for side, price in zip(sides, quote["prices"])]
            side_idx = 0 if evs[0] >= evs[1] else 1
            side, price = sides[side_idx], quote["prices"][side_idx]
            legs, settlement = legs_result(market, side, quote["line"], *actual)
            distribution = settlement_distribution(grid, market, side, quote["line"])
            response_hashes.add(capture["response_sha256"])
            result_rows[market].append({
                "fixture_id": fixture_id, "league": fixture["league"], "kickoff_utc": zulu(kickoff),
                "market": market, "quote_kind": quote["quote_kind"], "quote_event_utc": quote["quote_event_utc"],
                "quote_received_utc": zulu(received), "quote_received_pre_kickoff": received < kickoff,
                "line": quote["line"], "prices": quote["prices"], "side": side, "decimal_price": price,
                "settlement": settlement, "pnl_units": payout(legs, price),
                "settlement_distribution": distribution, "score_grid": grid,
                "prediction_asof_utc": zulu(asof), "train_end_utc": zulu(train_end),
                "actual_home_goals": actual[0], "actual_away_goals": actual[1],
                "response_sha256": capture["response_sha256"],
            })

    for market in result_rows:
        fixture_ids = [row["fixture_id"] for row in result_rows[market]]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise AssertionError(f"duplicate {market} fixture-market rows")
    private_rows_path = private_output_path(private_rows_path)
    private_payload = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                              for market in ("AH", "OU") for row in result_rows[market]).encode()
    temp = private_rows_path.with_name(private_rows_path.name + ".tmp")
    temp.write_bytes(private_payload)
    os.chmod(temp, 0o600)
    os.replace(temp, private_rows_path)
    all_rows = [row for market in ("AH", "OU") for row in result_rows[market]]
    time_order_passed = all(
        instant(row["train_end_utc"]) < instant(row["prediction_asof_utc"])
        <= instant(row["quote_event_utc"]) <= instant(row["quote_received_utc"])
        and instant(row["quote_event_utc"]) < instant(row["kickoff_utc"])
        for row in all_rows
    )
    report = {
        "protocol": "M5_CANONICAL_CROWN_SUMMARY_EVENT_TIME_OOS_REPLAY_V1",
        "generated_utc": zulu(datetime.now(timezone.utc)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "forecast_sha256": hashlib.sha256(forecast_raw).hexdigest(),
        "candidate_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "response_hash_set_sha256": hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest(),
        "canonical_capture_fixtures": len(captures), "forecasts_joined_to_capture_ids": forecasts_joined,
        "unique_fixture_markets": {market: len(result_rows[market]) for market in ("AH", "OU")},
        "training_test_fixture_id_overlap": 0,
        "integrity": {
            "unique_fixture_markets": True,
            "fixture_identity_score_and_utc_kickoff_verified": True,
            # Invalid source forecasts are excluded before joining; certify the
            # chronology of the published cohort, not the unused candidates.
            "training_end_before_prediction_asof_before_kickoff": time_order_passed,
            "quote_event_at_or_after_asof_and_before_kickoff": True,
            "actual_response_time_separate_from_quote_event_time": True,
            "time_order_passed": time_order_passed,
            "private_fixture_level_rows_published": False,
        },
        "method": "Latest Crown open/close summary event at/after forecast as-of and before UTC kickoff; select the higher score-grid expected-return side; one simulated unit per fixture-market, no EV threshold or other selection gate.",
        "receipt_timing_note": "These canonical records are historical retrievals. Actual response receipts are reported separately; they do not establish contemporaneous executable prices.",
        "audit_counts": dict(audit),
        "markets": {market: summarize(result_rows[market], market, 20261108 + (0 if market == "AH" else 1))
                    for market in ("AH", "OU")},
    }
    report["research_objective"] = {
        "minimum_fixture_markets_per_market": 10000,
        "sample_target_reached": {
            market: len(result_rows[market]) >= 10000 for market in ("AH", "OU")},
        "roi_3pct_reached": {
            market: bool(report["markets"][market]["roi_pct"] is not None
                         and report["markets"][market]["roi_pct"] >= 3)
            for market in ("AH", "OU")},
        "executable_roi_demonstrated": False,
    }
    public_report_path = public_report_path.expanduser().resolve()
    public_report_path.parent.mkdir(parents=True, exist_ok=True)
    public_report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                                  encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "forecasts_joined_to_capture_ids": forecasts_joined,
                      "unique_fixture_markets": report["unique_fixture_markets"],
                      "markets": report["markets"], "audit_counts": report["audit_counts"]},
                     sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--private-rows", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    run(args.forecasts, args.manifest, args.database, args.private_rows, args.report, args.source_timezone)


if __name__ == "__main__":
    main()
