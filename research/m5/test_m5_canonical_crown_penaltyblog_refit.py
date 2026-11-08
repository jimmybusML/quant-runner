from datetime import timezone

import pytest

from research.m5.m5_canonical_crown_penaltyblog_refit import (
    dt, league_average_grid, normalized_grid,
)


def test_utc_parser_requires_explicit_timezone():
    assert dt("2026-01-01T00:00:00Z").tzinfo == timezone.utc
    with pytest.raises(ValueError):
        dt("2026-01-01T00:00:00")


def test_unseen_team_fallback_is_normalized_and_uses_only_train_scores():
    train = [
        {"home_goals": 2, "away_goals": 0},
        {"home_goals": 0, "away_goals": 1},
        {"home_goals": 1, "away_goals": 1},
    ]
    grid = league_average_grid(train)
    assert len(grid) == len(grid[0]) == 15
    assert abs(sum(sum(row) for row in grid) - 1) < 1e-12
    assert all(value >= 0 for row in grid for value in row)


def test_normalized_grid_rejects_invalid_mass():
    class Prediction:
        grid = [[0.25, 0.25], [0.25, 0.2]]

    with pytest.raises(ValueError, match="mass"):
        normalized_grid(Prediction())
