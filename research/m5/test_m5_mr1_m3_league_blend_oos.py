from collections import Counter

import numpy as np

from research.m5.m5_mr1_m3_league_blend_oos import bootstrap_difference, settle


def _row(fid, actual=(1, 0)):
    dist = np.array([0.5, 0.0, 0.0, 0.0, 0.5])
    probs = np.tile(dist, (5, 2, 1))
    return {
        "id": fid,
        "market": "AH",
        "year": "2026",
        "line": 0.0,
        "actual": actual,
        "actual_category_by_side": np.array([0, 4]),
        "prices": np.array([2.0, 2.0]),
        "probabilities": probs,
        "event_utc": "2026-01-01T12:00:00Z",
    }


def test_local_weight_fallback_keeps_all_fixture_markets():
    rows = [_row("one"), _row("two")]
    leagues = {"one": "League A", "two": "League B"}
    report = settle(rows, {"League A": np.full(5, 0.2)}, leagues, np.full(5, 0.2), "AH")
    assert report["unique_fixture_markets"] == 2
    assert report["simulated_bets"] == report["settled_bets"] == 2
    assert report["global_weight_fallback_fixtures"] == 1
    assert sum(report["settlement_counts"].values()) == 2
    assert set(report["per_league"]) == {"League A", "League B"}


def test_paired_bootstrap_is_reproducible_and_uses_local_minus_global():
    local = np.array([0.5, -1.0, 0.5, 0.5])
    global_ = np.array([-1.0, -1.0, -1.0, -1.0])
    result = bootstrap_difference(local, global_, 17, reps=500)
    assert result == bootstrap_difference(local, global_, 17, reps=500)
    assert result["mean_roi_difference_pct_local_minus_global"] == 112.5
    assert result["unit"] == "paired fixture-market bootstrap"
