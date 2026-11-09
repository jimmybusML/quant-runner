import json
from pathlib import Path

from research.m5.m5_model_family_totalcorner_only_comparison import summarize


def test_summary_uses_unique_bet_count_as_roi_denominator():
    rows = [
        {"pnl": 0.5, "category": "win", "distribution": {"win": 1.0, "half_win": 0.0,
         "push": 0.0, "half_loss": 0.0, "loss": 0.0}, "quote_event_utc": "2026-01-01T10:00:00Z",
         "kickoff_utc": "2026-01-01T11:00:00Z", "source": "TotalCorner_default",
         "receipt_pre_kickoff": False},
        {"pnl": -1.0, "category": "loss", "distribution": {"win": 0.0, "half_win": 0.0,
         "push": 0.0, "half_loss": 0.0, "loss": 1.0}, "quote_event_utc": "2026-01-02T10:00:00Z",
         "kickoff_utc": "2026-01-02T11:00:00Z", "source": "TotalCorner_default",
         "receipt_pre_kickoff": False},
    ]
    report = summarize(rows, "AH")
    assert report["unique_fixture_markets"] == report["simulated_bets"] == report["settled_bets"] == 2
    assert report["net_units"] == -0.5
    assert report["roi_pct"] == -25.0
    assert report["receipt_timing"] == {"post_kickoff": 2}
    assert sum(report["settlement_counts"].values()) == 2


def test_public_totalcorner_model_comparison_receipt_is_sanitized_and_arithmetic_holds():
    path = Path(__file__).with_name("results") / "m5_totalcorner_model_comparison_20261109.json"
    report = json.loads(path.read_text())
    assert report["protocol"] == "M5_MODEL_FAMILY_TOTALCORNER_ONLY_OOS_COMPARISON_V1"
    assert report["data"]["source"] == "TotalCorner_default only; Crown not included"
    for market, total in (("AH", 1141), ("OU", 1141)):
        assert report["data"]["unique_quoted_fixture_markets"][market] == total
        models = report["markets"][market]["models"]
        assert models["MR1_V6"]["simulated_bets"] == 0
        for name, result in models.items():
            count = result["simulated_bets"]
            assert sum(result["settlement_counts"].values()) == count
            assert result["settled_bets"] == count
            if count:
                assert result["quote_sources"] == {"TotalCorner_default": count}
                assert result["receipt_timing"] == {"post_kickoff": count}
                assert abs(result["roi_pct"] - 100 * result["net_units"] / count) < 1e-6
    serialized = json.dumps(report)
    for forbidden in ('"match_id"', '"fixture_id"', '"prices"', '"actual_home_goals"',
                      '"score_grid"', '"api_token"', '"api_key"', '"private_rows_path"',
                      '"/Users/mac/', '"/private/tmp/'):
        assert forbidden not in serialized
