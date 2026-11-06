from __future__ import annotations

import importlib.util
from pathlib import Path

from research.m5.m3_grid_crown_replay import legs_result as m3_legs_result, payout as m3_payout

SPEC = importlib.util.spec_from_file_location(
    "m5_m1_full_cohort_replay",
    Path(__file__).with_name("m5_m1_full_cohort_replay.py"),
)
M1_RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M1_RUNNER)


def test_m1_full_cohort_settlement_matches_m3_for_supported_contracts():
    lines = (-2.25, -1.5, -1.25, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0)
    for market, sides in (("AH", ("HOME", "AWAY")), ("OU", ("OVER", "UNDER"))):
        old_sides = tuple(side.lower() for side in sides)
        for line in lines:
            if market == "OU" and line < 0:
                continue
            for home in range(7):
                for away in range(7):
                    for side, old_side in zip(sides, old_sides):
                        actual_legs, actual_category = M1_RUNNER.legs_result(market, side, line, home, away)
                        expected_legs, expected_category = m3_legs_result(market, old_side, line, home, away)
                        assert actual_legs == expected_legs
                        assert actual_category == expected_category
                        assert M1_RUNNER.payout(actual_legs, 1.91) == m3_payout(expected_legs, 1.91)
