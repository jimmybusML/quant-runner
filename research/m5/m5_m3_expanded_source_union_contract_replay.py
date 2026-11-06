#!/usr/bin/env python3
"""Replay the three frozen M3 OOS models on newly captured M5 market history.

Only the contracts exposed by M3's saved OOS file are evaluated: AH0 and OU2.5.
For each fixture-market, use Crown first and TotalCorner default only when Crown
has no valid exact contract. All three models use the same selected quote. Raw
fixtures, prices, and identities stay in the private archive; output contains
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
M5_LEAGUE_CODES = {
    "England Premier League": "E0", "Germany Bundesliga": "D1",
    "Belgium First Division A": "B1", "Belgium Jupiler Pro League": "B1",
    "France Ligue 1": "F1", "Italy Serie A": "I1", "Spain La Liga": "SP1",
}
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


def crown_first_exact_quote(crown_rows, totalcorner_rows, market, target_line,
                            cutoff, kickoff, zone, crown_received, totalcorner_received):
    """Select one exact contract, preserving source and receipt evidence."""
    for source, rows, received in (
            ("Crown", crown_rows, crown_received),
            ("TotalCorner_default", totalcorner_rows, totalcorner_received)):
        quote = latest_exact_quote(rows, market, target_line, cutoff, kickoff, zone)
        if quote and received and received >= quote[0]:
            return quote, source, received
    return None


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


def m5_probabilities(forecast: dict):
    grid = forecast["prediction"]["grid"]
    home = draw = away = over = 0.0
    for h, row in enumerate(grid):
        for a, probability in enumerate(row):
            p = float(probability)
            if not math.isfinite(p) or p < 0:
                raise ValueError("invalid M5 probability grid")
            if h > a: home += p
            elif h == a: draw += p
            else: away += p
            if h + a > 2: over += p
    if abs(home + draw + away - 1.0) > 1e-7:
        raise ValueError("M5 probability grid does not sum to one")
    return {"AH": (home, draw, away), "OU": (over, 1.0 - over)}


def select_side_from_probabilities(market: str, probabilities, prices: tuple[float, float]):
    if market == "AH":
        p_home, _p_draw, p_away = probabilities
        ev_home = p_home * (prices[0] - 1.0) - p_away
        ev_away = p_away * (prices[1] - 1.0) - p_home
        return ("home", prices[0]) if ev_home >= ev_away else ("away", prices[1])
    p_over, p_under = probabilities
    ev_over = p_over * (prices[0] - 1.0) - p_under
    ev_under = p_under * (prices[1] - 1.0) - p_over
    return ("over", prices[0]) if ev_over >= ev_under else ("under", prices[1])


def settlement_distribution(market: str, side: str, probabilities):
    if market == "AH":
        p_home, p_draw, p_away = probabilities
        return ({"win": p_home, "push": p_draw, "loss": p_away} if side == "home"
                else {"win": p_away, "push": p_draw, "loss": p_home})
    p_over, p_under = probabilities
    return ({"win": p_over, "loss": p_under} if side == "over"
            else {"win": p_under, "loss": p_over})


def add_probability_model(rows, market, label, probabilities, prices, actual, source, quote_event, received, start):
    side, price = select_side_from_probabilities(market, probabilities, prices)
    pnl, outcome = profit(market, side, *actual, price)
    rows[market][label].append({"pnl": pnl, "outcome": outcome,
        "quote_event_utc": quote_event.isoformat(), "receipt_after_kickoff": received >= start,
        "source": source, "settlement_probabilities": settlement_distribution(market, side, probabilities)})


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
    ret["quote_source_fixture_markets"] = dict(Counter(x["source"] for x in rows))
    if rows and all("settlement_probabilities" in row for row in rows):
        cats = ("win", "push", "loss") if market == "AH" else ("win", "loss")
        losses = [-math.log(max(float(row["settlement_probabilities"][row["outcome"]]), 1e-15))
                  for row in rows]
        briers = [sum((float(row["settlement_probabilities"][cat]) - float(row["outcome"] == cat)) ** 2
                      for cat in cats) for row in rows]
        ret["settlement_log_loss"] = round(sum(losses) / len(losses), 8)
        ret["settlement_brier"] = round(sum(briers) / len(briers), 8)
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
    total_idx_path = private / "totalcorner-default-index.jsonl"
    total_idx_raw = total_idx_path.read_bytes()
    total_idx = {}
    for line in total_idx_raw.decode().splitlines():
        try:
            record = json.loads(line)
            if record.get("status") == "verified_fixture_response":
                total_idx[str(record.get("match_id") or "")] = record
        except ValueError:
            continue
    m3_raw, m3, m3_collisions = load_m3(args.m3_predictions)
    if m3_collisions:
        raise ValueError("duplicate M3 model rows found for exact fixture keys")
    m5_by_key = {}
    m5_raw = None
    blend_report = None
    if args.m5_2026_forecasts or args.blend_report:
        if not args.m5_2026_forecasts or not args.blend_report:
            raise ValueError("--m5-2026-forecasts and --blend-report must be supplied together")
        m5_raw = args.m5_2026_forecasts.read_bytes()
        for line in m5_raw.decode().splitlines():
            try:
                row = json.loads(line)
                code = M5_LEAGUE_CODES.get(str(row.get("league") or ""))
                if code and str(row.get("kickoff") or "")[:4] == "2026":
                    key = (code, str(row.get("kickoff") or "")[:10], norm(row.get("home")), norm(row.get("away")))
                    if key in m5_by_key:
                        raise ValueError("duplicate M5 fixture identity")
                    m5_by_key[key] = row
            except (KeyError, TypeError, json.JSONDecodeError):
                continue
        blend_report = json.loads(args.blend_report.read_text(encoding="utf-8"))
        if blend_report.get("protocol") != "M5_M3_RECENCY_2025_FIT_2026_HOLDOUT_V1":
            raise ValueError("unsupported M3/M5 blend report")
        if (blend_report.get("M3_prediction_sha256") != digest(m3_raw)
                or blend_report.get("M5_recency_2026_forecast_sha256") != digest(m5_raw)):
            raise ValueError("blend report does not match the supplied frozen forecast inputs")
        blend_weights = {market: blend_report["proper_score_blends"][market]["weights"] for market in ("AH", "OU")}
        if any(abs(sum(float(v) for v in weights.values()) - 1.0) > 1e-7
               for weights in blend_weights.values()):
            raise ValueError("M3/M5 blend weights do not sum to one")
    else:
        blend_weights = None
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
    if blend_weights:
        for market in ("AH", "OU"):
            model_rows[market].update({"m5_recency": [], "m3_m5_2025fit_blend": []})
    counts = Counter()
    crown_hash_set = set()
    total_hash_set = set()
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
        m5_forecast = m5_by_key.get(key) if blend_weights else None
        if blend_weights:
            if not m5_forecast:
                continue
            try:
                if ((int(m5_forecast["home_goals"]), int(m5_forecast["away_goals"])) != actual
                        or instant(m5_forecast.get("kickoff")) != start):
                    counts["m5_forecast_identity_or_result_mismatch"] += 1
                    continue
                m5_asof = instant(m5_forecast.get("prediction_asof_utc"))
                m5_train_end = instant(m5_forecast.get("train_end_utc"))
                if not m5_asof or not m5_train_end or not m5_train_end < m5_asof < start:
                    counts["invalid_m5_forecast_chronology"] += 1
                    continue
                m5_probs = m5_probabilities(m5_forecast)
            except (KeyError, TypeError, ValueError):
                counts["invalid_m5_forecast"] += 1
                continue
        else:
            m5_asof = None
            m5_probs = None
        try:
            pred_scores = {(int(r["actual_home_goals"]), int(r["actual_away_goals"])) for r in preds.values()}
            train_ends = {instant(r.get("train_end_utc")) for r in preds.values()}
            if len(pred_scores) != 1 or actual not in pred_scores or None in train_ends:
                counts["m3_result_or_training_time_mismatch"] += 1
                continue
        except (KeyError, TypeError, ValueError):
            counts["invalid_m3_rows"] += 1
            continue
        books = []
        crown_received = None
        crown_raw = None
        response_path = private / "crown-responses" / f"{mid}.json"
        try:
            if response_path.exists():
                crown_raw = response_path.read_bytes()
                payload = json.loads(crown_raw)
                data = payload.get("data") or []
                if isinstance(data, dict): data = [data]
                matches = [x for x in data if isinstance(x, dict) and str(x.get("id") or "") == mid]
                if payload.get("success") == 1 and len(matches) == 1:
                    match = matches[0]
                    if ((match.get("h"), match.get("a"), match.get("l")) ==
                            (fixture.get("home"), fixture.get("away"), fixture.get("league"))
                            and local_to_utc(match.get("start"), zone) == start
                            and (int(match.get("hg")), int(match.get("ag"))) == actual):
                        books = [b for b in match.get("bookmakers", [])
                                 if isinstance(b, dict) and b.get("slug") == "crown"]
                        if len(books) != 1:
                            books = []
                        crown_received = instant(crown_idx.get(mid, {}).get("captured_at_utc"))
                    else:
                        counts["crown_fixture_validation_failure"] += 1
                else:
                    counts["crown_identity_failure"] += 1
        except (OSError, ValueError, TypeError):
            counts["bad_crown_payload"] += 1
            books = []

        total_match = None
        total_entry = total_idx.get(mid, {})
        total_path = private / "totalcorner-default-responses" / f"{mid}.json"
        try:
            total_raw = total_path.read_bytes() if total_path.exists() else None
            total_payload = json.loads(total_raw) if total_raw else None
            total_data = (total_payload or {}).get("data", [])
            if isinstance(total_data, dict): total_data = [total_data]
            total_matches = [x for x in total_data
                             if isinstance(x, dict) and str(x.get("id") or "") == mid]
            total_match = total_matches[0] if len(total_matches) == 1 else None
            if total_match and (total_match.get("h"), total_match.get("a"), total_match.get("l")) == (
                    fixture.get("home"), fixture.get("away"), fixture.get("league")):
                if (local_to_utc(total_match.get("start"), zone) != start
                        or (total_match.get("hg") is not None and total_match.get("ag") is not None
                            and (int(total_match["hg"]), int(total_match["ag"])) != actual)):
                    total_match = None
            else:
                total_match = None
        except (OSError, ValueError, TypeError):
            total_match = None
            total_raw = None
        for market, line in (("AH", 0.0), ("OU", 2.5)):
            cutoffs = [instant(preds[model].get("train_end_utc")) for model in MODELS]
            if not all(cutoffs):
                counts[f"invalid_m3_train_cutoff_{market}"] += 1
                continue
            cutoff = max([*cutoffs, *([m5_asof] if m5_asof else [])])
            field = "asian_list" if market == "AH" else "goal_list"
            selected = crown_first_exact_quote(
                books[0].get(field) or [] if books else [],
                total_match.get(field) or [] if total_match else [],
                market, line, cutoff, start, zone, crown_received,
                instant(total_entry.get("captured_at_utc")))
            if not selected:
                counts[f"no_source_union_exact_contract_{market}"] += 1
                continue
            chosen, source, received = selected
            if source == "Crown" and crown_raw:
                crown_hash_set.add(digest(crown_raw))
            if source == "TotalCorner_default" and total_raw:
                total_hash_set.add(digest(total_raw))
            quote_event, prices = chosen
            counts[f"selected_{source}_{market}"] += 1
            if received >= start:
                counts[f"post_kickoff_receipt_{market}"] += 1
            for model in MODELS:
                try:
                    side, price = select_side(market, preds[model], prices)
                    pnl, outcome = profit(market, side, *actual, price)
                    if market == "AH":
                        p_home_win = float(preds[model]["ah_home_0_p_win"])
                        p_push = float(preds[model]["ah_home_0_p_push"])
                        p_away_win = float(preds[model]["ah_home_0_p_lose"])
                        if side == "home":
                            dist = {"win": p_home_win, "push": p_push, "loss": p_away_win}
                        else:
                            dist = {"win": p_away_win, "push": p_push, "loss": p_home_win}
                    else:
                        p_over = float(preds[model]["ou_p_over_2_5"])
                        dist = ({"win": p_over, "loss": 1.0 - p_over} if side == "over"
                                else {"win": 1.0 - p_over, "loss": p_over})
                except (KeyError, TypeError, ValueError, ZeroDivisionError):
                    counts[f"invalid_model_contract_{market}"] += 1
                    continue
                model_rows[market][model].append({"pnl": pnl, "outcome": outcome,
                    "quote_event_utc": quote_event.isoformat(), "receipt_after_kickoff": received >= start,
                    "source": source, "settlement_probabilities": dist})
                counts[f"valid_fixture_market_{market}"] += 1
            if blend_weights:
                m5_component = m5_probs[market]
                add_probability_model(model_rows, market, "m5_recency", m5_component, prices,
                                      actual, source, quote_event, received, start)
                weights = blend_weights[market]
                component_names = ("poisson", "dixon_coles", "bivariate_poisson")
                m3_components = [
                    ([float(preds[name]["p_home"]), float(preds[name]["p_draw"]),
                      float(preds[name]["p_away"])] if market == "AH" else
                     [float(preds[name]["ou_p_over_2_5"]),
                      1.0 - float(preds[name]["ou_p_over_2_5"])])
                    for name in component_names]
                blended = tuple(
                    sum(float(weights[name]) * component[index]
                        for name, component in zip(component_names, m3_components))
                    + float(weights["m5_recency"]) * m5_component[index]
                    for index in range(len(m5_component)))
                add_probability_model(model_rows, market, "m3_m5_2025fit_blend", blended, prices,
                                      actual, source, quote_event, received, start)
                counts[f"valid_M5_and_blend_{market}"] += 1

    report = {"protocol": "M5_M3_THREE_MODEL_EXPANDED_CROWN_FIRST_TOTALCORNER_EXACT_CONTRACT_REPLAY_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_manifest_sha256": digest(manifest_raw), "crown_response_index_sha256": digest(crown_idx_raw),
        "totalcorner_default_index_sha256": digest(total_idx_raw),
        "crown_response_hash_set_sha256": digest("\n".join(sorted(crown_hash_set)).encode()),
        "totalcorner_default_response_hash_set_sha256": digest("\n".join(sorted(total_hash_set)).encode()),
        "m3_oos_prediction_sha256": digest(m3_raw), "candidate_fixture_count": len(manifest.get("rows", [])),
        "m5_2026_forecast_sha256": digest(m5_raw) if m5_raw is not None else None,
        "m3_m5_blend_report_sha256": digest(args.blend_report.read_bytes()) if args.blend_report else None,
        "m3_m5_2025fit_blend_weights": blend_weights,
        "m3_all_three_model_oos_fixture_keys": len(m3), "m3_duplicate_model_rows": m3_collisions,
        "model_names": list(MODELS),
        "markets": {market: {model: summarize(rows, market, 20261106 + i + (0 if market == "AH" else 10))
                             for i, (model, rows) in enumerate(model_rows[market].items())}
                    for market in ("AH", "OU")},
        "audit_counts": dict(counts),
        "scope": "Only the six frozen M3-supported leagues and exact AH0/OU2.5 contracts exposed by saved M3 probabilities; exact UTC kickoff and team/date identity joined to the larger M5 fixture archive. Each fixture-market uses one common Crown quote, with TotalCorner default only if no valid exact Crown contract exists; the quote event must be after every M3 model training cutoff and before kickoff. Per model/market, one 1U bet on the higher expected-return side; no EV gate.",
        "limitations": ["AH0 and OU2.5 do not cover arbitrary Asian lines.",
            "M3 forecasts are frozen historical season-forward predictions, not newly retrained on all M5 fixtures.",
            "Historical Crown and TotalCorner API responses may be received after kickoff; actual receipt timing is reported separately, and source event timestamps support event-time replay only.",
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
    parser.add_argument("--m5-2026-forecasts", type=Path)
    parser.add_argument("--blend-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
