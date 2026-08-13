import unittest
from uncertainty_engine import Range3, UncertaintyScenario, simulate_capacity, minimum_cash_for_target


class UncertaintyEngineTests(unittest.TestCase):
    def setUp(self):
        self.base = UncertaintyScenario(100000, Range3(300, 400, 500))

    def test_deterministic_seed(self):
        a = simulate_capacity(self.base, trials=1000, seed=7)
        b = simulate_capacity(self.base, trials=1000, seed=7)
        self.assertEqual(a, b)

    def test_percentiles_ordered(self):
        r = simulate_capacity(self.base, trials=1000, seed=42)
        self.assertLessEqual(r['capacity_p10'], r['capacity_p50'])
        self.assertLessEqual(r['capacity_p50'], r['capacity_p90'])
        self.assertLessEqual(r['loaded_unit_cost_p10_inr'], r['loaded_unit_cost_p50_inr'])
        self.assertLessEqual(r['loaded_unit_cost_p50_inr'], r['loaded_unit_cost_p90_inr'])

    def test_more_cash_increases_capacity(self):
        low = simulate_capacity(self.base, trials=1000, seed=42)
        high = simulate_capacity(UncertaintyScenario(200000, Range3(300,400,500)), trials=1000, seed=42)
        self.assertGreater(high['capacity_p10'], low['capacity_p10'])

    def test_invalid_triangular_range(self):
        with self.assertRaises(ValueError):
            simulate_capacity(UncertaintyScenario(100000, Range3(500,400,300)), trials=1000)

    def test_minimum_cash_hits_target(self):
        r = minimum_cash_for_target(100, self.base, confidence=.90, trials=1000, seed=42, tolerance_inr=100)
        self.assertGreater(r['minimum_cash_inr'], 0)
        stressed = UncertaintyScenario(r['minimum_cash_inr'], Range3(300,400,500))
        sim = simulate_capacity(stressed, trials=1000, seed=42)
        self.assertGreaterEqual(sim['capacity_p10'], 100)

    def test_trials_floor(self):
        with self.assertRaises(ValueError):
            simulate_capacity(self.base, trials=99)


if __name__ == '__main__':
    unittest.main()
