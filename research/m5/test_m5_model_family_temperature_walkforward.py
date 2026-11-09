from research.m5.m5_model_family_temperature_walkforward import (
    evaluate, fit_temperature, reverse_distribution,
)


def test_reverse_distribution_maps_asian_outcomes():
    values = {"win": .4, "half_win": .1, "push": .2, "half_loss": .15, "loss": .15}
    assert reverse_distribution(values) == {
        "win": .15, "half_win": .15, "push": .2, "half_loss": .1, "loss": .4,
    }


def test_temperature_one_preserves_direction_and_full_holdout_count():
    rows = [{
        "fixture_id": "a", "side": "home", "category": "win",
        "distribution": {"win": .6, "half_win": 0, "push": 0, "half_loss": 0, "loss": .4},
        "prices": [1.9, 1.9], "line": 0.0, "quote_event_utc": "2026-01-01T00:00:00Z",
    }]
    metrics, pnl = evaluate(rows, "AH", 1.0)
    assert metrics["settled_bets"] == 1
    assert metrics["roi_pct"] == 90.0
    assert metrics["settlement_counts"]["win"] == 1
    assert pnl == [.8999999999999999]


def test_temperature_fit_returns_bounded_finite_value():
    rows = [{"distribution": {"win": .9, "half_win": 0, "push": 0,
                              "half_loss": 0, "loss": .1}, "category": "loss"} for _ in range(10)]
    temperature, at_bound = fit_temperature(rows)
    assert .25 <= temperature <= 4.0
    assert at_bound is True
