import unittest

from research.m5.m5_penaltyblog_prior_year_selector import MODELS, select_model


class PriorYearPenaltyblogSelectorTests(unittest.TestCase):
    def test_selects_lowest_training_log_loss_per_market(self):
        scores = {"poisson": [0.9, 1.0], "dixon_coles": [1.1, 1.2],
                  "bivariate_poisson": [1.0, 1.0]}
        global_scores = {name: [1.0] for name in MODELS}

        self.assertEqual(select_model(scores, global_scores), "poisson")

    def test_uses_prior_global_model_when_league_has_no_training_rows(self):
        scores = {name: [] for name in MODELS}
        global_scores = {"poisson": [1.2], "dixon_coles": [1.1], "bivariate_poisson": [1.3]}

        self.assertEqual(select_model(scores, global_scores), "dixon_coles")


if __name__ == "__main__":
    unittest.main()
