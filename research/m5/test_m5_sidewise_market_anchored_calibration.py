from research.m5.m5_sidewise_market_anchored_calibration import (
    CATEGORIES, fit_softmax, make_features, paired_roi_difference_bootstrap,
    predict_softmax, reverse_distribution, two_sided_rows,
)


def test_reverse_distribution_is_an_involution():
    dist = {"win": .31, "half_win": .12, "push": .08, "half_loss": .17, "loss": .32}
    assert reverse_distribution(reverse_distribution(dist)) == dist


def test_two_sided_rows_reverses_actual_and_uses_each_price():
    row = {"fixture_id": "f1", "market": "AH", "side": "home", "line": .25,
           "prices": [1.91, 1.99], "distribution": {"win": .4, "half_win": .1,
           "push": .1, "half_loss": .1, "loss": .3}, "category": "half_win",
           "kickoff_utc": "2026-01-01T12:00:00Z"}
    sides = two_sided_rows([row], "AH")
    assert len(sides) == 2
    assert sides[0]["category"] == "half_win" and sides[0]["price"] == 1.91
    assert sides[1]["category"] == "half_loss" and sides[1]["price"] == 1.99


def test_multinomial_fit_outputs_finite_five_class_probabilities():
    x = []
    y = []
    for i in range(50):
        row = {"win": .6, "half_win": .1, "push": .1, "half_loss": .1, "loss": .1}
        x.append(make_features(row, 1.9 + i / 1000, 2.0, .25))
        y.append(CATEGORIES[i % len(CATEGORIES)])
    params = fit_softmax(__import__("numpy").asarray(x), y, .1)
    p = predict_softmax(params, __import__("numpy").asarray(x[:3]))
    assert p.shape == (3, 5)
    assert __import__("numpy").isfinite(p).all()
    assert __import__("numpy").allclose(p.sum(axis=1), 1.0)


def test_paired_bootstrap_requires_equal_fixture_rows():
    result = paired_roi_difference_bootstrap([.1, -.2, .3], [.0, -.1, .1], 7)
    assert result["repetitions"] == 10000
    assert result["lower_95_difference_pp"] <= result["upper_95_difference_pp"]
