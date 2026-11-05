"""OpenFootball walk-forward audit and no-market M3 prospective shadow ledger.

This workflow uses CC0 fixtures/results from openfootball/football.json. It does
not read odds, Crown, M1/M2/MR1 data, or any formal ledger. Source fixture times
are intentionally ignored because the dataset does not document their timezone.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
from importlib.metadata import version as package_version
import io
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from penaltyblog.models import (
    BivariatePoissonGoalModel,
    DixonColesGoalModel,
    PoissonGoalsModel,
)

from research.m3.penaltyblog_walkforward import build_predictions, score_rows


LEAGUE_FILES = {
    "E0": "en.1.json",
    "D1": "de.1.json",
    "SP1": "es.1.json",
    "I1": "it.1.json",
    "F1": "fr.1.json",
}
MODELS = {
    "poisson": PoissonGoalsModel,
    "dixon_coles": DixonColesGoalModel,
    "bivariate_poisson": BivariatePoissonGoalModel,
}
SUPPORTED_SEASON_START = 2017
DATE_GUARD_DAYS = 0
FORECAST_MODEL_SEMANTIC_VERSION = "penaltyblog-goal-distribution-v1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_json(value) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(body)


def _serialize_score_probability_grid(prediction) -> list[list[float]]:
    """Return penaltyblog's normalized score matrix in compact row-major form."""
    matrix = prediction.grid
    if hasattr(matrix, "tolist"):
        matrix = matrix.tolist()
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("penaltyblog prediction must expose a non-empty score grid")
    rows = []
    width = None
    for row in matrix:
        if hasattr(row, "tolist"):
            row = row.tolist()
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError("penaltyblog score grid rows must be non-empty arrays")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError("penaltyblog score grid must be rectangular")
        values = [float(value) for value in row]
        if any(not math.isfinite(value) or value < 0 or value > 1 for value in values):
            raise ValueError("penaltyblog score grid probabilities must be finite in [0, 1]")
        rows.append(values)
    mass = math.fsum(value for row in rows for value in row)
    if not math.isclose(mass, 1.0, rel_tol=0, abs_tol=1e-8):
        raise ValueError(f"penaltyblog normalized score grid must sum to one; got {mass}")
    return rows


def _evaluation_code_fingerprint() -> str:
    """Hash code that determines the OOS protocol, not unrelated repo commits."""
    paths = (Path(__file__), Path(__file__).with_name("penaltyblog_walkforward.py"))
    return _sha256_json([[path.name, _sha256_bytes(path.read_bytes())] for path in paths])


def _season_code(folder: str) -> str | None:
    try:
        start, end = folder.split("-", 1)
        start_year = int(start)
        end_value = int(end)
    except (ValueError, AttributeError):
        return None
    end_year = end_value if end_value >= 1000 else (start_year // 100) * 100 + end_value
    if end_year < start_year:
        end_year += 100
    if start_year < SUPPORTED_SEASON_START or end_year != start_year + 1:
        return None
    return f"{start_year % 100:02d}{end_year % 100:02d}"


def _finished_score(match: dict) -> tuple[int, int] | None:
    score = match.get("score")
    if not isinstance(score, dict):
        return None
    full_time = score.get("ft")
    if (not isinstance(full_time, list) or len(full_time) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in full_time)):
        return None
    return int(full_time[0]), int(full_time[1])


def _identity(league: str, season: str, home: str, away: str) -> str:
    return _sha256_json(["OPENFOOTBALL_FIXTURE_ID_V1", league, season, home, away])


