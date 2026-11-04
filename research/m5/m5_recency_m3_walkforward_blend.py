#!/usr/bin/env python3
"""Fit a log-loss M3/M5 probability blend on 2025, test on 2026, then replay Crown.

The source M3 predictions and M5 recency grids are strict out-of-sample for both
years. Blend weights are fit only on 2025 common fixtures using proper scores;
2026 is untouched until final evaluation. Crown ROI is evaluated only on exact
supported AH0 / OU2.5 MR1 received-before-kickoff contracts with separate FT.
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

import numpy as np
from scipy.optimize import minimize

M3_MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
LEAGUE_CODES = {
    "England Premier League": "E0", "Italy Serie A": "I1", "Spain La Liga": "SP1",
    "France Ligue 1": "F1", "Germany Bundesliga": "D1",
    "Belgium First Division A": "B1", "Belgium Jupiler Pro League": "B1",
}

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)

def dt(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None

def identity(code: str, date: str, home: str, away: str):
    return code, str(date)[:10], norm(home), norm(away)

def distribution_from_grid(grid):
    ah = [0.0, 0.0, 0.0]
    over = 0.0
    for h, row in enumerate(grid):
        for a, p in enumerate(row):
            p = float(p)
            ah[0 if h > a else 1 if h == a else 2] += p
            if h + a > 2:
                over += p
    return ah, [over, 1.0 - over]

def load_m5(path: Path, year: int):
    raw = path.read_bytes(); rows = {}
    for line in raw.decode().splitlines():
        try:
            r = json.loads(line); code = LEAGUE_CODES.get(r["league"])
            if not code or int(str(r["kickoff"])[:4]) != year:
                continue
            key = identity(code, r["kickoff"], r["home"], r["away"])
            if key in rows:
                raise ValueError(f"duplicate normalized M5 fixture identity for year {year}")
            ko, asof, train_end = dt(r.get("kickoff")), dt(r.get("prediction_asof_utc")), dt(r.get("train_end_utc"))
            if not ko or not asof or not train_end or not train_end < asof < ko:
                raise ValueError("M5 as-of/training time is missing or not before kickoff")
            rows[key] = {"raw": r, "kickoff": ko, "actual": (int(r["home_goals"]), int(r["away_goals"])),
                         "probs": distribution_from_grid(r["prediction"]["grid"])}
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise
    return raw, rows

def load_m3(path: Path):
    raw = path.read_bytes(); by_fixture = defaultdict(dict); actuals = defaultdict(set)
    time_rejections = 0
    for row in csv.DictReader(raw.decode().splitlines()):
        code = row.get("league"); model = row.get("model")
        if code not in set(LEAGUE_CODES.values()) or model not in M3_MODELS:
            continue
        key = identity(code, row.get("kickoff_date_utc") or row.get("match_date_utc"),
                       row.get("home_team"), row.get("away_team"))
        if key in by_fixture and model in by_fixture[key]:
            raise ValueError("duplicate M3 model row for a normalized fixture identity")
        kickoff = dt((row.get("kickoff_date_utc") or row.get("match_date_utc"))[:10] + "T00:00:00Z")
        train_end = dt(row.get("train_end_utc"))
        if not kickoff or not train_end or train_end >= kickoff:
            time_rejections += 1
            continue
        try:
            p_ah = [float(row["p_home"]), float(row["p_draw"]), float(row["p_away"])]
            p_ou = [float(row["ou_p_over_2_5"]), 1.0 - float(row["ou_p_over_2_5"])]
            if any(not math.isfinite(x) or x < 0 or x > 1 for x in p_ah + p_ou):
                continue
            if abs(sum(p_ah) - 1.0) > 1e-5:
                continue
            actual = (int(row["actual_home_goals"]), int(row["actual_away_goals"]))
        except (KeyError, TypeError, ValueError):
            continue
        by_fixture[key][model] = {"AH": p_ah, "OU": p_ou, "train_end": train_end}
        actuals[key].add(actual)
    return raw, by_fixture, actuals, time_rejections

def common_rows(year, m5, m3, actuals):
    rows = []; m3_after_asof = 0
    for key, forecast in m5.items():
        models = m3.get(key, {})
        if len(models) != len(M3_MODELS) or any(m not in models for m in M3_MODELS):
            continue
        if actuals.get(key) != {forecast["actual"]}:
            continue
        asof = dt(forecast["raw"].get("prediction_asof_utc"))
        if not asof or any(models[name]["train_end"] >= asof for name in M3_MODELS):
            m3_after_asof += 1
            continue
        rows.append({"identity": key, "league": forecast["raw"]["league"],
                     "forecast": forecast, "m3": models, "actual": forecast["actual"]})
    rows.sort(key=lambda x: (x["forecast"]["kickoff"], x["identity"]))
    return rows, m3_after_asof

def actual_label(market, actual):
    h, a = actual
    # AH order is home/draw/away; OU order is over/under.
    return (0 if h > a else 1 if h == a else 2) if market == "AH" else int(h + a <= 2)

def component_matrix(rows, market):
    names = [*M3_MODELS, "m5_recency"]
    matrix = []
    labels = []
    for r in rows:
        comp = [r["m3"][m][market] for m in M3_MODELS]
        comp.append(r["forecast"]["probs"][0 if market == "AH" else 1])
        matrix.append(comp); labels.append(actual_label(market, r["actual"]))
    return names, np.asarray(matrix, dtype=float), np.asarray(labels, dtype=int)

def fit_weights(matrix, labels):
    if len(matrix) < 20:
        raise ValueError("too few chronological training fixtures for blend fit")
    n_models = matrix.shape[1]
    def objective(w):
        mixed = np.einsum("m,nmk->nk", w, matrix)
        return float(-np.log(np.maximum(mixed[np.arange(len(labels)), labels], 1e-15)).mean())
    result = minimize(objective, np.ones(n_models) / n_models, method="SLSQP",
                      bounds=[(0.0, 1.0)] * n_models,
                      constraints=[{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}],
                      options={"maxiter": 2000, "ftol": 1e-12})
    if not result.success or not np.isfinite(result.fun):
        raise RuntimeError(f"blend optimizer failed: {result.message}")
    w = np.maximum(result.x, 0.0); w /= w.sum()
    return w, float(objective(w))

def score_probabilities(matrix, labels, weights):
    p = np.einsum("m,nmk->nk", weights, matrix)
    p = np.clip(p, 1e-12, 1.0); p /= p.sum(axis=1, keepdims=True)
    ll = -np.log(p[np.arange(len(labels)), labels]).mean()
    onehot = np.eye(p.shape[1])[labels]
    brier_rows = ((p - onehot) ** 2).sum(axis=1)
    if p.shape[1] == 2:
        brier_rows = brier_rows / 2.0  # Match the binary Brier convention used for OU O2.5.
    brier = brier_rows.mean()
    return {"fixtures": int(len(labels)), "log_loss": round(float(ll), 8), "brier": round(float(brier), 8)}

def score_components(matrix, labels):
    return {name: score_probabilities(matrix[:, i:i+1, :], labels, np.array([1.0]))
            for i, name in enumerate([*M3_MODELS, "m5_recency"])}

def ev_side(prob, market, line, prices):
    if market == "AH":
        if abs(line) > 1e-10:
            return None, None
        p_home, _p_draw, p_away = prob
        ev_home = p_home * (prices[0] - 1.0) - p_away
        ev_away = p_away * (prices[1] - 1.0) - p_home
        idx = 0 if ev_home >= ev_away else 1
        return idx, max(ev_home, ev_away)
    if abs(line - 2.5) > 1e-10:
        return None, None
    p_over, p_under = prob
    ev_over = p_over * (prices[0] - 1.0) - p_under
    ev_under = p_under * (prices[1] - 1.0) - p_over
    idx = 0 if ev_over >= ev_under else 1
    return idx, max(ev_over, ev_under)

def settle_units(market, side_idx, price, actual):
    h, a = actual
    if market == "AH":
        result = 0 if h == a else 1 if (h > a and side_idx == 0) or (a > h and side_idx == 1) else -1
    else:
        over = h + a > 2
        result = 1 if (over and side_idx == 0) or (not over and side_idx == 1) else -1
    return price - 1.0 if result == 1 else 0.0 if result == 0 else -1.0, result

def summarize_bets(rows):
    n = len(rows); cats = Counter(x["result"] for x in rows); net = sum(x["units"] for x in rows)
    grouped = defaultdict(float)
    for x in rows: grouped[x["observed"]] += x["units"]
    equity = peak = drawdown = 0.0
    for t in sorted(grouped):
        equity += grouped[t]; peak = max(peak, equity); drawdown = max(drawdown, peak - equity)
    boot = None
    if n:
        rng = random.Random(20261107); vals = [x["units"] for x in rows]
        samples = sorted(100.0 * sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
        boot = {"lower_2_5_pct": round(samples[249], 6), "upper_97_5_pct": round(samples[9749], 6),
                "resamples": len(samples), "seed": 20261107}
    return {"unique_fixtures": n, "simulated_bets": n, "settled_bets": n,
            "wins": cats[1], "pushes": cats[0], "losses": cats[-1],
            "net_units": round(net, 6), "roi_pct": round(net * 100 / n, 6) if n else None,
            "max_drawdown_units_by_quote_event": round(drawdown, 6) if n else None,
            "roi_fixture_bootstrap_95pct_interval": boot}

def run(args):
    m3_raw, m3, m3_actuals, m3_time_rejections = load_m3(args.m3_csv)
    m5_2025_raw, m5_2025 = load_m5(args.m5_2025, 2025)
    m5_2026_raw, m5_2026 = load_m5(args.m5_2026, 2026)
    baseline_raw, baseline_2026 = load_m5(args.m5_baseline, 2026)
    train, train_m3_after_asof = common_rows(2025, m5_2025, m3, m3_actuals)
    test, test_m3_after_asof = common_rows(2026, m5_2026, m3, m3_actuals)
    for row in test:
        row["baseline"] = baseline_2026.get(row["identity"])
    if not train or not test:
        raise ValueError("no complete 2025 train / 2026 test M3-M5 common fixture set")
    market_reports = {}
    fitted = {}
    for market in ("AH", "OU"):
        names, tr_matrix, tr_labels = component_matrix(train, market)
        weights, train_ll = fit_weights(tr_matrix, tr_labels)
        test_names, te_matrix, te_labels = component_matrix(test, market)
        assert names == test_names
        blend = score_probabilities(te_matrix, te_labels, weights)
        blend["weights"] = {name: round(float(w), 8) for name, w in zip(names, weights)}
        blend["training_log_loss"] = round(train_ll, 8)
        blend["training_fixtures"] = len(train)
        blend["holdout"] = score_components(te_matrix, te_labels)
        baseline_probs = np.asarray([r["baseline"]["probs"][0 if market == "AH" else 1]
                                     for r in test if r.get("baseline")], dtype=float)
        baseline_labels = np.asarray([actual_label(market, r["actual"]) for r in test if r.get("baseline")], dtype=int)
        if len(baseline_probs) == len(te_labels):
            blend["holdout"]["m5_baseline"] = score_probabilities(baseline_probs[:, None, :], baseline_labels,
                                                                   np.asarray([1.0]))
        market_reports[market] = blend; fitted[market] = weights

    # Compare Crown results only on the exact common OOS fixtures, verified MR1
    # Crown receipts, independent FT, and contracts M3 actually predicts.
    from research.m5.m5_crown_oos_source_union import load_mr1
    mr1_quotes, mr1_src = load_mr1(args.mr1_root, {r["forecast"]["raw"]["match_id"]: r["forecast"]["raw"] for r in test})
    test_by_id = {r["forecast"]["raw"]["match_id"]: r for r in test}
    baseline_by_identity = baseline_2026
    crown = {}
    for market in ("AH", "OU"):
        cohort = defaultdict(list); league_rows = defaultdict(list)
        supported = 0
        for (mid, mkt), quote in mr1_quotes.items():
            if mkt != market or mid not in test_by_id:
                continue
            row = test_by_id[mid]; f = row["forecast"]["raw"]
            if (market == "AH" and abs(quote["line"]) > 1e-10) or (market == "OU" and abs(quote["line"] - 2.5) > 1e-10):
                continue
            supported += 1
            baseline = baseline_by_identity.get(row["identity"])
            if not baseline:
                continue
            model_probs = {name: row["m3"][name][market] for name in M3_MODELS}
            model_probs["m5_recency"] = row["forecast"]["probs"][0 if market == "AH" else 1]
            b_ah, b_ou = distribution_from_grid(baseline["raw"]["prediction"]["grid"])
            model_probs["m5_baseline"] = b_ah if market == "AH" else b_ou
            blend_prob = np.sum(np.asarray([model_probs[name] for name in [*M3_MODELS, "m5_recency"]])
                                * fitted[market][:, None], axis=0)
            model_probs["m3_m5_walkforward_blend"] = list(blend_prob)
            for name, prob in model_probs.items():
                side, _ev = ev_side(prob, market, quote["line"], quote["prices"])
                if side is None:
                    continue
                price = quote["prices"][side]
                units, result = settle_units(market, side, price, row["actual"])
                item = {"observed": quote["observed"], "units": units, "result": result,
                        "league": f["league"]}
                cohort[name].append(item); league_rows[(name, f["league"])].append(item)
        crown[market] = {"candidate_common_fixture_count": len(test),
                         "verified_MR1_received_quote_count_before_contract_support": sum(1 for (mid, m) in mr1_quotes if m == market and mid in test_by_id),
                         "exact_contract_quote_fixtures": supported,
                         "market_contract": "AH 0.0" if market == "AH" else "OU 2.5",
                         "models": {name: summarize_bets(rows) for name, rows in cohort.items()},
                         "by_league": {name: {league: summarize_bets(rows) for (model, league), rows in league_rows.items() if model == name}
                                       for name in cohort}}

    result = {"protocol": "M5_M3_RECENCY_2025_FIT_2026_HOLDOUT_V1",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "M3_prediction_sha256": sha(m3_raw),
              "M5_recency_2025_forecast_sha256": sha(m5_2025_raw),
              "M5_recency_2026_forecast_sha256": sha(m5_2026_raw),
              "M5_baseline_2026_forecast_sha256": sha(baseline_raw),
              "MR1_snapshot_index_sha256": sha(mr1_src["index_raw"]),
              "MR1_fixture_registry_sha256": sha(mr1_src["registry_raw"]),
              "MR1_quote_snapshot_hash_set_sha256": sha("\n".join(sorted(mr1_src["snapshot_hashes"])).encode()),
              "MR1_verified_FT_hash_set_sha256": sha("\n".join(sorted(mr1_src["ft_hashes"])).encode()),
              "m3_rows_rejected_for_time_order": m3_time_rejections,
              "m3_fixtures_rejected_for_training_after_m5_asof": {
                  "2025_train_period": train_m3_after_asof, "2026_holdout": test_m3_after_asof},
              "train_2025_common_fixture_count": len(train), "holdout_2026_common_fixture_count": len(test),
              "holdout_2026_unique_m3_leagues": len({r["identity"][0] for r in test}),
              "proper_score_blends": market_reports,
              "crown_same_quote_oos": crown,
              "method": "For AH 1X2 proxy and OU O2.5 independently, fit nonnegative simplex weights over M3 Poisson/Dixon-Coles/Bivariate-Poisson and M5 recency probabilities by 2025 common-fixture log loss; freeze and evaluate on 2026 common fixtures. Crown ROI uses only exact AH0/OU2.5 verified MR1 received-before-kickoff quotes with independent post-kickoff FT. Each model makes one 1U bet at the same line and prices, selecting its higher expected-return side with no EV threshold. Asian settlement is used; 2026 is not used to fit weights.",
              "limitations": ["M3 comparison covers six supported leagues only and is a smaller common subset than the 51-league M5 OOS.", "Crown ROI is limited to exact supported AH0/OU2.5 contracts; it does not cover other AH or OU lines.", "2025 is a training/weight-selection period and must not be called holdout performance.", "The 2026 Crown test is a retrospective OOS study, not live M5 deployment; no model promotion, production, or Telegram action."],
              "crown_prices_used_only": True}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "train_2025": len(train), "holdout_2026": len(test),
                      "proper_score_blends": {m: {"weights": market_reports[m]["weights"],
                                                   "blend": {"log_loss": market_reports[m]["log_loss"], "brier": market_reports[m]["brier"]},
                                                   "holdout_components": market_reports[m]["holdout"]}
                                                   for m in ("AH", "OU")},
                      "crown_sample_counts": {m: x["exact_contract_quote_fixtures"] for m, x in crown.items()},
                      "crown_blend_roi": {m: x["models"].get("m3_m5_walkforward_blend", {}).get("roi_pct") for m, x in crown.items()}}, indent=2))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--m3-csv", type=Path, required=True)
    p.add_argument("--m5-2025", type=Path, required=True)
    p.add_argument("--m5-2026", type=Path, required=True)
    p.add_argument("--m5-baseline", type=Path, required=True)
    p.add_argument("--mr1-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    run(p.parse_args())

if __name__ == "__main__":
    main()
