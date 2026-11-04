#!/usr/bin/env python3
"""Descriptive Crown timing/price/movement audit using received MR1 snapshots.

One latest verified Crown contract is settled per M5 forecast fixture-market.
All factor bins are post-hoc descriptions, not filters or independent ROI tests.
The public artifact contains aggregates and hashes only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def dt(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None

def quantile_edges(values):
    ordered = sorted(values)
    return [ordered[min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1)]
            for q in (0.25, 0.50, 0.75)] if ordered else []

def bucket(value, edges):
    for i, edge in enumerate(edges):
        if value <= edge:
            return i
    return len(edges)

def summarize(rows, key):
    groups = defaultdict(list); edges = quantile_edges([r[key] for r in rows])
    for row in rows:
        groups[bucket(row[key], edges)].append(row)
    result = {}
    for i, group in sorted(groups.items()):
        counts = Counter(r["category"] for r in group); net = sum(r["units"] for r in group); n = len(group)
        result[str(i + 1)] = {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
                              "full_win": counts["win"], "half_win": counts["half_win"], "push": counts["push"],
                              "half_loss": counts["half_loss"], "full_loss": counts["loss"],
                              "net_units": round(net, 6), "roi_pct": round(net * 100 / n, 6) if n else None}
    return {"quantile_cut_values_private": True, "groups": result}

def overall(rows):
    counts = Counter(r["category"] for r in rows); n = len(rows); net = sum(r["units"] for r in rows)
    by_time = defaultdict(float)
    for r in rows: by_time[r["observed"]] += r["units"]
    equity = peak = dd = 0.0
    for t in sorted(by_time):
        equity += by_time[t]; peak = max(peak, equity); dd = max(dd, peak - equity)
    rng = random.Random(20261108); vals = [r["units"] for r in rows]
    boots = sorted(100 * sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)) if n else []
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "full_win": counts["win"], "half_win": counts["half_win"], "push": counts["push"],
            "half_loss": counts["half_loss"], "full_loss": counts["loss"],
            "net_units": round(net, 6), "roi_pct": round(net * 100 / n, 6) if n else None,
            "max_drawdown_units_by_quote_event": round(dd, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": {"lower_2_5_pct": round(boots[249], 6),
                "upper_97_5_pct": round(boots[9749], 6), "resamples": len(boots), "seed": 20261108} if n else None}

def run(mr1_root: Path, forecasts_path: Path, output: Path):
    from research.m5.m3_grid_crown_replay import expected_return, legs_result, payout
    base = mr1_root / "data/prospective-market/shadow-v23"
    index_path, registry_path = base / "snapshot-index.jsonl", base / "fixtures.json"
    index_raw, registry_raw = index_path.read_bytes(), registry_path.read_bytes()
    registry = json.loads(registry_raw)
    forecast_raw = forecasts_path.read_bytes(); forecasts = {}
    for line in forecast_raw.decode().splitlines():
        row = json.loads(line)
        if int(str(row.get("kickoff", ""))[:4]) != 2026:
            continue
        forecasts[str(row["match_id"])] = row
    ft_dir = mr1_root / "data/strategy-shadow-ledger/results"
    fts = {}; ft_hashes = set(); ft_stats = {}
    for path in ft_dir.glob("*.json"):
        try:
            raw = path.read_bytes(); row = json.loads(raw)
            if row.get("status") == "FT" and str(row.get("match_id")) == path.stem and isinstance(row.get("home_goals"), int) and isinstance(row.get("away_goals"), int):
                fts[path.stem] = row; ft_hashes.add(sha(raw)); ft_stats[path] = (len(raw), path.stat().st_mtime_ns)
        except Exception:
            continue
    index_stats = Counter(); snapshots = defaultdict(dict); snap_hashes = set(); snap_stats = {}
    for line in index_raw.decode().splitlines():
        try: entry = json.loads(line)
        except Exception: continue
        mid = str(entry.get("match_id") or ""); forecast = forecasts.get(mid)
        if not forecast or entry.get("classification") != "SNAPSHOT_OK": continue
        path = base / str(entry.get("snapshot_path") or "")
        try:
            st = path.stat(); raw = path.read_bytes(); snapshot = json.loads(raw)
        except Exception: continue
        registry_row = registry.get(mid, {}); kickoff = dt(forecast.get("kickoff")); ft = fts.get(mid)
        if (snapshot.get("match_id") != mid or registry_row.get("match_id") != mid
                or any(registry_row.get(k) != forecast.get(k) for k in ("league", "home", "away"))
                or not kickoff or dt(snapshot.get("kickoff_at")) != kickoff or dt(registry_row.get("kickoff_at")) != kickoff):
            index_stats["identity_or_kickoff_mismatch"] += 1; continue
        if (snapshot.get("source_bookmaker") != "crown" or snapshot.get("source_bookmaker_verified") is not True
                or snapshot.get("prematch_valid") is not True): continue
        if not ft or (ft.get("home_goals"), ft.get("away_goals")) != (forecast.get("home_goals"), forecast.get("away_goals")):
            continue
        observed_ft = dt(ft.get("observed_at")); received = dt(snapshot.get("received_at")); asof = dt(forecast.get("prediction_asof_utc"))
        if not observed_ft or observed_ft <= kickoff or not received or received >= kickoff or not asof or received < asof:
            continue
        snapshot_sha = sha(raw); snap_hashes.add(snapshot_sha); snap_stats[path] = (st.st_size, st.st_mtime_ns)
        for market in ("AH", "OU"):
            quote = snapshot.get(market) or {}; observed = dt(quote.get("observed_at_utc") or quote.get("observed_at"))
            if not observed or not asof <= observed <= received < kickoff or quote.get("closed") is True: continue
            try:
                line_value = float(quote["line"])
                prices = (float(quote["home_price"]), float(quote["away_price"])) if market == "AH" else (float(quote["over_price"]), float(quote["under_price"]))
            except (KeyError, TypeError, ValueError): continue
            if not math.isfinite(line_value) or abs(line_value * 4 - round(line_value * 4)) > 1e-8 or any(not math.isfinite(p) or p <= 1 for p in prices): continue
            quote_key = (observed, received, snapshot_sha)
            snapshots[(mid, market)][quote_key] = {"observed": observed, "received": received, "kickoff": kickoff,
                "line": line_value, "prices": prices, "snapshot_sha": snapshot_sha}
    if index_path.read_bytes() != index_raw or registry_path.read_bytes() != registry_raw:
        raise RuntimeError("MR1 index or registry changed during factor audit")
    for path, (size, mtime) in {**snap_stats, **ft_stats}.items():
        if path.stat().st_size != size or path.stat().st_mtime_ns != mtime:
            raise RuntimeError("MR1 snapshot or FT changed during factor audit")

    results = {}; selected_hashes = set()
    for market in ("AH", "OU"):
        rows = []
        for (mid, mkt), quote_map in snapshots.items():
            if mkt != market or not quote_map: continue
            movements = sorted(quote_map.values(), key=lambda q: (q["observed"], q["received"], q["snapshot_sha"]))
            first, last = movements[0], movements[-1]; forecast = forecasts[mid]
            grid = forecast["prediction"]["grid"]
            sides = ("home", "away") if market == "AH" else ("over", "under")
            ev = [expected_return(grid, market, side, last["line"], price) for side, price in zip(sides, last["prices"])]
            side_index = 0 if ev[0] >= ev[1] else 1
            legs, category = legs_result(market, sides[side_index], last["line"], int(forecast["home_goals"]), int(forecast["away_goals"]))
            units = payout(legs, last["prices"][side_index]); selected_hashes.add(last["snapshot_sha"])
            rows.append({"observed": last["observed"], "units": units, "category": category,
                         "quote_age_hours": (last["kickoff"] - last["observed"]).total_seconds() / 3600,
                         "selected_price": last["prices"][side_index],
                         "abs_line_change": abs(last["line"] - first["line"]),
                         "selected_side_price_change": last["prices"][side_index] - first["prices"][side_index],
                         "movement_count": len(movements)})
        results[market] = {"overall": overall(rows),
            "by_quote_age_to_kickoff_quartile": summarize(rows, "quote_age_hours"),
            "by_selected_price_quartile": summarize(rows, "selected_price"),
            "by_absolute_open_to_latest_line_change_quartile": summarize(rows, "abs_line_change"),
            "by_selected_side_price_change_quartile": summarize(rows, "selected_side_price_change"),
            "by_received_snapshot_count_quartile": summarize(rows, "movement_count")}
    result = {"protocol": "M5_MR1_VERIFIED_CROWN_QUOTE_FACTOR_AUDIT_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "forecast_sha256": sha(forecast_raw),
        "forecast_fixture_count": len(forecasts), "MR1_snapshot_index_sha256": sha(index_raw),
        "MR1_fixture_registry_sha256": sha(registry_raw),
        "MR1_quote_snapshot_hash_set_sha256": sha("\n".join(sorted(snap_hashes)).encode()),
        "selected_MR1_quote_hash_set_sha256": sha("\n".join(sorted(selected_hashes)).encode()),
        "verified_FT_hash_set_sha256": sha("\n".join(sorted(ft_hashes)).encode()),
        "markets": results,
        "method": "One latest Crown snapshot per unique 2026 forecast fixture-market, with verified Crown source, quote event <= received < kickoff, received >= forecast as-of, exact MR1 registry identity, and separate verified FT observed after kickoff. Model selects higher expected-return side without an EV threshold. Quote-age, selected-price, open-to-latest line/price move and number-of-snapshot quantiles are descriptive only.",
        "limitations": ["Single recent 2026 period; not cross-season stability evidence.", "Post-hoc factor quantiles are descriptive and not strategy filters or independent ROI tests.", "Quarter-line settlement rules are applied to the selected latest quote.", "Public artifact contains aggregate metrics and hashes only; no match IDs, teams, exact timestamps, prices, lines or credentials."],
        "crown_prices_used_only": True}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "markets": {m: x["overall"] for m, x in results.items()}}, indent=2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--forecasts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); run(a.mr1_root, a.forecasts, a.output)

if __name__ == "__main__": main()
