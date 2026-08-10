"""Scenario planner for ThinkSmiths kit rollouts.
Planning only: inputs must be replaced with current supplier quotes before external use.
"""
from dataclasses import dataclass, asdict
import json

@dataclass
class Scenario:
    kits: int
    unit_cost_inr: float
    fixed_program_cost_inr: float = 0
    contingency_rate: float = 0.05

    def calculate(self):
        if self.kits <= 0 or self.unit_cost_inr < 0 or self.fixed_program_cost_inr < 0:
            raise ValueError("kits must be positive and costs non-negative")
        if not 0 <= self.contingency_rate <= 1:
            raise ValueError("contingency_rate must be between 0 and 1")
        variable = self.kits * self.unit_cost_inr
        subtotal = variable + self.fixed_program_cost_inr
        contingency = subtotal * self.contingency_rate
        return {
            **asdict(self),
            "variable_cost_inr": round(variable, 2),
            "subtotal_inr": round(subtotal, 2),
            "contingency_inr": round(contingency, 2),
            "total_program_cost_inr": round(subtotal + contingency, 2),
            "effective_cost_per_kit_inr": round((subtotal + contingency) / self.kits, 2),
        }

if __name__ == "__main__":
    scenarios = [Scenario(n, c) for c in (300, 400, 500) for n in (50, 100, 250, 500, 1000)]
    print(json.dumps([s.calculate() for s in scenarios], indent=2))
