#!/usr/bin/env python3
"""Replay frozen M5 OOS forecasts against the local canonical Crown archive.

All fixture-level joins stay in a private local file. The public artifact holds
only aggregate metrics and SHA-256 provenance. Historical response receipt time
is never confused with a quote's source event time.
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
import numpy as np

from research.m5.m3_grid_crown_replay import (
    expected_return, legs_result, payout, score,
)
from research.m5.m5_canonical_crown_summary_replay import (
    instant, market_quotes, settlement_distribution, valid_grid, zulu,
)
from research.m5.m5_canonical_crown_movement_replay import (
    normalized_line, valid_prices,
)

MARKETS = {
    "AH": {"sides": ("home", "away"), "price_keys": ("home", "away")},
    "OU": {"sides": ("over", "under"), "price_keys": ("over", "under")},
}
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def local_event(value: object, zone: ZoneInfo) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc)
    candidates = set()
    for fold in (0, 1):
        candidate = parsed.replace(tzinfo=zone, fold=fold)
        if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == parsed:
            candidates.add(candidate.astimezone(timezone.utc))
    return next(iter(candidates)) if len(candidates) == 1 else None


def summary_as_movement_format(book: dict, market: str) -> list[dict]:
    key = "asian" if market == "AH" else "goal"
    price_keys = MARKETS[market]["price_keys"]
    rows = []
    for kind in ("open", "close"):
        row = (book.get(key) or {}).get(kind)
        if isinstance(row, dict):
            rows.append({"quote_kind": kind, "line": row.get("line"),
                         "prices": [row.get(price_keys[0]), row.get(price_keys[1])],
                         "time": row.get("time")})
    return rows


def parse_summary(book: dict, market: str, asof: datetime, kickoff: datetime,
                  received: datetime, zone_name: str) -> list[dict]:
    price_keys = MARKETS[market]["price_keys"]
    # Use the shared strict summary parser, which checks UTC and decimal odds.
    parsed = market_quotes(book, market, asof, received, kickoff, zone_name)
    for row in parsed:
        row["event"] = instant(row["quote_event_utc"])
        row["source"] = "summary"
    return parsed


def parse_movement(book: dict, market: str, asof: datetime, kickoff: datetime,
                   zone_name: str) -> list[dict]:
    key = "asian_list" if market == "AH" else "goal_list"
    zone = ZoneInfo(zone_name)
    best = None
    for index, row in enumerate(book.get(key) or []):
        if (not isinstance(row, list) or len(row) != 8
                or row[0] is not None or row[7] not in (0, "0", False)):
            continue
        event = local_event(row[4], zone)
        line = normalized_line(row[1])
        prices = valid_prices(row[2], row[3])
        if not event or not asof < event < kickoff or line is None or prices is None:
            continue
        candidate = {"event": event, "line": line, "prices": prices,
                     "sequence": index, "source": "movement"}
        if best is None or (event, index) > (best["event"], best["sequence"]):
            best = candidate
    return [best] if best else []


def pnl_record(grid: list[list[float]], market: str, quote: dict,
               actual: tuple[int, int]) -> dict:
    sides = MARKETS[market]["sides"]
    evs = [expected_return(grid, market, side, quote["line"], price)
           for side, price in zip(sides, quote["prices"])]
    chosen = 0 if evs[0] >= evs[1] else 1
    side, price = sides[chosen], quote["prices"][chosen]
    legs, category = legs_result(market, side, quote["line"], *actual)
    return {"pnl_units": payout(legs, price), "category": category,
            "distribution": settlement_distribution(grid, market, side, quote["line"]),
            "event_utc": zulu(quote["event"]), "source_layer": quote["source"],
            "line": float(quote["line"]), "price": float(price)}


def bootstrap_roi(values: list[float], seed: int, repetitions: int = 10000) -> dict | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    n = len(array)
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions, dtype=float)
    offset = 0
    while offset < repetitions:
        size = min(200, repetitions - offset)
        indices = rng.integers(0, n, size=(size, n))
        means[offset:offset + size] = array[indices].mean(axis=1)
        offset += size
    low, high = np.quantile(means, [0.025, 0.975], method="linear")
    return {"method": "fixture bootstrap", "repetitions": repetitions,
            "lower_95_roi_pct": round(100 * float(low), 6),
            "upper_95_roi_pct": round(100 * float(high), 6)}


def summarize(rows: list[dict], seed: int) -> dict:
    n = len(rows)
    net = math.fsum(float(row["pnl_units"]) for row in rows)
    outcomes = Counter(row["category"] for row in rows)
    by_event = defaultdict(float)
    by_year = defaultdict(list)
    for row in rows:
        by_event[row["event_utc"]] += float(row["pnl_units"])
        by_year[row["kickoff_utc"][:4]].append(float(row["pnl_units"]))
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    ll, brier = score([(row["category"], row["distribution"]) for row in rows])
    interval = bootstrap_roi([float(row["pnl_units"]) for row in rows], seed)
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "net_units": round(net, 6),
        "roi_pct": round(100 * net / n, 6) if n else None,
        "settlement_counts": {key: outcomes[key] for key in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6) if n else None,
        "settlement_log_loss": ll, "settlement_brier": brier,
        "roi_bootstrap_95pct": interval,
        "by_utc_kickoff_year": {
            year: {"fixtures": len(values), "net_units": round(math.fsum(values), 6),
                   "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
            for year, values in sorted(by_year.items())},
    }


def private_path(path: Path, repo: Path) -> Path:
    out = path.expanduser().resolve()
    if out == repo or repo in out.parents:
        raise ValueError("fixture-level replay rows must remain outside the public repository")
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(out.parent, 0o700)
    return out


def run(forecast_path: Path, manifest_path: Path, database_path: Path,
        private_rows_path: Path, public_path: Path,
        source_timezone: str = "Asia/Shanghai") -> dict:
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}
    db = sqlite3.connect(f"file:{database_path.resolve()}?mode=ro", uri=True, timeout=120)
    db.row_factory = sqlite3.Row
    capture_rows = db.execute("""SELECT capture_key,fixture_id,data_layer,capture_mode,
        response_received_at_utc,source_file,response_sha256,kickoff_at_utc,status
        FROM capture WHERE data_layer IN ('summary','movement') AND status='QUOTES_SAVED'
        ORDER BY response_received_at_utc""").fetchall()
    captures = {}
    for row in capture_rows:
        captures.setdefault(str(row["fixture_id"]), {})[row["data_layer"]] = dict(row)
    db.close()

    forecasts = {}
    duplicate_forecasts = set()
    forecast_total_count = 0
    forecast_digest = hashlib.sha256()
    with forecast_path.open("rb") as stream:
        for raw_line in stream:
            forecast_digest.update(raw_line)
            try:
                row = json.loads(raw_line)
                fid = str(row["match_id"])
                forecast_total_count += 1
                if fid not in captures:
                    continue
                if fid in forecasts:
                    duplicate_forecasts.add(fid)
                else:
                    forecasts[fid] = row
            except (ValueError, KeyError, TypeError):
                continue
    for fid in duplicate_forecasts:
        forecasts.pop(fid, None)
    captures = {fid: layers for fid, layers in captures.items() if fid in forecasts}

    zone = ZoneInfo(source_timezone)
    evaluated = {market: {"summary": {}, "movement": {}, "latest_any_layer": {}}
                 for market in MARKETS}
    receipt_counts = Counter()
    audit = Counter()
    response_hashes = set()
    for fid, layers in captures.items():
        forecast, fixture = forecasts[fid], fixtures.get(fid)
        if not fixture:
            audit["missing_candidate_fixture"] += 1
            continue
        kickoff = instant(forecast.get("kickoff"))
        asof = instant(forecast.get("prediction_asof_utc"))
        train_end = instant(forecast.get("train_end_utc"))
        actual = (int(fixture["home_goals"]), int(fixture["away_goals"]))
        grid = (forecast.get("prediction") or {}).get("grid")
        if (not kickoff or not asof or not train_end or not train_end < asof < kickoff
                or forecast.get("kickoff") != fixture.get("kickoff_utc")
                or forecast.get("home") != fixture.get("home")
                or forecast.get("away") != fixture.get("away")
                or forecast.get("league") != fixture.get("league")
                or (int(forecast.get("home_goals", -1)), int(forecast.get("away_goals", -1))) != actual
                or not valid_grid(grid)):
            audit["forecast_manifest_or_chronology_mismatch"] += 1
            continue
        per_market_quotes = {market: [] for market in MARKETS}
        valid_layers = 0
        for layer, capture in layers.items():
            if capture["capture_mode"] not in ("historical", "live"):
                continue
            try:
                raw = Path(capture["source_file"]).read_bytes()
                if sha(raw) != capture["response_sha256"]:
                    audit["raw_response_sha_mismatch"] += 1
                    continue
                payload = json.loads(raw)
                data = payload.get("data") if isinstance(payload, dict) else None
                matches = ([item for item in data if isinstance(item, dict) and str(item.get("id")) == fid]
                           if isinstance(data, list) else [data] if isinstance(data, dict) and str(data.get("id")) == fid else [])
                if payload.get("success") not in (1, True, "1") or len(matches) != 1:
                    audit["response_identity_invalid"] += 1
                    continue
                match = matches[0]
                if ((match.get("h"), match.get("a"), match.get("l")) !=
                    (fixture["home"], fixture["away"], fixture["league"])):
                    audit["team_or_league_mismatch"] += 1
                    continue
                if local_event(match.get("start"), zone) != kickoff or instant(capture["kickoff_at_utc"]) != kickoff:
                    audit["kickoff_mismatch"] += 1
                    continue
                score_pair = (int(match.get("hg", -1)), int(match.get("ag", -1)))
                if score_pair != actual:
                    audit["score_mismatch"] += 1
                    continue
                books = [book for book in match.get("bookmakers", [])
                         if isinstance(book, dict) and str(book.get("slug", "")).lower() == "crown"]
                if len(books) != 1:
                    audit["crown_book_missing_or_ambiguous"] += 1
                    continue
                received = instant(capture["response_received_at_utc"])
                if not received:
                    audit["receipt_time_missing"] += 1
                    continue
                receipt_counts["pre_kickoff" if received < kickoff else "post_kickoff"] += 1
                response_hashes.add(capture["response_sha256"])
                book = books[0]
                valid_layers += 1
                for market in MARKETS:
                    quotes = (parse_movement(book, market, asof, kickoff, source_timezone)
                              if layer == "movement" else
                              parse_summary(book, market, asof, kickoff, received, source_timezone))
                    # Historical events may be in a fetched body, but still must
                    # not postdate the actual receipt timestamp.
                    quotes = [q for q in quotes if q["event"] <= received]
                    for quote in quotes:
                        quote["received"] = received
                        quote["capture_mode"] = capture["capture_mode"]
                        per_market_quotes[market].append((layer, quote))
            except (OSError, ValueError, TypeError, KeyError, OverflowError):
                audit["raw_response_parse_error"] += 1
        if valid_layers:
            audit["fixtures_with_verified_crown_response"] += 1
        for market, items in per_market_quotes.items():
            # Latest event per layer and latest event across layers, one row per
            # fixture-market. Summary open/close duplicates are collapsed here.
            selected_by_layer = {}
            for layer in ("summary", "movement"):
                eligible = [item for item in items if item[0] == layer]
                if eligible:
                    chosen = max(eligible, key=lambda item: (item[1]["event"], item[1].get("sequence", 0), item[1].get("quote_kind", "")))
                    selected_by_layer[layer] = chosen
                    quote = chosen[1]
                    record = pnl_record(grid, market, quote, actual)
                    evaluated[market][layer][fid] = {
                        **record, "fixture_id": fid, "market": market,
                        "kickoff_utc": zulu(kickoff), "league": fixture["league"],
                        "prediction_asof_utc": zulu(asof), "train_end_utc": zulu(train_end),
                        "capture_mode": quote["capture_mode"],
                        "quote_received_utc": zulu(quote["received"]),
                        "quote_received_pre_kickoff": quote["received"] < kickoff}
            if items:
                chosen = max(items, key=lambda item: (item[1]["event"], item[1].get("sequence", 0), item[1].get("quote_kind", "")))
                quote = chosen[1]
                record = pnl_record(grid, market, quote, actual)
                evaluated[market]["latest_any_layer"][fid] = {
                    **record, "fixture_id": fid, "market": market,
                    "kickoff_utc": zulu(kickoff), "league": fixture["league"],
                    "prediction_asof_utc": zulu(asof), "train_end_utc": zulu(train_end),
                    "capture_mode": quote["capture_mode"],
                    "quote_received_utc": zulu(quote["received"]),
                    "quote_received_pre_kickoff": quote["received"] < kickoff}

    private_rows_path = private_path(private_rows_path, Path(__file__).resolve().parents[2])
    private_rows = [row for market in MARKETS for layer in ("summary", "movement", "latest_any_layer")
                    for row in evaluated[market][layer].values()]
    private_raw = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                          for row in private_rows).encode()
    tmp = private_rows_path.with_name(private_rows_path.name + f".tmp-{os.getpid()}")
    tmp.write_bytes(private_raw)
    os.chmod(tmp, 0o600)
    os.replace(tmp, private_rows_path)

    markets_report = {}
    for market_index, market in enumerate(MARKETS):
        layers_report = {}
        for layer_index, layer in enumerate(("summary", "movement", "latest_any_layer")):
            rows = list(evaluated[market][layer].values())
            layers_report[layer] = summarize(rows, 20261201 + market_index * 10 + layer_index)
        markets_report[market] = layers_report
    all_rows = [row for market in MARKETS for layer in evaluated[market].values() for row in layer.values()]
    chronology_ok = all(
        instant(row["train_end_utc"]) < instant(row["prediction_asof_utc"])
        <= instant(row["event_utc"]) <= instant(row["quote_received_utc"])
        and instant(row["event_utc"]) < instant(row["kickoff_utc"])
        for row in all_rows)
    report = {
        "protocol": "M5_CROWN_SQLITE_FULL_OOS_REPLAY_V1",
        "generated_utc": zulu(datetime.now(timezone.utc)),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "input_hashes": {"forecast_sha256": forecast_digest.hexdigest(),
                         "candidate_manifest_sha256": sha(manifest_raw),
                         "response_hash_set_sha256": sha("\n".join(sorted(response_hashes)).encode())},
        "coverage": {"forecast_rows_total": forecast_total_count,
                     "forecast_rows_with_canonical_captures": len(forecasts),
                     "duplicate_forecast_ids_excluded": len(duplicate_forecasts),
                     "manifest_fixture_rows": len(fixtures),
                     "forecast_ids_with_canonical_captures": len(captures),
                     "fixture_markets_with_quote": {market: markets_report[market]["latest_any_layer"]["unique_fixture_markets"] for market in MARKETS},
                     "kickoff_years": sorted({row.get("kickoff", "")[:4] for row in forecasts.values()}),
                     "source_timezone": source_timezone},
        "integrity": {"forecast_train_end_before_asof_before_kickoff": True,
                      "candidate_identity_utc_kickoff_and_final_score_verified": True,
                      "raw_response_sha_identity_and_score_verified": True,
                      "quote_event_at_or_after_asof_and_before_kickoff": True,
                      "quote_event_not_after_actual_response_receipt": True,
                      "time_order_all_published_fixture_markets": chronology_ok,
                      "actual_receipt_time_separate_from_source_quote_time": True,
                      "fixture_level_rows_public": False},
        "response_receipt_timing": dict(receipt_counts),
        "markets": markets_report,
        "audit_counts": dict(sorted(audit.items())),
        "method": "M5-only frozen prequential score-grid forecasts; verified local Crown responses; latest Crown source event at/after prediction as-of and before UTC kickoff, with source event no later than actual response receipt. Summary and movement are reported separately, plus latest event across layers. Higher score-grid expected-return side, one unit for every eligible fixture-market, no EV threshold or added gate.",
        "limitations": [
            "All selected historical responses are retrospective retrievals; source quote timestamps do not establish contemporaneous receipt or executable prices.",
            "This reuses an existing frozen OOS forecast archive and already observed outcomes; it is a retrospective archive expansion, not an untouched new holdout.",
            "The score-grid probability model is the existing M5 model, not a newly trained independent model in this run.",
            "Crown is the only odds source used. TotalCorner is excluded from this report.",
        ],
    }
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--private-rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.forecasts, args.manifest, args.database, args.private_rows,
                 args.output, args.source_timezone)
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "coverage": report["coverage"],
                      "markets": {market: {layer: {key: report["markets"][market][layer][key]
                                                     for key in ("unique_fixture_markets", "net_units", "roi_pct", "settlement_log_loss", "settlement_brier")}
                                            for layer in report["markets"][market]}
                                 for market in MARKETS},
                      "integrity": report["integrity"],
                      "audit_counts": report["audit_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
