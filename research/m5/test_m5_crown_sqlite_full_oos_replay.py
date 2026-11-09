from datetime import datetime, timezone

from research.m5.m5_crown_sqlite_full_oos_replay import (
    bootstrap_roi, local_event, parse_movement,
)


def test_local_event_converts_source_timezone_to_utc():
    value = local_event("2026-01-02 12:00:00", __import__("zoneinfo").ZoneInfo("Asia/Shanghai"))
    assert value == datetime(2026, 1, 2, 4, 0, tzinfo=timezone.utc)


def test_parse_movement_keeps_latest_post_asof_pregame_quote():
    book = {"asian_list": [
        [None, "0", 1.90, 1.90, "2026-01-02 11:00:00", 0, 0, 0],
        [None, "-0.25", 1.95, 1.91, "2026-01-02 12:30:00", 0, 0, 0],
        [None, "-0.5", 1.89, 1.97, "2026-01-02 13:00:00", 0, 0, 0],
        [None, "-0.5", 1.89, 1.97, "2026-01-02 13:30:00", 0, 0, 1],
        [None, "-0.5", 1.00, 1.97, "2026-01-02 13:40:00", 0, 0, 0],
    ]}
    rows = parse_movement(
        book, "AH", datetime(2026, 1, 2, 4, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 2, 6, 0, tzinfo=timezone.utc), "Asia/Shanghai")
    assert len(rows) == 1
    assert rows[0]["event"] == datetime(2026, 1, 2, 5, 0, tzinfo=timezone.utc)
    assert rows[0]["line"] == -0.5


def test_bootstrap_roi_is_seed_reproducible():
    values = [-1.0, 0.9, 0.95, -1.0, 0.9]
    first = bootstrap_roi(values, 123, repetitions=500)
    second = bootstrap_roi(values, 123, repetitions=500)
    assert first == second
    assert first["repetitions"] == 500
    assert first["lower_95_roi_pct"] <= first["upper_95_roi_pct"]
