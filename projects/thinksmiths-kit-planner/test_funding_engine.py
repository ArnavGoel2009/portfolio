import unittest
from funding_engine import FundingPlan, sensitivity

class FundingEngineTests(unittest.TestCase):
    def test_known_budget(self):
        r=FundingPlan(50000,400,50,0,0).calculate()
        self.assertEqual(r['deployable_kits'],111)
        self.assertEqual(r['unallocated_inr'],50)
    def test_rates_reduce_capacity(self):
        plain=FundingPlan(100000,400,50,0,0).calculate()['deployable_kits']
        loaded=FundingPlan(100000,400,50,.08,.07).calculate()['deployable_kits']
        self.assertLess(loaded,plain)
    def test_fixed_cost(self):
        r=FundingPlan(1000,400,50,0,0,1000).calculate()
        self.assertEqual(r['deployable_kits'],0)
    def test_invalid_cash(self):
        with self.assertRaises(ValueError): FundingPlan(0,400,50).calculate()
    def test_invalid_rate(self):
        with self.assertRaises(ValueError): FundingPlan(1000,400,50,1.1,0).calculate()
    def test_sensitivity_shape(self):
        self.assertEqual(len(sensitivity([1000,2000],[300,400])),4)

if __name__=='__main__': unittest.main()
