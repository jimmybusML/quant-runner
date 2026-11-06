#!/usr/bin/env python3
"""Replay the three frozen M3 OOS models on newly captured M5 Crown history.

Only the contracts exposed by M3's saved OOS file are evaluated: AH0 and OU2.5.
Raw fixtures, prices, and identities stay in the private archive; output contains
aggregate metrics and input hashes only. Historical API receipt timing remains
separate from quote event time.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import local_to_utc

MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
LEAGUE_CODES = {
    "England Premier League": "E0", "Germany Bundesliga I": "D1",
    "France Ligue 1": "F1", "Italy Serie A": "I1", "Spain La Liga": "SP1",
    "Belgium First Division A": "B1",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def norm(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


def instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def load_m3(path: Path):
    raw = path.read_bytes()
    grouped = defaultdict(dict)
    collisions = 0
    for row in csv.DictReader(raw.decode("utf-8-sig").splitlines()):
        if row.get("prediction_status") != "predicted":
            continue
        key = (row.get("league"), str(row.get("match_date_utc") or "")[:10],
               norm(row.get("home_team")), norm(row.get("away_team")))
        model = row.get("model")
        if model not in MODELS:
            continue
        if model in grouped[key]:
            collisions += 1
        grouped[key][model] = row
    valid = {key: rows for key, rows in grouped.items() if set(rows) == set(MODELS)}
    return raw, valid, collisions


def crown_market_rows(path: Path, match_id: str, market: str):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        data = payload.get("data") or []
        if isinstance(data, dict):
            data = [data]
        matches = [x for x in data if isinstance(x, dict) and str(x.get("id") or "") == match_id]
        if len(matches) != 1:
            return None
        books = [x for x in matches[0].get("bookmakers", [])
                 if isinstance(x, dict) and x.get("slug") == "crown"]
        if len(books) != 1:
            return None
        key = "asian_list" if market == "AH" else "goal_list"
        return books[0].get(key) or []
    except (OSError, ValueError, TypeError):
        return None


def latest_exact_quote(rows, market: str, target_line: float, train_end: datetime,
                       kickoff: datetime, zone: ZoneInfo):
    valid = []
    for row in rows or []:
        if not isinstance(row, list) or len(row) < 7:
            continue
        minute, raw_line, raw_p1, raw_p2, raw_time = row[:5]
        if minute not in (None, "", 0, "0"):
            continue
        if len(row) >= 8 and row[7] not in (0, "0", False):
            continue
        observed = local_to_utc(raw_time, zone)
        if not observed or not train_end < observed < kickoff:
            continue
        try:
            parts = [float(x.strip()) for x in str(raw_line).replace("/", ",").split(",")]
            prices = (float(raw_p1), float(raw_p2))
            line = sum(parts) / len(parts)
            if (len(parts) not in (1, 2) or any(not math.isfinite(x) for x in parts + list(prices))
                    or any(x <= 1 for x in prices) or abs(line - target_line) > 1e-8
                    or abs(line * 4 - round(line * 4)) > 1e-8
                    or (len(parts) == 2 and abs(abs(parts[0] - parts[1]) - .5) > 1e-8)):
                continue
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        valid.append((observed, prices))
    return max(valid, key=lambda x: x[0]) if valid else None


def profit(market: str, side: str, home: int, away: int, price: float) -> tuple[float, str]:
    if market == "AH":
        margin = home - away if side == "home" else away - home
        if margin > 0:
            return price - 1.0, "win"
        if margin < 0:
            return -1.0, "loss"
        return 0.0, "push"
    won = ((home + away) > 2) == (side == "over")
    return (price - 1.0, "win") if won else (-1.0, "loss")


def select_side(market: str, forecast: dict, prices: tuple[float, float]):
    if market == "AH":
        win = float(forecast["ah_home_0_p_win"])
        push = float(forecast["ah_home_0_p_push"])
        lose = float(forecast["ah_home_0_p_lose"])
        if abs(win + push + lose - 1.0) > 1e-5:
            raise ValueError("bad M3 AH0 probability mass")
        ev_home = win * (prices[0] - 1) - lose
        ev_away = lose * (prices[1] - 1) - win
        return ("home", prices[0]) if ev_home >= ev_away else ("away", prices[1])
    over = float(forecast["ou_p_over_2_5"])
    if not 0 <= over <= 1:
        raise ValueError("bad M3 OU probability")
    ev_over = over * (prices[0] - 1) - (1 - over)
    ev_under = (1 - over) * (prices[1] - 1) - over
    return ("over", prices[0]) if ev_over >= ev_under else ("under", prices[1])


def bootstrap(values: list[float], seed: int, reps: int = 10000):
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    estimates = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return {"method": "fixture percentile bootstrap, descriptive only", "repetitions": reps,
            "lower_95": round(estimates[int(.025 * (reps - 1))], 8),
            "upper_95": round(estimates[int(.975 * (reps - 1))], 8)}


def summarize(rows, market: str, seed: int):
    pnl = [x["pnl"] for x in rows]
    counts = Counter(x["outcome"] for x in rows)
    by_time = defaultdict(float)
    for row in rows:
        by_time[row["quote_event_utc"]] += row["pnl"]
    equity = peak = max_dd = 0.0
    for time_key in sorted(by_time):
        equity += by_time[time_key]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    ret = {"unique_fixtures": len(rows), "simulated_bets": len(rows), "settled_bets": len(rows),
           "pending_bets": 0, "settlement_counts": {k: counts[k] for k in ("win", "half_win", "push", "half_loss", "loss")},
           "net_units": round(sum(pnl), 6), "roi_pct": round(100 * sum(pnl) / len(rows), 6) if rows else None,
           "max_drawdown_units_by_quote_event_time": round(max_dd, 6) if rows else None,
           "roi_bootstrap_95pct": bootstrap(pnl, seed)}
    receipts = Counter("post_kickoff" if x["receipt_after_kickoff"] else "pre_kickoff" for x in rows)
    ret["actual_response_receipt_timing"] = dict(receipts)
    return ret


def run(args):
    private = args.private_dir.resolve()
    manifest_raw = (private / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    crown_idx_raw = (private / "crown-response-index.jsonl").read_bytes()
    crown_idx = {}
    for line in crown_idx_raw.decode().splitlines():
        try:
            record = json.loads(line)
            crown_idx[str(record.get("match_id") or "")] = record
        except ValueError:
            continue
    m3_raw, m3, m3_collisions = load_m3(args.m3_predictions)
    zone = ZoneInfo(args.source_timezone)
    keys = defaultdict(list)
    for fixture in manifest.get("rows", []):
        code = LEAGUE_CODES.get(str(fixture.get("league") or ""))
        if not code:
            continue
        key = (code, str(fixture.get("kickoff_utc") or "")[:10],
               norm(fixture.get("home")), norm(fixture.get("away")))
        keys[key].append(fixture)

    model_rows = {market: {model: [] for model in MODELS} for market in ("AH", "OU")}
    counts = Counter()
    hash_set = set()
    for key, fixtures in keys.items():
        preds = m3.get(key)
        if not preds:
            continue
        if len(fixtures) != 1:
            counts["ambiguous_m5_fixture_key"] += 1
            continue
        fixture = fixtures[0]
        mid = str(fixture.get("match_id") or "")
        start = instant(fixture.get("kickoff_utc"))
        if not start:
            continue
        try:
            actual = (int(fixture["home_goals"]), int(fixture["away_goals"]))
        except (KeyError, TypeError, ValueError):
            continue
        try:
            pred_scores = {(int(r["actual_home_goals"]), int(r["actual_away_goals"])) for r in preds.values()}
            train_ends = {instant(r.get("train_end_utc")) for r in preds.values()}
            if len(pred_scores) != 1 or actual not in pred_scores or None in train_ends:
                counts["m3_result_or_training_time_mismatch"] += 1
                continue
        except (KeyError, TypeError, ValueError):
            counts["invalid_m3_rows"] += 1
            continue
        response_path = private / "crown-responses" / f"{mid}.json"
        if not response_path.exists():
            continue
        receipt = crown_idx.get(mid, {})
        received = instant(receipt.get("captured_at_utc"))
        if not received:
            counts["missing_crown_receipt"] += 1
            continue
        try:
            payload = json.loads(response_path.read_text(encoding="utf-8"))
            data = payload.get("data") or []
            if isinstance(data, dict): data = [data]
            matches = [x for x in data if isinstance(x, dict) and str(x.get("id") or "") == mid]
            if payload.get("success") != 1 or len(matches) != 1:
                counts["crown_identity_failure"] += 1
                continue
            match = matches[0]
            if (match.get("h") != fixture.get("home") or match.get("a") != fixture.get("away")
                    or match.get("l") != fixture.get("league") or local_to_utc(match.get("start"), zone) != start
                    or (int(match.get("hg")), int(match.get("ag"))) != actual):
                counts["crown_fixture_validation_failure"] += 1
                continue
            books = [b for b in match.get("bookmakers", []) if isinstance(b, dict) and b.get("slug") == "crown"]
            if len(books) != 1:
                continue
        except (OSError, ValueError, TypeError):
            counts["bad_crown_payload"] += 1
            continue
        hash_set.add(digest(response_path.read_bytes()))
        for market, line in (("AH", 0.0), ("OU", 2.5)):
            rows = books[0].get("asian_list" if market == "AH" else "goal_list") or []
            by_model_quote = {}
            for model in MODELS:
                cutoff = instant(preds[model].get("train_end_utc"))
                quote = latest_exact_quote(rows, market, line, cutoff, start, zone)
                if quote:
                    by_model_quote[model] = quote
            if len(by_model_quote) != len(MODELS):
                continue
            # One exact contract quote is chosen per fixture-market, and the
            # same source event/prices are used for every M3 model.
            quote_events = {x[0] for x in by_model_quote.values()}
            quote_prices = {x[1] for x in by_model_quote.values()}
            if len(quote_events) != 1 or len(quote_prices) != 1:
                counts[f"m3_model_quote_cutoff_disagreement_{market}"] += 1
                continue
            quote_event, prices = next(iter(by_model_quote.values()))
            for model in MODELS:
                try:
                    side, price = select_side(market, preds[model], prices)
                    pnl, outcome = profit(market, side, *actual, price)
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    counts[f"invalid_model_contract_{market}"] += 1
                    continue
                model_rows[market][model].append({"pnl": pnl, "outcome": outcome,
                    "quote_event_utc": quote_event.isoformat(), "receipt_after_kickoff": received >= start})
                counts[f"valid_fixture_market_{market}"] += 1

    report = {"protocol": "M5_M3_THREE_MODEL_EXPANDED_CROWN_EXACT_CONTRACT_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_manifest_sha256": digest(manifest_raw), "crown_response_index_sha256": digest(crown_idx_raw),
        "crown_response_hash_set_sha256": digest("\n".join(sorted(hash_set)).encode()),
        "m3_oos_prediction_sha256": digest(m3_raw), "candidate_fixture_count": len(manifest.get("rows", [])),
        "m3_all_three_model_oos_fixture_keys": len(m3), "model_names": list(MODELS),
        "markets": {market: {model: summarize(rows, market, 20261106 + i + (0 if market == "AH" else 10))
                             for i, (model, rows) in enumerate(model_rows[market].items())}
                    for market in ("AH", "OU")},
        "audit_counts": dict(counts),
        "scope": "Only the six frozen M3-supported leagues and exact AH0/OU2.5 contracts exposed by saved M3 probabilities; exact UTC kickoff and team/date identity joined to the larger M5 fixture archive. Each model uses its strict season-forward M3 probabilities and only quote events later than its training cutoff and before kickoff. Per model/market, one 1U bet on the higher expected-return side; no EV gate.",
        "limitations": ["AH0 and OU2.5 do not cover arbitrary Asian lines.",
            "M3 forecasts are frozen historical season-forward predictions, not newly retrained on all M5 fixtures.",
            "Historical Crown API responses were received after kickoff; source event timestamps support event-time replay only.",
            "Public output contains no fixture IDs, team names, odds, or raw provider responses."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"], "markets": report["markets"],
                      "audit_counts": report["audit_counts"]}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--m3-predictions", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
