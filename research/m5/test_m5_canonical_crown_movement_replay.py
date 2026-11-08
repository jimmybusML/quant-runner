from datetime import datetime, timezone

from research.m5.m5_canonical_crown_movement_replay import (
    movement_quotes,
    summary_quotes,
)


def test_movement_quote_requires_strict_oos_event_window_and_valid_market_rows():
    asof = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    kickoff = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
    rows = [
        [None, "0.25", 1.91, 1.99, "2026-01-01 08:00:00", None, None, 0],  # exactly as-of
        [None, "0.25", 1.91, 1.99, "2026-01-01 10:30:00", None, None, 0],  # eligible
        [None, "0.25", 1.91, 1.99, "2026-01-01 11:00:00", None, None, 0],  # kickoff
        [2, "0.25", 1.91, 1.99, "2026-01-01 10:45:00", None, None, 0],
        [None, "0.25", 1.91, 1.99, "2026-01-01 10:45:00", None, None, 1],
        [None, "bad", 1.91, 1.99, "2026-01-01 10:45:00", None, None, 0],
    ]
    result = movement_quotes(rows, asof, kickoff, "Asia/Shanghai", "AH")
    assert len(result) == 1
    assert result[0]["line"] == 0.25
    assert result[0]["prices"] == (1.91, 1.99)
    assert result[0]["event"] == datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)


def test_ou_movement_uses_over_under_prices_and_normalizes_split_line():
    asof = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    kickoff = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
    rows = [[None, "2.5,3.0", 1.88, 2.02, "2026-01-01 10:30:00", None, None, 0]]
    result = movement_quotes(rows, asof, kickoff, "Asia/Shanghai", "OU")
    assert len(result) == 1
    assert result[0]["line"] == 2.75
    assert result[0]["prices"] == (1.88, 2.02)


def test_summary_quote_time_and_market_prices_are_strictly_pregame():
    asof = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    kickoff = datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc)
    book = {
        "goal": {
            "open": {"line": 2.5, "over": 1.90, "under": 1.98, "time": "2026-01-01 10:00:00"},
            "close": {"line": 2.75, "over": 1.88, "under": 2.02, "time": "2026-01-01 10:30:00"},
        }
    }
    result = summary_quotes(book, asof, kickoff, "Asia/Shanghai", "OU")
    assert len(result) == 2
    assert result[-1]["line"] == 2.75
    assert result[-1]["prices"] == (1.88, 2.02)
