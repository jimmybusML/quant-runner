#!/usr/bin/env python3
"""Compare global and league-local M3 probability stacks chronologically.

All weights and the best single-model comparator are chosen only from prior
season OOS predictions. AH 1X2 and OU 2.5 are scored independently. This is a
probability study; no Crown quotes, bets, or ROI are inferred here.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from research.m5.probability_stack_oos import MODELS, ROOT, read_rows, vectors, loss, brier_score

EPS = 1e-12


def metrics(probs: np.ndarray, labels: np.ndarray, market: str) -> dict:
    ll = -np.log(np.clip(probs[np.arange(len(labels)), labels], EPS, 1.0)).mean()
    br = brier_score(probs, labels, market)
    return {"fixtures": int(len(labels)), "log_loss": round(float(ll), 8), "brier": round(float(br), 8)}


def fit(train, market):
    if not train:
        return np.full(len(MODELS), 1 / len(MODELS))
    p, y = vectors(train, market)
    result = minimize(lambda w: loss(w, p, y), np.full(len(MODELS), 1 / len(MODELS)),
                      method="SLSQP", bounds=[(0.0, 1.0)] * len(MODELS),
                      constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0)}],
                      options={"maxiter": 400, "ftol": 1e-11})
    if not np.isfinite(result.fun):
        return np.full(len(MODELS), 1 / len(MODELS))
    weights = np.clip(result.x, 0, 1)
    return weights / weights.sum()


def predict(entries, market, weights):
    p, y = vectors(entries, market)
    return np.einsum("m,nmk->nk", weights, p), y


def evaluate_market(fixtures, market):
    seasons = sorted({x["season"] for x in fixtures})
    by_league = defaultdict(list)
    for x in fixtures:
        by_league[x["key"][0]].append(x)
    methods = {name: [] for name in ("global_blend", "league_local_blend", "league_local_best_single")}
    folds = []
    for season in seasons:
        train = [x for x in fixtures if x["season"] < season]
        test = [x for x in fixtures if x["season"] == season]
        if not train or not test:
            continue
        train_keys = {x["key"] for x in train}
        test_keys = {x["key"] for x in test}
        if train_keys & test_keys or any(x["season"] != season for x in test):
            raise ValueError("fixture identity or season leakage across fold")
        global_weights = fit(train, market)
        test_groups = defaultdict(list)
        for row in test:
            test_groups[row["key"][0]].append(row)
        fold = {"test_season": season, "train_fixtures": len(train), "test_fixtures": len(test),
                "league_weights": {}}
        for league, holdout in sorted(test_groups.items()):
            local_train = [x for x in by_league[league] if x["season"] < season]
            local_weights = fit(local_train, market) if local_train else global_weights
            p_local, y = predict(holdout, market, local_weights)
            p_global, _ = predict(holdout, market, global_weights)
            p_models, _ = vectors(holdout, market)
            single_train = local_train if local_train else train
            p_train, y_train = vectors(single_train, market)
            model_losses = [float(-np.log(np.clip(
                p_train[:, mi, :][np.arange(len(y_train)), y_train], EPS, 1)).mean())
                for mi in range(len(MODELS))]
            chosen = int(np.argmin(model_losses))
            methods["global_blend"].append((p_global, y))
            methods["league_local_blend"].append((p_local, y))
            methods["league_local_best_single"].append((p_models[:, chosen, :], y))
            fold["league_weights"][league] = {
                "prior_league_fixtures": len(local_train),
                "weights": {m: round(float(w), 8) for m, w in zip(MODELS, local_weights)},
                "prior_best_single_model": MODELS[chosen],
            }
        folds.append(fold)
    pooled = {}
    for name, parts in methods.items():
        p = np.concatenate([x[0] for x in parts], axis=0)
        y = np.concatenate([x[1] for x in parts], axis=0)
        pooled[name] = metrics(p, y, market)
    # Per-league results show whether an aggregate improvement masks reversals.
    league_results = {}
    for league in sorted(by_league):
        local = [x for x in fixtures if x["key"][0] == league]
        lg_seasons = sorted({x["season"] for x in local})
        accum = {name: [] for name in methods}
        for season in lg_seasons:
            train = [x for x in local if x["season"] < season]
            test = [x for x in local if x["season"] == season]
            if not train or not test:
                continue
            gw = fit([x for x in fixtures if x["season"] < season], market)
            lw = fit(train, market)
            p, y = predict(test, market, lw)
            accum["league_local_blend"].append((p, y))
            p, _ = predict(test, market, gw)
            accum["global_blend"].append((p, y))
            pm, _ = vectors(test, market)
            pt, yt = vectors(train, market)
            losses = [-np.log(np.clip(pt[:, mi, :][np.arange(len(yt)), yt], EPS, 1)).mean() for mi in range(len(MODELS))]
            accum["league_local_best_single"].append((pm[:, int(np.argmin(losses)), :], y))
        league_results[league] = {}
        for name, parts in accum.items():
            if parts:
                p = np.concatenate([x[0] for x in parts], axis=0)
                y = np.concatenate([x[1] for x in parts], axis=0)
                league_results[league][name] = metrics(p, y, market)
    return {"pooled_oos": pooled, "by_league_oos": league_results, "folds": folds}


def main():
    report, prediction_path, raw, fixtures = read_rows()
    result = {"protocol": "M5_LEAGUE_LOCAL_WALKFORWARD_STACK_V1",
              "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
              "input_prediction_sha256": hashlib.sha256(raw).hexdigest(),
              "input_report_generated_utc": report.get("generated_utc"),
              "input_fixtures": len(fixtures), "markets_independent": True,
              "crown_prices_used": False, "roi": None,
              "time_isolation": "For each target season, both global and league-local weights and the best single model are fit on prior seasons' OOS predictions only. Training and test fixture keys are disjoint.",
              "markets": {}}
    for market in ("1x2", "ou_over_2_5"):
        result["markets"][market] = evaluate_market(fixtures, market)
    out = ROOT / "research/m5/results/m5_league_local_probability_oos.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out.relative_to(ROOT)), "input_fixtures": len(fixtures),
                      "markets": {k: v["pooled_oos"] for k, v in result["markets"].items()}, "roi": None}, indent=2))


if __name__ == "__main__":
    main()
