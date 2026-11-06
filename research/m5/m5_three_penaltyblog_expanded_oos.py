#!/usr/bin/env python3
"""Run the three M3 penaltyblog goal models on the expanded M5 Crown/TOTAL archive.

The 51-league candidate manifest supplies only completed match results for
training/scoring. Each UTC-year test fold is fit strictly from earlier UTC
years. Crown is selected per fixture-market first; TotalCorner default fills
only a missing Crown market. Fixture-level forecasts and quote details stay in
the private directory; the repository receives an aggregate-only report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo

from penaltyblog.models import BivariatePoissonGoalModel, DixonColesGoalModel, PoissonGoalsModel

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.m5.m3_grid_crown_replay import legs_result, payout, bootstrap, score
from research.m5.m5_source_union_replay import event_rows, fixture_row, raw_event, read_jsonl
from research.m5.crown_historical_capture import ensure_private_destination, local_to_utc

MODELS = {
    "poisson": PoissonGoalsModel,
    "dixon_coles": DixonColesGoalModel,
    "bivariate_poisson": BivariatePoissonGoalModel,
}
MARKETS = ("AH", "OU")
CATEGORIES = ("win", "half_win", "push", "half_loss", "loss")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def instant(value: object) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def safe_private_output(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    repo = Path(__file__).resolve().parents[2]
    if resolved == repo or repo in resolved.parents:
        raise ValueError("fixture-level M3 forecasts must remain outside the public repository")
    resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(resolved.parent, 0o700)
    return resolved


def load_quotes(root: Path, fixtures: dict[str, dict], forecast_asof: dict[str, datetime], zone_name: str):
    zone = ZoneInfo(zone_name)
    crown_receipts = {str(x.get("match_id")): x for x in read_jsonl(root / "crown-response-index.jsonl")}
    total_receipts = {str(x.get("match_id")): x for x in read_jsonl(root / "totalcorner-default-index.jsonl")
                      if x.get("status") == "verified_fixture_response"}
    selected: dict[tuple[str, str], dict] = {}
    audit = Counter()
    response_hashes: set[str] = set()

    def read_provider(mid: str, fixture: dict, market: str, source: str):
        folder = "crown-responses" if source == "Crown" else "totalcorner-default-responses"
        path = root / folder / f"{mid}.json"
        if not path.exists():
            return None
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
            row = fixture_row(payload, mid)
            kickoff = instant(fixture.get("kickoff_utc"))
            start = local_to_utc(row.get("start"), zone) if row else None
            if (payload.get("success") != 1 or row is None or kickoff is None
                    or row.get("h") != fixture.get("home") or row.get("a") != fixture.get("away")
                    or row.get("l") != fixture.get("league") or start != kickoff):
                audit[f"{source}_identity_or_kickoff_mismatch"] += 1
                return None
            # The Crown fixture payload is expected to carry FT. TotalCorner may
            # omit FT in the fallback endpoint; the independent manifest anchors it.
            if source == "Crown" and (int(row.get("hg")), int(row.get("ag"))) != (
                    int(fixture["home_goals"]), int(fixture["away_goals"])):
                audit["Crown_score_mismatch"] += 1
                return None
            quote = raw_event(event_rows(row, market, "crown" if source == "Crown" else "totalcorner"),
                              market, forecast_asof[mid], kickoff, zone)
            if not quote:
                return None
            observed, line, prices = quote
            receipt_index = crown_receipts if source == "Crown" else total_receipts
            receipt = instant(receipt_index.get(mid, {}).get("captured_at_utc"))
            if receipt is None or receipt < observed:
                audit[f"{source}_missing_or_invalid_receipt"] += 1
                return None
            response_hashes.add(sha(raw))
            return {"source": source, "line": float(line), "prices": [float(prices[0]), float(prices[1])],
                    "event_utc": observed.isoformat().replace("+00:00", "Z"),
                    "receipt_utc": receipt.isoformat().replace("+00:00", "Z"),
                    "receipt_before_kickoff": receipt < kickoff}
        except (OSError, ValueError, TypeError, KeyError, OverflowError):
            audit[f"{source}_invalid_response"] += 1
            return None

    for mid, fixture in fixtures.items():
        if mid not in forecast_asof:
            continue
        for market in MARKETS:
            quote = read_provider(mid, fixture, market, "Crown")
            if quote is None:
                quote = read_provider(mid, fixture, market, "TotalCorner_default")
            if quote is not None:
                selected[(mid, market)] = quote
    return selected, audit, response_hashes


def normalized_grid(prediction) -> list[list[float]]:
    grid = prediction.grid.tolist() if hasattr(prediction.grid, "tolist") else prediction.grid
    out = [[float(x) for x in row] for row in grid]
    mass = math.fsum(x for row in out for x in row)
    if not out or not out[0] or any(len(row) != len(out[0]) for row in out):
        raise ValueError("invalid score grid shape")
    if any(not math.isfinite(x) or x < 0 for row in out for x in row) or abs(mass - 1.0) > 1e-7:
        raise ValueError("invalid score grid probabilities")
    return out


def category_distribution(grid: list[list[float]], market: str, side: str, line: float):
    mass = Counter()
    for home, row in enumerate(grid):
        for away, probability in enumerate(row):
            _, category = legs_result(market, side, line, home, away)
            mass[category] += probability
    return {category: float(mass[category]) for category in CATEGORIES}


def summarize_market_rows(rows: list[dict], seed: int, include_bootstrap: bool = False) -> dict:
    pnl = [float(row["pnl"]) for row in rows]
    outcomes = Counter(row["category"] for row in rows)
    by_event = defaultdict(float)
    for row in rows:
        by_event[row["event_utc"]] += float(row["pnl"])
    equity = peak = max_dd = 0.0
    for event_time in sorted(by_event):
        equity += by_event[event_time]
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    ll, brier = score([(row["category"], row["distribution"]) for row in rows])
    source_counts = Counter(row["source"] for row in rows)
    receipt_counts = Counter("pre_kickoff" if row["receipt_before_kickoff"] else "post_kickoff" for row in rows)
    return {
        "unique_fixtures": len(rows), "simulated_bets": len(rows), "settled_bets": len(rows), "pending_bets": 0,
        "net_units": round(math.fsum(pnl), 6),
        "roi_pct": round(100 * math.fsum(pnl) / len(rows), 6) if rows else None,
        "settlement_counts": {category: outcomes[category] for category in CATEGORIES},
        "max_drawdown_units_by_quote_event_time": round(max_dd, 6),
        "roi_bootstrap_95pct": bootstrap(pnl, seed) if include_bootstrap else None,
        "settlement_log_loss": ll, "settlement_brier": brier,
        "quote_source_fixture_markets": dict(source_counts),
        "actual_response_receipt_timing": dict(receipt_counts),
    }


def run(private_dir: Path, private_predictions: Path, public_report: Path,
        source_timezone: str = "Asia/Shanghai", years: tuple[int, ...] | None = None):
    root = ensure_private_destination(private_dir)
    manifest_raw = (root / "candidate-manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    fixtures = {str(row["match_id"]): row for row in manifest.get("rows", [])}
    forecast_path = root / "m5-model-oos" / "m5_goal_model_forecasts.jsonl"
    forecast_sha256 = sha_file(forecast_path)
    forecast_asof: dict[str, datetime] = {}
    target_years: set[int] = set()
    forecast_identity_errors = Counter()
    with forecast_path.open("r", encoding="utf-8") as forecast_stream:
        for line in forecast_stream:
            try:
                row = json.loads(line)
                mid = str(row["match_id"])
                fixture = fixtures.get(mid)
                asof, kickoff, train_end = instant(row.get("prediction_asof_utc")), instant(row.get("kickoff")), instant(row.get("train_end_utc"))
                if not fixture or not asof or not kickoff or not train_end:
                    continue
                if (row.get("league"), row.get("home"), row.get("away"), row.get("kickoff"),
                        int(row.get("home_goals")), int(row.get("away_goals"))) != (
                        fixture.get("league"), fixture.get("home"), fixture.get("away"), fixture.get("kickoff_utc"),
                        int(fixture.get("home_goals")), int(fixture.get("away_goals"))):
                    forecast_identity_errors["fixture_identity_or_result_mismatch"] += 1
                    continue
                if not (train_end < asof < kickoff):
                    forecast_identity_errors["invalid_forecast_chronology"] += 1
                    continue
                if years and kickoff.year not in years:
                    continue
                forecast_asof[mid] = asof
                target_years.add(kickoff.year)
            except (ValueError, TypeError, KeyError):
                continue

    quotes, quote_audit, response_hashes = load_quotes(root, fixtures, forecast_asof, source_timezone)
    quoted_ids = {mid for mid, _ in quotes}
    by_league: dict[str, list[dict]] = defaultdict(list)
    for row in fixtures.values():
        kickoff = instant(row.get("kickoff_utc"))
        if kickoff:
            by_league[str(row.get("league") or "")].append({**row, "kickoff": kickoff, "year": kickoff.year})

    forecast_rows = []
    fold_receipts = []
    failures = Counter()
    m3_models = {
        "poisson": PoissonGoalsModel,
        "dixon_coles": DixonColesGoalModel,
        "bivariate_poisson": BivariatePoissonGoalModel,
    }
    # All three models are fit independently using their original penaltyblog
    # implementations and default parameters on the same strictly earlier data.
    for league, matches in sorted(by_league.items()):
        for year in sorted(target_years):
            cutoff = datetime(year, 1, 1, tzinfo=timezone.utc)
            league_targets = [r for r in matches if r["year"] == year and r["match_id"] in quoted_ids]
            if not league_targets:
                continue
            train = [r for r in matches if r["kickoff"] < cutoff]
            if not train:
                failures["no_prior_training_rows"] += len(league_targets)
                continue
            train_end = max(r["kickoff"] for r in train)
            if not train_end < cutoff:
                raise AssertionError("training data crossed the target UTC-year boundary")
            if {str(r["match_id"]) for r in train} & {str(r["match_id"]) for r in league_targets}:
                raise AssertionError("train/test fixture ID overlap")
            fold = {"league": league, "target_utc_year": year, "training_matches": len(train),
                    "training_end_utc": train_end.isoformat().replace("+00:00", "Z"),
                    "forecast_asof_utc": cutoff.isoformat().replace("+00:00", "Z"),
                    "target_quoted_fixtures": len(league_targets), "models": {}}
            fitted = {}
            known_teams = {}
            for model_name, model_type in m3_models.items():
                try:
                    model = model_type([x["home_goals"] for x in train], [x["away_goals"] for x in train],
                                       [x["home"] for x in train], [x["away"] for x in train])
                    model.fit()
                    fitted[model_name] = model
                    known_teams[model_name] = set(model.teams)
                    fold["models"][model_name] = {"status": "fit", "team_count": len(model.teams)}
                except Exception as exc:
                    failures[f"fit_{model_name}_{type(exc).__name__}"] += len(league_targets)
                    fold["models"][model_name] = {"status": "fit_failed", "error_type": type(exc).__name__}
            for fixture in league_targets:
                mid = str(fixture["match_id"])
                model_predictions = {}
                for model_name, model in fitted.items():
                    if fixture["home"] not in known_teams[model_name] or fixture["away"] not in known_teams[model_name]:
                        failures[f"unseen_team_{model_name}"] += 1
                        continue
                    try:
                        prediction = model.predict(fixture["home"], fixture["away"], max_goals=15, normalize=True)
                        model_predictions[model_name] = normalized_grid(prediction)
                    except Exception as exc:
                        failures[f"predict_{model_name}_{type(exc).__name__}"] += 1
                if len(model_predictions) != len(m3_models):
                    failures["incomplete_three_model_fixture"] += 1
                    continue
                forecast_rows.append({"match_id": mid, "league": league, "year": year,
                    "kickoff_utc": fixture["kickoff"].isoformat().replace("+00:00", "Z"),
                    "home": fixture["home"], "away": fixture["away"],
                    "actual_home_goals": int(fixture["home_goals"]), "actual_away_goals": int(fixture["away_goals"]),
                    "prediction_asof_utc": cutoff.isoformat().replace("+00:00", "Z"),
                    "train_end_utc": train_end.isoformat().replace("+00:00", "Z"),
                    "training_matches": len(train), "grids": model_predictions})
            fold_receipts.append(fold)

    forecast_rows.sort(key=lambda r: (r["kickoff_utc"], r["match_id"]))
    # Ensure each model was scored on precisely the same complete fixture cohort.
    forecast_by_id = {r["match_id"]: r for r in forecast_rows}
    if len(forecast_by_id) != len(forecast_rows):
        raise ValueError("duplicate M3 forecast fixture identity")
    model_market_rows = {m: {name: [] for name in MARKETS} for m in m3_models}
    for fixture in forecast_rows:
        for market in MARKETS:
            quote = quotes.get((fixture["match_id"], market))
            if not quote:
                continue
            line, prices = quote["line"], quote["prices"]
            sides = ("home", "away") if market == "AH" else ("over", "under")
            for model_name, grid in fixture["grids"].items():
                ev = [math.fsum(float(p) * payout(legs_result(market, side, line, h, a)[0], price)
                                for h, row in enumerate(grid) for a, p in enumerate(row))
                      for side, price in zip(sides, prices)]
                side_index = 0 if ev[0] >= ev[1] else 1
                side, price = sides[side_index], prices[side_index]
                legs, actual_category = legs_result(market, side, line,
                                                      fixture["actual_home_goals"], fixture["actual_away_goals"])
                pnl = payout(legs, price)
                dist = category_distribution(grid, market, side, line)
                model_market_rows[model_name][market].append({
                    "fixture_id": fixture["match_id"], "pnl": pnl, "category": actual_category,
                    "distribution": dist, "event_utc": quote["event_utc"], "kickoff_utc": fixture["kickoff_utc"],
                    "source": quote["source"], "receipt_before_kickoff": quote["receipt_before_kickoff"],
                    "line": line, "side": side, "price": price})

    markets_report = {}
    for market in MARKETS:
        markets_report[market] = {"quoted_fixture_markets": len(quotes_by_market := [k for k in quotes if k[1] == market]),
            "models": {}}
        for model_idx, (model_name, market_map) in enumerate(model_market_rows.items()):
            rows = market_map[market]
            summary = summarize_market_rows(rows, 20261106 + model_idx * 3 + (0 if market == "AH" else 1),
                                           include_bootstrap=True)
            by_year = defaultdict(list)
            by_source = defaultdict(list)
            for row in rows:
                by_year[row["kickoff_utc"][:4]].append(row)
                by_source[row["source"]].append(row)
            summary["by_utc_kickoff_year"] = {
                year: summarize_market_rows(group, 20261116 + model_idx * 17 + int(year) + (0 if market == "AH" else 1))
                for year, group in sorted(by_year.items())
            }
            summary["by_quote_source"] = {
                source: summarize_market_rows(group, 20261216 + model_idx * 17 + (0 if market == "AH" else 1))
                for source, group in sorted(by_source.items())
            }
            summary["unique_fixtures_with_complete_three_model_forecast_and_quote"] = summary["unique_fixtures"]
            markets_report[market]["models"][model_name] = summary

    # Confirm target sample and model predictions are one-to-one by fixture ID.
    quote_fixture_ids = {mid for mid, _ in quotes}
    report = {
        "protocol": "M3_PENALTYBLOG_THREE_MODEL_EXPANDED_M5_UTC_YEAR_OOS_V1",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "penaltyblog_version": version("penaltyblog"),
        "models": list(m3_models),
        "model_method": "Original penaltyblog PoissonGoalsModel, DixonColesGoalModel, and BivariatePoissonGoalModel; independent default fits; one 1U simulated side per quoted fixture-market, selected by higher expected return, with no threshold.",
        "data_source": "Private M5 historical candidate manifest; completed scores and UTC fixture identities only for fitting and test outcomes. Crown AH/OU source events are selected first; TotalCorner default is used only for a missing Crown fixture-market.",
        "candidate_manifest_sha256": sha(manifest_raw),
        "m5_forecast_identity_and_asof_sha256": forecast_sha256,
        "crown_index_sha256": sha((root / "crown-response-index.jsonl").read_bytes()),
        "totalcorner_default_index_sha256": sha((root / "totalcorner-default-index.jsonl").read_bytes()),
        "quote_response_hash_set_sha256": sha("\n".join(sorted(response_hashes)).encode()),
        "candidate_completed_fixtures": len(fixtures),
        "source_union_unique_fixture_markets": {m: len([k for k in quotes if k[1] == m]) for m in MARKETS},
        "source_union_unique_fixtures": len(quote_fixture_ids),
        "three_model_complete_oos_forecast_fixtures": len(forecast_rows),
        "three_model_quote_matched_fixture_markets": {m: sum(1 for mid, mk in quotes if mk == m and mid in forecast_by_id) for m in MARKETS},
        "target_utc_years": sorted({int(row["target_utc_year"]) for row in fold_receipts}),
        "league_count_in_candidate_manifest": len(by_league),
        "fold_count": len(fold_receipts),
        "fit_failures_by_model_and_type": dict(failures),
        "training_rule": "For each league and target UTC year, train on every completed fixture in the same league with kickoff strictly before January 1 UTC of that year; test only the target year. The target fixture ID is excluded from training. No target-year result enters fit parameters.",
        "time_order_passed": all(instant(x["train_end_utc"]) < instant(x["prediction_asof_utc"]) < instant(x["kickoff_utc"]) for x in forecast_rows),
        "unique_oos_fixture_ids_passed": len(forecast_by_id) == len(forecast_rows),
        "quote_event_timing": "Each selected source event timestamp is at or after the M5-archived forecast as-of and before kickoff. Provider response receipt is reported independently and is expected to be retrospective for this archive.",
        "markets": markets_report,
        "quote_selection_audit": {**dict(quote_audit), **dict(forecast_identity_errors)},
        "folds": fold_receipts,
        "private_forecast_sha256": None,
        "crown_roi_is_executable": False,
        "limitations": [
            "Historical source quote events may predate kickoff, but provider responses were retrieved after kickoff; ROI is retrospective event-time replay, not demonstrated executable performance.",
            "This broad-scope M5 re-evaluation applies the three M3 penaltyblog model implementations over the frozen 51-league M5 result universe; it does not replace M3's six-league production or research artifacts.",
            "The new M3 forecasts and quote-level rows remain in the private archive; public output is aggregate-only.",
        ],
    }
    # Private file carries all prediction grids and quote-linked records. It is
    # never written under the repository path.
    private_predictions = safe_private_output(private_predictions)
    private_records = []
    for fixture in forecast_rows:
        private_records.append({k: fixture[k] for k in fixture if k != "grids"} | {
            "model_score_grids": fixture["grids"],
            "quotes": {market: quotes[(fixture["match_id"], market)] for market in MARKETS
                       if (fixture["match_id"], market) in quotes},
        })
    encoded = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                      for row in private_records).encode()
    tmp = private_predictions.with_name(private_predictions.name + f".tmp-{os.getpid()}")
    tmp.write_bytes(encoded)
    os.chmod(tmp, 0o600)
    os.replace(tmp, private_predictions)
    report["private_forecast_sha256"] = sha(encoded)
    public_report.parent.mkdir(parents=True, exist_ok=True)
    public_report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--private-predictions", type=Path, required=True)
    parser.add_argument("--public-report", type=Path, required=True)
    parser.add_argument("--source-timezone", default="Asia/Shanghai")
    parser.add_argument("--years", default="", help="comma-separated UTC target years; defaults to archived forecast years")
    args = parser.parse_args()
    years = tuple(int(x) for x in args.years.split(",") if x.strip()) or None
    report = run(args.private_dir, args.private_predictions, args.public_report, args.source_timezone, years)
    print(json.dumps({"generated_utc": report["generated_utc"],
                      "source_union_unique_fixture_markets": report["source_union_unique_fixture_markets"],
                      "three_model_complete_oos_forecast_fixtures": report["three_model_complete_oos_forecast_fixtures"],
                      "three_model_quote_matched_fixture_markets": report["three_model_quote_matched_fixture_markets"],
                      "markets": report["markets"],
                      "fold_count": report["fold_count"],
                      "fit_failures_by_model_and_type": report["fit_failures_by_model_and_type"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
