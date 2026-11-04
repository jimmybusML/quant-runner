#!/usr/bin/env python3
"""Strict UTC walk-forward recency-weighted Poisson study for M5.

Per competition, select a history half-life using only the previous calendar
year's exact-score log loss, then refit through the end of the prior year and
evaluate on the requested target year. Per-fixture predictions are written only to the
private output directory. Public output is aggregate-only.
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

import numpy as np
from scipy.optimize import minimize

HALF_LIVES = (0.5, 1.0, 2.0, 3.0, 5.0, 10.0, math.inf)
MAX_GOALS = 15
EPS = 1e-12
TARGET_YEAR = 2026


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_rows(path: Path):
    raw = path.read_bytes()
    manifest = json.loads(raw)
    rows = []
    seen = set()
    for r in manifest.get("rows", []):
        try:
            kickoff = datetime.fromisoformat(str(r["kickoff_utc"]).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                continue
            kickoff = kickoff.astimezone(timezone.utc)
            item = {"match_id": str(r["match_id"]), "league": str(r["league"]),
                    "home": str(r["home"]), "away": str(r["away"]),
                    "kickoff": kickoff, "year": kickoff.year,
                    "home_goals": int(r["home_goals"]), "away_goals": int(r["away_goals"])}
        except (KeyError, TypeError, ValueError):
            continue
        if item["match_id"] in seen or min(item["home_goals"], item["away_goals"]) < 0:
            continue
        seen.add(item["match_id"])
        rows.append(item)
    rows.sort(key=lambda x: (x["kickoff"], x["match_id"]))
    return raw, manifest, rows


def decay_weights(rows, asof: datetime, half_life_years: float):
    if math.isinf(half_life_years):
        return np.ones(len(rows), dtype=float)
    age_years = np.array([(asof - r["kickoff"]).total_seconds() / (365.2425 * 86400) for r in rows])
    if np.any(age_years < 0):
        raise ValueError("training row is after model as-of")
    weights = np.power(2.0, -age_years / half_life_years)
    # Keep total likelihood weight comparable to the unweighted fit so that
    # the existing ridge coefficient retains its scale.
    return weights * (len(weights) / weights.sum())


def fit_rates(rows, regularization: float, half_life_years: float, asof: datetime):
    teams = sorted({r["home"] for r in rows} | {r["away"] for r in rows})
    if len(rows) < 20 or len(teams) < 2:
        raise ValueError("insufficient training support")
    ti = {name: i for i, name in enumerate(teams)}
    hi = np.array([ti[r["home"]] for r in rows], dtype=int)
    ai = np.array([ti[r["away"]] for r in rows], dtype=int)
    hg = np.array([r["home_goals"] for r in rows], dtype=float)
    ag = np.array([r["away_goals"] for r in rows], dtype=float)
    w = decay_weights(rows, asof, half_life_years)
    log_hf = np.array([math.lgamma(float(x) + 1.0) for x in hg])
    log_af = np.array([math.lgamma(float(x) + 1.0) for x in ag])
    free = len(teams) - 1
    initial = np.zeros(2 + 2 * free, dtype=float)
    initial[0] = math.log(max(float(np.average(hg, weights=w)), 0.2))
    initial[1] = math.log(max(float(np.average(ag, weights=w)), 0.2))

    def unpack(x):
        attack = np.concatenate((x[2:2 + free], [-float(np.sum(x[2:2 + free]))]))
        defense = np.concatenate((x[2 + free:2 + 2 * free], [-float(np.sum(x[2 + free:2 + 2 * free]))]))
        return attack, defense

    def objective(x):
        attack, defense = unpack(x)
        eh = x[0] + attack[hi] + defense[ai]
        ea = x[1] + attack[ai] + defense[hi]
        if np.any(eh > 5) or np.any(ea > 5) or np.any(eh < -6) or np.any(ea < -6):
            return 1e100
        nll = np.sum(w * (np.exp(eh) - hg * eh + log_hf))
        nll += np.sum(w * (np.exp(ea) - ag * ea + log_af))
        nll += 0.5 * regularization * (float(np.dot(attack, attack)) + float(np.dot(defense, defense)))
        return float(nll) if math.isfinite(float(nll)) else 1e100

    result = minimize(objective, initial, method="L-BFGS-B", options={"maxiter": 500, "ftol": 1e-10})
    if not np.isfinite(result.fun) or result.fun >= 1e99:
        raise RuntimeError("weighted Poisson optimizer failed")
    attack, defense = unpack(result.x)
    return {"team_index": ti, "attack": attack, "defense": defense,
            "mu_home": float(result.x[0]), "mu_away": float(result.x[1]),
            "training_end": max(r["kickoff"] for r in rows)}


def predict(model, home: str, away: str):
    hi, ai = model["team_index"].get(home), model["team_index"].get(away)
    ha, hd = (model["attack"][hi], model["defense"][hi]) if hi is not None else (0.0, 0.0)
    aa, ad = (model["attack"][ai], model["defense"][ai]) if ai is not None else (0.0, 0.0)
    lh = float(np.exp(model["mu_home"] + ha + ad))
    la = float(np.exp(model["mu_away"] + aa + hd))

    def pmf(lam):
        p = [math.exp(-lam)]
        for k in range(1, MAX_GOALS):
            p.append(p[-1] * lam / k)
        z = sum(p)
        return [x / z for x in p]

    ph, pa = pmf(lh), pmf(la)
    grid = [[ph[h] * pa[a] for a in range(MAX_GOALS)] for h in range(MAX_GOALS)]
    z = sum(map(sum, grid))
    grid = [[x / z for x in row] for row in grid]
    p_home = sum(grid[h][a] for h in range(MAX_GOALS) for a in range(MAX_GOALS) if h > a)
    p_draw = sum(grid[i][i] for i in range(MAX_GOALS))
    p_away = 1.0 - p_home - p_draw
    p_over = sum(grid[h][a] for h in range(MAX_GOALS) for a in range(MAX_GOALS) if h + a > 2)
    return {"lambda_home": lh, "lambda_away": la, "grid": grid,
            "p_home": p_home, "p_draw": p_draw, "p_away": p_away, "p_over_2_5": p_over}


def exact_score_ll(model, rows):
    losses = []
    for r in rows:
        p = predict(model, r["home"], r["away"])["grid"]
        hg, ag = r["home_goals"], r["away_goals"]
        prob = p[hg][ag] if max(hg, ag) < MAX_GOALS else EPS
        losses.append(-math.log(max(prob, EPS)))
    return float(np.mean(losses))


def scores(records):
    ah_ll = ah_brier = ou_ll = ou_brier = score_ll = 0.0
    n = len(records)
    for r in records:
        p = r["prediction"]; hg, ag = r["home_goals"], r["away_goals"]
        y = 0 if hg > ag else 1 if hg == ag else 2
        probs = [p["p_home"], p["p_draw"], p["p_away"]]
        ah_ll -= math.log(max(probs[y], EPS)); ah_brier += sum((probs[i] - int(i == y)) ** 2 for i in range(3))
        yo = int(hg + ag > 2)
        po = min(max(p["p_over_2_5"], EPS), 1 - EPS)
        ou_ll -= yo * math.log(po) + (1 - yo) * math.log(1 - po)
        ou_brier += (po - yo) ** 2
        score_ll -= math.log(max(p["grid"][hg][ag], EPS) if max(hg, ag) < MAX_GOALS else EPS)
    return {"unique_fixtures": n, "ah_1x2_log_loss": ah_ll / n if n else None,
            "ah_1x2_brier": ah_brier / n if n else None, "ou_o25_log_loss": ou_ll / n if n else None,
            "ou_o25_brier": ou_brier / n if n else None, "exact_score_log_loss": score_ll / n if n else None}


def run(manifest_path: Path, baseline_path: Path, private_output: Path, aggregate_output: Path,
        target_year: int = TARGET_YEAR):
    raw, manifest, all_rows = load_rows(manifest_path)
    baseline_raw = baseline_path.read_bytes()
    baseline = {}
    for line in baseline_raw.decode().splitlines():
        try:
            r = json.loads(line)
            if int(str(r["kickoff"])[:4]) == target_year:
                baseline[str(r["match_id"])] = r
        except Exception:
            continue
    by_league = defaultdict(list)
    for r in all_rows:
        by_league[r["league"]].append(r)
    oos, fold_receipts = [], []
    identity_conflicts = 0
    parameter_counts = Counter()
    for league, league_rows in sorted(by_league.items()):
        train_target = [r for r in league_rows if r["year"] < target_year]
        train_validation = [r for r in league_rows if r["year"] < target_year - 1]
        validation = [r for r in league_rows if r["year"] == target_year - 1]
        target = []
        for r in league_rows:
            if r["year"] != target_year or r["match_id"] not in baseline:
                continue
            old = baseline[r["match_id"]]
            try:
                old_kickoff = datetime.fromisoformat(str(old["kickoff"]).replace("Z", "+00:00")).astimezone(timezone.utc)
            except (KeyError, TypeError, ValueError):
                identity_conflicts += 1
                continue
            if (old.get("league"), old.get("home"), old.get("away"), old_kickoff) != (r["league"], r["home"], r["away"], r["kickoff"]):
                identity_conflicts += 1
                continue
            target.append(r)
        if len(train_validation) < 20 or len(validation) < 5 or not target:
            continue
        # Reuse only the prior-year regularization chosen by the existing M5
        # fold. The new choice is the recency half-life, selected by 2025
        # exact-score log loss. All 2026 outcomes remain untouched.
        lam = float(next(iter(baseline.values())).get("regularization", 0.1))
        # The existing 2026 fold uses a league-specific penalty. Read it from
        # the matching baseline row rather than borrowing another competition.
        baseline_league = next((x for x in baseline.values() if x.get("league") == league), None)
        if baseline_league is not None:
            lam = float(baseline_league.get("regularization", 0.1))
        validation_asof = datetime(target_year - 1, 1, 1, tzinfo=timezone.utc)
        final_asof = datetime(target_year, 1, 1, tzinfo=timezone.utc)
        candidates = {}
        for half_life in HALF_LIVES:
            model = fit_rates(train_validation, lam, half_life, validation_asof)
            candidates[str(half_life)] = exact_score_ll(model, validation)
        selected = min(HALF_LIVES, key=lambda h: (candidates[str(h)], 0.0 if math.isinf(h) else abs(math.log(h))))
        model = fit_rates(train_target, lam, selected, final_asof)
        first_target = min(r["kickoff"] for r in target)
        if model["training_end"] >= first_target or model["training_end"] >= final_asof:
            raise ValueError(f"{target_year} target training cutoff is not prior to the forecast window")
        train_validation_ids = {r["match_id"] for r in train_validation}
        train_target_ids = {r["match_id"] for r in train_target}
        validation_ids = {r["match_id"] for r in validation}
        target_ids = {r["match_id"] for r in target}
        if train_validation_ids & validation_ids or train_target_ids & target_ids or validation_ids & target_ids:
            raise ValueError("fixture identity overlaps across model phase boundaries")
        parameter_counts[str(selected)] += len(target)
        fold_receipts.append({"league": league, "train_fixtures": len(train_target),
                              "validation_year_fixtures": len(validation),
                              "validation_year": target_year - 1,
                              "target_year_fixtures": len(target),
                              "training_end_utc": model["training_end"].isoformat().replace("+00:00", "Z"),
                              "regularization_from_existing_m5_fold": lam,
                              "selected_half_life_years": None if math.isinf(selected) else selected,
                              "validation_exact_score_log_loss": candidates,
                              "validation_fit_train_ids_disjoint_from_validation": True,
                              "final_fit_train_ids_disjoint_from_target": True,
                              "validation_ids_disjoint_from_target": True})
        for fixture in target:
            p = predict(model, fixture["home"], fixture["away"])
            old = baseline[fixture["match_id"]]
            oos.append({**fixture, "prediction": p, "prediction_asof_utc": final_asof,
                        "train_end_utc": model["training_end"], "regularization": lam,
                        "half_life_years": None if math.isinf(selected) else selected,
                        "baseline_prediction": old["prediction"]})
    oos.sort(key=lambda x: (x["kickoff"], x["match_id"]))
    private_output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_output.parent, 0o700)
    with private_output.open("w", encoding="utf-8") as f:
        for r in oos:
            out = {k: v for k, v in r.items() if k != "baseline_prediction"}
            out["kickoff"] = r["kickoff"].isoformat().replace("+00:00", "Z")
            out["prediction_asof_utc"] = r["prediction_asof_utc"].isoformat().replace("+00:00", "Z")
            out["train_end_utc"] = r["train_end_utc"].isoformat().replace("+00:00", "Z")
            f.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(private_output, 0o600)
    candidate_records = [{**r, "prediction": r["prediction"]} for r in oos]
    baseline_records = [{**r, "prediction": r["baseline_prediction"]} for r in oos]
    by_league_scores = {}
    for league in sorted({r["league"] for r in oos}):
        a = [r for r in candidate_records if r["league"] == league]
        b = [r for r in baseline_records if r["league"] == league]
        by_league_scores[league] = {"candidate": scores(a), "baseline": scores(b)}
    receipt = {"protocol": f"M5_RECENCY_WEIGHTED_{target_year}_STRICT_UTC_OOS_V1",
               "generated_utc": datetime.now(timezone.utc).isoformat(),
               "candidate_manifest_sha256": sha(raw), "candidate_manifest_complete_historical_universe": bool(manifest.get("complete_historical_universe")),
               "baseline_forecast_sha256": sha(baseline_raw), "private_candidate_forecast_sha256": sha(private_output.read_bytes()),
               "unique_fixture_count": len(oos), "fold_count": len(fold_receipts),
               "baseline_fixture_identity_conflicts_excluded": identity_conflicts,
               "by_half_life_fixture_counts": dict(parameter_counts),
               "candidate_oos": scores(candidate_records), "baseline_same_fixture_oos": scores(baseline_records),
               "by_league": by_league_scores,
               "fold_receipts": fold_receipts,
               "time_isolation": f"Half-life selected independently per league using {target_year - 1} exact-score log loss only. Model refit uses UTC fixtures before {target_year}-01-01; every scored {target_year} fixture is identity-disjoint and strictly later than training. No {target_year} outcome is used for selection.",
               "scope_note": f"Partial frozen M1 51-league schedule universe. Candidate and baseline use exact common {target_year} fixture IDs; Crown ROI is reported by separate Crown replay, not inferred from proper scores. No production model or trade rule changed."}
    aggregate_output.parent.mkdir(parents=True, exist_ok=True)
    aggregate_output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"unique_fixtures": len(oos), "folds": len(fold_receipts),
                      "by_half_life_fixture_counts": dict(parameter_counts),
                      "candidate_oos": receipt["candidate_oos"],
                      "baseline_same_fixture_oos": receipt["baseline_same_fixture_oos"],
                      "aggregate_output": str(aggregate_output)}, indent=2, sort_keys=True))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--baseline-forecasts", type=Path, required=True)
    p.add_argument("--private-output", type=Path, required=True)
    p.add_argument("--aggregate-output", type=Path, required=True)
    p.add_argument("--target-year", type=int, default=TARGET_YEAR)
    args = p.parse_args()
    run(args.manifest, args.baseline_forecasts, args.private_output, args.aggregate_output, args.target_year)


if __name__ == "__main__":
    main()
