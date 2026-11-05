#!/usr/bin/env python3
"""Deduplicated M5 OU replay across MR1 receipt and M1 event-time Crown quotes.

For a fixture present in both sources, retain the latest Crown event quote
which is after the M5 as-of time and before kickoff. Quote evidence class stays
visible; M1 historical quotes fetched later are never called receipt-verified.
All raw inputs and fixture rows stay local; only aggregates and hashes publish.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def normalize(row):
    return (m1_event.norm(row["league"]), row["kickoff"].date().isoformat(),
            m1_event.norm(row["forecast"]["home"]),
            m1_event.norm(row["forecast"]["away"]))


def adapt_mr1(row):
    return {"match_id": row["match_id"], "league": row["league"],
            "kickoff": row["kickoff"], "event": row["observed"],
            "line": row["line"], "prices": row["prices"],
            "forecast": row["forecast"], "baseline": row["baseline_forecast"],
            "result": {"home_goals": row["ft"]["home_goals"],
                       "away_goals": row["ft"]["away_goals"]},
            "evidence": "MR1_V6_Crown_received_before_kickoff"}


def choose_union(m1_rows, mr1_rows):
    by_id = {}
    for item in list(m1_rows) + list(mr1_rows):
        key = item["match_id"]
        if key not in by_id:
            by_id[key] = item
            continue
        old = by_id[key]
        # Prefer the later market event; at an exact tie prefer verified receipt.
        rank = (item["event"], item["evidence"].startswith("MR1_"))
        old_rank = (old["event"], old["evidence"].startswith("MR1_"))
        if rank > old_rank:
            by_id[key] = item
    by_identity = defaultdict(list)
    for item in by_id.values():
        by_identity[normalize(item)].append(item)
    ambiguous = {key for key, rows in by_identity.items()
                 if len({r["match_id"] for r in rows}) > 1}
    kept = [rows[0] for key, rows in by_identity.items() if key not in ambiguous]
    return kept, ambiguous


def metrics(rows, model, seed, bootstrap=True):
    scored = [(r, *m1_event.settle(r, model)) for r in rows]
    n = len(scored); counts = Counter(x[2] for x in scored)
    net = math.fsum(x[1] for x in scored)
    by_time = defaultdict(float)
    for row, units, _ in scored:
        by_time[row["event"]] += units
    equity = peak = dd = 0.0
    for instant in sorted(by_time):
        equity += by_time[instant]; peak = max(peak, equity)
        dd = max(dd, peak - equity)
    interval = None
    if n and bootstrap:
        import random
        rng = random.Random(seed); units = [x[1] for x in scored]
        boot = sorted(100 * math.fsum(units[rng.randrange(n)] for _ in range(n)) / n
                      for _ in range(10000))
        interval = {"lower_2_5_pct": round(boot[249], 6),
                    "upper_97_5_pct": round(boot[9749], 6),
                    "resamples": 10000, "seed": seed}
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": counts["win"], "half_win": counts["half_win"],
            "push": counts["push"], "half_loss": counts["half_loss"],
            "full_loss": counts["loss"], "net_units": round(net, 6),
            "roi_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_by_quote_event_units": round(dd, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": interval}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--m1-observations", type=Path, required=True)
    p.add_argument("--baseline-forecasts", type=Path, required=True)
    p.add_argument("--candidate-forecasts", type=Path, required=True)
    p.add_argument("--finished-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    m1_stat = (a.m1_observations.stat().st_size, a.m1_observations.stat().st_mtime_ns)
    manifest_stat = (a.finished_manifest.stat().st_size, a.finished_manifest.stat().st_mtime_ns)
    m1_raw = a.m1_observations.read_bytes()
    manifest_raw = a.finished_manifest.read_bytes()
    manifest_doc = json.loads(manifest_raw)
    manifest = {str(r["match_id"]): r for r in manifest_doc["rows"]}
    baseline_raw, baseline, base_dups = m1_event.read_jsonl(a.baseline_forecasts)
    candidate_raw, candidate, candidate_dups = m1_event.read_jsonl(a.candidate_forecasts)
    m1_rows, m1_counts = m1_event.select_rows(m1_raw, baseline, candidate, manifest)
    for row in m1_rows:
        row["evidence"] = "M1_Crown_eventtime_fetched_later"
    (mr1_chosen, mr1_counts, _, _, mr1_index_raw, mr1_registry_raw,
     record_hashes, snapshot_hashes, ft_hashes, _, _) = mr1_v6.build_common_quotes(
         a.mr1_root, a.baseline_forecasts, a.candidate_forecasts)
    mr1_rows = [adapt_mr1(row) for (mid, market), row in mr1_chosen.items() if market == "OU"]
    union, ambiguous = choose_union(m1_rows, mr1_rows)

    model_names = ("M5_baseline", "M5_recency")
    metrics_all = {name: metrics(union, name, 20261130 + i)
                   for i, name in enumerate(model_names)}
    metrics_m1 = {name: metrics(m1_rows, name, 20261140 + i)
                  for i, name in enumerate(model_names)}
    metrics_mr1 = {name: metrics(mr1_rows, name, 20261150 + i)
                   for i, name in enumerate(model_names)}
    by_class = {}
    for evidence in sorted({r["evidence"] for r in union}):
        group = [r for r in union if r["evidence"] == evidence]
        by_class[evidence] = {name: metrics(group, name, 20261160 + i)
                              for i, name in enumerate(model_names)}
    leagues = defaultdict(list)
    for row in union:
        leagues[row["league"]].append(row)
    by_league = {}
    for i, (league, rows) in enumerate(sorted(leagues.items())):
        by_league[league] = {name: {k: v for k, v in metrics(rows, name,
                              20261200 + i, bootstrap=False).items()
                              if k in ("unique_fixtures", "net_units", "roi_pct")}
                             for name in model_names}
    if ((a.m1_observations.stat().st_size, a.m1_observations.stat().st_mtime_ns) != m1_stat
            or (a.finished_manifest.stat().st_size, a.finished_manifest.stat().st_mtime_ns) != manifest_stat
            or a.baseline_forecasts.read_bytes() != baseline_raw
            or a.candidate_forecasts.read_bytes() != candidate_raw):
        raise RuntimeError("M1 quote archive, M5 forecast, or finished manifest changed during run")

    report = {
        "protocol": "M5_M1_MR1_OU_CROWN_SOURCE_UNION_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "market": "OU",
        "source_priority_rule": "Use the latest Crown market event across identity-verified M1/MR1 candidates; on exact event-time ties prefer MR1 receipt-verified snapshot. Preserve evidence class in the output aggregates.",
        "temporal_rule": "train_end < M5 forecast_asof <= selected Crown event < kickoff",
        "quote_evidence": {
            "MR1_V6": "Verified Crown snapshot and received time before kickoff",
            "M1_V23": "Crown historical source event time before kickoff; archive records fetched later; no contemporaneous receipt proof",
        },
        "input_sha256": {
            "M1_Crown_observations": sha(m1_raw),
            "M5_baseline_forecasts": sha(baseline_raw),
            "M5_recency_forecasts": sha(candidate_raw),
            "finished_fixture_manifest": sha(manifest_raw),
            "MR1_snapshot_index": sha(mr1_index_raw),
            "MR1_fixture_registry": sha(mr1_registry_raw),
            "MR1_V6_record_hash_set": sha("\n".join(sorted(record_hashes)).encode()),
            "MR1_Crown_snapshot_hash_set": sha("\n".join(sorted(snapshot_hashes)).encode()),
            "MR1_independent_FT_hash_set": sha("\n".join(sorted(ft_hashes)).encode()),
        },
        "coverage": {
            "M1_eventtime_unique_fixtures": len(m1_rows),
            "MR1_receipt_verified_unique_fixtures": len(mr1_rows),
            "same_fixture_id_overlap": len({r["match_id"] for r in m1_rows}
                                            & {r["match_id"] for r in mr1_rows}),
            "union_unique_fixture_markets_after_normalized_dedup": len(union),
            "ambiguous_normalized_identity_groups_dropped": len(ambiguous),
            "M1_validation_counters": dict(m1_counts),
            "MR1_validation_counters": dict(mr1_counts),
            "duplicate_baseline_forecast_rows": base_dups,
            "duplicate_candidate_forecast_rows": candidate_dups,
            "all_kickoff_years": sorted({r["kickoff"].year for r in union}),
        },
        "source_stratum_only_metrics": {
            "M1_eventtime_only": metrics_m1,
            "MR1_receipt_verified": metrics_mr1,
        },
        "union_metrics": metrics_all,
        "union_metrics_by_selected_quote_evidence": by_class,
        "union_metrics_by_league": by_league,
        "strategy": "One 1U selection per unique OU fixture; each M5 model independently selects the higher expected-return over/under side from its pre-event score grid at the chosen Crown line/prices; no ROI/EV threshold, league filter, or quantity gate; split-line settlement.",
        "crown_prices_used_only": True,
        "limitations": [
            "The M1 historical quote stratum has source event timestamps but was fetched later; those rows do not prove contemporaneous receipt or fill.",
            "Results are separated by evidence class. The combined union is a historical event-time reconstruction, not an executable P&L ledger.",
            "All selected fixtures are from 2026 and the period has prior exploratory analyses; this is not an untouched independent confirmation.",
            "The deduplicated OU sample remains below 10,000 fixtures.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "coverage": report["coverage"],
                      "union_metrics": {n: {k: v[k] for k in (
                          "unique_fixtures", "net_units", "roi_pct",
                          "max_drawdown_by_quote_event_units")}
                                        for n, v in metrics_all.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
