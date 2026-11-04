#!/usr/bin/env python3
"""Calendar-year walk-forward M5 goal model on the frozen M1 competition scope.

This candidate is fit independently from M1/MR1 predictions, orders and ledgers.
It provides a broad-scope score distribution for later Crown-only replay. The
private candidate manifest and per-fixture forecasts stay outside this repo;
only aggregate proper scores and source hashes are written publicly.
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

EPS = 1e-12
MAX_GOALS = 15
REGULARIZATIONS = (0.01, 0.1, 1.0)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("kickoff must include an explicit UTC offset")
    return dt.astimezone(timezone.utc)


def safe_private_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if resolved == repo or repo in resolved.parents:
        raise ValueError("per-fixture forecast output must remain outside the public repository")
    resolved.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(resolved, 0o700)
    return resolved


def read_manifest(path: Path):
    raw = path.read_bytes()
    manifest = json.loads(raw)
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        raise ValueError("private candidate manifest has no rows array")
    fixtures, seen = [], set()
    for row in rows:
        mid = str(row.get("match_id") or "")
        league = str(row.get("league") or "")
        home, away = str(row.get("home") or ""), str(row.get("away") or "")
        try:
            kickoff = parse_utc(row["kickoff_utc"])
            hg, ag = int(row["home_goals"]), int(row["away_goals"])
        except (KeyError, TypeError, ValueError):
            continue
        if not mid or not league or not home or not away or hg < 0 or ag < 0:
            continue
        if mid in seen:
            raise ValueError("duplicate fixture ID in private candidate manifest")
        seen.add(mid)
        fixtures.append({"match_id": mid, "league": league, "home": home, "away": away,
                         "kickoff": kickoff, "home_goals": hg, "away_goals": ag,
                         "year": kickoff.year})
    fixtures.sort(key=lambda x: (x["kickoff"], x["match_id"]))
    return raw, fixtures


def fit_rates(rows, regularization: float):
    teams = sorted({x["home"] for x in rows} | {x["away"] for x in rows})
    if not rows or len(teams) < 2:
        raise ValueError("insufficient history to fit team goal rates")
    team_index = {name: i for i, name in enumerate(teams)}
    hi = np.array([team_index[x["home"]] for x in rows], dtype=int)
    ai = np.array([team_index[x["away"]] for x in rows], dtype=int)
    hg = np.array([x["home_goals"] for x in rows], dtype=float)
    ag = np.array([x["away_goals"] for x in rows], dtype=float)
    log_h_factorial = np.array([math.lgamma(float(x) + 1.0) for x in hg])
    log_a_factorial = np.array([math.lgamma(float(x) + 1.0) for x in ag])
    free = len(teams) - 1
    mean_h = max(float(hg.mean()), 0.2)
    mean_a = max(float(ag.mean()), 0.2)
    initial = np.zeros(2 + 2 * free, dtype=float)
    initial[0], initial[1] = math.log(mean_h), math.log(mean_a)

    def unpack(x):
        attack = np.concatenate((x[2:2 + free], [-float(np.sum(x[2:2 + free]))]))
        defense = np.concatenate((x[2 + free:2 + 2 * free], [-float(np.sum(x[2 + free:2 + 2 * free]))]))
        return attack, defense

    def objective(x):
        attack, defense = unpack(x)
        eta_h = x[0] + attack[hi] + defense[ai]
        eta_a = x[1] + attack[ai] + defense[hi]
        if np.any(eta_h > 5) or np.any(eta_a > 5) or np.any(eta_h < -6) or np.any(eta_a < -6):
            return 1e100
        lam_h, lam_a = np.exp(eta_h), np.exp(eta_a)
        nll = np.sum(lam_h - hg * eta_h + log_h_factorial)
        nll += np.sum(lam_a - ag * eta_a + log_a_factorial)
        nll += 0.5 * regularization * (float(np.dot(attack, attack)) + float(np.dot(defense, defense)))
        return float(nll) if math.isfinite(float(nll)) else 1e100

    result = minimize(objective, initial, method="L-BFGS-B", options={"maxiter": 500, "ftol": 1e-10})
    if not np.isfinite(result.fun) or result.fun >= 1e99:
        raise RuntimeError("goal-rate optimizer failed")
    attack, defense = unpack(result.x)
    return {"teams": teams, "team_index": team_index, "mu_home": float(result.x[0]),
            "mu_away": float(result.x[1]), "attack": attack, "defense": defense,
            "regularization": regularization, "training_matches": len(rows),
            "training_end_utc": max(x["kickoff"] for x in rows)}


def predict(model, home: str, away: str):
    # Each unseen team receives neutral strength independently; a newly
    # promoted home team must not erase the known away team's fitted effects.
    hi = model["team_index"].get(home)
    ai = model["team_index"].get(away)
    home_attack = model["attack"][hi] if hi is not None else 0.0
    home_defense = model["defense"][hi] if hi is not None else 0.0
    away_attack = model["attack"][ai] if ai is not None else 0.0
    away_defense = model["defense"][ai] if ai is not None else 0.0
    lam_h = float(np.exp(model["mu_home"] + home_attack + away_defense))
    lam_a = float(np.exp(model["mu_away"] + away_attack + home_defense))
    if not math.isfinite(lam_h + lam_a) or lam_h <= 0 or lam_a <= 0:
        raise ValueError("invalid predicted goal rate")
    def pmf(lam):
        values = [math.exp(-lam)]
        for k in range(1, MAX_GOALS):
            values.append(values[-1] * lam / k)
        total = sum(values)
        return [x / total for x in values]
    ph, pa = pmf(lam_h), pmf(lam_a)
    grid = [[ph[h] * pa[a] for a in range(MAX_GOALS)] for h in range(MAX_GOALS)]
    mass = sum(sum(row) for row in grid)
    grid = [[v / mass for v in row] for row in grid]
    p_home = sum(grid[h][a] for h in range(MAX_GOALS) for a in range(MAX_GOALS) if h > a)
    p_draw = sum(grid[i][i] for i in range(MAX_GOALS))
    p_away = 1.0 - p_home - p_draw
    p_over = sum(grid[h][a] for h in range(MAX_GOALS) for a in range(MAX_GOALS) if h + a > 2.5)
    return {"lambda_home": lam_h, "lambda_away": lam_a, "grid": grid,
            "p_home": p_home, "p_draw": p_draw, "p_away": p_away, "p_over_2_5": p_over}


def choose_regularization(prior_rows, validation_year: int):
    train = [x for x in prior_rows if x["year"] < validation_year]
    valid = [x for x in prior_rows if x["year"] == validation_year]
    if len(train) < 20 or not valid:
        return 0.1, {"validation_year": None, "candidate_log_losses": None}
    scores = {}
    for penalty in REGULARIZATIONS:
        try:
            model = fit_rates(train, penalty)
            score = 0.0
            for item in valid:
                pred = predict(model, item["home"], item["away"])
                ph = max(pred["grid"][item["home_goals"]][item["away_goals"]], EPS) if max(item["home_goals"], item["away_goals"]) < MAX_GOALS else EPS
                score -= math.log(ph)
            scores[str(penalty)] = score / len(valid)
        except Exception:
            scores[str(penalty)] = float("inf")
    best = min(REGULARIZATIONS, key=lambda x: scores.get(str(x), float("inf")))
    if not math.isfinite(scores.get(str(best), float("inf"))):
        best = 0.1
    return best, {"validation_year": validation_year, "candidate_exact_score_log_loss": scores,
                  "validation_fixtures": len(valid), "training_fixtures": len(train)}


def score_report(rows):
    if not rows:
        return {"unique_fixtures": 0, "log_loss": None, "brier": None}
    p1 = np.array([[x["prediction"][k] for k in ("p_home", "p_draw", "p_away")] for x in rows], dtype=float)
    y1 = np.array([0 if x["home_goals"] > x["away_goals"] else 1 if x["home_goals"] == x["away_goals"] else 2 for x in rows])
    ll1 = float(-np.log(np.clip(p1[np.arange(len(rows)), y1], EPS, 1)).mean())
    br1 = float(np.square(p1 - np.eye(3)[y1]).sum(axis=1).mean())
    po = np.array([x["prediction"]["p_over_2_5"] for x in rows], dtype=float)
    yo = np.array([int(x["home_goals"] + x["away_goals"] > 2.5) for x in rows], dtype=float)
    llu = float(-(yo * np.log(np.clip(po, EPS, 1)) + (1 - yo) * np.log(np.clip(1 - po, EPS, 1))).mean())
    bru = float(np.square(po - yo).mean())
    ll_score = []
    for x in rows:
        h, a = x["home_goals"], x["away_goals"]
        probability = x["prediction"]["grid"][h][a] if max(h, a) < MAX_GOALS else EPS
        ll_score.append(-math.log(max(probability, EPS)))
    return {"unique_fixtures": len(rows), "1x2_log_loss": round(ll1, 8), "1x2_brier": round(br1, 8),
            "ou_over_2_5_log_loss": round(llu, 8), "ou_over_2_5_brier": round(bru, 8),
            "exact_score_log_loss": round(sum(ll_score) / len(ll_score), 8)}


def run(private_dir: Path, output_path: Path):
    manifest_path = private_dir / "candidate-manifest.json"
    raw, fixtures = read_manifest(manifest_path)
    grouped = defaultdict(list)
    for fixture in fixtures:
        grouped[fixture["league"]].append(fixture)
    forecasts = []
    fit_receipts = []
    yearly = defaultdict(list)
    for league, league_rows in sorted(grouped.items()):
        years = sorted({x["year"] for x in league_rows})
        for year in years:
            train = [x for x in league_rows if x["year"] < year]
            test = [x for x in league_rows if x["year"] == year]
            if not train or not test:
                continue
            train_ids = {x["match_id"] for x in train}
            test_ids = {x["match_id"] for x in test}
            if train_ids & test_ids or any(x["year"] != year for x in test):
                raise ValueError("fixture identity/year leakage across M5 fold")
            validation_year = max(x["year"] for x in train)
            penalty, tuning = choose_regularization(train, validation_year)
            model = fit_rates(train, penalty)
            if model["training_end_utc"] >= min(x["kickoff"] for x in test):
                raise ValueError("M5 training cutoff is not before target fixtures")
            fit_receipts.append({"league": league, "test_year": year, "train_fixtures": len(train),
                                 "test_fixtures": len(test), "train_end_utc": model["training_end_utc"].isoformat(),
                                 "regularization": penalty, "tuning": tuning})
            for fixture in test:
                prediction = predict(model, fixture["home"], fixture["away"])
                event = {**fixture, "prediction": prediction, "train_end_utc": model["training_end_utc"],
                         "training_fixtures": len(train), "regularization": penalty,
                         "prediction_asof_utc": datetime(year, 1, 1, tzinfo=timezone.utc)}
                forecasts.append(event)
                yearly[year].append(event)
    out_private = safe_private_dir(private_dir / "m5-model-oos")
    forecast_path = out_private / "m5_goal_model_forecasts.jsonl"
    with forecast_path.open("w", encoding="utf-8") as stream:
        for row in forecasts:
            serial = {**row, "kickoff": row["kickoff"].isoformat().replace("+00:00", "Z"),
                      "train_end_utc": row["train_end_utc"].isoformat().replace("+00:00", "Z"),
                      "prediction_asof_utc": row["prediction_asof_utc"].isoformat().replace("+00:00", "Z")}
            stream.write(json.dumps(serial, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(forecast_path, 0o600)
    aggregate = {"protocol": "M5_M1_SCOPE_CALENDAR_YEAR_GOAL_MODEL_OOS_V1",
                 "generated_utc": datetime.now(timezone.utc).isoformat(),
                 "input_candidate_manifest_sha256": digest(raw), "input_schedule_fixtures": len(fixtures),
                 "unique_oos_fixtures": len(forecasts), "source_scope": "frozen M1 formal top-tier competition whitelist",
                 "model": "independent home/away Poisson goal-rate model with zero-sum team attack/defence effects; ridge penalty selected only on the immediately prior calendar-year validation fold; 15x15 independent score distribution",
                 "time_isolation": "Each target UTC calendar year is fit only on earlier-year FT fixtures in that competition; team-season fixture IDs are disjoint; training cutoff precedes every test kickoff.",
                 "M1_MR1_predictions_or_ledgers_used": False, "Crown_prices_used": False,
                 "ROI": None, "overall_oos": score_report(forecasts),
                 "by_year_oos": {str(year): score_report(rows) for year, rows in sorted(yearly.items())},
                 "by_competition_oos": {league: score_report([x for x in forecasts if x["league"] == league]) for league in sorted(grouped)},
                 "fold_count": len(fit_receipts), "fold_metadata": fit_receipts,
                 "private_forecast_sha256": digest(forecast_path.read_bytes()),
                 "private_forecast_rows": len(forecasts)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "input_fixtures": len(fixtures),
                      "oos_fixtures": len(forecasts), "folds": len(fit_receipts),
                      "oos_metrics": aggregate["overall_oos"], "ROI": None}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "results/m5_goal_model_oos.json")
    args = parser.parse_args()
    run(args.private_dir, args.output)


if __name__ == "__main__":
    main()
