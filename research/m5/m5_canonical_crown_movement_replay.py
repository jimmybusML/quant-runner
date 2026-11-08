#!/usr/bin/env python3
"""Compare Crown movement quotes with summary quotes on M5 OOS fixtures.

The SQLite movement capture identifies the exact cached Crown response hashes.
This runner reads those same response bodies to recover AH and OU movement rows,
then compares the latest eligible source-time movement with the latest eligible
open/close summary quote on the same fixture-market set. Historical receipts
remain retrospective even when source quote times precede kickoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.m3_grid_crown_replay import (
    expected_return,
    legs_result,
    payout,
    score,
)

MARKETS = {
    "AH": {"list_key": "asian_list", "summary_key": "asian", "sides": ("home", "away"),
           "prices": ("home", "away")},
    "OU": {"list_key": "goal_list", "summary_key": "goal", "sides": ("over", "under"),
           "prices": ("over", "under")},
}
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def local_to_utc(value: object, zone: ZoneInfo) -> datetime | None:
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


def normalized_line(raw: object) -> float | None:
    try:
        values = [float(part.strip()) for part in str(raw).split(",")]
    except (TypeError, ValueError):
        return None
    if len(values) not in (1, 2) or any(not math.isfinite(value) for value in values):
        return None
    line = sum(values) / len(values)
    return line if abs(line * 4 - round(line * 4)) <= 1e-7 else None


def valid_prices(first: object, second: object) -> tuple[float, float] | None:
    try:
        prices = (float(first), float(second))
    except (TypeError, ValueError):
        return None
    if any(not math.isfinite(price) or price <= 1 for price in prices):
        return None
    return prices


def movement_quotes(rows: object, asof: datetime, kickoff: datetime,
                    source_timezone: str, market: str) -> list[dict]:
    """Parse pregame movement entries and retain only post-as-of events."""
    if market not in MARKETS or not isinstance(rows, list):
        return []
    zone = ZoneInfo(source_timezone)
    output = []
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 8:
            continue
        minute, raw_line, first, second, source_time, _home_score, _away_score, closed = row
        if minute is not None or closed not in (0, "0", False):
            continue
        event = local_to_utc(source_time, zone)
        line = normalized_line(raw_line)
        prices = valid_prices(first, second)
        if (not event or not asof < event < kickoff or line is None or prices is None):
            continue
        output.append({"event": event, "line": line, "prices": prices, "sequence": index})
    return output


def summary_quotes(book: dict, asof: datetime, kickoff: datetime,
                   source_timezone: str, market: str) -> list[dict]:
    """Parse open/close summary quotes with the same strict time contract."""
    config = MARKETS[market]
    zone = ZoneInfo(source_timezone)
    output = []
    quotes = book.get(config["summary_key"]) or {}
    for sequence, kind in enumerate(("open", "close")):
        row = quotes.get(kind)
        if not isinstance(row, dict):
            continue
        event = local_to_utc(row.get("time"), zone)
        line = normalized_line(row.get("line"))
        prices = valid_prices(*(row.get(key) for key in config["prices"]))
        if not event or not asof < event < kickoff or line is None or prices is None:
            continue
        output.append({"event": event, "line": line, "prices": prices, "sequence": sequence})
    return output


def evaluate(grid: list[list[float]], market: str, quote: dict,
             home_goals: int, away_goals: int) -> dict:
    config = MARKETS[market]
    sides = config["sides"]
    evs = [expected_return(grid, market, side, quote["line"], price)
           for side, price in zip(sides, quote["prices"])]
    selected = 0 if evs[0] >= evs[1] else 1
    side, price = sides[selected], quote["prices"][selected]
    legs, category = legs_result(market, side, quote["line"], home_goals, away_goals)
    distribution = score_distribution(grid, market, side, quote["line"])
    return {"event": quote["event"], "pnl": payout(legs, price),
            "category": category, "distribution": distribution}


def score_distribution(grid: list[list[float]], market: str, side: str, line: float) -> dict:
    categories = Counter()
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _legs, category = legs_result(market, side, line, home, away)
            categories[category] += probability
    return {category: categories[category] for category in CATEGORIES}


def bootstrap_difference(values: list[float], seed: int, repetitions: int = 5000) -> dict | None:
    if not values:
        return None
    import random
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(repetitions))
    return {"method": "paired fixture bootstrap", "repetitions": repetitions,
            "lower_95_roi_difference_pp": round(100 * means[int(.025 * (repetitions - 1))], 6),
            "upper_95_roi_difference_pp": round(100 * means[int(.975 * (repetitions - 1))], 6)}


def summarize(rows: list[dict], seed: int) -> dict:
    count = len(rows)
    net = math.fsum(row["pnl"] for row in rows)
    outcomes = Counter(row["category"] for row in rows)
    by_event: dict[datetime, float] = defaultdict(float)
    for row in rows:
        by_event[row["event"]] += row["pnl"]
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    log_loss, brier = score([(row["category"], row["distribution"]) for row in rows])
    return {
        "unique_fixture_markets": count, "simulated_bets": count, "settled_bets": count,
        "stake_units": count, "net_units": round(net, 6),
        "roi_pct": round(100 * net / count, 6) if count else None,
        "settlement_counts": {category: outcomes[category] for category in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "settlement_log_loss": log_loss, "settlement_brier": brier,
    }


def run(authorized_data: Path, crown_db: Path, output: Path,
        source_timezone: str = "Asia/Shanghai") -> dict:
    forecast_path = authorized_data / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    index_path = authorized_data / "crown-response-index.jsonl"
    response_dir = authorized_data / "crown-responses"
    index = {}
    for line in index_path.open(encoding="utf-8"):
        try:
            item = json.loads(line)
            index[str(item["match_id"])] = item
        except (KeyError, json.JSONDecodeError):
            continue
    db = sqlite3.connect(f"file:{crown_db.resolve()}?mode=ro", uri=True)
    captures: dict[str, dict] = {}
    for fid, layer, kickoff, digest, receipt, count in db.execute(
        """SELECT fixture_id,data_layer,kickoff_at_utc,response_sha256,
                  response_received_at_utc,quote_count
             FROM capture WHERE data_layer IN ('summary','movement')
               AND capture_mode='historical' AND status='QUOTES_SAVED'"""
    ):
        key = str(fid)
        source = index.get(key)
        if not source or source.get("response_sha256") != digest:
            continue
        captures.setdefault(key, {})[layer] = {
            "kickoff": kickoff, "sha": digest, "receipt": receipt, "quote_count": count,
        }
    movement_ids = {fid for fid, layers in captures.items() if "movement" in layers}
    forecasts = {}
    forecast_raw_hash = hashlib.sha256()
    for raw_line in forecast_path.open("rb"):
        forecast_raw_hash.update(raw_line)
        if not raw_line.startswith(b'{"match_id":"'):
            continue
        fid = raw_line[13:raw_line.find(b'"', 13)].decode("utf-8")
        if fid not in movement_ids:
            continue
        try:
            forecast = json.loads(raw_line)
            if int(forecast.get("year", 0)) in (2025, 2026):
                forecasts[fid] = forecast
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    zone = ZoneInfo(source_timezone)
    output_rows: dict[str, dict[str, dict]] = {market: {} for market in MARKETS}
    audit = Counter()
    response_hashes = set()
    response_receipt_timing = Counter()
    for fid, forecast in forecasts.items():
        captured = captures[fid]["movement"]
        body_path = response_dir / f"{fid}.json"
        try:
            raw = body_path.read_bytes()
            if sha(raw) != captured["sha"]:
                audit["raw_sha_mismatch"] += 1
                continue
            payload = json.loads(raw)
            matches = [m for m in payload.get("data", [])
                       if isinstance(m, dict) and str(m.get("id")) == fid]
            books = [b for m in matches for b in (m.get("bookmakers") or [])
                     if isinstance(b, dict) and b.get("slug") == "crown"]
            if payload.get("success") != 1 or len(matches) != 1 or len(books) != 1:
                audit["crown_body_or_identity_invalid"] += 1
                continue
            match = matches[0]
            if (match.get("h"), match.get("a"), match.get("l")) != (
                forecast.get("home"), forecast.get("away"), forecast.get("league")
            ):
                audit["team_or_league_mismatch"] += 1
                continue
            kickoff = utc(forecast.get("kickoff"))
            source_kickoff = local_to_utc(match.get("start"), zone)
            if not kickoff or source_kickoff != kickoff or (
                int(match.get("hg")), int(match.get("ag"))
            ) != (int(forecast["home_goals"]), int(forecast["away_goals"])):
                audit["kickoff_or_score_mismatch"] += 1
                continue
            asof = utc(forecast.get("prediction_asof_utc"))
            train_end = utc(forecast.get("train_end_utc"))
            if not asof or not train_end or not train_end < asof < kickoff:
                audit["forecast_order_invalid"] += 1
                continue
            receipt = utc(captured.get("receipt"))
            response_receipt_timing["post_kickoff" if receipt and receipt >= kickoff else "not_post_kickoff"] += 1
            response_hashes.add(captured["sha"])
            for market, config in MARKETS.items():
                movement = movement_quotes(books[0].get(config["list_key"]), asof, kickoff,
                                           source_timezone, market)
                summary = summary_quotes(books[0], asof, kickoff, source_timezone, market)
                if not movement:
                    audit[f"{market}_no_eligible_movement"] += 1
                    continue
                chosen_movement = max(movement, key=lambda quote: (quote["event"], quote["sequence"]))
                move_result = evaluate(forecast["prediction"]["grid"], market, chosen_movement,
                                       int(forecast["home_goals"]), int(forecast["away_goals"]))
                record = {"movement": move_result, "year": int(forecast["year"])}
                if summary:
                    chosen_summary = max(summary, key=lambda quote: (quote["event"], quote["sequence"]))
                    record["summary"] = evaluate(forecast["prediction"]["grid"], market, chosen_summary,
                                                   int(forecast["home_goals"]), int(forecast["away_goals"]))
                output_rows[market][fid] = record
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError):
            audit["invalid_or_unreadable_response"] += 1
    report = {
        "protocol": "M5_CROWN_MOVEMENT_VS_SUMMARY_OOS_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "forecast_file": forecast_path.name,
            "forecast_sha256": forecast_raw_hash.hexdigest(),
            "crown_response_index_sha256": sha(index_path.read_bytes()),
            "response_hash_set_sha256": hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest(),
            "historical_movement_capture_fixtures_matching_index_sha": len(movement_ids),
            "forecast_fixtures_matching_movement_sha": len(forecasts),
            "source_timezone": source_timezone,
            "quote_source": "Crown only",
            "kickoff_years": [2025, 2026],
        },
        "markets": {},
        "audit_counts": dict(sorted(audit.items())),
        "response_receipt_timing": dict(sorted(response_receipt_timing.items())),
        "method": "Strict annual M5 OOS score grids. Per fixture-market, select the latest source-time Crown movement and latest open/close summary quote strictly after prediction as-of and before kickoff. Independently select the model higher-expected-return side at each quote, one unit per fixture-market, no EV threshold or sample filter. Compare paired P&L on the exact movement/summary fixture intersection.",
        "limitations": [
            "Historical Crown response receipts were received after kickoff; source-event quotes support retrospective event-time analysis only, not contemporaneous executable ROI.",
            "This is an exploratory price-path comparison on previously examined 2025-2026 outcomes, not a new untouched holdout or a production rule.",
            "No M1, MR1, M3, M4 production route, order, Telegram, ledger, or trading gate was changed.",
        ],
    }
    for market, rows in output_rows.items():
        movement_rows = [record["movement"] for record in rows.values()]
        summary_rows = [record["summary"] for record in rows.values() if "summary" in record]
        paired_ids = [fid for fid, record in rows.items() if "summary" in record]
        paired_movement = [rows[fid]["movement"] for fid in paired_ids]
        paired_summary = [rows[fid]["summary"] for fid in paired_ids]
        paired_diff = [a["pnl"] - b["pnl"] for a, b in zip(paired_movement, paired_summary)]
        report["markets"][market] = {
            "movement": summarize(movement_rows, seed=20261109 + (0 if market == "AH" else 1)),
            "summary_open_close": summarize(summary_rows, seed=20261119 + (0 if market == "AH" else 1)),
            "paired_fixture_markets": len(paired_ids),
            "paired_movement": summarize(paired_movement, seed=20261129 + (0 if market == "AH" else 1)),
            "paired_summary_open_close": summarize(paired_summary, seed=20261139 + (0 if market == "AH" else 1)),
            "paired_movement_minus_summary": {
                "net_units": round(math.fsum(paired_diff), 6),
                "mean_units_per_fixture": round(math.fsum(paired_diff) / len(paired_diff), 8) if paired_diff else None,
                "movement_higher_return_fixtures": sum(value > 1e-9 for value in paired_diff),
                "summary_higher_return_fixtures": sum(value < -1e-9 for value in paired_diff),
                "ties": sum(abs(value) <= 1e-9 for value in paired_diff),
                "bootstrap_95_roi_difference": bootstrap_difference(paired_diff, seed=20261149 + (0 if market == "AH" else 1)),
            },
            "by_utc_kickoff_year": {
                str(year): {
                    "movement": summarize([record["movement"] for record in rows.values() if record["year"] == year], seed=20261159 + year),
                    "summary_open_close": summarize([record["summary"] for record in rows.values() if record["year"] == year and "summary" in record], seed=20261169 + year),
                    "movement_unique_fixture_markets": sum(record["year"] == year for record in rows.values()),
                    "summary_unique_fixture_markets": sum(record["year"] == year and "summary" in record for record in rows.values()),
                } for year in (2025, 2026)
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorized-data", type=Path, required=True)
    parser.add_argument("--crown-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.authorized_data, args.crown_db, args.output, args.source_timezone)
    print(json.dumps({"output": str(args.output), "markets": {
        market: {"movement": {key: report["markets"][market]["movement"][key]
                                for key in ("unique_fixture_markets", "net_units", "roi_pct")},
                 "paired_fixture_markets": report["markets"][market]["paired_fixture_markets"]}
        for market in MARKETS
    }}, sort_keys=True))


if __name__ == "__main__":
    main()
