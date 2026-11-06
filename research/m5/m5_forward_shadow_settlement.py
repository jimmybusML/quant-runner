#!/usr/bin/env python3
"""Capture verified M5 forward FT results and settle the private shadow cohort.

This M5-only utility reads the immutable private forecast/quote pairs, fetches
TotalCorner /match/view outcomes after kickoff, and writes raw scores plus
fixture-level settlements only outside the public repository. The public
summary contains aggregate metrics and input hashes only.
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

from research.m5.crown_historical_capture import (
    API, atomic_write, ensure_private_destination, local_to_utc,
    request_json, token_value, utc_now,
)
from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout

FT_STATUSES = {"full", "finished", "ft", "complete", "completed", "ended", "aet"}
UTC = timezone.utc


def instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def response_match(payload: dict, match_id: str) -> dict:
    if not isinstance(payload, dict) or payload.get("success") != 1:
        raise ValueError("provider response not successful")
    data = payload.get("data")
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    found = [row for row in rows if isinstance(row, dict) and str(row.get("id") or "") == str(match_id)]
    if len(found) != 1:
        raise ValueError("provider match identity unresolved")
    return found[0]


def verified_final(payload: dict, fixture: dict, received_utc: str, response_sha256: str,
                   source_timezone: str = "Asia/Shanghai") -> dict | None:
    """Verify result identity, exact UTC kickoff, FT status and post-kickoff receipt."""
    row = response_match(payload, str(fixture["match_id"]))
    if (row.get("h") != fixture.get("home") or row.get("a") != fixture.get("away")
            or row.get("l") != fixture.get("league")):
        raise ValueError("provider fixture identity mismatch")
    kickoff = instant(fixture.get("kickoff_utc"))
    provider_kickoff = local_to_utc(row.get("start"), ZoneInfo(source_timezone))
    if kickoff is None or provider_kickoff is None or kickoff != provider_kickoff:
        raise ValueError("provider UTC kickoff mismatch")
    received = instant(received_utc)
    if received is None or received <= kickoff:
        raise ValueError("full-time result was not actually received after kickoff")
    if str(row.get("status") or "").strip().lower() not in FT_STATUSES:
        return None

    def score(key):
        value = row.get(key)
        if isinstance(value, bool) or not str(value).isdigit():
            raise ValueError("invalid full-time score")
        return int(value)

    return {"home_goals": score("hg"), "away_goals": score("ag"),
            "observed_at_utc": received.isoformat().replace("+00:00", "Z"),
            "response_sha256": response_sha256}


def settle_pair(pair: dict, result: dict) -> dict:
    market = pair["market"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    grid, line, prices = pair["score_grid"], float(pair["line"]), pair["prices"]
    evs = [expected_return(grid, market, side, line, float(price))
           for side, price in zip(sides, prices)]
    side_index = 0 if evs[0] >= evs[1] else 1
    side, price = sides[side_index], float(prices[side_index])
    legs, category = legs_result(market, side, line,
                                 int(result["home_goals"]), int(result["away_goals"]))
    net = payout(legs, price)
    return {"match_id": pair["match_id"], "market": market, "source": pair["source"],
            "kickoff_utc": pair["kickoff_utc"], "line": line, "prices": prices,
            "quote_event_utc": pair["quote_event_utc"],
            "quote_received_utc": pair["quote_received_utc"],
            "prediction_asof_utc": pair["prediction_asof_utc"],
            "train_end_utc": pair["train_end_utc"],
            "home_goals": int(result["home_goals"]), "away_goals": int(result["away_goals"]),
            "result_observed_at_utc": result["observed_at_utc"],
            "result_response_sha256": result["response_sha256"],
            "side": side, "decimal_price": price, "settlement": category,
            "pnl_units": net, "stake_units": 1.0}


def summarize(rows: list[dict], market: str, paired_rows: list[dict]) -> dict:
    selected = [row for row in rows if row["market"] == market]
    paired = [row for row in paired_rows if row["market"] == market]
    counts = Counter(row["settlement"] for row in selected)
    sources = Counter(row["source"] for row in selected)
    paired_sources = Counter(row["source"] for row in paired)
    net = math.fsum(float(row["pnl_units"]) for row in selected)
    ordered = sorted(selected, key=lambda row: (row["kickoff_utc"], row["match_id"]))
    equity = peak = drawdown = 0.0
    for row in ordered:
        equity += float(row["pnl_units"])
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    n, total = len(selected), len(paired)
    return {"unique_fixture_markets": total, "simulated_bets": total,
            "settled_bets": n, "pending_bets": total - n,
            "total_stake_units": float(total), "settled_stake_units": float(n),
            "settlement_counts": {key: counts[key] for key in
                                  ("win", "half_win", "push", "half_loss", "loss")},
            "net_units": round(net, 6),
            "roi_pct": round(100 * net / total, 6) if total and n == total else None,
            "realized_roi_on_settled_stake_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_units_by_kickoff": round(drawdown, 6) if n else None,
            "paired_source_fixture_markets": dict(sorted(paired_sources.items())),
            "settled_source_fixture_markets": dict(sorted(sources.items()))}


def run(private_dir: Path, pairs_path: Path, summary_output: Path,
        source_timezone: str = "Asia/Shanghai", min_interval: float = 3.1) -> dict:
    if min_interval < 2.6:
        raise ValueError("min_interval must be at least 2.6 seconds")
    root = ensure_private_destination(private_dir)
    pairs_raw = pairs_path.read_bytes()
    pairs = [json.loads(line) for line in pairs_raw.decode().splitlines() if line.strip()]
    if len({(row["match_id"], row["market"]) for row in pairs}) != len(pairs):
        raise ValueError("duplicate fixture-market in paired source cohort")

    shadow = root / "forward-shadow"
    raw_dir = shadow / "result-responses"
    index_path = shadow / "verified-ft-index.jsonl"
    events_path = shadow / "settled-pairs.jsonl"
    raw_dir.mkdir(parents=True, exist_ok=True)
    token = token_value(None)
    state = {"last_start": 0.0}
    now = datetime.now(UTC)
    fixtures = {}
    for row in pairs:
        fixture = {key: row[key] for key in
                   ("match_id", "league", "home", "away", "kickoff_utc")}
        prior = fixtures.get(str(row["match_id"]))
        if prior and prior != fixture:
            raise ValueError("conflicting fixture identities inside paired cohort")
        fixtures[str(row["match_id"])] = fixture

    old_results = {}
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") == "verified_ft":
                mid = str(row.get("match_id") or "")
                prior = old_results.get(mid)
                if prior and (prior.get("home_goals"), prior.get("away_goals")) != (
                        row.get("home_goals"), row.get("away_goals")):
                    raise ValueError("conflicting previously verified M5 FT records")
                old_results[mid] = row

    counts = Counter()
    hashes = set()
    for mid, fixture in sorted(fixtures.items(), key=lambda item: item[1]["kickoff_utc"]):
        if mid in old_results:
            counts["already_verified_ft"] += 1
            continue
        kickoff = instant(fixture["kickoff_utc"])
        if kickoff is None or kickoff >= now:
            counts["not_yet_kicked_off"] += 1
            continue
        import urllib.parse
        url = f"{API}/match/view/{urllib.parse.quote(mid, safe='')}"
        try:
            payload, meta, raw = request_json(url, token, min_interval, state)
            received = meta.get("received_at_utc")
            received_dt = instant(received)
            raw_path = raw_dir / f"{mid}-{received_dt.strftime('%Y%m%dT%H%M%S%fZ')}.json"
            atomic_write(raw_path, raw)
            result = verified_final(payload, fixture, received,
                                    str(meta.get("response_sha256") or ""), source_timezone)
            if result is None:
                entry = {**fixture, "status": "not_ft_at_receipt",
                         "captured_at_utc": received,
                         "response_sha256": meta.get("response_sha256"),
                         "raw_response_relative_path": str(raw_path.relative_to(shadow))}
                counts["not_ft_at_receipt"] += 1
            else:
                entry = {**fixture, **result, "status": "verified_ft",
                         "captured_at_utc": result["observed_at_utc"],
                         "raw_response_relative_path": str(raw_path.relative_to(shadow))}
                counts["verified_ft"] += 1
                hashes.add(str(result["response_sha256"]))
            with index_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        except Exception as exc:
            entry = {**fixture, "status": "verification_error",
                     "error_type": type(exc).__name__, "captured_at_utc": utc_now()}
            with index_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
            counts["verification_error"] += 1

    verified = dict(old_results)
    for line in index_path.read_text(encoding="utf-8").splitlines() if index_path.exists() else []:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("status") == "verified_ft":
            verified[str(row["match_id"])] = row

    settled = []
    for pair in pairs:
        result = verified.get(str(pair["match_id"]))
        if result:
            if (result.get("home"), result.get("away"), result.get("league"),
                    instant(result.get("kickoff_utc"))) != (
                    pair.get("home"), pair.get("away"), pair.get("league"),
                    instant(pair.get("kickoff_utc"))):
                raise ValueError("verified FT identity does not match paired forecast")
            settled.append(settle_pair(pair, result))
    settled_keys = {(row["match_id"], row["market"]) for row in settled}
    hashes = {str(row.get("response_sha256")) for row in verified.values()
              if row.get("response_sha256")}
    with events_path.open("w", encoding="utf-8") as stream:
        for row in settled:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    report = {"protocol": "M5_FORWARD_SHADOW_SETTLEMENT_V1",
              "generated_utc": utc_now(),
              "paired_input_sha256": hashlib.sha256(pairs_raw).hexdigest(),
              "verified_result_response_hash_set_sha256": hashlib.sha256(
                  "\n".join(sorted(hashes)).encode()).hexdigest(),
              "fixture_count": len(fixtures), "settled_fixture_markets": len(settled_keys),
              "pending_fixture_markets": len(pairs) - len(settled_keys),
              "capture_counts": dict(counts),
              "markets": {market: summarize(settled, market, pairs) for market in ("AH", "OU")},
              "method": "One 1U shadow bet per unique pregame-paired fixture-market; choose the higher M5 model expected return at the observed line and two prices; Asian quarter/half-line settlement; no extra filter. Final cohort ROI is null until every simulated bet settles; settled-only ROI is reported separately.",
              "timing": "FT scores accepted only from verified TotalCorner /match/view responses received after UTC kickoff; raw responses and row-level settlements remain private.",
              "production_or_telegram_changes": False}
    summary_output = summary_output.expanduser().resolve()
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "fixture_count": report["fixture_count"],
                      "settled_fixture_markets": report["settled_fixture_markets"],
                      "pending_fixture_markets": report["pending_fixture_markets"],
                      "markets": report["markets"], "summary_output": str(summary_output)},
                     ensure_ascii=False, sort_keys=True))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--min-interval", type=float, default=3.1)
    args = parser.parse_args()
    run(args.private_dir, args.pairs, args.summary_output, args.source_timezone, args.min_interval)


if __name__ == "__main__":
    main()
