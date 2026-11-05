#!/usr/bin/env python3
"""Replay M5 OU predictions on M1's saved historical Crown quote events.

The M1 archive marks these quotes as fetched later, so the result is an
event-time historical reconstruction, not proof of contemporaneous receipt or
execution. Outputs are aggregate-only; all inputs remain local/private.
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

from m3_grid_crown_replay import expected_return, legs_result, payout


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def dt(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (TypeError, ValueError):
        return None


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def read_jsonl(path: Path):
    raw = path.read_bytes()
    rows = {}
    duplicates = 0
    for line in raw.decode("utf-8-sig").splitlines():
        try:
            row = json.loads(line)
            key = str(row["match_id"])
            if key in rows:
                duplicates += 1
                continue
            rows[key] = row
        except (ValueError, KeyError, TypeError):
            continue
    return raw, rows, duplicates


def identity_key(league, kickoff, home, away):
    return (norm(league), kickoff.date().isoformat(), norm(home), norm(away))


def select_rows(m1_raw, baseline, candidate, manifest):
    counters = Counter()
    eligible = {}
    canonical_keys = defaultdict(list)
    for line in m1_raw.decode("utf-8-sig").splitlines():
        try:
            quote = json.loads(line)
        except ValueError:
            counters["malformed_M1_rows"] += 1
            continue
        if quote.get("bookmaker") != "crown":
            counters["non_Crown_rows"] += 1
            continue
        counters["M1_Crown_observation_rows"] += 1
        mid = str(quote.get("fixture_id") or "")
        f = candidate.get(mid); b = baseline.get(mid); result = manifest.get(mid)
        if not f or not b:
            counters["missing_M5_baseline_or_candidate"] += 1
            continue
        counters["exact_M5_ID_join"] += 1
        ko = dt(quote.get("kickoff_at")); event = dt(quote.get("crown_event_at"))
        asof = dt(f.get("prediction_asof_utc")); train_end = dt(f.get("train_end_utc"))
        b_asof = dt(b.get("prediction_asof_utc")); b_train_end = dt(b.get("train_end_utc"))
        if not all((ko, event, asof, train_end, b_asof, b_train_end)):
            counters["missing_or_invalid_timestamps"] += 1
            continue
        if (quote.get("history_fetched_later_not_executable_receipt") is not True
                or event >= ko):
            counters["not_historical_prematch_eventtime"] += 1
            continue
        if (dt(f.get("kickoff")) != ko or dt(b.get("kickoff")) != ko
                or f.get("league") != b.get("league")
                or f.get("home") != b.get("home") or f.get("away") != b.get("away")
                or norm(quote.get("competition")) != norm(f.get("league"))
                or norm(quote.get("home")) != norm(f.get("home"))
                or norm(quote.get("away")) != norm(f.get("away"))):
            counters["fixture_identity_conflict"] += 1
            continue
        counters["exact_fixture_identity"] += 1
        if not (train_end < asof <= event < ko and b_train_end < b_asof <= event):
            counters["forecast_quote_time_order_fail"] += 1
            continue
        counters["M5_forecast_precedes_Crown_event"] += 1
        if not result:
            counters["missing_independent_schedule_result"] += 1
            continue
        rko = dt(result.get("kickoff_utc"))
        if (rko != ko or result.get("league") != f.get("league")
                or norm(result.get("home")) != norm(f.get("home"))
                or norm(result.get("away")) != norm(f.get("away"))
                or result.get("home_goals") != f.get("home_goals")
                or result.get("away_goals") != f.get("away_goals")
                or not isinstance(result.get("home_goals"), int)
                or not isinstance(result.get("away_goals"), int)):
            counters["schedule_result_identity_or_score_conflict"] += 1
            continue
        result_status = str(result.get("schedule_status") or "").lower()
        if result_status and result_status not in {"full", "ft", "finished"}:
            counters["schedule_result_not_finished"] += 1
            continue
        try:
            line = float(quote["asian_ou_line"])
            over = float(quote["over_price"]); under = float(quote["under_price"])
        except (KeyError, TypeError, ValueError):
            counters["invalid_Crown_contract"] += 1
            continue
        if (not all(math.isfinite(x) for x in (line, over, under))
                or line < 0 or abs(line * 4 - round(line * 4)) > 1e-8
                or over <= 1 or under <= 1):
            counters["invalid_Crown_contract"] += 1
            continue
        key = identity_key(f["league"], ko, f["home"], f["away"])
        item = {"match_id": mid, "league": f["league"], "kickoff": ko,
                "event": event, "line": line, "prices": (over, under),
                "forecast": f, "baseline": b, "result": result,
                "source_quote_sha": quote.get("crown_quote_evidence_sha256")}
        previous = eligible.get(mid)
        if previous is None or event > previous["event"]:
            eligible[mid] = item
        canonical_keys[key].append(mid)

    duplicates = {key for key, mids in canonical_keys.items() if len(set(mids)) > 1}
    if duplicates:
        for mid, item in list(eligible.items()):
            if identity_key(item["league"], item["kickoff"],
                            item["forecast"]["home"], item["forecast"]["away"]) in duplicates:
                eligible.pop(mid)
        counters["normalized_fixture_identity_collision_groups_dropped"] = len(duplicates)
    counters["unique_fixture_markets_after_dedup"] = len(eligible)
    return sorted(eligible.values(), key=lambda r: (r["event"], r["match_id"])), counters


def settle(row, model):
    forecast = row["forecast"] if model == "M5_recency" else row["baseline"]
    grid = (forecast.get("prediction") or {}).get("grid")
    if not grid:
        raise ValueError("M5 forecast missing score probability grid")
    prices = row["prices"]
    sides = ("over", "under")
    ev = [expected_return(grid, "OU", side, row["line"], price)
          for side, price in zip(sides, prices)]
    index = 0 if ev[0] >= ev[1] else 1
    goals = (row["result"]["home_goals"], row["result"]["away_goals"])
    legs, category = legs_result("OU", sides[index], row["line"], *goals)
    return payout(legs, prices[index]), category


def metrics(rows, model, seed):
    scored = [(r, *settle(r, model)) for r in rows]
    n = len(scored); counts = Counter(x[2] for x in scored)
    net = math.fsum(x[1] for x in scored)
    by_time = defaultdict(float)
    for row, units, _ in scored:
        by_time[row["event"]] += units
    equity = peak = drawdown = 0.0
    for instant in sorted(by_time):
        equity += by_time[instant]; peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    rng = random.Random(seed); units = [x[1] for x in scored]
    boot = sorted(100 * math.fsum(units[rng.randrange(n)] for _ in range(n)) / n
                  for _ in range(10000)) if n else []
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": counts["win"], "half_win": counts["half_win"],
            "push": counts["push"], "half_loss": counts["half_loss"],
            "full_loss": counts["loss"], "net_units": round(net, 6),
            "roi_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_by_quote_event_units": round(drawdown, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": {
                "lower_2_5_pct": round(boot[249], 6),
                "upper_97_5_pct": round(boot[9749], 6),
                "resamples": 10000, "seed": seed} if n else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m1-observations", type=Path, required=True)
    ap.add_argument("--baseline-forecasts", type=Path, required=True)
    ap.add_argument("--candidate-forecasts", type=Path, required=True)
    ap.add_argument("--finished-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    m1_raw = a.m1_observations.read_bytes()
    base_raw, baseline, base_dups = read_jsonl(a.baseline_forecasts)
    cand_raw, candidate, cand_dups = read_jsonl(a.candidate_forecasts)
    manifest_raw = a.finished_manifest.read_bytes()
    manifest_doc = json.loads(manifest_raw)
    if manifest_doc.get("protocol") not in {
            "M5_M1_SCOPE_HISTORICAL_FT_CANDIDATES_V1",
            "M5_PRIVATE_PARTIAL_SCHEDULE_MANIFEST_V1"}:
        raise ValueError("unexpected finished-match manifest protocol")
    if not isinstance(manifest_doc.get("rows"), list):
        raise ValueError("finished-match manifest rows missing")
    manifest = {str(r["match_id"]): r for r in manifest_doc["rows"]}
    rows, counters = select_rows(m1_raw, baseline, candidate, manifest)
    counters["duplicate_baseline_forecast_rows"] = base_dups
    counters["duplicate_candidate_forecast_rows"] = cand_dups
    by_model = {model: metrics(rows, model, 20261120 + i)
                for i, model in enumerate(("M5_baseline", "M5_recency"))}
    by_league = {}
    groups = defaultdict(list)
    for row in rows:
        groups[row["league"]].append(row)
    # League aggregates deliberately omit bootstrap intervals to keep output compact.
    for i, (league, group) in enumerate(sorted(groups.items())):
        by_league[league] = {}
        for model in ("M5_baseline", "M5_recency"):
            lm = metrics(group, model, 20261200 + i)
            by_league[league][model] = {k: lm[k] for k in (
                "unique_fixtures", "net_units", "roi_pct")}
    years = sorted({str(r["kickoff"].year) for r in rows})
    report = {
        "protocol": "M5_M1_CROWN_OU_EVENTTIME_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "market": "OU",
        "quote_evidence_class": "Crown historical source event time; fetch occurred later; not contemporaneous receipt proof",
        "training_asof_quote_kickoff_order": "train_end < forecast_asof <= Crown event < kickoff",
        "unique_kickoff_years": years,
        "input_sha256": {"M1_Crown_observations": sha(m1_raw),
                         "M5_baseline_forecasts": sha(base_raw),
                         "M5_recency_forecasts": sha(cand_raw),
                         "finished_fixture_manifest": sha(manifest_raw)},
        "finished_fixture_manifest_protocol": manifest_doc["protocol"],
        "coverage_counts": dict(counters),
        "models_same_Crown_event_time_quote_and_FT": by_model,
        "by_league": by_league,
        "crown_prices_used_only": True,
        "strategy": "One 1U side per unique fixture; select the higher expected-return side from each model's pre-event score grid at the M1 Crown OU line and two prices; no ROI/EV threshold or league/time/price filter; correct split-line settlement.",
        "limitations": [
            "M1 archive explicitly marks these historical quotes as fetched later, so source event timestamps do not prove contemporaneous receipt or executable fill.",
            "This is an event-time historical reconstruction and is reported separately from Crown snapshots with verified receipt-before-kickoff.",
            "All eligible matches are from the 2026 season; the M5 forecasts are out of sample in model time, but this archive period has appeared in earlier exploratory analyses.",
            "The sample is below 10,000 and cannot establish stable profitability.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "coverage": dict(counters),
                      "models": {m: {x: v[x] for x in (
                          "unique_fixtures", "net_units", "roi_pct",
                          "max_drawdown_by_quote_event_units")}
                                  for m, v in by_model.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
