#!/usr/bin/env python3
"""Prepare a private MR1 V6 batch from M5 OOS rows and Crown responses.

The batch includes only fixture identity, results, UTC timestamps, and Crown
AH/OU/1X2 inputs. It is written outside the repository with mode 0600.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from research.m5.crown_historical_capture import local_to_utc


def instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(private_dir: Path, forecasts: Path, output: Path, timezone_name: str):
    private_dir, forecasts, output = (p.expanduser().resolve() for p in (private_dir, forecasts, output))
    if output == REPO_ROOT or REPO_ROOT in output.parents:
        raise ValueError("prepared fixture-level inputs must remain outside the public repository")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output.parent, 0o700)
    zone = ZoneInfo(timezone_name)
    receipt_index = {}
    with (private_dir / "crown-response-index.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            receipt_index[str(row.get("match_id"))] = row

    counts = {key: 0 for key in ("forecast_rows", "both_crown_AH_OU", "exact_Crown_identity", "valid_1X2", "valid_event_time_1X2", "valid_receipt", "included")}
    response_hashes = set()
    rows = []
    manifest = json.loads((private_dir / "candidate-manifest.json").read_text(encoding="utf-8"))
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}
    with forecasts.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            forecast = json.loads(line)
            counts["forecast_rows"] += 1
            quotes = forecast.get("quotes") or {}
            ah, ou = quotes.get("AH"), quotes.get("OU")
            if not ah or not ou or ah.get("source") != "Crown" or ou.get("source") != "Crown":
                continue
            counts["both_crown_AH_OU"] += 1
            match_id = str(forecast["match_id"])
            fixture = fixtures.get(match_id)
            response_path = private_dir / "crown-responses" / f"{match_id}.json"
            if not fixture or not response_path.is_file():
                continue
            raw = response_path.read_bytes()
            payload = json.loads(raw)
            data = payload.get("data") or []
            data = data if isinstance(data, list) else [data]
            candidates = [x for x in data if isinstance(x, dict) and str(x.get("id")) == match_id]
            if payload.get("success") != 1 or len(candidates) != 1:
                continue
            match = candidates[0]
            bookmakers = [b for b in match.get("bookmakers", []) if isinstance(b, dict) and b.get("slug") == "crown"]
            if len(bookmakers) != 1:
                continue
            counts["exact_Crown_identity"] += 1
            kickoff = instant(forecast.get("kickoff_utc"))
            if (match.get("h") != forecast.get("home") or match.get("a") != forecast.get("away")
                    or match.get("l") != forecast.get("league")
                    or local_to_utc(match.get("start"), zone) != kickoff
                    or (int(match.get("hg")), int(match.get("ag"))) !=
                       (int(forecast.get("actual_home_goals")), int(forecast.get("actual_away_goals")))
                    or (fixture.get("home_goals"), fixture.get("away_goals")) !=
                       (forecast.get("actual_home_goals"), forecast.get("actual_away_goals"))):
                continue
            asof = instant(forecast.get("prediction_asof_utc"))
            train_end = instant(forecast.get("train_end_utc"))
            if not (train_end and asof and kickoff and train_end < asof < kickoff):
                continue
            if any(not (asof <= instant(q.get("event_utc")) < kickoff) for q in (ah, ou)):
                continue
            odds = bookmakers[0].get("odds") or {}
            one_x_two = []
            for label in ("open", "close"):
                row = odds.get(label)
                if not isinstance(row, dict):
                    continue
                try:
                    prices = [float(row[key]) for key in ("home", "draw", "away")]
                except (KeyError, TypeError, ValueError):
                    continue
                event = local_to_utc(row.get("time"), zone)
                if event and all(price > 1 for price in prices):
                    one_x_two.append((event, prices, label))
            if not one_x_two:
                continue
            counts["valid_1X2"] += 1
            one_x_two = [row for row in one_x_two if asof <= row[0] < kickoff]
            if not one_x_two:
                continue
            counts["valid_event_time_1X2"] += 1
            event, prices, price_point = max(one_x_two, key=lambda row: row[0])
            receipt = instant(receipt_index.get(match_id, {}).get("captured_at_utc"))
            if not receipt or receipt < max(event, instant(ah["event_utc"]), instant(ou["event_utc"])):
                continue
            counts["valid_receipt"] += 1
            response_hash = digest(raw)
            response_hashes.add(response_hash)
            rows.append({
                "match_id": match_id, "league": forecast["league"], "year": str(forecast["kickoff_utc"])[:4],
                "kickoff_utc": forecast["kickoff_utc"], "train_end_utc": forecast["train_end_utc"],
                "prediction_asof_utc": forecast["prediction_asof_utc"],
                "actual_home_goals": forecast["actual_home_goals"], "actual_away_goals": forecast["actual_away_goals"],
                "quotes": {"AH": ah, "OU": ou, "X1X2": {
                    "event_utc": event.isoformat().replace("+00:00", "Z"), "prices": prices,
                    "snapshot_part": price_point, "receipt_utc": receipt.isoformat().replace("+00:00", "Z")}},
                "source_response_sha256": response_hash,
            })
    if len({row["match_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate fixture identity in prepared batch")
    encoded = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows).encode()
    output.write_bytes(encoded)
    os.chmod(output, 0o600)
    counts["included"] = len(rows)
    return {"coverage": counts, "forecast_input_sha256": digest(forecasts.read_bytes()),
            "prepared_batch_sha256": digest(encoded),
            "response_hash_set_sha256": digest("\n".join(sorted(response_hashes)).encode())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--output-private", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    print(json.dumps(prepare(args.private_dir, args.forecasts, args.output_private, args.source_timezone), sort_keys=True))


if __name__ == "__main__":
    main()
