import unittest

from funding_risk import estimate_funding_risk


class FundingRiskTests(unittest.TestCase):
    def test_seed_makes_output_reproducible(self):
        a = estimate_funding_risk(50000, 100, (300, 500), iterations=1000, seed=7)
        b = estimate_funding_risk(50000, 100, (300, 500), iterations=1000, seed=7)
        self.assertEqual(a, b)

    def test_fixed_cost_case_is_exact(self):
        r = estimate_funding_risk(
            50000,
            100,
            (400, 400),
            (50, 50),
            (0, 0),
            (0, 0),
            (0, 0),
            iterations=50,
        )
        self.assertEqual(r["median_total_inr"], 45000)
        self.assertEqual(r["probability_affordable"], 1.0)

    def test_insufficient_budget_is_zero_probability(self):
        r = estimate_funding_risk(
            10000,
            100,
            (400, 400),
            (50, 50),
            (0, 0),
            (0, 0),
            iterations=50,
        )
        self.assertEqual(r["probability_affordable"], 0.0)
        self.assertEqual(r["probability_over_budget"], 1.0)

    def test_more_cash_cannot_reduce_affordability_with_same_seed(self):
        low = estimate_funding_risk(40000, 100, (300, 500), iterations=1500, seed=13)
        high = estimate_funding_risk(60000, 100, (300, 500), iterations=1500, seed=13)
        self.assertGreaterEqual(high["probability_affordable"], low["probability_affordable"])

    def test_rejects_invalid_ranges(self):
        with self.assertRaises(ValueError):
            estimate_funding_risk(50000, 100, (500, 300))
        with self.assertRaises(ValueError):
            estimate_funding_risk(50000, 100, (300, 500), logistics_rate_range=(0, 1.1))

    def test_rejects_invalid_target_and_iterations(self):
        with self.assertRaises(ValueError):
            estimate_funding_risk(50000, 0, (300, 500))
        with self.assertRaises(ValueError):
            estimate_funding_risk(50000, 100, (300, 500), iterations=0)


if __name__ == "__main__":
    unittest.main()
