import unittest
from kit_planner import Scenario

class TestScenario(unittest.TestCase):
    def test_no_contingency(self):
        self.assertEqual(Scenario(100,300,0,0).calculate()["total_program_cost_inr"],30000)
    def test_fixed_and_contingency(self):
        self.assertEqual(Scenario(250,400,10000,.05).calculate()["total_program_cost_inr"],115500)
    def test_invalid(self):
        with self.assertRaises(ValueError): Scenario(0,400).calculate()

if __name__ == '__main__': unittest.main()
