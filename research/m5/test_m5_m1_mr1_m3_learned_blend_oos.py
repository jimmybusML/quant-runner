import math

import numpy as np

from research.m5.m5_m1_mr1_m3_learned_blend_oos import (
    CATEGORIES,
    expected_returns,
    invert_distribution,
    normalize,
    score_weights,
)


def test_opposite_asian_side_distribution_is_involution():
    probabilities = normalize([0.31, 0.12, 0.08, 0.19, 0.30])
    opposite = invert_distribution(probabilities)
    assert np.allclose(opposite, [0.30, 0.19, 0.08, 0.12, 0.31])
    assert np.allclose(invert_distribution(opposite), probabilities)


def test_expected_return_uses_all_asian_settlement_states():
    distribution = np.asarray([[[0.2, 0.1, 0.1, 0.2, 0.4]]])
    actual = expected_returns(distribution, np.asarray([[2.0]]))
    assert np.allclose(actual, [[0.2 + 0.05 - 0.4 - 0.1]])


def test_scoring_uses_the_selected_side_distribution_and_outcome():
    probabilities = np.full((1, 5, 2, len(CATEGORIES)), 0.2)
    probabilities[:, :, 0, :] = [0.6, 0.1, 0.1, 0.1, 0.1]
    probabilities[:, :, 1, :] = [0.1, 0.1, 0.1, 0.1, 0.6]
    prices = np.asarray([[2.0, 2.0]])
    actual = np.asarray([[0, 4]])
    loss, chosen, distribution, categories = score_weights(
        np.full(5, 0.2), probabilities, prices, actual
    )
    assert chosen.tolist() == [0]
    assert categories.tolist() == [0]
    assert np.allclose(distribution[0], probabilities[0, 0, 0])
    assert math.isclose(loss, -math.log(0.6))
