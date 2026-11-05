#!/usr/bin/env python3
"""Paired M5 OU replay at earlier M1 and later MR1 Crown quote times.

Uses only fixture IDs present in both source archives, matching Crown OU lines,
two-sided prices, UTC quote events before kickoff, and identical independent
FT. M1 source-event quotes are fetched later and are not receipt proof. The
diagnostic is descriptive and adds no selection threshold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m5 import m3_grid_crown_replay as settlement
from research.m5 import m5_m1_ou_crown_eventtime_replay as m1_event
from research.m5 import m5_mr1_v6_same_crown_oos as mr1_v6


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def quantile(values, p):
    if not values:
        return None
    vals = sorted(values)
    pos = (len(vals) - 1) * p
    lo = math.floor(pos); hi = math.ceil(pos)
    return vals[lo] if lo == hi else vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def score(row, quote, model):
    forecast = row["forecast"] if model == "M5_recency" else row["baseline"]
    grid = (forecast.get("prediction") or {}).get("grid")
    evs = [settlement.expected_return(grid, "OU", side, quote["line"], price)
           for side, price in zip(("over", "under"), quote["prices"])]
    i = 0 if evs[0] >= evs[1] else 1
    goals = (row["goals"][0], row["goals"][1])
    legs, category = settlement.legs_result("OU", ("over", "under")[i],
                                             quote["line"], *goals)
    return settlement.payout(legs, quote["prices"][i]), category, ("over", "under")[i]


def metric(rows, quote_name, model, seed):
    vals = []
    by_time = defaultdict(float)
    counts = Counter()
    for row in rows:
        pnl, category, side = score(row, row[quote_name], model)
        vals.append((row, pnl)); counts[category] += 1
        by_time[row[quote_name]["event"]] += pnl
    n = len(vals); net = math.fsum(x[1] for x in vals)
    equity = peak = dd = 0.0
    for t in sorted(by_time):
        equity += by_time[t]; peak = max(peak, equity); dd = max(dd, peak - equity)
    rng = random.Random(seed); units = [x[1] for x in vals]
    boots = sorted(100 * math.fsum(units[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(10000)) if n else []
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": counts["win"], "half_win": counts["half_win"],
            "push": counts["push"], "half_loss": counts["half_loss"],
            "full_loss": counts["loss"], "net_units": round(net, 6),
            "roi_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_by_quote_event_units": round(dd, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": {
                "lower_2_5_pct": round(boots[249], 6),
                "upper_97_5_pct": round(boots[9749], 6),
                "resamples": 10000, "seed": seed} if n else None}


def paired_delta(rows, model, seed):
    diffs = []
    for row in rows:
        early = score(row, row["m1_quote"], model)[0]
        late = score(row, row["mr1_quote"], model)[0]
        diffs.append(late - early)
    n = len(diffs); net = math.fsum(diffs); rng = random.Random(seed)
    boots = sorted(100 * math.fsum(diffs[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(10000)) if n else []
    return {"paired_unique_fixtures": n, "late_minus_early_net_units": round(net, 6),
            "late_minus_early_roi_percentage_points": round(100 * net / n, 6) if n else None,
            "paired_fixture_bootstrap_95pct_interval_pp": {
                "lower_2_5_pct": round(boots[249], 6),
                "upper_97_5_pct": round(boots[9749], 6),
                "resamples": 10000, "seed": seed} if n else None}


def main():
    p = argparse.ArgumentParser()
    for name in ("mr1-root", "m1-observations", "baseline-forecasts",
                 "candidate-forecasts", "finished-manifest", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    m1_stat = (a.m1_observations.stat().st_size, a.m1_observations.stat().st_mtime_ns)
    manifest_stat = (a.finished_manifest.stat().st_size, a.finished_manifest.stat().st_mtime_ns)
    m1_raw = a.m1_observations.read_bytes(); manifest_raw = a.finished_manifest.read_bytes()
    manifest_doc = json.loads(manifest_raw)
    manifest = {str(r["match_id"]): r for r in manifest_doc["rows"]}
    base_raw, base, _ = m1_event.read_jsonl(a.baseline_forecasts)
    cand_raw, cand, _ = m1_event.read_jsonl(a.candidate_forecasts)
    m1_rows, m1_counts = m1_event.select_rows(m1_raw, base, cand, manifest)
    for r in m1_rows:
        r["goals"] = (r["result"]["home_goals"], r["result"]["away_goals"])
    (mr1_chosen, mr1_counts, _, _, index_raw, registry_raw,
     record_hashes, quote_hashes, ft_hashes, _, _) = mr1_v6.build_common_quotes(
         a.mr1_root, a.baseline_forecasts, a.candidate_forecasts)
    mr1_rows = {}
    for (mid, market), r in mr1_chosen.items():
        if market != "OU":
            continue
        mr1_rows[mid] = {
            "match_id": mid, "league": r["league"], "kickoff": r["kickoff"],
            "goals": (int(r["ft"]["home_goals"]), int(r["ft"]["away_goals"])),
            "forecast": r["forecast"], "baseline": r["baseline_forecast"],
            "mr1_quote": {"event": r["observed"], "line": r["line"],
                          "prices": r["prices"], "received": r["received"]}}
    m1_by_id = {r["match_id"]: r for r in m1_rows}
    common = sorted(set(m1_by_id) & set(mr1_rows))
    rows = []
    for mid in common:
        early, late = m1_by_id[mid], mr1_rows[mid]
        if (early["league"] != late["league"] or early["kickoff"] != late["kickoff"]
                or early["goals"] != late["goals"]
                or not early["event"] < late["mr1_quote"]["event"]
                or late["mr1_quote"]["event"] > late["mr1_quote"]["received"]
                or late["mr1_quote"]["received"] >= late["kickoff"]):
            continue
        rows.append({"match_id": mid, "league": early["league"],
                     "kickoff": early["kickoff"], "goals": early["goals"],
                     "forecast": early["forecast"], "baseline": early["baseline"],
                     "m1_quote": {"event": early["event"], "line": early["line"],
                                  "prices": early["prices"]},
                     "mr1_quote": late["mr1_quote"]})

    gaps = [(r["mr1_quote"]["event"] - r["m1_quote"]["event"]).total_seconds() / 3600
            for r in rows]
    line_changed = [r for r in rows if abs(r["m1_quote"]["line"] - r["mr1_quote"]["line"]) > 1e-8]
    price_changed = [r for r in rows if any(abs(a-b) > 1e-8 for a, b in zip(
        r["m1_quote"]["prices"], r["mr1_quote"]["prices"]))]
    selected_side_changed = {model: sum(score(r, r["m1_quote"], model)[2] !=
                                        score(r, r["mr1_quote"], model)[2] for r in rows)
                             for model in ("M5_baseline", "M5_recency")}
    metrics = {}
    deltas = {}
    for i, model in enumerate(("M5_baseline", "M5_recency")):
        metrics[model] = {
            "early_M1_eventtime_quote": metric(rows, "m1_quote", model, 20261210 + i),
            "later_MR1_receipt_verified_quote": metric(rows, "mr1_quote", model, 20261220 + i),
        }
        deltas[model] = paired_delta(rows, model, 20261230 + i)

    by_change = {}
    for label, group in (("OU_line_changed", line_changed),
                         ("OU_line_unchanged", [r for r in rows if r not in line_changed]),
                         ("either_side_price_changed", price_changed),
                         ("both_prices_unchanged", [r for r in rows if r not in price_changed])):
        by_change[label] = {model: {
            "fixtures": len(group),
            "M1_eventtime_ROI_pct": metric(group, "m1_quote", model, 20261240)["roi_pct"],
            "MR1_later_quote_ROI_pct": metric(group, "mr1_quote", model, 20261241)["roi_pct"],
        } for model in ("M5_baseline", "M5_recency")}

    if ((a.m1_observations.stat().st_size, a.m1_observations.stat().st_mtime_ns) != m1_stat
            or (a.finished_manifest.stat().st_size, a.finished_manifest.stat().st_mtime_ns) != manifest_stat
            or a.baseline_forecasts.read_bytes() != base_raw
            or a.candidate_forecasts.read_bytes() != cand_raw):
        raise RuntimeError("M1/M5 inputs changed during paired quote replay")

    report = {
        "protocol": "M5_M1_MR1_OU_PAIRED_QUOTE_TIMING_DIAGNOSTIC_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "market": "OU",
        "matched_unique_fixtures": len(rows),
        "all_kickoff_years": sorted({r["kickoff"].year for r in rows}),
        "source_evidence": {
            "early": "M1 Crown historical source-event timestamp; fetched later and not contemporaneous receipt proof",
            "late": "MR1 V6 verified Crown snapshot; received before kickoff",
            "pairing_rule": "Same exact fixture ID, league, UTC kickoff, home/away outcome; early M1 Crown event precedes later MR1 Crown event; both forecast as-of times precede their quote events",
        },
        "quote_timing_and_movement": {
            "M1_event_before_MR1_event_fixtures": len(rows),
            "line_changed_fixtures": len(line_changed),
            "line_unchanged_fixtures": len(rows) - len(line_changed),
            "either_side_price_changed_fixtures": len(price_changed),
            "both_prices_unchanged_fixtures": len(rows) - len(price_changed),
            "forecast_side_flipped_between_quotes": selected_side_changed,
            "quote_gap_hours_median": round(statistics.median(gaps), 6) if gaps else None,
            "quote_gap_hours_p90": round(quantile(gaps, .9), 6),
            "mean_absolute_line_change": round(statistics.mean(
                abs(r["mr1_quote"]["line"] - r["m1_quote"]["line"]) for r in rows), 6) if rows else None,
            "mean_absolute_over_price_change": round(statistics.mean(
                abs(r["mr1_quote"]["prices"][0] - r["m1_quote"]["prices"][0]) for r in rows), 6) if rows else None,
            "mean_absolute_under_price_change": round(statistics.mean(
                abs(r["mr1_quote"]["prices"][1] - r["m1_quote"]["prices"][1]) for r in rows), 6) if rows else None,
        },
        "same_fixture_same_forecast_metrics": metrics,
        "paired_later_minus_earlier_roi_delta": deltas,
        "descriptive_change_groups": by_change,
        "validation_counts": {"M1": dict(m1_counts), "MR1_V6": dict(mr1_counts)},
        "input_sha256": {
            "M1_Crown_observations": sha(m1_raw),
            "M5_baseline_forecasts": sha(base_raw),
            "M5_recency_forecasts": sha(cand_raw),
            "finished_fixture_manifest": sha(manifest_raw),
            "MR1_snapshot_index": sha(index_raw),
            "MR1_fixture_registry": sha(registry_raw),
            "MR1_V6_record_hash_set": sha("\n".join(sorted(record_hashes)).encode()),
            "MR1_Crown_snapshot_hash_set": sha("\n".join(sorted(quote_hashes)).encode()),
            "MR1_independent_FT_hash_set": sha("\n".join(sorted(ft_hashes)).encode()),
        },
        "limitations": [
            "Both quote timestamps precede kickoff and both M5 predictions precede their quote event. The early M1 historical source-event rows were fetched later and do not prove fill or contemporaneous receipt.",
            "This compares quote times on the same fixtures; line/price movements are descriptive and do not define a new bet gate.",
            "All fixtures are from 2026 and have appeared in previous M5 exploratory research; this is not an untouched independent profitability confirmation.",
            "Sample size is below 10,000; ROI changes are not evidence of stable profit.",
        ],
        "crown_prices_used_only": True,
        "no_filters_or_gates_added": True,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "matched_unique_fixtures": len(rows),
                      "movement": report["quote_timing_and_movement"],
                      "metrics": {model: {kind: {k: v[k] for k in (
                          "unique_fixtures", "net_units", "roi_pct",
                          "max_drawdown_by_quote_event_units")}
                                          for kind, v in model_metrics.items()}
                                  for model, model_metrics in metrics.items()},
                      "paired_delta": deltas}, sort_keys=True))


if __name__ == "__main__":
    main()
