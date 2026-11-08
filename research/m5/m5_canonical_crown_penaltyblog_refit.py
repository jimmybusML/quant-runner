#!/usr/bin/env python3
"""Refit original penaltyblog goal models on the current M5 Crown cohort.

For each target UTC year and league, fit strictly on completed same-league
fixtures before January 1 UTC, then predict every Crown-quoted target fixture
with known teams. This is an event-time retrospective OOS replay: the historic
API response was received after kickoff even when its quote event was earlier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from penaltyblog.models import BivariatePoissonGoalModel, DixonColesGoalModel, PoissonGoalsModel

from research.m5.m3_grid_crown_replay import legs_result, payout, score
from research.m5.m5_model_family_canonical_crown_comparison import fast_bootstrap, grid_distribution, category_return, CAT

MODELS = {
    "M3_Poisson": PoissonGoalsModel,
    "M3_Dixon_Coles": DixonColesGoalModel,
    "M3_Bivariate_Poisson": BivariatePoissonGoalModel,
}
FALLBACK_MODELS = {f"{name}_LeagueAvgFallback": name for name in MODELS}
SIDES = {"AH": ("home", "away"), "OU": ("over", "under")}


def dt(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must carry an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_grid(prediction):
    raw = prediction.grid.tolist() if hasattr(prediction.grid, "tolist") else prediction.grid
    grid = [[float(value) for value in row] for row in raw]
    mass = math.fsum(value for row in grid for value in row)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("invalid penaltyblog grid shape")
    if any(not math.isfinite(v) or v < 0 for row in grid for v in row) or abs(mass - 1) > 1e-7:
        raise ValueError("invalid penaltyblog grid mass")
    return grid


def league_average_grid(train, max_goals=15):
    """Independent home/away Poisson prior from pre-cutoff league scores."""
    home_rate = math.fsum(r["home_goals"] for r in train) / len(train)
    away_rate = math.fsum(r["away_goals"] for r in train) / len(train)
    def pmf(rate):
        values = [math.exp(-rate)]
        for k in range(1, max_goals):
            values.append(values[-1] * rate / k)
        mass = math.fsum(values)
        return [x / mass for x in values]
    hp, ap = pmf(home_rate), pmf(away_rate)
    return [[h * a for a in ap] for h in hp]


def safe_private(path, repo):
    p = path.expanduser().resolve()
    if p == repo or repo in p.parents:
        raise ValueError("fixture-level forecasts must remain outside the public repository")
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(p.parent, 0o700)
    return p


def summarize(rows, seed):
    n = len(rows)
    pnl = [r["pnl"] for r in rows]
    counts = Counter(r["settlement"] for r in rows)
    by_event, by_year = defaultdict(float), defaultdict(list)
    for r in rows:
        by_event[r["quote_event_utc"]] += r["pnl"]
        by_year[r["kickoff_utc"][:4]].append(r["pnl"])
    equity = peak = dd = 0.0
    for event in sorted(by_event):
        equity += by_event[event]
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    ll, brier = score([(r["settlement"], r["distribution"]) for r in rows])
    ci = fast_bootstrap(pnl, seed) if n else None
    return {
        "unique_fixture_markets": n, "simulated_bets": n, "settled_bets": n,
        "stake_units": n, "net_units": round(math.fsum(pnl), 6),
        "roi_pct": round(100 * math.fsum(pnl) / n, 6) if n else None,
        "settlement_counts": {c: counts[c] for c in CAT},
        "max_drawdown_units_by_quote_event_time": round(dd, 6) if n else None,
        "settlement_log_loss": ll, "settlement_brier": brier,
        "bootstrap_95_roi_pct": ({"lower": round(100 * ci["lower_95"], 6),
                                   "upper": round(100 * ci["upper_95"], 6),
                                   "repetitions": ci["repetitions"]} if ci else None),
        "by_utc_kickoff_year": {year: {"n": len(values), "net_units": round(math.fsum(values), 6),
            "roi_pct": round(100 * math.fsum(values) / len(values), 6)} for year, values in sorted(by_year.items())},
        "quote_sources": {"Crown": n}, "response_receipt_timing": {"post_kickoff": n},
        "unique_leagues": len({r["league"] for r in rows}),
    }


def run(manifest_path: Path, quote_rows_path: Path, private_rows_path: Path,
        public_report_path: Path):
    repo = Path(__file__).resolve().parents[2]
    private_rows_path = safe_private(private_rows_path, repo)
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {}
    by_league = defaultdict(list)
    for row in manifest.get("rows", []):
        fid = str(row["match_id"])
        if fid in fixtures:
            raise ValueError(f"duplicate candidate fixture {fid}")
        kickoff = dt(row.get("kickoff_utc"))
        if not kickoff:
            continue
        fixture = {**row, "match_id": fid, "kickoff_dt": kickoff,
                   "home_goals": int(row["home_goals"]), "away_goals": int(row["away_goals"])}
        fixtures[fid] = fixture
        by_league[str(row["league"])].append(fixture)

    quotes = {}
    for line in quote_rows_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (str(row["fixture_id"]), row["market"])
        if key in quotes:
            raise ValueError(f"duplicate Crown fixture-market {key}")
        fixture = fixtures.get(key[0])
        if fixture is None:
            continue
        kickoff = dt(row["kickoff_utc"]); event = dt(row["quote_event_utc"])
        received = dt(row["quote_received_utc"])
        asof = datetime(kickoff.year, 1, 1, tzinfo=timezone.utc)
        if (fixture["kickoff_dt"] != kickoff or fixture["league"] != row["league"]
                or fixture["home_goals"] != int(row["actual_home_goals"])
                or fixture["away_goals"] != int(row["actual_away_goals"])):
            raise ValueError("candidate manifest and canonical Crown row identity/result mismatch")
        if not asof <= event < kickoff:
            raise ValueError("Crown quote event is outside annual forecast-to-kickoff UTC window")
        if (row.get("quote_received_pre_kickoff") is not False or not received or received < kickoff):
            raise ValueError("historic API receipt timing must be explicitly marked post-kickoff")
        prices = [float(x) for x in row["prices"]]
        if len(prices) != 2 or any(not math.isfinite(x) or x <= 1 for x in prices):
            raise ValueError("invalid Crown decimal prices")
        quotes[key] = {**row, "fixture_id": key[0], "market": key[1], "kickoff_dt": kickoff,
                       "asof_dt": asof, "event_dt": event, "received_dt": received,
                       "line_value": float(row["line"]),
                       "price_values": prices}

    target_years = sorted({q["kickoff_dt"].year for q in quotes.values()})
    rows_by_model_market = {name: {m: [] for m in SIDES}
                            for name in (*MODELS, *FALLBACK_MODELS)}
    folds = []
    audit = Counter()
    predictions = 0
    with private_rows_path.open("w", encoding="utf-8") as output:
        os.chmod(private_rows_path, 0o600)
        for league, matches in sorted(by_league.items()):
            for year in target_years:
                targets = {fid for fid, _ in quotes
                           if fixtures[fid]["league"] == league and fixtures[fid]["kickoff_dt"].year == year}
                if not targets:
                    continue
                cutoff = datetime(year, 1, 1, tzinfo=timezone.utc)
                train = [r for r in matches if r["kickoff_dt"] < cutoff]
                if not train:
                    audit["no_prior_training_rows"] += len(targets)
                    continue
                train_end = max(r["kickoff_dt"] for r in train)
                if not train_end < cutoff:
                    raise AssertionError("training period crosses UTC-year boundary")
                train_ids = {r["match_id"] for r in train}
                if train_ids & targets:
                    raise AssertionError("train/test fixture overlap")
                fallback_grid = league_average_grid(train)
                models, known = {}, {}
                fold = {"league": league, "year": year, "cutoff_utc": cutoff.isoformat(),
                        "training_fixtures": len(train), "training_end_utc": train_end.isoformat(),
                        "target_crown_fixtures": len(targets), "model_fit": {}}
                for name, model_class in MODELS.items():
                    try:
                        model = model_class([r["home_goals"] for r in train],
                                            [r["away_goals"] for r in train],
                                            [r["home"] for r in train], [r["away"] for r in train])
                        model.fit()
                        models[name] = model
                        known[name] = set(model.teams)
                        fold["model_fit"][name] = "fit"
                    except Exception as exc:
                        audit[f"fit_failure_{name}_{type(exc).__name__}"] += len(targets)
                        fold["model_fit"][name] = f"fit_failure_{type(exc).__name__}"
                for fid in sorted(targets):
                    fixture = fixtures[fid]
                    quote_keys = [(fid, m) for m in SIDES if (fid, m) in quotes]
                    grids = {}
                    hybrids = {}
                    unseen = any(any(fixture[t] not in known[name] for t in ("home", "away"))
                                 for name in models)
                    if unseen:
                        audit["unseen_team_fixture"] += 1
                    failed = False
                    for name, model in models.items():
                        known_for_model = all(fixture[t] in known[name] for t in ("home", "away"))
                        if not known_for_model:
                            hybrids[name] = fallback_grid
                            continue
                        try:
                            model_grid = normalized_grid(model.predict(fixture["home"], fixture["away"],
                                                                       max_goals=15, normalize=True))
                            grids[name] = model_grid
                            hybrids[name] = model_grid
                        except Exception as exc:
                            audit[f"prediction_failure_{type(exc).__name__}"] += 1
                            hybrids[name] = fallback_grid
                    if len(hybrids) != len(MODELS):
                        audit["incomplete_model_fixture"] += 1
                        continue
                    if len(grids) == len(MODELS):
                        predictions += 1
                    else:
                        audit["fallback_fixture_prediction"] += 1
                    serialized = {"fixture_id": fid, "league": league, "kickoff_utc": fixture["kickoff_dt"].isoformat(),
                                  "prediction_asof_utc": cutoff.isoformat(), "train_end_utc": train_end.isoformat(),
                                  "grids": grids, "league_average_fallback_used": unseen}
                    for _, market in quote_keys:
                        q = quotes[(fid, market)]
                        sides = SIDES[market]
                        evaluation_grids = {**grids, **{f"{name}_LeagueAvgFallback": grid
                                             for name, grid in hybrids.items()}}
                        for name, grid in evaluation_grids.items():
                            dist = [grid_distribution(grid, market, side, q["line_value"]) for side in sides]
                            ev = [category_return(d, price) for d, price in zip(dist, q["price_values"])]
                            idx = 0 if ev[0] >= ev[1] else 1
                            side, price = sides[idx], q["price_values"][idx]
                            _, result = legs_result(market, side, q["line_value"],
                                                    fixture["home_goals"], fixture["away_goals"])
                            row = {"fixture_id": fid, "market": market, "league": league,
                                   "kickoff_utc": q["kickoff_utc"], "quote_event_utc": q["quote_event_utc"],
                                   "quote_received_utc": q["quote_received_utc"], "line": q["line_value"],
                                   "prices": q["prices"], "side": side, "price": price,
                                   "settlement": result, "pnl": payout(legs_result(market, side, q["line_value"],
                                       fixture["home_goals"], fixture["away_goals"])[0], price),
                                   "distribution": dist[idx]}
                            if name in MODELS or name in FALLBACK_MODELS:
                                rows_by_model_market[name][market].append(row)
                            serialized.setdefault("market_evaluations", {}).setdefault(market, {})[name] = {
                                "side": side, "price": price, "settlement": result,
                                "distribution": dist[idx], "pnl": row["pnl"]}
                    output.write(json.dumps(serialized, separators=(",", ":")) + "\n")
                folds.append(fold)

    report = {
        "protocol": "M5_CANONICAL_CROWN_PENALTYBLOG_ANNUAL_WALK_FORWARD_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": digest(Path(__file__).resolve()),
        "penaltyblog_version": version("penaltyblog"),
        "inputs": {"candidate_manifest_sha256": digest(manifest_path),
                   "canonical_quote_rows_sha256": digest(quote_rows_path),
                   "quote_rows_file_sha256": hashlib.sha256(quote_rows_path.read_bytes()).hexdigest()},
        "candidate_manifest_fixtures": len(fixtures),
        "canonical_crown_fixture_markets_by_market": {m: sum(1 for _, mk in quotes if mk == m) for m in SIDES},
        "utc_coverage": {m: {
            "kickoff": [min(q["kickoff_utc"] for k, q in quotes.items() if k[1] == m),
                        max(q["kickoff_utc"] for k, q in quotes.items() if k[1] == m)],
            "quote_event": [min(q["quote_event_utc"] for k, q in quotes.items() if k[1] == m),
                            max(q["quote_event_utc"] for k, q in quotes.items() if k[1] == m)],
            "response_received": [min(q["quote_received_utc"] for k, q in quotes.items() if k[1] == m),
                                  max(q["quote_received_utc"] for k, q in quotes.items() if k[1] == m)],
        } for m in SIDES},
        "unique_target_fixtures": len({fid for fid, _ in quotes}),
        "complete_three_model_oos_fixture_predictions": predictions,
        "three_model_predictions_with_league_average_unseen_team_fallback": len({
            r["fixture_id"] for name in FALLBACK_MODELS
            for market_rows in rows_by_model_market[name].values() for r in market_rows}),
        "fold_count": len(folds), "target_utc_years": target_years,
        "time_order_passed": all(dt(f["training_end_utc"]) < dt(f["cutoff_utc"])
                                  and dt(f["cutoff_utc"]) == datetime(int(f["year"]), 1, 1, tzinfo=timezone.utc)
                                  for f in folds),
        "training_test_fixture_ids_disjoint": True,
        "fixture_level_rows_published": False,
        "markets": {}, "audit": dict(audit), "folds": folds,
        "training_rule": "For each league and target UTC year, fit original penaltyblog defaults using all same-league candidate-manifest results with kickoff strictly before January 1 UTC. Test fixtures are from the newly captured canonical Crown summary set. Prediction cutoff < quote source-event UTC < kickoff; target fixtures are excluded by date and ID.",
        "quote_source": "Crown only; no TotalCorner substitution.",
        "receipt_timing": "All historical provider responses were received after kickoff; event-time OOS simulation is not contemporaneously executable ROI.",
        "limitations": ["The strict original-model rows exclude fixtures with either team unseen by that league's pre-year training sample.",
                        "Separately named LeagueAvgFallback variants use only same-league pre-year home/away goal means for fixtures the original model cannot predict; this is an exploratory hybrid, not the original penaltyblog model.",
                        "Retrospective Crown summary retrieval does not establish pre-kickoff receipt or execution.",
                        "This research does not alter any production model, gate, order, ledger, or Telegram flow."],
    }
    for market_idx, market in enumerate(SIDES):
        report["markets"][market] = {name: summarize(model_rows[market], 20261400 + market_idx * 10 + i)
            for i, (name, model_rows) in enumerate(rows_by_model_market.items())}
    public_report_path.parent.mkdir(parents=True, exist_ok=True)
    public_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quote-rows", type=Path, required=True)
    parser.add_argument("--private-rows", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.manifest, args.quote_rows, args.private_rows, args.report)
    print(json.dumps({m: {name: {"n": x["simulated_bets"], "roi_pct": x["roi_pct"]}
                          for name, x in models.items()} for m, models in report["markets"].items()}, sort_keys=True))


if __name__ == "__main__":
    main()
