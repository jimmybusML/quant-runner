#!/usr/bin/env python3
"""Compare archived M1/MR1/M3 forecasts on the canonical M5 Crown cohort.

M3 score grids are repriced on each current Crown contract. M1 and MR1 only
archive categorical settlement distributions, so those forecasts are scored
when their archived handicap/total line exactly matches the selected Crown
line. Aggregate output is public; fixture rows must remain outside the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from research.m5.m3_grid_crown_replay import (
    legs_result, payout, score,
)

MODELS = ("M1", "MR1_V6", "M3_Poisson", "M3_Dixon_Coles", "M3_Bivariate_Poisson")
M3_KEYS = {"M3_Poisson": "poisson", "M3_Dixon_Coles": "dixon_coles",
           "M3_Bivariate_Poisson": "bivariate_poisson"}
M4_PASS_LEAGUES = {"Japan J-League", "Türkiye Super Lig"}
CAT = ("win", "half_win", "push", "half_loss", "loss")
_CATEGORY_INDEX = {name: i for i, name in enumerate(CAT)}


def grid_distribution(grid, market, side, line):
    """Fast weighted settlement histogram for a score grid."""
    import numpy as np
    key = (market, side, float(line), len(grid), len(grid[0]))
    mapping = _GRID_CATEGORY_MAP.get(key)
    if mapping is None:
        mapping = np.empty((len(grid), len(grid[0])), dtype=np.uint8)
        for home in range(len(grid)):
            for away in range(len(grid[0])):
                _, category = legs_result(market, side, line, home, away)
                mapping[home, away] = _CATEGORY_INDEX[category]
        _GRID_CATEGORY_MAP[key] = mapping
    mass = np.bincount(mapping.ravel(), weights=np.asarray(grid, dtype=float).ravel(), minlength=len(CAT))
    return {category: float(mass[i]) for i, category in enumerate(CAT)}


_GRID_CATEGORY_MAP = {}


def fast_bootstrap(values, seed, repetitions=5000):
    """Vectorized fixture bootstrap, chunked to keep memory bounded."""
    import numpy as np
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    samples = np.empty(repetitions, dtype=float)
    for start in range(0, repetitions, 200):
        size = min(200, repetitions - start)
        samples[start:start + size] = rng.choice(arr, size=(size, len(arr)), replace=True).mean(axis=1)
    samples.sort()
    return {"lower_95": float(samples[int(.025 * (repetitions - 1))]),
            "upper_95": float(samples[int(.975 * (repetitions - 1))]),
            "method": "fixture percentile bootstrap, descriptive only",
            "repetitions": repetitions}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def private_path(path: Path, repo: Path) -> Path:
    p = path.expanduser().resolve()
    if p == repo or repo in p.parents:
        raise ValueError("row-level comparison data must stay outside the public repository")
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(p.parent, 0o700)
    return p


def canonical_probs(raw: dict, family: str) -> dict[str, float]:
    if family == "MR1":
        out = {"win": raw["full_win"], "half_win": raw["half_win"],
               "push": raw["push"], "half_loss": raw["half_loss"],
               "loss": raw["full_loss"]}
    else:
        out = {key: raw[key] for key in CAT}
    values = [float(out[k]) for k in CAT]
    if any(not math.isfinite(v) or v < -1e-10 for v in values) or abs(sum(values) - 1) > 1e-6:
        raise ValueError("invalid archived settlement distribution")
    return {k: max(0.0, float(out[k])) for k in CAT}


def opposite(dist: dict[str, float]) -> dict[str, float]:
    return {"win": dist["loss"], "half_win": dist["half_loss"],
            "push": dist["push"], "half_loss": dist["half_win"],
            "loss": dist["win"]}


def category_return(dist: dict[str, float], price: float) -> float:
    return (dist["win"] * (price - 1) + dist["half_win"] * (price - 1) / 2
            - dist["half_loss"] / 2 - dist["loss"])


def run(crown_rows: Path, m1_path: Path, mr1_path: Path, m3_path: Path,
        private_rows: Path, public_report: Path) -> dict:
    repo = Path(__file__).resolve().parents[2]
    crown = {}
    for line in crown_rows.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["fixture_id"]), row["market"])
        if key in crown:
            raise ValueError(f"duplicate canonical Crown pair: {key}")
        if row.get("quote_received_pre_kickoff") is not False:
            raise ValueError("expected historical retrospective receipts to be explicitly post-kickoff")
        crown[key] = row

    def load_index(path, id_key, market_key):
        out = {}
        for line in path.read_text().splitlines():
            row = json.loads(line)
            key = (str(row[id_key]), row[market_key])
            if key in out:
                raise ValueError(f"duplicate model forecast: {path.name} {key}")
            out[key] = row
        return out

    m1 = load_index(m1_path, "match_id", "market")
    mr1 = load_index(mr1_path, "match_id", "market")
    m3 = {}
    for line in m3_path.read_text().splitlines():
        row = json.loads(line)
        for market in ("AH", "OU"):
            key = (str(row["match_id"]), market)
            if key in m3:
                raise ValueError(f"duplicate M3 forecast: {key}")
            m3[key] = row
    markets = {m: {name: [] for name in MODELS} for m in ("AH", "OU")}
    audit = {m: Counter() for m in ("AH", "OU")}
    private_rows = private_path(private_rows, repo)

    with private_rows.open("w", encoding="utf-8") as output:
        os.chmod(private_rows, 0o600)
        for key, quote in crown.items():
            fid, market = key
            m1r, mr1r, m3r = m1.get(key), mr1.get(key), m3.get(key)
            line_value, prices = float(quote["line"]), [float(x) for x in quote["prices"]]
            sides = ("home", "away") if market == "AH" else ("over", "under")
            scoreline = (int(quote["actual_home_goals"]), int(quote["actual_away_goals"]))
            common = {"fixture_id": fid, "market": market, "line": line_value,
                      "prices": prices, "quote_event_utc": quote["quote_event_utc"],
                      "kickoff_utc": quote["kickoff_utc"], "league": quote["league"]}

            # M1 and MR1 archived only one categorical distribution at their
            # original line. Reprice and choose both sides only on exact-line joins.
            for name, row, family in (("M1", m1r, "M1"), ("MR1_V6", mr1r, "MR1")):
                if not row:
                    audit[market][f"{name}_forecast_missing"] += 1
                    continue
                old_line = float(row["line"])
                if abs(old_line - line_value) > 1e-8:
                    audit[market][f"{name}_line_mismatch"] += 1
                    continue
                if row.get("kickoff_utc") and row["kickoff_utc"] != quote["kickoff_utc"]:
                    audit[market][f"{name}_kickoff_mismatch"] += 1
                    continue
                old_event = row.get("event_utc")
                if not old_event or old_event > quote["quote_event_utc"] or quote["quote_event_utc"] >= quote["kickoff_utc"]:
                    audit[market][f"{name}_forecast_quote_chronology_invalid"] += 1
                    continue
                if family == "M1" and not (row.get("prediction_asof_utc")
                        and row["prediction_asof_utc"] < quote["quote_event_utc"] < quote["kickoff_utc"]):
                    audit[market]["M1_prediction_quote_chronology_invalid"] += 1
                    continue
                try:
                    raw = row.get("m1_distribution") if family == "M1" else row["probabilities"]
                    old_side = str(row["m1_side"] if family == "M1" else row["side"]).lower()
                    if old_side in ("home", "away"): old_side = old_side
                    elif old_side in ("over", "under"): old_side = old_side
                    else: raise ValueError("unrecognized forecast side")
                    old_dist = canonical_probs(raw, family)
                    side_dists = {old_side: old_dist, sides[1] if old_side == sides[0] else sides[0]: opposite(old_dist)}
                    evs = [category_return(side_dists[s], price) for s, price in zip(sides, prices)]
                    idx = 0 if evs[0] >= evs[1] else 1
                    side, price = sides[idx], prices[idx]
                    _, category = legs_result(market, side, line_value, *scoreline)
                    pnl = payout(legs_result(market, side, line_value, *scoreline)[0], price)
                    selected_dist = side_dists[side]
                    markets[market][name].append({**common, "side": side, "price": price,
                        "category": category, "pnl": pnl, "distribution": selected_dist,
                        "source_model_line": old_line})
                except (KeyError, TypeError, ValueError) as exc:
                    audit[market][f"{name}_invalid_distribution"] += 1
                    continue

            # M3 OOS grids are line-independent and can be recomputed at the
            # current Crown AH/OU contract, retaining full Crown quote coverage.
            if not m3r:
                audit[market]["M3_forecast_missing"] += 1
                continue
            if (m3r.get("kickoff_utc") != quote["kickoff_utc"]
                    or int(m3r.get("actual_home_goals", -1)) != scoreline[0]
                    or int(m3r.get("actual_away_goals", -1)) != scoreline[1]):
                audit[market]["M3_identity_or_score_mismatch"] += 1
                continue
            try:
                if not (m3r["train_end_utc"] < m3r["prediction_asof_utc"] < quote["quote_event_utc"] < quote["kickoff_utc"]):
                    raise ValueError("M3 forecast/quote chronology invalid")
            except KeyError as exc:
                raise ValueError("M3 chronology fields missing") from exc
            for public_name, model_key in M3_KEYS.items():
                grid = m3r["model_score_grids"][model_key]
                dists = [grid_distribution(grid, market, side, line_value) for side in sides]
                evs = [category_return(dist, price) for dist, price in zip(dists, prices)]
                idx = 0 if evs[0] >= evs[1] else 1
                side, price = sides[idx], prices[idx]
                legs, category = legs_result(market, side, line_value, *scoreline)
                dist = dists[idx]
                markets[market][public_name].append({**common, "side": side, "price": price,
                    "category": category, "pnl": payout(legs, price), "distribution": dist})
                if quote["league"] not in M4_PASS_LEAGUES:
                    m4name = "M4_Pass_" + public_name.removeprefix("M3_")
                    markets[market].setdefault(m4name, []).append(markets[market][public_name][-1])

        output.write(json.dumps({m: {name: rows for name, rows in groups.items()}
                                 for m, groups in markets.items()}, separators=(",", ":")))
        output.write("\n")

    def summarize(rows, market, seed):
        pnl = [float(r["pnl"]) for r in rows]
        counts = Counter(r["category"] for r in rows)
        by_time = defaultdict(float)
        by_year = defaultdict(list)
        for r in rows:
            by_time[r["quote_event_utc"]] += float(r["pnl"])
            by_year[r["kickoff_utc"][:4]].append(float(r["pnl"]))
        balance = peak = dd = 0.0
        for event in sorted(by_time):
            balance += by_time[event]
            peak = max(peak, balance)
            dd = max(dd, peak - balance)
        ll, brier = score([(r["category"], r["distribution"]) for r in rows])
        interval = fast_bootstrap(pnl, seed) if pnl else None
        return {
            "unique_fixture_markets": len(rows), "simulated_bets": len(rows),
            "settled_bets": len(rows), "stake_units": len(rows),
            "net_units": round(math.fsum(pnl), 6),
            "roi_pct": round(100 * math.fsum(pnl) / len(pnl), 6) if pnl else None,
            "settlement_counts": {c: counts[c] for c in CAT},
            "max_drawdown_units_by_quote_event_time": round(dd, 6),
            "settlement_log_loss": ll, "settlement_brier": brier,
            "bootstrap_95_roi_pct": ({"lower": round(100 * interval["lower_95"], 6),
                                      "upper": round(100 * interval["upper_95"], 6)} if interval else None),
            "by_utc_kickoff_year": {year: {"n": len(vals), "net_units": round(math.fsum(vals), 6),
                "roi_pct": round(100 * math.fsum(vals) / len(vals), 6)}
                for year, vals in sorted(by_year.items())},
            "receipt_timing": {"post_kickoff": len(rows)},
            "quote_sources": {"Crown": len(rows)},
            "unique_leagues": len({r["league"] for r in rows}),
        }

    report = {
        "protocol": "M5_MODEL_FAMILY_CANONICAL_CROWN_MATCHED_COMPARISON_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "crown_fixture_markets": len(crown),
            "crown_fixture_markets_by_market": {market: sum(1 for _, m in crown if m == market)
                                                for market in ("AH", "OU")},
            "crown_input_sha256": sha(crown_rows), "m1_trace_sha256": sha(m1_path),
            "mr1_trace_sha256": sha(mr1_path), "m3_grid_archive_sha256": sha(m3_path),
            "runner_sha256": sha(Path(__file__).resolve()),
            "kickoff_range_utc": [min(r["kickoff_utc"] for r in crown.values()),
                                  max(r["kickoff_utc"] for r in crown.values())],
            "all_quote_sources": ["Crown"],
            "historical_response_receipts": "all post-kickoff; event-time retrospective only",
        },
        "markets": {},
        "audit": {m: dict(c) for m, c in audit.items()},
        "method": (
            "AH and OU evaluated separately on the exact canonical Crown fixture-market cohort. "
            "M3 uses each archived strict UTC OOS score grid and re-selects the higher expected-return side "
            "at the newly canonical Crown line/prices. M1 and MR1 V6 use their archived side-specific "
            "settlement probability vectors only where their original line exactly equals the canonical Crown "
            "line; the opposite-side vector is the exact Asian settlement complement. M4 is the existing "
            "Japan J-League/Turkiye Super Lig Pass research rule applied to M3 model selections. "
            "One 1U per model/fixture-market, no extra filters or gates. Historical responses were received "
            "after kickoff, so ROI is retrospective event-time replay, not executable performance."
        ),
        "limitations": [
            "M1/MR1 settlement distributions are line-specific and cannot be transferred when the Crown line differs; these rows are excluded and coverage is reported.",
            "MR1 V6 may not cover every fixture; absence is not filled with M3 in its standalone rows.",
            "M4 is a post-hoc research Pass rule, not an independent prediction model or untouched validation.",
            "No live receipt or prospective profitability is demonstrated by these historical archives.",
        ],
    }
    for market, groups in markets.items():
        report["markets"][market] = {name: summarize(rows, market, 20261120 + len(report["markets"]) * 100 + i)
                                      for i, (name, rows) in enumerate(groups.items())}
        report["markets"][market]["canonical_cohort_n"] = sum(1 for _, m in crown if m == market)
        report["markets"][market]["audit"] = dict(audit[market])
        core = ["M1", "MR1_V6", "M3_Poisson", "M3_Dixon_Coles", "M3_Bivariate_Poisson"]
        by_id = {name: {r["fixture_id"]: r for r in groups[name]} for name in core}
        common_ids = set.intersection(*(set(by_id[name]) for name in core))
        report["markets"][market]["same_fixture_common_cohort"] = {
            "unique_fixture_markets": len(common_ids),
            "models": {name: summarize([by_id[name][fid] for fid in sorted(common_ids)], market,
                            20261220 + len(report["markets"]) * 100 + i)
                       for i, name in enumerate(core)},
            "M4_existing_pass_on_common_cohort": {
                "excluded_leagues": sorted(M4_PASS_LEAGUES),
                "models": {name.replace("M3_", "M4_Pass_"): summarize(
                    [by_id[name][fid] for fid in sorted(common_ids)
                     if by_id[name][fid]["league"] not in M4_PASS_LEAGUES], market, 20261320 + i)
                    for i, name in enumerate(core[2:])},
            },
        }
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--crown-rows", type=Path, required=True)
    p.add_argument("--m1-trace", type=Path, required=True)
    p.add_argument("--mr1-trace", type=Path, required=True)
    p.add_argument("--m3-grids", type=Path, required=True)
    p.add_argument("--private-rows", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    report = run(a.crown_rows, a.m1_trace, a.mr1_trace, a.m3_grids, a.private_rows, a.report)
    print(json.dumps({m: {k: {"n": v["simulated_bets"], "roi_pct": v["roi_pct"]}
                          for k, v in values.items() if isinstance(v, dict) and "simulated_bets" in v}
                      for m, values in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
