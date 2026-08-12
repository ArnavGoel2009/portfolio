"""Funding allocation engine for ThinkSmiths.
All costs are planning inputs, not supplier quotes. The engine converts a cash budget
into conservative deployable-kit estimates and rejects unsupported inputs.
"""
from dataclasses import dataclass, asdict
from math import floor
from typing import Iterable

@dataclass(frozen=True)
class FundingPlan:
    cash_inr: float
    kit_unit_cost_inr: float
    guide_unit_cost_inr: float
    logistics_rate: float = 0.08
    contingency_rate: float = 0.07
    fixed_cost_inr: float = 0.0

    def calculate(self):
        vals = (self.cash_inr, self.kit_unit_cost_inr, self.guide_unit_cost_inr,
                self.fixed_cost_inr)
        if any(v < 0 for v in vals) or self.cash_inr <= 0:
            raise ValueError('cash must be positive and costs non-negative')
        if self.kit_unit_cost_inr + self.guide_unit_cost_inr <= 0:
            raise ValueError('per-student direct cost must be positive')
        if not 0 <= self.logistics_rate <= 1 or not 0 <= self.contingency_rate <= 1:
            raise ValueError('rates must be between 0 and 1')
        usable = self.cash_inr - self.fixed_cost_inr
        if usable <= 0:
            return {**asdict(self), 'deployable_kits': 0, 'total_used_inr': 0,
                    'unallocated_inr': round(self.cash_inr, 2), 'loaded_unit_cost_inr': None}
        direct = self.kit_unit_cost_inr + self.guide_unit_cost_inr
        loaded = direct * (1 + self.logistics_rate) * (1 + self.contingency_rate)
        kits = max(0, floor(usable / loaded))
        used = self.fixed_cost_inr + kits * loaded
        return {**asdict(self), 'deployable_kits': kits,
                'loaded_unit_cost_inr': round(loaded, 2),
                'total_used_inr': round(used, 2),
                'unallocated_inr': round(self.cash_inr - used, 2)}

def sensitivity(cash_levels: Iterable[float], unit_costs: Iterable[float], guide_cost=50):
    return [FundingPlan(c, u, guide_cost).calculate() for c in cash_levels for u in unit_costs]

if __name__ == '__main__':
    import json
    print(json.dumps(sensitivity((25000,50000,100000,250000),(300,400,500)), indent=2))