def read_openfootball(root: Path):
    """Return full-time matches, unscored fixtures, and per-file provenance."""
    results: list[dict] = []
    fixtures: list[dict] = []
    files: list[dict] = []
    coverage = {league: {"files": 0, "result_rows": 0, "unscored_fixture_rows": 0,
                         "invalid_rows": 0, "status": "source_not_present"}
                for league in ("E0", "I1", "SP1", "D1", "F1", "B1")}

    season_dirs = sorted((p for p in root.iterdir() if p.is_dir() and _season_code(p.name)),
                         key=lambda p: _season_code(p.name) or "")
    for season_dir in season_dirs:
        season = _season_code(season_dir.name)
        for league, filename in LEAGUE_FILES.items():
            path = season_dir / filename
            if not path.is_file():
                continue
            raw = path.read_bytes()
            digest = _sha256_bytes(raw)
            try:
                payload = json.loads(raw)
                matches = payload.get("matches", [])
                if not isinstance(matches, list):
                    raise ValueError("matches must be an array")
            except Exception as exc:
                files.append({"file": f"{season_dir.name}/{filename}", "sha256": digest,
                              "status": "read_error", "error": str(exc)})
                continue
            files.append({"file": f"{season_dir.name}/{filename}", "sha256": digest,
                          "bytes": len(raw), "rows": len(matches), "status": "ok"})
            coverage[league]["files"] += 1
            coverage[league]["status"] = "available"
            for index, match in enumerate(matches):
                try:
                    source_date = date.fromisoformat(str(match["date"]))
                    home, away = str(match["team1"]).strip(), str(match["team2"]).strip()
                    round_name = str(match.get("round", ""))
                    if not home or not away or home == away:
                        raise ValueError("invalid team identity")
                    source_id = _identity(league, season, home, away)
                    source_file = f"{season_dir.name}/{filename}"
                    score = _finished_score(match)
                    common = {"league": league, "season": season, "source_date": source_date.isoformat(),
                              "home_team": home, "away_team": away, "round": round_name,
                              "fixture_identity_id": source_id, "source_file": source_file,
                              "source_row": index + 1}
                    if score is None:
                        fixtures.append({**common, "schedule_revision_id": _sha256_json(
                            [source_id, source_date.isoformat(), round_name])})
                        coverage[league]["unscored_fixture_rows"] += 1
                    else:
                        hg, ag = score
                        results.append({**common,
                            "fixture_identity_id": source_id,
                            "match_date_utc": pd.Timestamp(source_date.isoformat(), tz="UTC"),
                            "kickoff_date_utc": source_date.isoformat() + "T00:00:00Z",
                            "home_goals": hg, "away_goals": ag,
                            "actual_result_1x2": "H" if hg > ag else "A" if hg < ag else "D",
                            "actual_ah_home_0": "win" if hg > ag else "lose" if hg < ag else "push",
                            "actual_ou_over_2_5": int(hg + ag > 2.5),
                            "source_file": source_file,
                            "source_file_sha256": digest})
                        coverage[league]["result_rows"] += 1
                except Exception:
                    coverage[league]["invalid_rows"] += 1

    if results:
        frame = pd.DataFrame(results).sort_values(
            ["league", "match_date_utc", "season", "source_file", "source_row"], kind="stable")
        frame["source_file"] = frame["source_file"].astype("string")
        frame["kickoff_date_utc"] = frame["kickoff_date_utc"].astype("string")
    else:
        frame = pd.DataFrame(columns=["league", "season", "match_date_utc", "kickoff_date_utc",
                                     "home_team", "away_team", "home_goals", "away_goals", "source_file"])
    return frame, fixtures, files, coverage


def _results_fingerprint(data: pd.DataFrame) -> str:
    rows = [[r.league, r.season, r.match_date_utc.strftime("%Y-%m-%d"), r.home_team, r.away_team,
             int(r.home_goals), int(r.away_goals)] for r in data.itertuples(index=False)]
    return _sha256_json(rows)


def _fixtures_fingerprint(fixtures: list[dict]) -> str:
    rows = sorted([[f["fixture_identity_id"], f["source_date"], f["round"]] for f in fixtures])
    return _sha256_json(rows)


