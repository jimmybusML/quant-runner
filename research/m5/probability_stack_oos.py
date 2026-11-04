#!/usr/bin/env python3
"""Strict chronological probability-stack experiment over saved M3 OOS rows.

This evaluates probabilities only. It does not use or infer Crown prices and
cannot produce betting ROI. The saved input has three independently fitted
M3 score models on the same fixture rows; learned weights are fitted only on
earlier seasons' out-of-sample predictions.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "research/m3/results/latest_penaltyblog_oos_report.json"
MODELS = ("poisson", "dixon_coles", "bivariate_poisson")
EPS = 1e-12


def read_rows():
    report = json.loads(REPORT.read_text())
    path = ROOT / report["prediction_artifact"]
    raw = path.read_bytes()
    grouped = defaultdict(dict)
    key_fields = ("league", "match_date_utc", "home_team", "away_team")
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = tuple(r[k] for k in key_fields)
            model = r["model"]
            if model not in MODELS:
                raise ValueError(f"unexpected model: {model}")
            grouped[key][model] = r
    output = []
    for key, records in grouped.items():
        if set(records) != set(MODELS):
            raise ValueError("model rows are not one-to-one per fixture")
        rows = [records[m] for m in MODELS]
        for field in ("actual_home_goals", "actual_away_goals", "season"):
            if len({r[field] for r in rows}) != 1:
                raise ValueError(f"fixture outcome/season conflict: {field}")
        if any(not r.get("p_home") for r in rows):
            continue
        for r in rows:
            p1 = np.array([float(r[k]) for k in ("p_home", "p_draw", "p_away")])
            p_ou = float(r["ou_p_over_2_5"])
            if (not np.all(np.isfinite(p1)) or np.any(p1 < 0) or np.any(p1 > 1)
                    or abs(float(p1.sum()) - 1.0) > 1e-6 or not 0 <= p_ou <= 1):
                raise ValueError("invalid saved probability vector")
        output.append({"key": key, "season": rows[0]["season"], "rows": rows})
    output.sort(key=lambda x: (x["season"], x["key"][1], x["key"][0], x["key"][2], x["key"][3]))
    return report, path, raw, output


def vectors(entries, market):
    if market == "1x2":
        probs = np.array([[[float(r["p_home"]), float(r["p_draw"]), float(r["p_away"])] for r in e["rows"]] for e in entries])
        labels = np.array([{"H": 0, "D": 1, "A": 2}[e["rows"][0]["actual_result_1x2"]] for e in entries])
    else:
        probs = np.array([[[float(r["ou_p_over_2_5"])] for r in e["rows"]] for e in entries])
        probs = np.concatenate([probs, 1.0 - probs], axis=2)
        labels = np.array([int(e["rows"][0]["actual_ou_over_2_5"]) for e in entries])
    return np.clip(probs, EPS, 1.0), labels


def loss(weights, probs, labels):
    blended = np.einsum("m,nmk->nk", weights, probs)
    return float(-np.log(np.clip(blended[np.arange(len(labels)), labels], EPS, 1)).mean())


def fit_weights(entries, market):
    probs, labels = vectors(entries, market)
    result = minimize(
        lambda w: loss(w, probs, labels), np.full(len(MODELS), 1 / len(MODELS)),
        method="SLSQP", bounds=[(0.0, 1.0)] * len(MODELS),
        constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0)}],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success and not np.isfinite(result.fun):
        raise RuntimeError(f"weight fit failed: {result.message}")
    weights = np.clip(result.x, 0, 1)
    weights /= weights.sum()
    return weights


def brier_score(pred, labels, market):
    if market == "ou_over_2_5":
        return float(np.square(pred[:, 0] - labels).mean())
    return float(np.square(pred - np.eye(pred.shape[1])[labels]).sum(axis=1).mean())


def metrics(probs, labels, market):
    n = probs.shape[0]
    chosen = probs[np.arange(n), :, :]
    values = {}
    for i, name in enumerate((*MODELS, "equal_blend")):
        if i < len(MODELS):
            pred = chosen[:, i, :]
        elif i == len(MODELS):
            pred = chosen.mean(axis=1)
        values[name] = {
            "log_loss": round(float(-np.log(np.clip(pred[np.arange(n), labels], EPS, 1)).mean()), 8),
            "brier": round(brier_score(pred, labels, market), 8),
        }
    return values


def main():
    report, path, raw, fixtures = read_rows()
    if len(fixtures) != report["test_matches_scored"]:
        raise ValueError("common scored fixture count differs from source receipt")
    seasons = sorted({x["season"] for x in fixtures})
    result = {
        "protocol": "M5_M3_OOS_CONVEX_STACK_V1",
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "input_report_generated_utc": report["generated_utc"],
        "input_artifact": str(path.relative_to(ROOT)),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "unique_scored_fixtures": len(fixtures),
        "fixture_identity": ["league", "match_date_utc", "home_team", "away_team"],
        "source_models": list(MODELS),
        "scope": "Only fixtures present in the saved M3 Football-Data.co.uk OOS artifact; scope is a subset of the established M1/MR1 union.",
        "time_isolation": "For each target season, weights are fit only on earlier seasons' saved OOS predictions. No fixture from the target season is used for weight fitting.",
        "markets": {},
        "crown_prices_used": False,
        "roi": None,
        "interpretation": "Probability-quality study only; no Crown-linked prices, EV, simulated bets, ROI, or drawdown are available from this input.",
    }
    for market in ("1x2", "ou_over_2_5"):
        split_records = []
        for season in seasons:
            train = [x for x in fixtures if x["season"] < season]
            test = [x for x in fixtures if x["season"] == season]
            if not train or not test:
                continue
            train_keys = {x["key"] for x in train}
            if any(x["key"] in train_keys or x["season"] != season for x in test):
                raise ValueError("target-season leakage in probability stack")
            w = fit_weights(train, market)
            p, y = vectors(test, market)
            blended = np.einsum("m,nmk->nk", w, p)
            base_metrics = metrics(p, y, market)
            base_metrics["walkforward_blend"] = {
                "log_loss": round(loss(w, p, y), 8),
                "brier": round(brier_score(blended, y, market), 8),
            }
            split_records.append({
                "test_season": season,
                "train_seasons": sorted({x["season"] for x in train}),
                "train_unique_fixtures": len(train),
                "test_unique_fixtures": len(test),
                "walkforward_weights": {m: round(float(v), 8) for m, v in zip(MODELS, w)},
                "metrics": base_metrics,
            })
        # Pooled OOS metrics are computed from fold-specific predictions/weights.
        pooled_labels, pooled_blend = [], []
        pooled_count = 0
        for split in split_records:
            test = [x for x in fixtures if x["season"] == split["test_season"]]
            p, y = vectors(test, market)
            w = np.array([split["walkforward_weights"][m] for m in MODELS])
            b = np.einsum("m,nmk->nk", w, p)
            pooled_labels.extend(y.tolist())
            pooled_blend.extend(b.tolist())
            pooled_count += len(y)
        yall = np.array(pooled_labels)
        ball = np.array(pooled_blend)
        pooled = {"n_unique_fixtures": pooled_count,
                  "walkforward_blend": {"log_loss": round(float(-np.log(np.clip(ball[np.arange(len(yall)), yall], EPS, 1)).mean()), 8),
                                        "brier": round(brier_score(ball, yall, market), 8)}}
        for m in MODELS:
            # The model baselines are evaluated on the identical pooled fixture set.
            parts = []
            for split in split_records:
                test = [x for x in fixtures if x["season"] == split["test_season"]]
                p, y = vectors(test, market)
                parts.append((p[:, MODELS.index(m), :], y))
            pm = np.concatenate([x[0] for x in parts], axis=0)
            ym = np.concatenate([x[1] for x in parts], axis=0)
            pooled[m] = {"log_loss": round(float(-np.log(np.clip(pm[np.arange(len(ym)), ym], EPS, 1)).mean()), 8),
                         "brier": round(brier_score(pm, ym, market), 8)}
        result["markets"][market] = {"walkforward_oos": pooled, "season_splits": split_records}
    out = ROOT / "research/m5/results/m5_probability_stack_oos.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out.relative_to(ROOT)), "unique_scored_fixtures": len(fixtures),
                      "markets": {k: v["walkforward_oos"] for k, v in result["markets"].items()},
                      "roi": None}, indent=2))


if __name__ == "__main__":
    main()
