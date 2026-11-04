#!/usr/bin/env python3
"""Descriptive, non-deployable Crown quote timing/price/line audit.

Reads only private M5 forecast and Crown endpoint files. Public output contains
aggregate counts, score summaries and input hashes; no fixture IDs, team names,
timestamps, exact lines or prices. Quantile groups are descriptive and must not
be interpreted as approved filters or independent strategy validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.crown_historical_capture import local_to_utc
from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def quantile_edges(values: list[float]) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        return []
    return [ordered[min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1)] for q in (.25, .5, .75)]


def bucket(value: float, edges: list[float]) -> int:
    for i, edge in enumerate(edges):
        if value <= edge:
            return i
    return len(edges)


def summarize(rows: list[dict], key: str) -> dict:
    values = [r[key] for r in rows]
    edges = quantile_edges(values)
    grouped = defaultdict(list)
    for row in rows:
        grouped[bucket(row[key], edges)].append(row)
    output = {}
    for i, group in sorted(grouped.items()):
        units = sum(r["units"] for r in group)
        output[str(i + 1)] = {
            "fixtures": len(group), "net_units": round(units, 6),
            "roi_pct": round(100 * units / len(group), 6),
            "full_win": sum(r["category"] == "win" for r in group),
            "half_win": sum(r["category"] == "half_win" for r in group),
            "push": sum(r["category"] == "push" for r in group),
            "half_loss": sum(r["category"] == "half_loss" for r in group),
            "full_loss": sum(r["category"] == "loss" for r in group),
        }
    return {"quantile_cut_values_private": True, "groups": output}


def run(private_dir: Path, source_timezone: str, output: Path) -> None:
    forecast_path = private_dir / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecasts = {}
    raw_forecasts = forecast_path.read_bytes()
    for line in raw_forecasts.decode().splitlines():
        try:
            row = json.loads(line)
            forecasts[str(row["match_id"])] = row
        except Exception:
            continue
    zone = ZoneInfo(source_timezone)
    results = {"AH": {}, "OU": {}}
    response_hashes = set()
    for market, list_key in (("AH", "asian_list"), ("OU", "goal_list")):
        rows = []
        movement_fixture_count = 0
        for mid, forecast in forecasts.items():
            path = private_dir / "crown-responses" / f"{mid}.json"
            if not path.exists():
                continue
            try:
                raw = path.read_bytes()
                payload = json.loads(raw)
                matches = [m for m in payload.get("data", []) if isinstance(m, dict) and str(m.get("id")) == mid]
                books = [b for m in matches for b in (m.get("bookmakers") or []) if b.get("slug") == "crown"]
                if payload.get("success") != 1 or len(matches) != 1 or len(books) != 1:
                    continue
                match = matches[0]
                if (match.get("h"), match.get("a"), match.get("l")) != (forecast["home"], forecast["away"], forecast["league"]):
                    continue
                kickoff = datetime.fromisoformat(forecast["kickoff"].replace("Z", "+00:00")).astimezone(timezone.utc)
                if local_to_utc(match.get("start"), zone) != kickoff:
                    continue
                if (int(match.get("hg")), int(match.get("ag"))) != (int(forecast["home_goals"]), int(forecast["away_goals"])):
                    continue
                asof = datetime.fromisoformat(forecast["prediction_asof_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
                movements = []
                for movement in books[0].get(list_key) or []:
                    if not isinstance(movement, list) or len(movement) != 8 or movement[0] is not None or movement[7] not in (0, "0", False):
                        continue
                    observed = local_to_utc(movement[4], zone)
                    try:
                        pieces = [float(x.strip()) for x in str(movement[1]).split(",")]
                        line_value = sum(pieces) / len(pieces)
                        prices = (float(movement[2]), float(movement[3]))
                    except (ValueError, TypeError, ZeroDivisionError):
                        continue
                    if (not observed or observed < asof or observed >= kickoff or len(pieces) not in (1, 2)
                            or abs(line_value * 4 - round(line_value * 4)) > 1e-8
                            or any(not math.isfinite(p) or p <= 1 for p in prices)):
                        continue
                    movements.append((observed, line_value, prices))
                if not movements:
                    continue
                movements.sort(key=lambda x: x[0])
                movement_fixture_count += 1
                first, last = movements[0], movements[-1]
                grid = forecast["prediction"]["grid"]
                sides = ("home", "away") if market == "AH" else ("over", "under")
                evs = [expected_return(grid, market, side, last[1], price) for side, price in zip(sides, last[2])]
                side_index = 0 if evs[0] >= evs[1] else 1
                side = sides[side_index]
                legs, category = legs_result(market, side, last[1], int(forecast["home_goals"]), int(forecast["away_goals"]))
                units = payout(legs, last[2][side_index])
                price_delta = last[2][side_index] - first[2][side_index]
                rows.append({"units": units, "category": category,
                             "quote_age_hours": (kickoff - last[0]).total_seconds() / 3600,
                             "latest_price": last[2][side_index],
                             "abs_line_change": abs(last[1] - first[1]),
                             "price_change": price_delta})
                response_hashes.add(sha(raw))
            except Exception:
                continue
        units = sum(r["units"] for r in rows)
        results[market] = {
            "unique_oos_quote_fixtures": len(rows), "fixtures_with_valid_quote_movement": movement_fixture_count,
            "settled_bets": len(rows), "net_units": round(units, 6),
            "roi_pct": round(100 * units / len(rows), 6) if rows else None,
            "by_quote_age_to_kickoff_quartile": summarize(rows, "quote_age_hours"),
            "by_selected_price_quartile": summarize(rows, "latest_price"),
            "by_absolute_open_to_latest_line_change_quartile": summarize(rows, "abs_line_change"),
            "by_selected_side_price_change_quartile": summarize(rows, "price_change"),
        }
    report = {
        "protocol": "M5_CROWN_QUOTE_FACTOR_DESCRIPTIVE_AUDIT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_rows": len(forecasts), "forecast_sha256": sha(raw_forecasts),
        "private_crown_response_hash_set_sha256": hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest(),
        "markets": results,
        "method": "For each fixture-market, select the latest source-time Crown pre-kickoff movement after the UTC OOS forecast as-of; select the model's higher-expected-return side without an EV threshold; settle one unit using quarter-line split settlement. Descriptive quartiles are calculated separately by market from this observed sample.",
        "limitations": ["Partial historical source coverage and one dominant recent OOS year.", "Post-hoc descriptive associations only; quantile groups are not approved filters or independent ROI validation.", "No fixture identifiers, team names, source timestamps, exact lines or prices are included."],
        "crown_prices_used_only": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"markets": {k: {x: v.get(x) for x in ("unique_oos_quote_fixtures", "net_units", "roi_pct")} for k, v in results.items()}, "output": str(output)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.private_dir, args.source_timezone, args.output)


if __name__ == "__main__":
    main()
