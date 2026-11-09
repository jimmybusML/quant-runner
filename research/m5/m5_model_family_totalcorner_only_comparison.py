#!/usr/bin/env python3
"""Compare frozen M1/MR1/M3 forecasts on TotalCorner-only M5 quotes.

This is a source-specific historical event-time replay. Provider receipt time
is kept separate from quote event time; row-level inputs/outputs remain local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from research.m5.m3_grid_crown_replay import legs_result, payout
from research.m5.m5_model_family_canonical_crown_comparison import (
    CAT, M3_KEYS, M4_PASS_LEAGUES, category_return, canonical_probs, grid_distribution,
    opposite, score,
)
from research.m5.m5_source_union_replay import event_rows, fixture_row, instant, read_jsonl, raw_event
from research.m5.crown_historical_capture import local_to_utc


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def outside_repo(path: Path, repo: Path) -> Path:
    result = path.expanduser().resolve()
    if result == repo or repo in result.parents:
        raise ValueError("fixture-level output must remain outside the public repository")
    result.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(result.parent, 0o700)
    return result


def load_jsonl(path: Path, id_key="match_id", market_key="market"):
    output = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row[id_key]), row[market_key])
        if key in output:
            raise ValueError(f"duplicate forecast key: {path.name} {key}")
        output[key] = row
    return output


def summarize(rows, market):
    pnl = [float(row["pnl"]) for row in rows]
    counts = Counter(row["category"] for row in rows)
    ll, brier = score([(row["category"], row["distribution"]) for row in rows])
    by_event = defaultdict(float)
    by_year = defaultdict(list)
    by_source = defaultdict(list)
    receipts = Counter()
    for row in rows:
        by_event[row["quote_event_utc"]] += row["pnl"]
        by_year[row["kickoff_utc"][:4]].append(row["pnl"])
        by_source[row["source"]].append(row["pnl"])
        receipts["pre_kickoff" if row["receipt_pre_kickoff"] else "post_kickoff"] += 1
    equity = peak = drawdown = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "unique_fixture_markets": len(rows), "simulated_bets": len(rows),
        "settled_bets": len(rows), "pending_bets": 0, "stake_units": len(rows),
        "net_units": round(math.fsum(pnl), 6),
        "roi_pct": round(100 * math.fsum(pnl) / len(rows), 6) if rows else None,
        "settlement_counts": {name: counts[name] for name in CAT},
        "max_drawdown_units_by_quote_event_time": round(drawdown, 6),
        "settlement_log_loss": ll, "settlement_brier": brier,
        "receipt_timing": dict(receipts),
        "quote_sources": {"TotalCorner_default": len(rows)} if rows else {},
        "by_utc_kickoff_year": {
            year: {"n": len(values), "net_units": round(math.fsum(values), 6),
                   "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
            for year, values in sorted(by_year.items())
        },
        "by_source": {source: {"n": len(values), "net_units": round(math.fsum(values), 6),
                                "roi_pct": round(100 * math.fsum(values) / len(values), 6)}
                      for source, values in sorted(by_source.items())},
    }


def run(private_dir: Path, private_rows: Path, public_report: Path,
        source_timezone="Asia/Shanghai"):
    repo = Path(__file__).resolve().parents[2]
    root = private_dir.expanduser().resolve()
    model_root = root / "m5-model-oos"
    manifest_raw = (root / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}
    m5_fixtures = {}
    for line in (model_root / "m5_goal_model_forecasts.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        mid = str(row["match_id"])
        if mid in m5_fixtures:
            raise ValueError(f"duplicate M5 forecast fixture {mid}")
        m5_fixtures[mid] = row
    m1 = load_jsonl(model_root / "m1_full_cohort_trace_20261106.jsonl")
    mr1 = load_jsonl(model_root / "mr1_m3_samecohort_trace_20261106.jsonl")
    m3 = {}
    for line in (model_root / "m3_three_model_expanded_20261106.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for market in ("AH", "OU"):
            key = (str(row["match_id"]), market)
            if key in m3:
                raise ValueError(f"duplicate M3 forecast {key}")
            m3[key] = row
    total_idx_path = root / "totalcorner-default-index.jsonl"
    total_idx = {str(row.get("match_id")): row for row in read_jsonl(total_idx_path)
                 if row.get("status") == "verified_fixture_response"}
    zone = ZoneInfo(source_timezone)
    models = {market: {name: [] for name in ("M1", "MR1_V6", *M3_KEYS.keys())}
              for market in ("AH", "OU")}
    models["AH"].update({f"M4_Pass_{name.removeprefix('M3_')}": [] for name in M3_KEYS})
    models["OU"].update({f"M4_Pass_{name.removeprefix('M3_')}": [] for name in M3_KEYS})
    audit = {market: Counter() for market in ("AH", "OU")}
    fixtures_seen = set()
    rows_private = []
    response_hashes = set()

    for mid, receipt_row in total_idx.items():
        forecast = m5_fixtures.get(mid)
        fixture = fixtures.get(mid)
        response_path = root / "totalcorner-default-responses" / f"{mid}.json"
        if not forecast or not fixture or not response_path.exists():
            continue
        try:
            asof, train_end = instant(forecast["prediction_asof_utc"]), instant(forecast["train_end_utc"])
            kickoff = instant(forecast["kickoff"])
            receipt = instant(receipt_row["captured_at_utc"])
            if not asof or not train_end or not kickoff or not receipt or not train_end < asof < kickoff:
                raise ValueError("invalid M5 forecast chronology")
            if (forecast.get("league"), forecast.get("home"), forecast.get("away"), kickoff,
                    int(forecast["home_goals"]), int(forecast["away_goals"])) != (
                    fixture.get("league"), fixture.get("home"), fixture.get("away"),
                    instant(fixture.get("kickoff_utc")), int(fixture["home_goals"]), int(fixture["away_goals"])):
                raise ValueError("M5 forecast/manifest identity mismatch")
            raw = response_path.read_bytes()
            payload = json.loads(raw)
            provider = fixture_row(payload, mid)
            if (payload.get("success") != 1 or provider is None
                    or (provider.get("h"), provider.get("a"), provider.get("l")) !=
                       (fixture.get("home"), fixture.get("away"), fixture.get("league"))
                    or local_to_utc(provider.get("start"), zone) != kickoff):
                raise ValueError("TotalCorner identity/kickoff mismatch")
            if (provider.get("hg") is not None and provider.get("ag") is not None
                    and (int(provider["hg"]), int(provider["ag"])) !=
                    (int(fixture["home_goals"]), int(fixture["away_goals"]))):
                raise ValueError("TotalCorner score mismatch")
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            for market in ("AH", "OU"):
                audit[market]["identity_or_forecast_rejected"] += 1
            continue

        for market in ("AH", "OU"):
            quote = raw_event(event_rows(provider, market, "totalcorner"), market, asof, kickoff, zone)
            if not quote:
                audit[market]["no_valid_quote"] += 1
                continue
            quote_event, line, prices = quote
            if receipt < quote_event:
                audit[market]["receipt_before_quote_event_rejected"] += 1
                continue
            fixtures_seen.add((mid, market))
            response_hashes.add(hashlib.sha256(raw).hexdigest())
            actual = (int(fixture["home_goals"]), int(fixture["away_goals"]))
            sides = ("home", "away") if market == "AH" else ("over", "under")
            base = {"fixture_id": mid, "market": market, "line": float(line),
                    "prices": list(map(float, prices)), "quote_event_utc": quote_event.isoformat(),
                    "receipt_utc": receipt.isoformat(), "kickoff_utc": kickoff.isoformat(),
                    "league": fixture["league"], "actual": actual,
                    "source": "TotalCorner_default",
                    "receipt_pre_kickoff": receipt < kickoff}

            m1row = m1.get((mid, market))
            mr1row = mr1.get((mid, market))
            if m1row is None:
                audit[market]["M1_forecast_missing"] += 1
            else:
                if abs(float(m1row["line"]) - float(line)) > 1e-8:
                    audit[market]["M1_line_mismatch"] += 1
                elif (m1row.get("kickoff_utc") != forecast.get("kickoff")
                      or not m1row.get("prediction_asof_utc")
                      or instant(m1row["prediction_asof_utc"]) > quote_event
                      or (m1row.get("event_utc") and instant(m1row["event_utc"]) > quote_event)):
                    audit[market]["M1_time_or_identity_mismatch"] += 1
                else:
                    old_side = str(m1row["m1_side"]).lower()
                    if old_side not in sides:
                        audit[market]["M1_invalid_side"] += 1
                    else:
                        dist = canonical_probs(m1row["m1_distribution"], "M1")
                        side_dists = {old_side: dist, sides[1] if old_side == sides[0] else sides[0]: opposite(dist)}
                        evs = [category_return(side_dists[side], price) for side, price in zip(sides, prices)]
                        index = 0 if evs[0] >= evs[1] else 1
                        side, price = sides[index], float(prices[index])
                        legs, category = legs_result(market, side, float(line), *actual)
                        result = {**base, "model": "M1", "side": side, "price": price,
                                  "category": category, "pnl": payout(legs, price),
                                  "distribution": side_dists[side]}
                        models[market]["M1"].append(result)
                        rows_private.append(result)
                        audit[market]["M1_scored"] += 1

            if mr1row is None:
                audit[market]["MR1_V6_forecast_missing"] += 1
            elif abs(float(mr1row["line"]) - float(line)) > 1e-8:
                audit[market]["MR1_V6_line_mismatch"] += 1
            elif (mr1row.get("kickoff_utc") != forecast.get("kickoff")
                  or not mr1row.get("event_utc")
                  or instant(mr1row["event_utc"]) > quote_event):
                audit[market]["MR1_V6_time_or_identity_mismatch"] += 1
            else:
                try:
                    dist = canonical_probs(mr1row["probabilities"], "MR1")
                    old_side = str(mr1row["side"]).lower()
                    if old_side not in sides:
                        raise ValueError("invalid MR1 side")
                    side_dists = {old_side: dist,
                                  sides[1] if old_side == sides[0] else sides[0]: opposite(dist)}
                    evs = [category_return(side_dists[side], price) for side, price in zip(sides, prices)]
                    index = 0 if evs[0] >= evs[1] else 1
                    side, price = sides[index], float(prices[index])
                    legs, category = legs_result(market, side, float(line), *actual)
                    result = {**base, "model": "MR1_V6", "side": side, "price": price,
                              "category": category, "pnl": payout(legs, price),
                              "distribution": side_dists[side]}
                    models[market]["MR1_V6"].append(result)
                    rows_private.append(result)
                    audit[market]["MR1_V6_scored"] += 1
                except (KeyError, TypeError, ValueError):
                    audit[market]["MR1_V6_invalid_distribution"] += 1
            # M3 archived score grids are line-independent; each is repriced
            # at the actual TotalCorner contract after validating UTC OOS time.
            m3row = m3.get((mid, market))
            if m3row is None:
                audit[market]["M3_forecast_missing"] += 1
                continue
            try:
                if (m3row.get("kickoff_utc") != forecast.get("kickoff")
                        or int(m3row["actual_home_goals"]) != actual[0]
                        or int(m3row["actual_away_goals"]) != actual[1]
                        or not (instant(m3row["train_end_utc"]) < instant(m3row["prediction_asof_utc"])
                                <= quote_event < kickoff)):
                    raise ValueError("M3 fixture or time mismatch")
                for public_name, grid_key in M3_KEYS.items():
                    grid = m3row["model_score_grids"][grid_key]
                    distributions = [grid_distribution(grid, market, side, float(line)) for side in sides]
                    evs = [category_return(dist, float(price)) for dist, price in zip(distributions, prices)]
                    index = 0 if evs[0] >= evs[1] else 1
                    side, price, dist = sides[index], float(prices[index]), distributions[index]
                    legs, category = legs_result(market, side, float(line), *actual)
                    result = {**base, "model": public_name, "side": side, "price": price,
                              "category": category, "pnl": payout(legs, price),
                              "distribution": dist}
                    models[market][public_name].append(result)
                    rows_private.append(result)
                    audit[market][f"{public_name}_scored"] += 1
                    if fixture["league"] not in M4_PASS_LEAGUES:
                        pass_name = f"M4_Pass_{public_name.removeprefix('M3_')}"
                        pass_result = {**result, "model": pass_name}
                        models[market][pass_name].append(pass_result)
                        audit[market][f"{pass_name}_scored"] += 1
            except (KeyError, TypeError, ValueError, OverflowError):
                audit[market]["M3_forecast_time_or_identity_mismatch"] += 1

    private_rows = outside_repo(private_rows, repo)
    with private_rows.open("w", encoding="utf-8") as stream:
        os.chmod(private_rows, 0o600)
        for row in rows_private:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")

    markets_report = {}
    for market in ("AH", "OU"):
        metrics = {name: summarize(rows, market) for name, rows in models[market].items()}
        common = set.intersection(*(set((row["fixture_id"], row["market"]) for row in models[market][name])
                                   for name in ("M1", *M3_KEYS.keys())))
        common_metrics = {}
        for name in ("M1", *M3_KEYS.keys()):
            common_metrics[name] = summarize([row for row in models[market][name]
                                               if (row["fixture_id"], row["market"]) in common], market)
        markets_report[market] = {"models": metrics,
                                  "M1_and_M3_exact_shared_cohort_n": len(common),
                                  "M1_and_M3_exact_shared_cohort": common_metrics}

    total_index_raw = (root / "totalcorner-default-index.jsonl").read_bytes()
    response_hash_set = hashlib.sha256("\n".join(sorted(response_hashes)).encode()).hexdigest()
    report = {
        "protocol": "M5_MODEL_FAMILY_TOTALCORNER_ONLY_OOS_COMPARISON_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": {
            "source": "TotalCorner_default only; Crown not included",
            "unique_quoted_fixture_markets": {market: sum(1 for _, m in fixtures_seen if m == market)
                                               for market in ("AH", "OU")},
            "candidate_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "totalcorner_index_sha256": hashlib.sha256(total_index_raw).hexdigest(),
            "totalcorner_response_hash_set_sha256": response_hash_set,
            "m1_forecast_sha256": sha(model_root / "m1_full_cohort_trace_20261106.jsonl"),
            "mr1_forecast_sha256": sha(model_root / "mr1_m3_samecohort_trace_20261106.jsonl"),
            "m3_grid_sha256": sha(model_root / "m3_three_model_expanded_20261106.jsonl"),
            "m5_forecast_sha256": sha(model_root / "m5_goal_model_forecasts.jsonl"),
            "runner_sha256": sha(Path(__file__).resolve()),
            "receipt_timing": "All selected API receipts post-kickoff; event-time retrospective only",
            "time_rule": "train_end < prediction_asof <= quote_event < kickoff <= response receipt",
        },
        "markets": markets_report,
        "audit": {market: dict(counts) for market, counts in audit.items()},
        "limitations": [
            "MR1 V6 archive has no fixture-ID overlap with this TotalCorner response cohort; no MR1 score is reported.",
            "M1 rows are scored only when their archived settlement line exactly matches the TotalCorner line.",
            "M3 grids are line-independent frozen OOS forecasts and are repriced at the selected TotalCorner contract.",
            "All provider responses were received after kickoff; this is not contemporaneous executable ROI.",
            "M4 entries apply the existing Pass research rule to M3; M4 is not an independent predictive model.",
        ],
    }
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                             encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--private-rows", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    args = parser.parse_args()
    report = run(args.private_dir, args.private_rows, args.report, args.source_timezone)
    print(json.dumps({market: {"source_n": report["data"]["unique_quoted_fixture_markets"][market],
                              "models": {name: {"n": result["simulated_bets"], "roi_pct": result["roi_pct"]}
                                         for name, result in values["models"].items()}}
                      for market, values in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
