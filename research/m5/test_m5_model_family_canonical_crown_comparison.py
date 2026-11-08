from research.m5.m5_model_family_canonical_crown_comparison import (
    CAT, category_return, canonical_probs, opposite,
)


def test_opposite_asian_settlement_distribution_is_complement():
    home = {"win": .3, "half_win": .2, "push": .1, "half_loss": .15, "loss": .25}
    away = opposite(home)
    assert away == {"win": .25, "half_win": .15, "push": .1, "half_loss": .2, "loss": .3}
    assert sum(away.values()) == 1


def test_mr1_distribution_normalizes_to_common_category_names():
    d = canonical_probs({"full_win": .4, "half_win": .1, "push": .1,
                         "half_loss": .1, "full_loss": .3}, "MR1")
    assert tuple(d) == CAT
    assert d["win"] == .4 and d["loss"] == .3


def test_expected_return_uses_quarter_line_settlement_mass():
    d = {"win": .2, "half_win": .3, "push": .1, "half_loss": .2, "loss": .2}
    # At decimal 2.0, full win=+1, half win=+0.5, half loss=-0.5.
    assert category_return(d, 2.0) == .2 + .15 - .1 - .2
