import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research.m3 import openfootball_shadow as shadow


class FakeGrid:
    home_draw_away = (0.45, 0.30, 0.25)
    grid = [[0.4, 0.2], [0.2, 0.2]]

    def asian_handicap_probs(self, side, line):
        return {"win": 0.45, "push": 0.30, "lose": 0.25}

    def total_goals(self, side, line):
        return 0.52


class FakeModel:
    def __init__(self, home_goals, away_goals, home_teams, away_teams):
        self.teams = sorted(set(home_teams) | set(away_teams))

    def fit(self):
        return self

    def get_params(self):
        return {"home_advantage": 0.1}

    def predict(self, home, away):
        return FakeGrid()


class OpenFootballShadowTests(unittest.TestCase):
    def test_season_code_and_finished_zero_zero_score(self):
        self.assertEqual(shadow._season_code("2017-18"), "1718")
        self.assertEqual(shadow._season_code("2026-27"), "2627")
        self.assertEqual(shadow._finished_score({"score": {"ft": [0, 0]}}), (0, 0))
        self.assertIsNone(shadow._finished_score({"score": [0, 0]}))

    def test_source_parser_separates_finished_results_from_unscored_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "2017-18"
            folder.mkdir()
            payload = {"matches": [
                {"date": "2017-08-12", "round": "Matchday 1", "team1": "Alpha FC",
                 "team2": "Beta FC", "score": {"ft": [0, 0]}},
                {"date": "2017-08-19", "round": "Matchday 2", "team1": "Alpha FC",
                 "team2": "Beta FC"},
            ]}
            (folder / "en.1.json").write_text(json.dumps(payload))
            data, fixtures, files, coverage = shadow.read_openfootball(Path(tmp))
            self.assertEqual(len(data), 1)
            self.assertEqual(len(fixtures), 1)
            self.assertEqual((int(data.iloc[0].home_goals), int(data.iloc[0].away_goals)), (0, 0))
            self.assertEqual(coverage["E0"]["result_rows"], 1)
            self.assertEqual(coverage["E0"]["unscored_fixture_rows"], 1)
            self.assertEqual(coverage["B1"]["status"], "source_not_present")

    def test_shadow_is_no_market_idempotent_and_settles_separately(self):
        training = [{"league": "E0", "season": "2526", "match_date_utc": pd.Timestamp("2026-10-10", tz="UTC"),
                     "home_team": "Home", "away_team": "Away", "home_goals": 2, "away_goals": 1,
                     "fixture_identity_id": shadow._identity("E0", "2526", "Home", "Away"),
                     "actual_result_1x2": "H", "actual_ah_home_0": "win", "actual_ou_over_2_5": 1,
                     "source_file": "2025-26/en.1.json", "source_file_sha256": "abc"}]
        data = pd.DataFrame(training)
        base_fixture = {"league": "E0", "season": "2627", "source_date": "2026-10-23",
            "home_team": "Home", "away_team": "Away", "round": "Matchday 5",
            "fixture_identity_id": shadow._identity("E0", "2627", "Home", "Away"),
            "schedule_revision_id": "revision-1", "source_file": "2026-27/en.1.json", "source_row": 5}
        near_fixture = {**base_fixture, "source_date": "2026-10-22", "fixture_identity_id": "near-id",
                        "schedule_revision_id": "revision-near"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger.jsonl"
            output = root / "output"
            with patch.dict(shadow.MODELS, {"poisson": FakeModel}, clear=True):
                first = shadow.run_shadow(data, [base_fixture, near_fixture], [], {}, "commit-a",
                    datetime(2026, 10, 20, 12, tzinfo=timezone.utc), ledger, output, "test-1")
                # The unapproved three-day minimum lead gate was removed.
                # Both future source dates are eligible for research forecasts.
                self.assertEqual(first["eligible_future_fixture_identities"], 2)
                self.assertEqual(first["forecasts_appended"], 2)
                forecast = json.loads(ledger.read_text().splitlines()[0])
                self.assertEqual(forecast["market_data_status"], "NO_CROWN_QUOTE_CAPTURED")
                self.assertEqual(forecast["score_probability_grid"], FakeGrid.grid)
                self.assertEqual(forecast["score_probability_grid_semantics"],
                    "penaltyblog_normalized_rows_home_goals_columns_away_goals")
                self.assertIsNone(forecast["ev_per_unit"])
                self.assertIsNone(forecast["roi"])
                self.assertFalse(forecast["formal_order"])

                # Simulate the old release, which generated a second forecast
                # solely because the whole repository commit changed.
                legacy_duplicate = {**forecast, "forecast_id": "legacy-duplicate-id",
                    "forecast_key_id": None, "model_version_id": "legacy-commit-bound-version",
                    "quant_runner_commit": "docs-only-commit"}
                with ledger.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(legacy_duplicate) + "\n")

                second = shadow.run_shadow(data, [base_fixture, near_fixture], [], {}, "docs-only-commit",
                    datetime(2026, 10, 20, 16, tzinfo=timezone.utc), ledger, output, "test-2")
                self.assertEqual(second["forecasts_appended"], 0)
                self.assertEqual(second["superseded_forecasts_appended"], 1)
                self.assertEqual(second["unique_forecast_keys"], 2)

                settled_data = pd.concat([data, pd.DataFrame([{
                    **training[0], "season": "2627", "match_date_utc": pd.Timestamp("2026-10-23", tz="UTC"),
                    "fixture_identity_id": base_fixture["fixture_identity_id"],
                    "actual_result_1x2": "H", "actual_ah_home_0": "win", "actual_ou_over_2_5": 1,
                    "home_goals": 3, "away_goals": 1, "source_file": "2026-27/en.1.json",
                }])], ignore_index=True)
                third = shadow.run_shadow(settled_data, [], [], {}, "commit-b",
                    datetime(2026, 10, 25, 12, tzinfo=timezone.utc), ledger, output, "test-3")
                self.assertEqual(third["settlements_appended"], 1)
                self.assertIsNone(third["roi"])
                self.assertEqual(third["probability_metrics_by_model"]["poisson"]["n_settled"], 1)
                all_events = [json.loads(line) for line in ledger.read_text().splitlines()]
                self.assertEqual([e["event_type"] for e in all_events], ["FORECAST", "FORECAST",
                    "FORECAST", "FORECAST_DUPLICATE_SUPERSEDED", "SETTLEMENT"])
                self.assertFalse(all_events[-1]["formal_ledger_write"])


if __name__ == "__main__":
    unittest.main()
