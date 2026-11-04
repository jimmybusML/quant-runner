#!/usr/bin/env python3
"""Rate-limited, private TotalCorner Crown history capture for M5 research.

This is a one-off research utility, not a production collector. It requests
only TotalCorner league schedules and the Crown-specific bookmaker endpoint.
All source responses and IDs must remain in a private directory outside this
repository. The public repository contains code and aggregate receipts only.
"""
from __future__ import annotations

import argparse
import math
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m3.reference.m1_runtime_policy import scope_status

API = "https://api.totalcorner.com/v1"
USER_AGENT = "M5-authorized-Crown-historical-research/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def token_value(token_file: Path | None) -> str:
    value = os.environ.get("TOTALCORNER_TOKEN", "").strip()
    if not value and token_file:
        value = token_file.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("TotalCorner credential is unavailable")
    return value


def ensure_private_destination(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if resolved == repo or repo in resolved.parents:
        raise ValueError("private output directory must be outside the public repository")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(resolved, 0o700)
    return resolved


def request_json(url: str, token: str, min_interval: float, state: dict) -> tuple[dict, dict, bytes]:
    # The token is added here and is never included in logs or exception text.
    joiner = "&" if "?" in url else "?"
    full_url = url + joiner + urllib.parse.urlencode({"token": token})
    request = urllib.request.Request(full_url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    for attempt in range(6):
        wait = min_interval - (time.monotonic() - state.get("last_start", 0.0))
        if wait > 0:
            time.sleep(wait)
        state["last_start"] = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                raw = response.read()
                headers = {k.lower(): v for k, v in response.headers.items()}
                status = response.status
        except urllib.error.HTTPError as exc:
            # Do not stringify exc: urllib errors can include the credential-bearing URL.
            if exc.code == 429 and attempt < 5:
                time.sleep(10.5)
                continue
            return {"success": 0, "error": {"code": f"HTTP_{exc.code}"}}, {"http_status": exc.code}, b""
        parsed = json.loads(raw.decode("utf-8"))
        error = parsed.get("error") if isinstance(parsed, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        if code == "TOO_MANY_REQUEST" and attempt < 5:
            try:
                retry_after = max(10.0, float(headers.get("x-rate-limit-reset") or 10))
            except (TypeError, ValueError):
                retry_after = 10.0
            time.sleep(retry_after + 0.25)
            continue
        return parsed, {"http_status": status, "rate_limit_remaining": headers.get("x-rate-limit-remaining"),
                        "rate_limit_reset": headers.get("x-rate-limit-reset"), "response_sha256": sha(raw)}, raw
    raise RuntimeError("TotalCorner rate limit retry budget exhausted")


def atomic_write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    os.chmod(path, 0o600)


def save_json(path: Path, value: object) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode())


def load_leagues(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        pairs = value.items()
    elif isinstance(value, list):
        pairs = ((str(row["league_id"]), str(row["league_name"])) for row in value)
    else:
        raise ValueError("league map must be an object or list")
    leagues = {str(k): str(v) for k, v in pairs if scope_status(str(v)).get("status") == "IN"}
    if not leagues:
        raise ValueError("no leagues in the frozen M1 top-tier scope")
    return leagues


def fetch_schedules(args) -> None:
    out = ensure_private_destination(args.private_dir)
    token = token_value(args.token_file)
    leagues = load_leagues(args.leagues)
    state = {"last_start": 0.0}
    summary = {"protocol": "M5_CROWN_PRIVATE_SCHEDULE_CAPTURE_V1", "started_utc": utc_now(),
               "league_count": len(leagues), "pages_requested": 0, "pages_saved": 0,
               "pages_processed": 0, "schedule_rows": 0, "in_scope_rows": 0, "unique_fixture_ids": 0,
               "page_errors": 0, "api_errors": 0}
    seen_ids: set[str] = set()
    errors = out / "schedule-errors.jsonl"
    for league_id, expected_name in sorted(leagues.items()):
        first_path = out / "schedules" / league_id / "page-1.json"
        if first_path.exists():
            first = json.loads(first_path.read_text(encoding="utf-8"))
        else:
            url = f"{API}/league/schedule/{urllib.parse.quote(league_id, safe='')}?page=1"
            try:
                first, receipt, raw_body = request_json(url, token, args.min_interval, state)
                summary["pages_requested"] += 1
                if first.get("success") != 1:
                    summary["api_errors"] += 1
                    with errors.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({"league_id": league_id, "page": 1,
                                                "error_code": (first.get("error") or {}).get("code")}) + "\n")
                    continue
                save_json(first_path, {"payload": first, "receipt": {**receipt, "captured_at_utc": utc_now()}})
                atomic_write(first_path.with_suffix(".raw.json"), raw_body)
                summary["pages_saved"] += 1
            except Exception as exc:
                summary["page_errors"] += 1
                with errors.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"league_id": league_id, "page": 1,
                                            "error_type": type(exc).__name__}) + "\n")
                continue
        pagination = first.get("pagination") or {}
        pages = int(pagination.get("pages") or 1)
        for page in range(1, pages + 1):
            path = out / "schedules" / league_id / f"page-{page}.json"
            if not path.exists():
                url = f"{API}/league/schedule/{urllib.parse.quote(league_id, safe='')}?page={page}"
                try:
                    payload, receipt, raw_body = request_json(url, token, args.min_interval, state)
                    summary["pages_requested"] += 1
                    if payload.get("success") != 1:
                        summary["api_errors"] += 1
                        with errors.open("a", encoding="utf-8") as stream:
                            stream.write(json.dumps({"league_id": league_id, "page": page,
                                                    "error_code": (payload.get("error") or {}).get("code")}) + "\n")
                        continue
                    save_json(path, {"payload": payload, "receipt": {**receipt, "captured_at_utc": utc_now()}})
                    atomic_write(path.with_suffix(".raw.json"), raw_body)
                    summary["pages_saved"] += 1
                except Exception as exc:
                    summary["page_errors"] += 1
                    with errors.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps({"league_id": league_id, "page": page,
                                                "error_type": type(exc).__name__}) + "\n")
                    continue
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
                payload = stored.get("payload") or {}
                page_data = payload.get("data") or {}
                rows = page_data.get("matches") or []
            except Exception:
                summary["page_errors"] += 1
                continue
            summary["pages_processed"] += 1
            for row in rows:
                if not isinstance(row, dict):
                    continue
                summary["schedule_rows"] += 1
                if scope_status(str(row.get("l") or expected_name)).get("status") != "IN":
                    continue
                summary["in_scope_rows"] += 1
                if row.get("id") is not None:
                    seen_ids.add(str(row["id"]))
            if summary["pages_processed"] % 50 == 0:
                summary["unique_fixture_ids"] = len(seen_ids)
                summary["updated_utc"] = utc_now()
                save_json(out / "schedule-summary.json", summary)
                print(json.dumps({"pages_processed": summary["pages_processed"],
                                  "in_scope_schedule_rows": summary["in_scope_rows"],
                                  "unique_fixture_ids": summary["unique_fixture_ids"],
                                  "page_errors": summary["page_errors"], "api_errors": summary["api_errors"]}), flush=True)
        print(json.dumps({"league_index": len(summary.get("completed_leagues", [])) + 1,
                          "league_count": len(leagues), "pages_total": pages,
                          "pages_saved": summary["pages_saved"], "page_errors": summary["page_errors"]}), flush=True)
        summary.setdefault("completed_leagues", []).append(league_id)
        summary["unique_fixture_ids"] = len(seen_ids)
        summary["updated_utc"] = utc_now()
        save_json(out / "schedule-summary.json", summary)
    summary["finished_utc"] = utc_now()
    save_json(out / "schedule-summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "completed_leagues"}, sort_keys=True))


def local_to_utc(value: object, zone: ZoneInfo) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    instants = set()
    for fold in (0, 1):
        candidate = dt.replace(tzinfo=zone, fold=fold)
        if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == dt:
            instants.add(candidate.astimezone(timezone.utc))
    return next(iter(instants)) if len(instants) == 1 else None


def valid_market_rows(rows: object, kickoff: datetime, zone: ZoneInfo) -> int:
    if not isinstance(rows, list):
        return 0
    valid = 0
    for row in rows:
        if not isinstance(row, list) or len(row) != 8:
            continue
        minute, line, side1, side2, time_value, _home_score, _away_score, closed = row
        if minute is not None or closed not in (0, "0", False):
            continue
        observed = local_to_utc(time_value, zone)
        try:
            line_values = [float(x.strip()) for x in str(line).split(",")]
            prices = (float(side1), float(side2))
        except (TypeError, ValueError):
            continue
        if (not observed or observed >= kickoff or len(line_values) not in (1, 2)
                or any(not math.isfinite(x) for x in line_values + list(prices))
                or any(x <= 1 for x in prices)):
            continue
        normalized = sum(line_values) / len(line_values)
        if abs(normalized * 4 - round(normalized * 4)) > 1e-7:
            continue
        valid += 1
    return valid


def iter_schedule_rows(private_dir: Path):
    for path in sorted((private_dir / "schedules").glob("*/page-*.json")):
        if ".raw." in path.name:
            continue
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope.get("payload") or {}
            rows = ((payload.get("data") or {}).get("matches") or [])
            for row in rows:
                if isinstance(row, dict):
                    yield row
        except Exception:
            continue


def fetch_crown(args) -> None:
    out = ensure_private_destination(args.private_dir)
    token = token_value(args.token_file)
    zone = ZoneInfo(args.source_timezone)
    candidates = {}
    identity_conflicts: set[str] = set()
    now = datetime.now(timezone.utc)
    for row in iter_schedule_rows(out):
        if scope_status(str(row.get("l") or "")).get("status") != "IN":
            continue
        if str(row.get("status") or "").lower() not in ("full", "ft", "finished", "ended"):
            continue
        try:
            home_goals, away_goals = int(row.get("hg")), int(row.get("ag"))
        except (TypeError, ValueError):
            continue
        if home_goals < 0 or away_goals < 0:
            continue
        kickoff = local_to_utc(row.get("start"), zone)
        if not kickoff or kickoff >= now:
            continue
        mid = str(row.get("id") or "")
        if not mid:
            continue
        if mid in identity_conflicts:
            continue
        record = {"match_id": mid, "league": str(row.get("l") or ""),
                  "home": str(row.get("h") or ""), "away": str(row.get("a") or ""),
                  "kickoff_source_local": str(row.get("start") or ""),
                  "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
                  "home_goals": home_goals, "away_goals": away_goals,
                  "schedule_status": str(row.get("status") or "")}
        prior = candidates.get(mid)
        if prior and (prior["home"], prior["away"], prior["kickoff_utc"], prior["home_goals"], prior["away_goals"]) != (
                record["home"], record["away"], record["kickoff_utc"], record["home_goals"], record["away_goals"]):
            candidates.pop(mid, None)
            identity_conflicts.add(mid)
            continue
        candidates[mid] = record
    candidate_rows = list(candidates.values())
    candidate_rows.sort(key=lambda x: (x["kickoff_utc"], x["match_id"]))
    save_json(out / "candidate-manifest.json", {"protocol": "M5_M1_SCOPE_HISTORICAL_FT_CANDIDATES_V1",
              "generated_utc": utc_now(), "source_timezone": args.source_timezone,
              "unique_candidates": len(candidate_rows), "identity_conflicts_excluded": len(identity_conflicts),
              "rows": candidate_rows})
    state = {"last_start": 0.0}
    counts = {"candidate_unique_fixtures": len(candidate_rows), "requests": 0,
              "crown_exact_identity": 0, "crown_ah_prematch_fixtures": 0,
              "crown_ou_prematch_fixtures": 0, "crown_both_market_fixtures": 0,
              "no_crown_or_invalid_response": 0, "transport_errors": 0,
              "schedule_identity_or_time_mismatch": 0, "processed": 0}
    receipts_path = out / "crown-response-index.jsonl"
    latest = out / "quote-progress.json"
    if receipts_path.exists():
        for line in receipts_path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            counts["crown_exact_identity"] += 1
            counts["crown_ah_prematch_fixtures"] += int(entry.get("ah_valid_prematch_rows", 0) > 0)
            counts["crown_ou_prematch_fixtures"] += int(entry.get("ou_valid_prematch_rows", 0) > 0)
            counts["crown_both_market_fixtures"] += int(entry.get("ah_valid_prematch_rows", 0) > 0 and entry.get("ou_valid_prematch_rows", 0) > 0)
    no_crown_files = list((out / "no-crown").glob("*.json"))
    counts["no_crown_or_invalid_response"] = len(no_crown_files)
    counts["transport_errors"] = sum(1 for p in no_crown_files
                                      if json.loads(p.read_text(encoding="utf-8")).get("status") == "transport_error")
    counts["processed"] = counts["crown_exact_identity"] + counts["no_crown_or_invalid_response"]
    counts["requests"] = counts["processed"]
    for fixture in candidate_rows:
        mid = fixture["match_id"]
        raw_path = out / "crown-responses" / f"{mid}.json"
        no_path = out / "no-crown" / f"{mid}.json"
        if raw_path.exists() or no_path.exists():
            continue
        query = urllib.parse.urlencode({"bookmaker": "crown", "columns": "asianList,goalList"})
        url = f"{API}/match/bookmaker_odds/{urllib.parse.quote(mid, safe='')}?{query}"
        try:
            payload, receipt, raw_body = request_json(url, token, args.min_interval, state)
            counts["requests"] += 1
        except Exception as exc:
            counts["transport_errors"] += 1
            save_json(no_path, {"status": "transport_error", "error_type": type(exc).__name__,
                                "captured_at_utc": utc_now()})
            counts["processed"] += 1
            if counts["processed"] % 100 == 0:
                save_json(latest, {"protocol": "M5_CROWN_BACKFILL_PROGRESS_V1", "updated_utc": utc_now(), **counts})
                print(json.dumps({"processed": counts["processed"], "candidate_unique_fixtures": counts["candidate_unique_fixtures"],
                                  "crown_ah_fixtures": counts["crown_ah_prematch_fixtures"],
                                  "crown_ou_fixtures": counts["crown_ou_prematch_fixtures"]}), flush=True)
            continue
        data = payload.get("data") if isinstance(payload, dict) else None
        matches = [m for m in data if isinstance(m, dict) and str(m.get("id") or "") == mid] if isinstance(data, list) else []
        crown = [b for m in matches for b in (m.get("bookmakers") or [])
                 if isinstance(b, dict) and b.get("slug") == "crown"]
        error_code = ((payload.get("error") or {}).get("code") if isinstance(payload, dict) else None)
        if error_code in ("TOKEN_ERROR", "NO_PERMISSION"):
            raise RuntimeError("TotalCorner authorization failed; stopping without logging credential data")
        if (payload.get("success") != 1 or len(matches) != 1 or len(crown) != 1
                or matches[0].get("h") != fixture["home"] or matches[0].get("a") != fixture["away"]):
            save_json(no_path, {"status": "no_crown_or_identity_failure", "error_code": error_code,
                                "captured_at_utc": utc_now()})
            counts["no_crown_or_invalid_response"] += 1
            counts["processed"] += 1
            if counts["processed"] % 100 == 0:
                save_json(latest, {"protocol": "M5_CROWN_BACKFILL_PROGRESS_V1", "updated_utc": utc_now(), **counts})
                print(json.dumps({"processed": counts["processed"], "candidate_unique_fixtures": counts["candidate_unique_fixtures"],
                                  "crown_ah_fixtures": counts["crown_ah_prematch_fixtures"],
                                  "crown_ou_fixtures": counts["crown_ou_prematch_fixtures"]}), flush=True)
            continue
        source_kickoff = local_to_utc(matches[0].get("start"), zone)
        expected_kickoff = local_to_utc(fixture["kickoff_source_local"], zone)
        if not source_kickoff or source_kickoff != expected_kickoff:
            counts["schedule_identity_or_time_mismatch"] += 1
            save_json(no_path, {"status": "schedule_identity_or_time_mismatch", "captured_at_utc": utc_now()})
            counts["processed"] += 1
            if counts["processed"] % 100 == 0:
                save_json(latest, {"protocol": "M5_CROWN_BACKFILL_PROGRESS_V1", "updated_utc": utc_now(), **counts})
                print(json.dumps({"processed": counts["processed"], "candidate_unique_fixtures": counts["candidate_unique_fixtures"],
                                  "crown_ah_fixtures": counts["crown_ah_prematch_fixtures"],
                                  "crown_ou_fixtures": counts["crown_ou_prematch_fixtures"]}), flush=True)
            continue
        counts["crown_exact_identity"] += 1
        bookmaker = crown[0]
        ah_count = valid_market_rows(bookmaker.get("asian_list"), source_kickoff, zone)
        ou_count = valid_market_rows(bookmaker.get("goal_list"), source_kickoff, zone)
        counts["crown_ah_prematch_fixtures"] += int(ah_count > 0)
        counts["crown_ou_prematch_fixtures"] += int(ou_count > 0)
        counts["crown_both_market_fixtures"] += int(ah_count > 0 and ou_count > 0)
        atomic_write(raw_path, raw_body)
        receipt_row = {"match_id": mid, "captured_at_utc": utc_now(), "http_status": receipt.get("http_status"),
                       "response_sha256": receipt.get("response_sha256"), "ah_valid_prematch_rows": ah_count,
                       "ou_valid_prematch_rows": ou_count}
        with receipts_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt_row, sort_keys=True) + "\n")
        counts["processed"] += 1
        if counts["processed"] % 100 == 0:
            save_json(latest, {"protocol": "M5_CROWN_BACKFILL_PROGRESS_V1", "updated_utc": utc_now(), **counts})
            print(json.dumps({"processed": counts["processed"], "candidate_unique_fixtures": counts["candidate_unique_fixtures"],
                              "crown_ah_fixtures": counts["crown_ah_prematch_fixtures"],
                              "crown_ou_fixtures": counts["crown_ou_prematch_fixtures"]}), flush=True)
        if (counts["crown_ah_prematch_fixtures"] >= args.target_market_fixtures
                and counts["crown_ou_prematch_fixtures"] >= args.target_market_fixtures):
            break
    summary = {"protocol": "M5_CROWN_HISTORICAL_BACKFILL_SUMMARY_V1", "finished_utc": utc_now(), **counts}
    save_json(latest, summary)
    print(json.dumps(summary, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    schedules = sub.add_parser("schedules")
    schedules.add_argument("--leagues", type=Path, required=True)
    schedules.add_argument("--private-dir", type=Path, required=True)
    schedules.add_argument("--token-file", type=Path)
    schedules.add_argument("--min-interval", type=float, default=3.1)
    schedules.set_defaults(func=fetch_schedules)
    quotes = sub.add_parser("quotes")
    quotes.add_argument("--private-dir", type=Path, required=True)
    quotes.add_argument("--token-file", type=Path)
    quotes.add_argument("--source-timezone", required=True)
    quotes.add_argument("--min-interval", type=float, default=3.1)
    quotes.add_argument("--target-market-fixtures", type=int, default=10000)
    quotes.set_defaults(func=fetch_crown)
    args = parser.parse_args()
    if args.min_interval < 2.6:
        raise SystemExit("min-interval must be at least 2.6 seconds")
    args.func(args)


if __name__ == "__main__":
    main()
