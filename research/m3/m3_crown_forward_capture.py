"""M3-only, value-suppressing Crown quote capture for recorded forward forecasts.

The collector uses the existing TotalCorner credential in the caller's runtime,
queries only bookmaker=crown, and never writes or prints quote lines/prices or raw
responses. It records HMAC commitments and both the UTC API-snapshot receipt time
and provider quote-update time in a public append-only receipt, distinguishing a
current pre-kickoff snapshot from a retrospective history download. M1/M2/MR1
inputs are never opened.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import statistics
import time
from zoneinfo import ZoneInfo

import requests
from research.m3.probabilities import settle_score


LEAGUES = {
    "D1": "Germany Bundesliga I", "E0": "England Premier League",
    "F1": "France Ligue 1", "I1": "Italy Serie A", "SP1": "Spain La Liga",
    "B1": "Belgium First Division A",
}
MODELS = {"poisson", "dixon_coles", "bivariate_poisson"}
ALIASES = {
    "1 fsv mainz 05": "mainz", "sv werder bremen": "werder bremen",
    "aston villa fc": "aston villa", "manchester city fc": "man city",
    "arsenal fc": "arsenal", "everton fc": "everton", "rb leipzig": "rb leipzig",
    "sv 07 elversberg": "elversberg", "fc augsburg": "augsburg",
    "1 fc union berlin": "union berlin", "cagliari calcio": "cagliari",
    "bologna fc 1909": "bologna", "como 1907": "como",
    "us sassuolo calcio": "sassuolo", "coventry city fc": "coventry",
    "fulham fc": "fulham", "toulouse fc": "toulouse", "es troyes ac": "troyes",
}
API = "https://api.totalcorner.com/v1"
UTC = timezone.utc
SAFE_API_ERRORS = {"TOO_MANY_REQUEST", "INVALID_TOKEN", "NO_PERMISSION",
                   "UNAUTHORIZED", "INVALID_PARAMETER", "NOT_FOUND", "INTERNAL_ERROR"}


def safe_api_error(payload: object) -> str:
    if not isinstance(payload, dict):
        return "UNEXPECTED_RESPONSE"
    error = payload.get("error")
    code = error.get("code") if isinstance(error, dict) else None
    return code if isinstance(code, str) and code in SAFE_API_ERRORS else "OTHER"


def request_json(url: str, params: dict) -> dict:
    for attempt in range(7):
        try:
            response = requests.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
        except requests.RequestException:
            if attempt < 6:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError("TotalCorner network request failed") from None
        if response.status_code == 429 and attempt < 6:
            time.sleep(11)
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"TotalCorner HTTP status {response.status_code}")
        try:
            payload = response.json()
        except ValueError:
            raise RuntimeError("TotalCorner returned malformed JSON") from None
        if (isinstance(payload, dict) and safe_api_error(payload) == "TOO_MANY_REQUEST"
                and attempt < 6):
            time.sleep(11)
            continue
        return payload
    raise RuntimeError("TotalCorner rate limit retry bound exhausted")


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 UTC string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must have a UTC offset of zero")
    return parsed.astimezone(UTC)


def source_local_to_utc(value: str, timezone_name: str) -> datetime:
    """Convert provider wall time without guessing an ambiguous/nonexistent DST fold."""
    local = datetime.fromisoformat(str(value).strip())
    if local.tzinfo is not None:
        raise ValueError("provider timestamp must be a source-local wall time")
    zone = ZoneInfo(timezone_name)
    instants = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=fold)
        roundtrip = candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        if roundtrip == local:
            instants.add(candidate.astimezone(UTC))
    if len(instants) != 1:
        raise ValueError("provider wall time is ambiguous or nonexistent")
    return next(iter(instants))


def normalize_name(value: str) -> str:
    import unicodedata
    text = "".join(c for c in unicodedata.normalize("NFKD", str(value or "").lower())
                   if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def canonical_team(value: str) -> str:
    normalized = normalize_name(value)
    return ALIASES.get(normalized, normalized)


def movement_rows(match: dict, market: str, kickoff: datetime,
                  snapshot_at: datetime, source_timezone: str) -> list[tuple[datetime, list]]:
    field = "asian_list" if market == "AH" else "goal_list"
    rows = match.get(field, match.get("asianList" if market == "AH" else "goalList", []))
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise ValueError("Crown movement field must be a list")
    # TotalCorner documents movement arrays as oldest-first and says the last
    # row reports whether a market is currently suspended. Use that one row;
    # falling back to an older open row after a later suspension would create
    # a quote that was not available at the API snapshot time.
    row = rows[-1] if rows else None
    if not isinstance(row, list) or len(row) != 8:
        return []
    minute, line, price1, price2, source_time, _hg, _ag, closed = row
    if minute is not None or closed not in (0, "0", False):
        return []
    try:
        updated = source_local_to_utc(source_time, source_timezone)
        prices = (float(price1), float(price2))
        if (not isinstance(line, (str, int, float)) or not str(line).strip()
                or any(not math.isfinite(price) or price <= 1 for price in prices)
                or updated > snapshot_at or updated >= kickoff):
            return []
    except (TypeError, ValueError, OverflowError):
        return []
    return [(updated, row)]


def _hmac(secret: str, value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()


def _line_parts(value: object) -> list[float]:
    """Read ordinary or quarter-line provider notation without publishing it."""
    if isinstance(value, bool):
        raise ValueError("invalid line")
    parts = [part.strip() for part in str(value).split(",")]
    if len(parts) not in (1, 2) or any(not part for part in parts):
        raise ValueError("unsupported compound line")
    numbers = [float(part) for part in parts]
    if any(not math.isfinite(number) for number in numbers):
        raise ValueError("line components must be finite")
    if len(numbers) == 2 and abs(numbers[0] - numbers[1]) != 0.5:
        raise ValueError("compound line must split a quarter-line stake evenly")
    return numbers


def _line_ev(forecast: dict, market: str, line_value: object,
             prices: tuple[float, float]) -> dict[str, float] | None:
    grid = forecast.get("score_probability_grid")
    try:
        lines = _line_parts(line_value)
    except (TypeError, ValueError):
        return None
    if not isinstance(grid, list) or not grid:
        try:
            if market == "AH" and len(lines) == 1 and lines[0] == 0:
                p_win = float(forecast["ah_home_0_p_win"])
                p_push = float(forecast["ah_home_0_p_push"])
                p_lose = float(forecast["ah_home_0_p_lose"])
                if not all(0 <= value <= 1 for value in (p_win, p_push, p_lose)) or abs(p_win + p_push + p_lose - 1) > 1e-8:
                    return None
                return {"home": p_win * (prices[0] - 1) - p_lose,
                        "away": p_lose * (prices[1] - 1) - p_win}
            if market == "OU" and len(lines) == 1 and lines[0] == 2.5:
                p_over = float(forecast["ou_p_over_2_5"])
                if not 0 <= p_over <= 1:
                    return None
                return {"over": p_over * (prices[0] - 1) - (1 - p_over),
                        "under": (1 - p_over) * (prices[1] - 1) - p_over}
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        return None
    sides = ("home", "away") if market == "AH" else ("over", "under")
    result = {}
    for side, price in zip(sides, prices):
        expected = 0.0
        mass = 0.0
        for home_goals, row in enumerate(grid):
            if not isinstance(row, list):
                return None
            for away_goals, probability in enumerate(row):
                probability = float(probability)
                if not math.isfinite(probability) or not 0 <= probability <= 1:
                    return None
                if probability <= 0:
                    continue
                for line in lines:
                    _, pnl = settle_score(market, line, side, home_goals, away_goals, price)
                    expected += probability * pnl / len(lines)
                mass += probability
        if mass <= 0:
            return None
        result[side] = expected / mass
    return result


def choose_forecasts(events: list[dict], now: datetime, horizon_days: int) -> list[dict]:
    superseded = {row.get("superseded_forecast_id") for row in events
                  if row.get("event_type") == "FORECAST_DUPLICATE_SUPERSEDED"}
    latest: dict[tuple[str, str], dict] = {}
    for row in events:
        if row.get("event_type") != "FORECAST" or row.get("forecast_id") in superseded:
            continue
        if row.get("forecast_status") != "PREDICTED_NO_MARKET":
            continue
        if row.get("league") not in LEAGUES:
            continue
        if row.get("model") not in MODELS:
            continue
        has_grid = isinstance(row.get("score_probability_grid"), list) and bool(row.get("score_probability_grid"))
        has_direct_markets = all(isinstance(row.get(key), (int, float))
            for key in ("ah_home_0_p_win", "ah_home_0_p_push", "ah_home_0_p_lose", "ou_p_over_2_5"))
        if not (has_grid or has_direct_markets):
            continue
        try:
            fixture_day = date.fromisoformat(row["source_fixture_date"])
            forecast_at = parse_utc(row["forecasted_at_utc"], "forecasted_at_utc")
            # Legacy forward forecasts predate explicit train_end serialization.
            # run_shadow always excludes the entire current UTC date from training,
            # so forecast-date minus one day is a conservative upper bound.
            train_end = (date.fromisoformat(row["train_end_calendar_date"])
                         if row.get("train_end_calendar_date") else forecast_at.date() - timedelta(days=1))
        except (KeyError, ValueError, TypeError):
            continue
        if not (now.date() - timedelta(days=1) <= fixture_day <= now.date() + timedelta(days=horizon_days)):
            continue
        if train_end >= now.date() or forecast_at >= now:
            continue
        key = (str(row.get("fixture_identity_id")), str(row.get("model")))
        previous = latest.get(key)
        if previous is None or row["forecasted_at_utc"] > previous["forecasted_at_utc"]:
            latest[key] = row
    return list(latest.values())


def exact_schedule_matches(forecast: dict, schedules: list[dict]) -> list[dict]:
    league_name = LEAGUES.get(forecast.get("league"))
    home = canonical_team(forecast.get("home_team", ""))
    away = canonical_team(forecast.get("away_team", ""))
    result = []
    for match in schedules:
        if match.get("l") != league_name:
            continue
        if (canonical_team(match.get("h", "")) == home
                and canonical_team(match.get("a", "")) == away):
            result.append(match)
    return result


def crown_bookmaker(match: dict) -> dict | None:
    bookmakers = match.get("bookmakers")
    if not isinstance(bookmakers, list):
        return None
    rows = [row for row in bookmakers if isinstance(row, dict) and row.get("slug") == "crown"]
    return rows[0] if len(rows) == 1 else None


def build_commitments(forecasts: list[dict], schedule: dict, payload: dict,
                      received_at: datetime, source_timezone: str,
                      key: str) -> tuple[list[dict], dict]:
    if not isinstance(payload, dict) or payload.get("success") != 1 or not isinstance(payload.get("data"), list):
        return [], {"status": "CROWN_RESPONSE_UNAVAILABLE", "api_error": safe_api_error(payload), "records": 0}
    matches = [row for row in payload["data"]
               if isinstance(row, dict) and str(row.get("id")) == str(schedule.get("id"))]
    bookmaker = crown_bookmaker(matches[0]) if len(matches) == 1 else None
    if bookmaker is None:
        return [], {"status": "CROWN_BOOKMAKER_MISSING_OR_AMBIGUOUS", "records": 0}
    source_match = matches[0]
    if any(source_match.get(key) != schedule.get(key) for key in ("h", "a")):
        return [], {"status": "SOURCE_FIXTURE_IDENTITY_MISMATCH", "records": 0}
    if source_match.get("l") is not None and source_match.get("l") != schedule.get("l"):
        return [], {"status": "SOURCE_COMPETITION_MISMATCH", "records": 0}
    kickoff = source_local_to_utc(schedule.get("start"), source_timezone)
    source_kickoff = source_local_to_utc(source_match.get("start"), source_timezone)
    if source_kickoff != kickoff:
        return [], {"status": "SOURCE_KICKOFF_MISMATCH", "records": 0}
    if received_at >= kickoff:
        return [], {"status": "RESPONSE_AFTER_KICKOFF", "records": 0}
    commitments = []
    market_counts = Counter()
    model_counts = Counter()
    ev_sums = Counter()
    ev_counts = Counter()
    raw_response_hash = _hmac(key, payload)
    for forecast in forecasts:
        forecast_at = parse_utc(forecast["forecasted_at_utc"], "forecasted_at_utc")
        # The API response itself is the current-snapshot evidence. The quote
        # row's provider update time can be earlier when an active price did
        # not move; preserve both timestamps rather than calling it a new
        # historical odds update.
        if received_at <= forecast_at:
            continue
        train_end = (date.fromisoformat(forecast["train_end_calendar_date"])
                     if forecast.get("train_end_calendar_date") else
                     forecast_at.date() - timedelta(days=1))
        if forecast_at >= kickoff or train_end >= kickoff.date():
            continue
        for market in ("AH", "OU"):
            current = movement_rows(bookmaker, market, kickoff, received_at, source_timezone)
            if not current:
                continue
            observed, row = current[0]
            try:
                line_ev = _line_ev(forecast, market, row[1], (float(row[2]), float(row[3])))
            except (TypeError, ValueError, OverflowError):
                line_ev = None
            if line_ev:
                for side, value in line_ev.items():
                    ev_key = (market, forecast["model"], side)
                    ev_sums[ev_key] += value
                    ev_counts[ev_key] += 1
            row_commitment = _hmac(key, row)
            event = {
                "protocol": "M3_CROWN_FORWARD_QUOTE_COMMITMENT_V2",
                "forecast_id": forecast["forecast_id"],
                "fixture_identity_id": forecast["fixture_identity_id"],
                "league": forecast["league"],
                "model": forecast["model"],
                "model_version_id": forecast["model_version_id"],
                "training_input_sha256": forecast["training_input_sha256"],
                "train_end_calendar_date": train_end.isoformat(),
                "forecasted_at_utc": forecast["forecasted_at_utc"],
                "provider": "TotalCorner",
                "bookmaker": "crown",
                "market": market,
                "source_match_id_hmac": _hmac(key, str(schedule["id"])),
                "source_quote_row_hmac": row_commitment,
                "source_response_hmac": raw_response_hash,
                "quote_source_updated_at_utc": observed.isoformat().replace("+00:00", "Z"),
                "snapshot_received_at_utc": received_at.isoformat().replace("+00:00", "Z"),
                "quote_update_age_seconds_at_snapshot": max(0, round((received_at - observed).total_seconds())),
                "snapshot_time_basis": "current API response; latest active pre-match Crown movement row",
                "kickoff_at_utc": kickoff.isoformat().replace("+00:00", "Z"),
                "source_timezone": source_timezone,
                "source_timezone_evidence": "existing TotalCorner profile offset configuration; UTC+08:00",
                "price_or_line_persisted": False,
                "formal_order": False,
                "telegram_sent": False,
            }
            event["event_id"] = hashlib.sha256(json.dumps(
                [event["forecast_id"], market, row_commitment], separators=(",", ":")
            ).encode()).hexdigest()
            commitments.append(event)
            market_counts[market] += 1
            model_counts[forecast["model"]] += 1
    ev_summary = {"|".join(key): {"n": ev_counts[key], "mean_expected_unit_return": round(ev_sums[key] / ev_counts[key], 8)}
                  for key in sorted(ev_counts)}
    return commitments, {"status": "CROWN_IDENTIFIED", "records": len(commitments),
                         "markets": dict(market_counts), "models": dict(model_counts),
                         "mean_ev": ev_summary}


def get_schedule(day: str, token: str) -> list[dict]:
    rows = []
    page = 1
    for _ in range(100):
        payload = request_json(f"{API}/match/schedule",
            {"token": token, "date": day.replace("-", ""), "page": page})
        if not isinstance(payload, dict) or payload.get("success") != 1 or not isinstance(payload.get("data"), list):
            code = safe_api_error(payload)
            raise RuntimeError(f"TotalCorner schedule API error {code}")
        rows.extend(payload["data"])
        if not (payload.get("pagination") or {}).get("next"):
            return rows
        page += 1
        time.sleep(2.2)
    raise RuntimeError("TotalCorner schedule exceeded pagination safety bound")


def get_crown(match_id: str, token: str) -> dict:
    return request_json(f"{API}/match/bookmaker_odds/{match_id}",
        {"token": token, "bookmaker": "crown", "columns": "asianList,goalList"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--horizon-days", type=int, default=14)
    args = parser.parse_args()
    token = os.environ.get("TOTALCORNER_TOKEN")
    if not token:
        raise RuntimeError("existing TotalCorner credential is unavailable")
    now = datetime.now(UTC)
    events = [json.loads(line) for line in args.ledger.read_text().splitlines() if line.strip()]
    forecasts = choose_forecasts(events, now, args.horizon_days)
    forecast_input_fingerprint = hashlib.sha256(json.dumps(sorted(
        [[row["forecast_id"], row["model_version_id"], row["training_input_sha256"]]
         for row in forecasts]), separators=(",", ":")).encode()).hexdigest()
    forecast_dates = {row["source_fixture_date"] for row in forecasts}
    schedule_cache = {}
    candidates: dict[str, tuple[dict, list[dict]]] = {}
    rejected = Counter()
    for day in sorted(forecast_dates):
        for offset in (-1, 0, 1):
            local_day = (date.fromisoformat(day) + timedelta(days=offset)).isoformat()
            if local_day not in schedule_cache:
                try:
                    schedule_cache[local_day] = get_schedule(local_day, token)
                except (requests.RequestException, RuntimeError, ValueError, TypeError, AttributeError) as exc:
                    schedule_cache[local_day] = []
                    message = str(exc)
                    safe_category = (message.removeprefix("TotalCorner schedule API error ")
                                     if message.startswith("TotalCorner schedule API error ") else
                                     "REQUEST_OR_PARSE_FAILURE")
                    rejected[f"schedule_request_failed_{safe_category}"] += 1
                time.sleep(2.2)
        schedules = [match for offset in (-1, 0, 1)
                     for match in schedule_cache[(date.fromisoformat(day) + timedelta(days=offset)).isoformat()]]
        fixtures: dict[str, list[dict]] = {}
        for forecast in forecasts:
            if forecast.get("source_fixture_date") == day:
                fixtures.setdefault(str(forecast.get("fixture_identity_id")), []).append(forecast)
        for fixture_forecasts in fixtures.values():
            forecast = fixture_forecasts[0]
            matches = exact_schedule_matches(forecast, schedules)
            if len(matches) != 1:
                rejected["schedule_identity_missing_or_ambiguous"] += 1
                continue
            schedule = matches[0]
            if str(schedule.get("id")) in candidates:
                existing_forecasts = candidates[str(schedule["id"])][1]
                existing_forecasts.extend(fixture_forecasts)
            else:
                candidates[str(schedule["id"])] = (schedule, fixture_forecasts)
    prior = {}
    if args.output.exists():
        prior = {json.loads(line)["event_id"]: json.loads(line)
                 for line in args.output.read_text().splitlines() if line.strip()}
    previous_report = {}
    if args.report.exists():
        try:
            previous_report = json.loads(args.report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous_report = {}
    added = []
    statuses = Counter()
    ev_aggregate = {}
    key = token
    for match_id, (schedule, fixture_forecasts) in candidates.items():
        try:
            payload = get_crown(match_id, token)
            received_at = datetime.now(UTC)
            rows, status = build_commitments(fixture_forecasts, schedule, payload,
                                             received_at, args.source_timezone, key)
            statuses[status["status"]] += 1
            if status.get("api_error"):
                statuses[f"api_error_{status['api_error']}"] += 1
            for key_name, values in status.get("mean_ev", {}).items():
                bucket = ev_aggregate.setdefault(key_name, {"n": 0, "sum": 0.0})
                bucket["n"] += values["n"]
                bucket["sum"] += values["mean_expected_unit_return"] * values["n"]
            for row in rows:
                if row["event_id"] not in prior:
                    added.append(row)
                    prior[row["event_id"]] = row
        except (requests.RequestException, ValueError, RuntimeError, KeyError, TypeError, AttributeError):
            statuses["CAPTURE_ERROR_REDACTED"] += 1
        time.sleep(2.2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.touch(exist_ok=True)
    if added:
        with args.output.open("a", encoding="utf-8") as stream:
            for row in added:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
    previous_forecast_fingerprint = previous_report.get("forecast_input_fingerprint_sha256")
    commitment_counts_by_market = Counter(row.get("market") for row in prior.values())
    commitment_counts_by_league_market = Counter(
        (row.get("league"), row.get("market")) for row in prior.values())
    update_ages = [row["quote_update_age_seconds_at_snapshot"] for row in added]
    summary = {"protocol": "M3_CROWN_FORWARD_CAPTURE_REPORT_V2",
        "generated_utc": now.isoformat().replace("+00:00", "Z"),
        "data_source": "TotalCorner bookmaker=crown only",
        "forecast_source": "M3 OpenFootball forward-only shadow; public M3 ledger only",
        "forecasts_considered": len(forecasts), "fixtures_with_unique_schedule_identity": len(candidates),
        "forecast_input_fingerprint_sha256": forecast_input_fingerprint,
        "forecast_input_changed_vs_previous_run": None if previous_forecast_fingerprint is None else
            forecast_input_fingerprint != previous_forecast_fingerprint,
        "new_learning_information": (None if previous_forecast_fingerprint is None else
            forecast_input_fingerprint != previous_forecast_fingerprint or bool(added)),
        "new_learning_information_baseline": "unavailable_first_capture_run" if previous_forecast_fingerprint is None else "previous_capture_report",
        "quote_commitments_added": len(added), "quote_commitments_total": len(prior),
        "new_commitments_protocol": "M3_CROWN_FORWARD_QUOTE_COMMITMENT_V2",
        "snapshot_time_basis": "API response received after forecast and before kickoff; latest active Crown pre-match movement row; provider update time retained separately",
        "new_commitment_quote_update_age_seconds": ({"n": len(update_ages),
            "median": round(statistics.median(update_ages)),
            "max": max(update_ages)} if update_ages else {"n": 0, "median": None, "max": None}),
        "quote_commitments_by_market": dict(commitment_counts_by_market),
        "quote_commitments_by_league_market": {"|".join(key): value
            for key, value in sorted(commitment_counts_by_league_market.items())},
        "status_counts": dict(statuses), "rejected_counts": dict(rejected),
        "source_timezone": args.source_timezone,
        "timezone_semantics": "configured existing TotalCorner UTC+08:00 profile interpreted as Asia/Shanghai",
        "mean_ev_by_market_model_side": {name: {"n": values["n"],
            "mean_expected_unit_return": round(values["sum"] / values["n"], 8)}
            for name, values in sorted(ev_aggregate.items()) if values["n"]},
        "scope_note": "The research scope remains six M3 leagues; the current OpenFootball forward forecast feed has no B1 fixtures, so B1 coverage is zero until a compatible independent M3 forecast source is available.",
        "quote_values_or_raw_response_persisted": False,
        "m1_m2_mr1_inputs_read": False, "formal_order": False, "telegram_sent": False,
        "EV": None, "ROI": None}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "COMPLETED", "forecasts_considered": len(forecasts),
        "fixtures_with_unique_schedule_identity": len(candidates),
        "quote_commitments_added": len(added), "status_counts": dict(statuses),
        "rejected_counts": dict(rejected), "price_values_logged": False,
        "raw_response_logged": False, "formal_order": False, "telegram_sent": False}))


if __name__ == "__main__":
    main()
