#!/usr/bin/env python3
"""Compare M5 with the MR1 V6 cross-market model on the same Crown quotes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower())


def read_forecasts(path: Path):
    raw = path.read_bytes()
    rows = {}
    for line in raw.decode().splitlines():
        try:
            row = json.loads(line)
            rows[str(row["match_id"])] = row
        except Exception:
            continue
    return raw, rows


def build_common_quotes(mr1_root: Path, baseline_path: Path, candidate_path: Path):
    data = mr1_root / "data"
    base = data / "prospective-market/shadow-v23"
    index_raw = (base / "snapshot-index.jsonl").read_bytes()
    registry_raw = (base / "fixtures.json").read_bytes()
    registry = json.loads(registry_raw)
    index = {}
    for line in index_raw.decode().splitlines():
        try:
            entry = json.loads(line)
            index[str(entry.get("key"))] = entry
        except Exception:
            continue
    baseline_raw, baseline = read_forecasts(baseline_path)
    candidate_raw, candidate = read_forecasts(candidate_path)
    ft_dir = data / "strategy-shadow-ledger/results"
    fts = {}
    ft_hashes = {}
    for path in ft_dir.glob("*.json"):
        try:
            raw = path.read_bytes()
            row = json.loads(raw)
            if (row.get("status") == "FT" and str(row.get("match_id")) == path.stem
                    and isinstance(row.get("home_goals"), int) and isinstance(row.get("away_goals"), int)):
                fts[path.stem] = row
                ft_hashes[path.stem] = sha(raw)
        except Exception:
            continue
    record_dir = data / "mr1-v6-cross-market/forward/records"
    chosen = {}
    counters = Counter()
    record_hashes = set()
    snapshot_hashes = set()
    ft_used = set()
    snapshot_stats = {}

    for record_path in record_dir.glob("*.json"):
        try:
            record_raw = record_path.read_bytes()
            record = json.loads(record_raw)
        except Exception:
            continue
        if record.get("source_bookmaker") != "crown" or record.get("source_bookmaker_verified") is not True:
            continue
        counters["verified_crown_forward_records"] += 1
        mid = str(record.get("match_id") or "")
        forecast = candidate.get(mid)
        baseline_forecast = baseline.get(mid)
        if not forecast or not baseline_forecast:
            continue
        counters["candidate_exact_id_records"] += 1
        ko = dt(forecast.get("kickoff")); asof = dt(forecast.get("prediction_asof_utc"))
        candidate_train_end = dt(forecast.get("train_end_utc"))
        baseline_asof = dt(baseline_forecast.get("prediction_asof_utc"))
        baseline_train_end = dt(baseline_forecast.get("train_end_utc"))
        if (not ko or not asof or not candidate_train_end or candidate_train_end >= asof
                or not baseline_asof or not baseline_train_end or baseline_train_end >= baseline_asof
                or any(dt(f.get("kickoff")) != ko for f in (forecast, baseline_forecast))):
            counters["forecast_time_fail"] += 1
            continue
        identity_fields = ("league", "home", "away", "home_goals", "away_goals")
        if any(forecast.get(k) != baseline_forecast.get(k) for k in identity_fields):
            counters["baseline_candidate_identity_conflict"] += 1
            continue
        if (record.get("league") != forecast.get("league") or dt(record.get("kickoff_at")) != ko
                or record.get("outcome_accessed") is not False
                or record.get("production_write") is not False
                or record.get("telegram_write") is not False
                or record.get("formal_candidate_write") is not False):
            counters["forward_record_identity_or_outcome_flag_fail"] += 1
            continue
        reg = registry.get(mid, {})
        if (any(reg.get(k) != forecast.get(v) for k, v in (("league", "league"), ("home", "home"), ("away", "away")))
                or dt(reg.get("kickoff_at")) != ko):
            counters["fixture_registry_identity_fail"] += 1
            continue
        ft = fts.get(mid)
        if (not ft or (ft.get("home_goals"), ft.get("away_goals")) !=
                (forecast.get("home_goals"), forecast.get("away_goals"))
                or dt(ft.get("observed_at")) is None or dt(ft.get("observed_at")) <= ko):
            counters["independent_ft_fail"] += 1
            continue
        entry = index.get(str(record.get("source_snapshot_key") or ""))
        if not entry or entry.get("match_id") != mid:
            counters["snapshot_index_join_fail"] += 1
            continue
        snapshot_path = base / str(entry.get("snapshot_path") or "")
        try:
            stat = snapshot_path.stat(); snapshot_raw = snapshot_path.read_bytes(); snapshot = json.loads(snapshot_raw)
        except Exception:
            counters["snapshot_read_fail"] += 1
            continue
        snapshot_hash = sha(snapshot_raw)
        if (snapshot_hash != record.get("source_snapshot_sha256")
                or snapshot_hash != entry.get("snapshot_sha256")
                or snapshot.get("match_id") != mid
                or snapshot.get("source_bookmaker") != "crown"
                or snapshot.get("source_bookmaker_verified") is not True
                or snapshot.get("prematch_valid") is not True):
            counters["source_snapshot_verification_fail"] += 1
            continue
        received = dt(record.get("received_at")); snapshot_received = dt(snapshot.get("received_at"))
        if not received or received != snapshot_received or received >= ko:
            counters["source_receipt_time_fail"] += 1
            continue
        record_hashes.add(sha(record_raw)); snapshot_hashes.add(snapshot_hash); ft_used.add(ft_hashes[mid])
        for market in ("AH", "OU"):
            quote = snapshot.get(market) or {}
            observed = dt(quote.get("observed_at_utc") or quote.get("observed_at"))
            record_observed = dt((record.get("quote_times") or {}).get(market))
            if (not observed or observed != record_observed or observed >= ko
                    or observed < asof or observed > received or observed < baseline_asof):
                continue
            try:
                line = float(quote["line"])
                prices = ((float(quote["home_price"]), float(quote["away_price"])) if market == "AH"
                          else (float(quote["over_price"]), float(quote["under_price"])))
            except (KeyError, TypeError, ValueError):
                continue
            if (not math.isfinite(line) or abs(line * 4 - round(line * 4)) > 1e-8
                    or any(not math.isfinite(p) or p <= 1 for p in prices)):
                continue
            v6_market = (record.get("evaluation") or {}).get(market) or {}
            v6_selected = v6_market.get("selected") or {}
            sides = ("home", "away") if market == "AH" else ("over", "under")
            selected_side = v6_selected.get("side")
            expected_v6_line = -line if market == "AH" and selected_side == "away" else line
            if (v6_selected.get("side") not in sides
                    or abs(float(v6_selected.get("line", math.inf)) - expected_v6_line) > 1e-8):
                counters[f"v6_selection_contract_mismatch_{market}"] += 1
                continue
            v6_idx = sides.index(v6_selected["side"])
            if abs(float(v6_selected.get("price", math.inf)) - prices[v6_idx]) > 1e-8:
                counters[f"v6_selection_price_mismatch_{market}"] += 1
                continue
            key = (mid, market)
            item = {"match_id": mid, "market": market, "line": line, "prices": prices,
                    "observed": observed, "received": received, "kickoff": ko,
                    "forecast": forecast, "baseline_forecast": baseline_forecast,
                    "ft": ft, "v6_selected": v6_selected, "league": forecast["league"],
                    "snapshot_hash": snapshot_hash, "record_hash": sha(record_raw),
                    "ft_hash": ft_hashes[mid]}
            prior = chosen.get(key)
            if prior is None or (observed, received, sha(record_raw)) > (prior["observed"], prior["received"], prior["record_hash"]):
                chosen[key] = item
            counters[f"eligible_quote_records_{market}"] += 1
        snapshot_stats[snapshot_path] = (stat.st_size, stat.st_mtime_ns)

    if ((base / "snapshot-index.jsonl").read_bytes() != index_raw
            or (base / "fixtures.json").read_bytes() != registry_raw):
        raise RuntimeError("MR1 archive index/registry changed during source comparison")
    for path, (size, mtime) in snapshot_stats.items():
        if path.stat().st_size != size or path.stat().st_mtime_ns != mtime:
            raise RuntimeError("MR1 Crown snapshot changed during source comparison")
    return (chosen, counters, baseline_raw, candidate_raw, index_raw, registry_raw,
            record_hashes, snapshot_hashes, ft_used, len(baseline), len(candidate))


def strategy(row, model_name):
    market = row["market"]
    sides = ("home", "away") if market == "AH" else ("over", "under")
    if model_name == "MR1_V6_cross_market":
        side = row["v6_selected"]["side"]
        price = row["v6_selected"]["price"]
    else:
        forecast = row["forecast"] if model_name == "M5_recency" else row["baseline_forecast"]
        grid = (forecast.get("prediction") or {}).get("grid")
        if not grid:
            raise ValueError("missing M5 probability grid")
        evs = [expected_return(grid, market, side, row["line"], price)
               for side, price in zip(sides, row["prices"])]
        idx = 0 if evs[0] >= evs[1] else 1
        side = sides[idx]; price = row["prices"][idx]
    score = (int(row["ft"]["home_goals"]), int(row["ft"]["away_goals"]))
    legs, category = legs_result(market, side, row["line"], *score)
    return payout(legs, price), category


def metric(rows, model_name, seed, include_bootstrap=True):
    scored = [(r, *strategy(r, model_name)) for r in rows]
    n = len(scored); counts = Counter(x[2] for x in scored); net = sum(x[1] for x in scored)
    by_time = defaultdict(float)
    for row, units, _ in scored:
        by_time[row["observed"]] += units
    equity = peak = dd = 0.0
    for t in sorted(by_time):
        equity += by_time[t]; peak = max(peak, equity); dd = max(dd, peak - equity)
    rng = random.Random(seed); values = [x[1] for x in scored]
    boots = sorted(100 * sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)) if n and include_bootstrap else []
    return {"unique_forecast_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": counts["win"], "half_win": counts["half_win"], "push": counts["push"],
            "half_loss": counts["half_loss"], "full_loss": counts["loss"],
            "net_units": round(net, 6), "roi_pct": round(100 * net / n, 6) if n else None,
            "max_drawdown_units_by_quote_time": round(dd, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": {"lower_2_5_pct": round(boots[249], 6),
                "upper_97_5_pct": round(boots[9749], 6), "resamples": 10000, "seed": seed} if n and include_bootstrap else None}


def run(mr1_root: Path, baseline_path: Path, candidate_path: Path, output: Path):
    (chosen, counters, baseline_raw, candidate_raw, index_raw, registry_raw,
     record_hashes, snapshot_hashes, ft_hashes, baseline_n, candidate_n) = build_common_quotes(mr1_root, baseline_path, candidate_path)
    reports = {}
    for market in ("AH", "OU"):
        rows = sorted((r for (_, m), r in chosen.items() if m == market), key=lambda r: (r["observed"], r["match_id"]))
        by_model = {}
        for i, model_name in enumerate(("M5_baseline", "M5_recency", "MR1_V6_cross_market")):
            result = metric(rows, model_name, 20261110 + i)
            result["by_league"] = {}
            groups = defaultdict(list)
            for row in rows:
                groups[row["league"]].append(row)
            for league, league_rows in sorted(groups.items()):
                lm = metric(league_rows, model_name, 20261120 + i, include_bootstrap=False)
                result["by_league"][league] = {k: lm[k] for k in ("unique_forecast_fixtures", "net_units", "roi_pct")}
            by_model[model_name] = result
        reports[market] = {"common_unique_fixture_markets": len(rows),
                           "forecast_universe_M5_baseline": baseline_n,
                           "forecast_universe_M5_recency": candidate_n,
                           "coverage_pct_of_recency_forecasts": round(100 * len(rows) / candidate_n, 6) if candidate_n else None,
                           "models_same_Crown_quote_and_FT": by_model}
    report = {"protocol": "M5_MR1_V6_SAME_CROWN_RECEIPT_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "M5_baseline_forecast_sha256": sha(baseline_raw),
        "M5_recency_forecast_sha256": sha(candidate_raw),
        "MR1_snapshot_index_sha256": sha(index_raw),
        "MR1_fixture_registry_sha256": sha(registry_raw),
        "MR1_V6_forward_record_hash_set_sha256": sha("\n".join(sorted(record_hashes)).encode()),
        "verified_Crown_snapshot_hash_set_sha256": sha("\n".join(sorted(snapshot_hashes)).encode()),
        "independent_FT_receipt_hash_set_sha256": sha("\n".join(sorted(ft_hashes)).encode()),
        "markets": reports,
        "validation_counts": dict(counters),
        "method": "Reconstruct one latest MR1 V6 verified-Crown source snapshot per exact M5 forecast fixture-market where train_end < M5 prediction_asof <= Crown quote event <= received < kickoff. Exact fixture registry and source snapshot hash verified; independent post-kickoff FT must match. Compare M5 baseline, M5 recency, and the MR1 V6 cross-market model's saved selected side at the exact same line/prices; 1U Asian settlement, no EV threshold.",
        "limitations": [
            "This is retrospective reconstruction from verified Crown snapshots and M5 UTC OOS forecasts, not contemporaneously archived M5 deployment.",
            "The matched quote period is 2026 and has been studied previously; this is not a new untouched independent sample.",
            "Only matches with both M5 forecast variants, a verifiable V6 record/snapshot, strict time order, and independent FT are included.",
            "The per-market matched sample remains below 10,000 fixtures.",
        ],
        "crown_prices_used_only": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({m: {"n": x["common_unique_fixture_markets"],
                          "models": {k: {kk: v[kk] for kk in ("net_units", "roi_pct", "max_drawdown_units_by_quote_time")}
                                     for k, v in x["models_same_Crown_quote_and_FT"].items()}}
                      for m, x in reports.items()}, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--baseline-forecasts", type=Path, required=True)
    p.add_argument("--candidate-forecasts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.mr1_root, a.baseline_forecasts, a.candidate_forecasts, a.output)


if __name__ == "__main__":
    main()