def evaluate_oos(data: pd.DataFrame, files: list[dict], source_commit: str,
                 output_dir: Path, quant_runner_commit: str = "unknown") -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    if data.empty:
        raise ValueError("OpenFootball dataset contains no completed matches from M3's supported period")
    predictions, splits, fitted = build_predictions(data)
    for row in predictions:
        row["source_match_date_calendar_key_utc"] = row.pop("kickoff_date_utc")
        row["source_match_date_semantics"] = "calendar_date_only_timezone_unspecified_not_kickoff_time"
    models = []
    for model in MODELS:
        rows = [r for r in predictions if r["model"] == model]
        seasons = []
        for season in sorted({r["season"] for r in rows}):
            season_rows = [r for r in rows if r["season"] == season]
            seasons.append({"test_season": season, "metrics": {
                league: {market: score_rows([r for r in season_rows if r["league"] == league], model, market)
                         for market in ("1x2", "ah_home_0", "ou_over_2_5")}
                for league in sorted({r["league"] for r in season_rows})}})
        models.append({"model": model, "overall_metrics": {
            market: score_rows(predictions, model, market)
            for market in ("1x2", "ah_home_0", "ou_over_2_5")},
            "by_test_season": seasons})
    fingerprint = _results_fingerprint(data)
    evaluation_code_fingerprint = _evaluation_code_fingerprint()
    evaluation_fingerprint = _sha256_json(["M3_OPENFOOTBALL_STRICT_WALKFORWARD_V1",
                                           fingerprint, evaluation_code_fingerprint])
    previous_path = output_dir / "latest_oos_report.json"
    previous_fingerprint = None
    previous_evaluation_fingerprint = None
    previous_generated_utc = None
    if previous_path.exists():
        previous_report = json.loads(previous_path.read_text())
        previous_fingerprint = previous_report.get("input_fingerprint_sha256")
        previous_evaluation_fingerprint = previous_report.get("evaluation_fingerprint_sha256")
        previous_generated_utc = previous_report.get("generated_utc")
    source_snapshot_fingerprint = _sha256_json([{"file": f["file"], "sha256": f["sha256"]}
                                                for f in files if f.get("status") == "ok"])
    prediction_path = output_dir / "latest_oos_predictions.csv"
    prediction_csv = pd.DataFrame(predictions).to_csv(index=False)
    prediction_path.write_text(prediction_csv)
    snapshot_dir = output_dir / "predictions"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    prediction_snapshot = snapshot_dir / f"{evaluation_fingerprint}.csv.gz"
    if not prediction_snapshot.exists():
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as compressed:
            compressed.write(prediction_csv.encode("utf-8"))
        prediction_snapshot.write_bytes(buffer.getvalue())
    split_dir = output_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    split_snapshot = split_dir / f"{evaluation_fingerprint}.json"
    if not split_snapshot.exists():
        split_snapshot.write_text(json.dumps(splits, indent=2, ensure_ascii=False) + "\n")
    split_path = output_dir / "latest_oos_splits.json"
    split_path.write_text(json.dumps(splits, indent=2, ensure_ascii=False) + "\n")
    report = {
        "protocol": "M3_OPENFOOTBALL_STRICT_WALKFORWARD_V1",
        "generated_utc": (previous_generated_utc if previous_evaluation_fingerprint == evaluation_fingerprint and previous_generated_utc
                          else datetime.now(timezone.utc).isoformat()),
        "data_source": "openfootball/football.json",
        "data_source_license": "CC0-1.0",
        "data_source_commit": source_commit,
        "data_source_url": "https://github.com/openfootball/football.json",
        "data_source_time_semantics": "source calendar dates normalized to UTC date keys; source kickoff times ignored and never treated as UTC",
        "quant_runner_commit": quant_runner_commit,
        "penaltyblog_version": package_version("penaltyblog"),
        "input_files": files,
        "input_fingerprint_sha256": fingerprint,
        "evaluation_fingerprint_sha256": evaluation_fingerprint,
        "evaluation_code_fingerprint_sha256": evaluation_code_fingerprint,
        "data_changed_vs_previous_snapshot": None if previous_fingerprint is None else fingerprint != previous_fingerprint,
        "source_file_snapshot_sha256": source_snapshot_fingerprint,
        "results_rows": int(len(data)),
        "test_matches_total": int(sum(s.get("test_rows", 0) for s in splits)),
        "scored_predictions": len(predictions),
        "prediction_file": str(prediction_snapshot),
        "prediction_file_sha256": _sha256_bytes(prediction_snapshot.read_bytes()),
        "latest_predictions_file": str(prediction_path),
        "latest_predictions_file_sha256": _sha256_bytes(prediction_path.read_bytes()),
        "splits_file": str(split_path),
        "splits_snapshot_file": str(split_snapshot),
        "coverage_by_league": {
            league: {"completed_matches": int(sum(r["league"] == league for r in data.to_dict("records"))),
                     "test_rows": int(sum(s.get("test_rows", 0) for s in splits if s.get("league") == league)),
                     "predicted_rows": int(sum(r["league"] == league and r["prediction_status"] == "predicted"
                                                for r in predictions))}
            for league in sorted({r["league"] for r in data.to_dict("records")})},
        "models": models,
        "train_test_isolation": "Each league-season tests only that season; training is earlier seasons and strictly before the first test calendar date.",
        "odds_used": False,
        "crown_roi": None,
        "telegram_sent": False,
    }
    parameter_bytes = (json.dumps(fitted, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    parameter_digest = _sha256_bytes(parameter_bytes)
    parameter_dir = output_dir / "model_parameters"
    parameter_dir.mkdir(parents=True, exist_ok=True)
    parameter_snapshot = parameter_dir / f"{parameter_digest}.json"
    if not parameter_snapshot.exists():
        parameter_snapshot.write_bytes(parameter_bytes)
    latest_parameters = output_dir / "latest_model_parameters.json"
    latest_parameters.write_bytes(parameter_bytes)
    report["model_parameters_file"] = str(parameter_snapshot)
    report["model_parameters_sha256"] = parameter_digest
    report["latest_model_parameters_file"] = str(latest_parameters)
    (output_dir / "latest_oos_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    history = output_dir / "history" / "oos" / evaluation_fingerprint
    history.mkdir(parents=True, exist_ok=True)
    if not (history / "summary.json").exists():
        (history / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def _read_ledger(path: Path):
    events = []
    if path.exists():
        for line_no, line in enumerate(path.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid ledger JSONL at {path}:{line_no}") from exc
    return events


def _append_once(path: Path, events: list[dict], new_event: dict, id_field: str) -> bool:
    if any(event.get(id_field) == new_event.get(id_field) for event in events):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(new_event, ensure_ascii=False, sort_keys=True) + "\n")
    events.append(new_event)
    return True


def _model_version(model_name: str, train: pd.DataFrame, params: dict,
                   quant_runner_commit: str, penaltyblog_version: str) -> tuple[str, str]:
    rows = [[r.league, r.season, r.match_date_utc.strftime("%Y-%m-%d"), r.home_team, r.away_team,
             int(r.home_goals), int(r.away_goals)] for r in train.itertuples(index=False)]
    input_hash = _sha256_json(rows)
    version_hash = _sha256_json(["M3_OPENFOOTBALL_MODEL_VERSION_V1", model_name, input_hash,
                                 params, FORECAST_MODEL_SEMANTIC_VERSION, penaltyblog_version])
    return input_hash, version_hash


def _forecast_key(fixture_identity_id: str, schedule_revision_id: str, model: str,
                  training_input_sha256: str, penaltyblog_version: str,
                  semantic_version: str = FORECAST_MODEL_SEMANTIC_VERSION) -> str:
    return _sha256_json(["M3_SHADOW_FORECAST_KEY_V1", fixture_identity_id,
                         schedule_revision_id, model, training_input_sha256,
                         semantic_version, penaltyblog_version])


def _forecast_key_from_event(event: dict) -> str:
    if event.get("forecast_key_id"):
        return str(event["forecast_key_id"])
    # Migrate pre-key records. Their only version difference was repository
    # commit identity, which is provenance and must not create a new forecast.
    return _forecast_key(event["fixture_identity_id"], event["schedule_revision_id"],
                         event["model"], event["training_input_sha256"],
                         event["penaltyblog_version"],
                         event.get("model_semantic_version", "penaltyblog-goal-distribution-v1"))


def _settlement_metrics(events: list[dict]) -> dict:
    latest = {}
    forecasts = {e["forecast_id"]: e for e in events if e.get("event_type") == "FORECAST"}
    for event in events:
        if event.get("event_type") == "SETTLEMENT":
            latest[event["forecast_id"]] = event
    result = {}
    for model in MODELS:
        matched = []
    superseded = {e.get("superseded_forecast_id") for e in events
                  if e.get("event_type") == "FORECAST_DUPLICATE_SUPERSEDED"}
    seen_keys = set()
    for forecast_id, settlement in latest.items():
        forecast = forecasts.get(forecast_id)
        if forecast and forecast_id not in superseded and forecast.get("model") == model:
            key = _forecast_key_from_event(forecast)
            if key not in seen_keys:
                matched.append((forecast, settlement))
                seen_keys.add(key)
        scored = [(f, s) for f, s in matched if f.get("forecast_status") == "PREDICTED_NO_MARKET"
                  and all(isinstance(f.get(key), (int, float)) for key in
                          ("p_home", "p_draw", "p_away", "ou_p_over_2_5"))]
        if not scored:
            result[model] = {"n_settled": len(matched), "n_probability_scored": 0,
                             "n_unscored_settlements": len(matched),
                             "ah0_log_loss": None, "ah0_brier": None,
                             "ou_over_2_5_log_loss": None, "ou_over_2_5_brier": None}
            continue
        eps = 1e-15
        ah_log, ah_brier, ou_log, ou_brier = [], [], [], []
        for f, s in scored:
            actual = {"H": 0, "D": 1, "A": 2}[s["actual_result_1x2"]]
            probs = [f["p_home"], f["p_draw"], f["p_away"]]
            ah_log.append(-math.log(max(eps, probs[actual])))
            ah_brier.append(sum((probs[i] - int(i == actual)) ** 2 for i in range(3)))
            p = min(1 - eps, max(eps, f["ou_p_over_2_5"]))
            y = int(s["actual_ou_over_2_5"])
            ou_log.append(-(y * math.log(p) + (1-y) * math.log(1-p)))
            ou_brier.append((f["ou_p_over_2_5"] - y) ** 2)
        result[model] = {"n_settled": len(matched), "n_probability_scored": len(scored),
                         "n_unscored_settlements": len(matched) - len(scored),
                         "ah0_log_loss": sum(ah_log) / len(ah_log),
                         "ah0_brier": sum(ah_brier) / len(ah_brier),
                         "ou_over_2_5_log_loss": sum(ou_log) / len(ou_log),
                         "ou_over_2_5_brier": sum(ou_brier) / len(ou_brier)}
    return result


def run_shadow(data: pd.DataFrame, fixtures: list[dict], files: list[dict], coverage: dict,
               source_commit: str, as_of_utc: datetime, ledger_path: Path,
               output_dir: Path, run_id: str = "local",
               quant_runner_commit: str = "unknown") -> dict:
    if as_of_utc.tzinfo is None or as_of_utc.utcoffset() != timedelta(0):
        raise ValueError("as_of_utc must be timezone-aware UTC")
    as_of_utc = as_of_utc.astimezone(timezone.utc)
    cutoff = pd.Timestamp(as_of_utc.date().isoformat(), tz="UTC")
    train_data = data.loc[data.match_date_utc.lt(cutoff)].copy()
    result_hash = _results_fingerprint(data)
    fixture_hash = _fixtures_fingerprint(fixtures)
    snapshot_hash = _sha256_json([{"file": f["file"], "sha256": f["sha256"]}
                                  for f in files if f.get("status") == "ok"])
    prior_meta_path = output_dir / "latest_shadow_run.json"
    previous_result_fingerprint = None
    previous_fixture_fingerprint = None
    if prior_meta_path.exists():
        prior_meta = json.loads(prior_meta_path.read_text())
        previous_result_fingerprint = prior_meta.get("results_fingerprint_sha256")
        previous_fixture_fingerprint = prior_meta.get("fixture_fingerprint_sha256")
    events = _read_ledger(ledger_path)
    # Append explicit correction events for duplicate legacy forecasts, preserving
    # the append-only audit trail while selecting one canonical sample per key.
    existing_forecasts = [e for e in events if e.get("event_type") == "FORECAST"]
    superseded_ids = {e.get("superseded_forecast_id") for e in events
                      if e.get("event_type") == "FORECAST_DUPLICATE_SUPERSEDED"}
    canonical_by_key = {}
    duplicate_corrections = 0
    for event in existing_forecasts:
        key = _forecast_key_from_event(event)
        canonical = canonical_by_key.setdefault(key, event)
        if event is canonical or event.get("forecast_id") in superseded_ids:
            continue
        correction = {"event_type": "FORECAST_DUPLICATE_SUPERSEDED",
            "supersession_id": _sha256_json(["M3_SHADOW_DUPLICATE_SUPERSEDED_V1",
                                               event.get("forecast_id"), canonical.get("forecast_id")]),
            "superseded_forecast_id": event.get("forecast_id"),
            "canonical_forecast_id": canonical.get("forecast_id"),
            "forecast_key_id": key,
            "reason": "same fixture schedule, model, training data, semantic model version, and library; repository commit alone differed",
            "formal_order": False}
        if _append_once(ledger_path, events, correction, "supersession_id"):
            duplicate_corrections += 1
            superseded_ids.add(event.get("forecast_id"))
    forecast_keys = {_forecast_key_from_event(e) for e in existing_forecasts
                     if e.get("forecast_id") not in superseded_ids}
    model_records = []
    eligible_fixtures = [f for f in fixtures if date.fromisoformat(f["source_date"]) >=
                         (as_of_utc.date() + timedelta(days=DATE_GUARD_DAYS))]
    forecasts_added = 0
    per_league = {}
    penaltyblog_version = package_version("penaltyblog")
    for league in sorted(LEAGUE_FILES):
        league_train = train_data.loc[train_data.league.eq(league)].copy()
        known_fixtures = [f for f in eligible_fixtures if f["league"] == league]
        per_league[league] = {"training_rows": len(league_train),
                              "scheduled_fixtures_seen": sum(f["league"] == league for f in fixtures),
                              "future_date_guard_eligible": len(known_fixtures),
                              "forecasts_added": 0, "unseen_team_fixtures": 0}
        if league_train.empty:
            continue
        for model_name, model_cls in MODELS.items():
            model = model_cls(league_train.home_goals, league_train.away_goals,
                              league_train.home_team, league_train.away_team)
            model.fit()
            params = {str(k): float(v) for k, v in model.get_params().items()}
            train_hash, model_version = _model_version(model_name, league_train, params,
                                                       quant_runner_commit, penaltyblog_version)
            record = {"league": league, "model": model_name, "model_version_id": model_version,
                      "quant_runner_commit": quant_runner_commit,
                      "penaltyblog_version": penaltyblog_version,
                      "training_input_sha256": train_hash, "training_rows": len(league_train),
                      "train_start_calendar_date": league_train.match_date_utc.min().strftime("%Y-%m-%d"),
                      "train_end_calendar_date": league_train.match_date_utc.max().strftime("%Y-%m-%d"),
                      "parameters": params}
            model_records.append(record)
            known_teams = set(str(t) for t in model.teams)
            for fixture in known_fixtures:
                forecast_key_id = _forecast_key(fixture["fixture_identity_id"],
                    fixture["schedule_revision_id"], model_name, train_hash, penaltyblog_version)
                if forecast_key_id in forecast_keys:
                    continue
                forecast_id = forecast_key_id
                base = {"event_type": "FORECAST", "forecast_id": forecast_id,
                    "forecast_key_id": forecast_key_id,
                    "model_semantic_version": FORECAST_MODEL_SEMANTIC_VERSION,
                    "fixture_identity_id": fixture["fixture_identity_id"], "league": league,
                    "season": fixture["season"], "round": fixture["round"],
                    "source_fixture_date": fixture["source_date"],
                    "source_date_semantics": "calendar_date_only_timezone_unspecified",
                    "schedule_revision_id": fixture["schedule_revision_id"],
                    "home_team": fixture["home_team"], "away_team": fixture["away_team"],
                    "forecasted_at_utc": as_of_utc.isoformat().replace("+00:00", "Z"),
                    "date_guard_min_days": DATE_GUARD_DAYS,
                    "data_source": "openfootball/football.json",
                    "data_source_commit": source_commit,
                    "data_fingerprint_sha256": result_hash,
                    "model": model_name, "model_version_id": model_version,
                    "quant_runner_commit": quant_runner_commit,
                    "penaltyblog_version": penaltyblog_version,
                    "training_input_sha256": train_hash, "train_rows": len(league_train),
                    "train_end_calendar_date": league_train.match_date_utc.max().strftime("%Y-%m-%d"),
                    "market_data_status": "NO_CROWN_QUOTE_CAPTURED",
                    "crown_snapshot_id": None, "ev_per_unit": None, "roi": None,
                    "formal_order": False, "telegram_sent": False}
                if fixture["home_team"] not in known_teams or fixture["away_team"] not in known_teams:
                    base["forecast_status"] = "UNSEEN_TRAINING_TEAM"
                    base.update({"p_home": None, "p_draw": None, "p_away": None,
                                 "ah_home_0_p_win": None, "ah_home_0_p_push": None,
                                 "ah_home_0_p_lose": None, "ou_p_over_2_5": None})
                    per_league[league]["unseen_team_fixtures"] += 1
                else:
                    grid = model.predict(fixture["home_team"], fixture["away_team"])
                    p_h, p_d, p_a = [float(x) for x in grid.home_draw_away]
                    ah = grid.asian_handicap_probs("home", 0.0)
                    base["forecast_status"] = "PREDICTED_NO_MARKET"
                    base.update({"p_home": p_h, "p_draw": p_d, "p_away": p_a,
                                 "ah_home_0_p_win": float(ah["win"]),
                                 "ah_home_0_p_push": float(ah["push"]),
                                 "ah_home_0_p_lose": float(ah["lose"]),
                                 "ou_p_over_2_5": float(grid.total_goals("over", 2.5)),
                                 "score_probability_grid": _serialize_score_probability_grid(grid),
                                 "score_probability_grid_semantics":
                                     "penaltyblog_normalized_rows_home_goals_columns_away_goals"})
                base["source_file"] = fixture["source_file"]
                base["source_row"] = fixture["source_row"]
                if _append_once(ledger_path, events, base, "forecast_id"):
                    forecasts_added += 1
                    per_league[league]["forecasts_added"] += 1
                    forecast_keys.add(forecast_key_id)
    # Results are joined only after a full-time score is present in the current source snapshot.
    completed = {}
    for row in data.to_dict("records"):
        completed[row["fixture_identity_id"]] = row
    settlement_ids = {e.get("settlement_id") for e in events if e.get("event_type") == "SETTLEMENT"}
    settlements_added = 0
    forecasts = []
    seen_forecast_keys = set()
    for event in events:
        if event.get("event_type") != "FORECAST" or event.get("forecast_id") in superseded_ids:
            continue
        key = _forecast_key_from_event(event)
        if key not in seen_forecast_keys:
            forecasts.append(event)
            seen_forecast_keys.add(key)
    for forecast in forecasts:
        row = completed.get(forecast["fixture_identity_id"])
        if row is None:
            continue
        # Do not settle anything until the observed result calendar date is after
        # the stored source fixture date; this guards against a malformed source row.
        if row["match_date_utc"].strftime("%Y-%m-%d") < forecast["source_fixture_date"]:
            continue
        score_hash = _sha256_json([int(row["home_goals"]), int(row["away_goals"])])
        settlement_id = _sha256_json(["M3_SHADOW_SETTLEMENT_V1", forecast["forecast_id"], score_hash])
        if settlement_id in settlement_ids:
            continue
        settlement = {"event_type": "SETTLEMENT", "settlement_id": settlement_id,
            "forecast_id": forecast["forecast_id"], "fixture_identity_id": forecast["fixture_identity_id"],
            "settled_at_utc": as_of_utc.isoformat().replace("+00:00", "Z"),
            "actual_home_goals": int(row["home_goals"]), "actual_away_goals": int(row["away_goals"]),
            "actual_result_1x2": row["actual_result_1x2"],
            "actual_ah_home_0": row["actual_ah_home_0"],
            "actual_ou_over_2_5": int(row["actual_ou_over_2_5"]),
            "result_source": "openfootball/football.json",
            "result_source_commit": source_commit,
            "result_source_file": row["source_file"],
            "result_source_file_sha256": row["source_file_sha256"],
            "crown_roi": None, "formal_ledger_write": False}
        if _append_once(ledger_path, events, settlement, "settlement_id"):
            settlements_added += 1
            settlement_ids.add(settlement_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    parameter_path = output_dir / "latest_shadow_model_parameters.json"
    parameter_path.write_text(json.dumps(model_records, indent=2, ensure_ascii=False) + "\n")
    param_digest = _sha256_bytes(parameter_path.read_bytes())
    parameter_snapshots = output_dir / "model_parameters"
    parameter_snapshots.mkdir(parents=True, exist_ok=True)
    parameter_snapshot_path = parameter_snapshots / f"{param_digest}.json"
    if not parameter_snapshot_path.exists():
        parameter_snapshot_path.write_bytes(parameter_path.read_bytes())
    meta = {
        "protocol": "M3_OPENFOOTBALL_SHADOW_RUN_V1",
        "run_id": run_id,
        "generated_utc": as_of_utc.isoformat().replace("+00:00", "Z"),
        "data_source": "openfootball/football.json",
        "data_source_license": "CC0-1.0",
        "data_source_commit": source_commit,
        "quant_runner_commit": quant_runner_commit,
        "penaltyblog_version": penaltyblog_version,
        "input_fingerprint_sha256": result_hash,
        "results_fingerprint_sha256": result_hash,
        "fixture_fingerprint_sha256": fixture_hash,
        "source_file_snapshot_sha256": snapshot_hash,
        "data_changed_vs_previous_snapshot": None if previous_result_fingerprint is None else result_hash != previous_result_fingerprint,
        "fixture_schedule_changed_vs_previous_snapshot": None if previous_fixture_fingerprint is None else fixture_hash != previous_fixture_fingerprint,
        "training_cutoff_rule": "exclude all source calendar dates on or after current UTC date",
        "fixture_rule": "no minimum advance-day gate; source calendar date alone does not prove unstarted status",
        "fixture_time_semantics": "no source timezone assumption and no kickoff UTC inferred",
        "scope": ["E0", "D1", "SP1", "I1", "F1", "B1"],
        "source_coverage": coverage,
        "unsupported_schedule_leagues": ["B1"],
        "eligible_future_fixture_identities": len(eligible_fixtures),
        "forecasts_appended": forecasts_added,
        "superseded_forecasts_appended": duplicate_corrections,
        "settlements_appended": settlements_added,
        "total_forecast_events": sum(e.get("event_type") == "FORECAST" for e in events),
        "unique_forecast_keys": len({_forecast_key_from_event(e) for e in events
                                      if e.get("event_type") == "FORECAST" and
                                      e.get("forecast_id") not in superseded_ids}),
        "superseded_forecast_events": len(superseded_ids),
        "total_settlement_events": sum(e.get("event_type") == "SETTLEMENT" for e in events),
        "probability_metrics_by_model": _settlement_metrics(events),
        "crown_quote_captured": False,
        "ev_available": False,
        "roi": None,
        "maximum_drawdown": None,
        "formal_order_count": 0,
        "telegram_sent": False,
        "ledger_path": str(ledger_path),
        "ledger_sha256": _sha256_bytes(ledger_path.read_bytes()) if ledger_path.exists() else None,
        "model_parameters_path": str(parameter_path),
        "model_parameters_sha256": param_digest,
        "model_parameters_snapshot_path": str(parameter_snapshot_path),
        "model_versions": [{"league": r["league"], "model": r["model"],
                             "model_version_id": r["model_version_id"],
                             "training_input_sha256": r["training_input_sha256"],
                             "training_rows": r["training_rows"]} for r in model_records],
        "per_league": per_league,
    }
    (output_dir / "latest_shadow_run.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    history = output_dir / "history" / "shadow-runs" / f"{run_id}.json"
    research_state_changed = (
        meta["data_changed_vs_previous_snapshot"] is not False
        or meta["fixture_schedule_changed_vs_previous_snapshot"] is not False
        or forecasts_added > 0
        or duplicate_corrections > 0
        or settlements_added > 0
    )
    if research_state_changed:
        history.parent.mkdir(parents=True, exist_ok=True)
        history.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("research/m3/results/openfootball"))
    parser.add_argument("--ledger", type=Path, default=Path("research/m3/results/openfootball/shadow_ledger.jsonl"))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--quant-runner-commit", default="unknown")
    parser.add_argument("--run-id", default="local")
    parser.add_argument("--as-of-utc")
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of_utc.replace("Z", "+00:00")) if args.as_of_utc else datetime.now(timezone.utc)
    data, fixtures, files, coverage = read_openfootball(args.input_root)
    oos = evaluate_oos(data, files, args.source_commit, args.output_dir, args.quant_runner_commit)
    shadow = run_shadow(data, fixtures, files, coverage, args.source_commit, as_of,
                        args.ledger, args.output_dir, args.run_id, args.quant_runner_commit)
    print(json.dumps({"oos_input_fingerprint_sha256": oos["input_fingerprint_sha256"],
                      "oos_test_matches": oos["test_matches_total"],
                      "shadow": shadow}, ensure_ascii=False))


if __name__ == "__main__":
    main()
