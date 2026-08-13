"""Deterministic uncertainty analysis for ThinkSmiths funding scenarios.

This module is for planning only. It does not claim supplier prices. It models
uncertainty in kit, guide, logistics and contingency inputs and reports a
distribution of deployable-kit capacity for a fixed cash ceiling.
"""
from dataclasses import dataclass, asdict
from math import floor
from random import Random


@dataclass(frozen=True)
class Range3:
    low: float
    mode: float
    high: float

    def validate(self, name: str) -> None:
        if self.low < 0 or not (self.low <= self.mode <= self.high):
            raise ValueError(f"invalid {name} triangular range")


@dataclass(frozen=True)
class UncertaintyScenario:
    cash_inr: float
    kit_cost: Range3
    guide_cost: Range3 = Range3(40, 50, 65)
    logistics_rate: Range3 = Range3(0.05, 0.08, 0.12)
    contingency_rate: Range3 = Range3(0.05, 0.07, 0.10)
    fixed_cost_inr: float = 0.0

    def validate(self) -> None:
        if self.cash_inr <= 0 or self.fixed_cost_inr < 0:
            raise ValueError("cash must be positive and fixed cost non-negative")
        self.kit_cost.validate("kit_cost")
        self.guide_cost.validate("guide_cost")
        self.logistics_rate.validate("logistics_rate")
        self.contingency_rate.validate("contingency_rate")
        if self.logistics_rate.high > 1 or self.contingency_rate.high > 1:
            raise ValueError("rates must be <= 1")


def _percentile(sorted_values, q):
    if not sorted_values:
        raise ValueError("empty values")
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def simulate_capacity(scenario: UncertaintyScenario, trials: int = 10000, seed: int = 42):
    scenario.validate()
    if trials < 100:
        raise ValueError("use at least 100 trials")
    rng = Random(seed)
    usable = max(0.0, scenario.cash_inr - scenario.fixed_cost_inr)
    capacities = []
    loaded_costs = []
    for _ in range(trials):
        kit = rng.triangular(scenario.kit_cost.low, scenario.kit_cost.high, scenario.kit_cost.mode)
        guide = rng.triangular(scenario.guide_cost.low, scenario.guide_cost.high, scenario.guide_cost.mode)
        logistics = rng.triangular(scenario.logistics_rate.low, scenario.logistics_rate.high, scenario.logistics_rate.mode)
        contingency = rng.triangular(scenario.contingency_rate.low, scenario.contingency_rate.high, scenario.contingency_rate.mode)
        loaded = (kit + guide) * (1 + logistics) * (1 + contingency)
        loaded_costs.append(loaded)
        capacities.append(floor(usable / loaded) if loaded > 0 else 0)
    capacities.sort()
    loaded_costs.sort()
    mean_capacity = sum(capacities) / len(capacities)
    return {
        "scenario": {
            "cash_inr": scenario.cash_inr,
            "kit_cost": asdict(scenario.kit_cost),
            "guide_cost": asdict(scenario.guide_cost),
            "logistics_rate": asdict(scenario.logistics_rate),
            "contingency_rate": asdict(scenario.contingency_rate),
            "fixed_cost_inr": scenario.fixed_cost_inr,
        },
        "trials": trials,
        "seed": seed,
        "capacity_mean": round(mean_capacity, 2),
        "capacity_p10": round(_percentile(capacities, 0.10), 1),
        "capacity_p50": round(_percentile(capacities, 0.50), 1),
        "capacity_p90": round(_percentile(capacities, 0.90), 1),
        "loaded_unit_cost_p10_inr": round(_percentile(loaded_costs, 0.10), 2),
        "loaded_unit_cost_p50_inr": round(_percentile(loaded_costs, 0.50), 2),
        "loaded_unit_cost_p90_inr": round(_percentile(loaded_costs, 0.90), 2),
    }


def minimum_cash_for_target(target_kits: int, scenario_template: UncertaintyScenario,
                            confidence: float = 0.90, trials: int = 5000,
                            seed: int = 42, tolerance_inr: float = 100.0):
    """Find cash such that the simulated lower-tail capacity meets target_kits.

    confidence=.90 means require the 10th percentile capacity to reach target.
    The result is a planning stress test, not a supplier quote.
    """
    if target_kits <= 0:
        raise ValueError("target_kits must be positive")
    if not 0.5 <= confidence < 1:
        raise ValueError("confidence must be in [0.5, 1)")
    q = 1 - confidence

    def lower_capacity(cash):
        s = UncertaintyScenario(
            cash, scenario_template.kit_cost, scenario_template.guide_cost,
            scenario_template.logistics_rate, scenario_template.contingency_rate,
            scenario_template.fixed_cost_inr)
        s.validate()
        rng = Random(seed)
        caps = []
        usable = max(0.0, cash - s.fixed_cost_inr)
        for _ in range(trials):
            kit = rng.triangular(s.kit_cost.low, s.kit_cost.high, s.kit_cost.mode)
            guide = rng.triangular(s.guide_cost.low, s.guide_cost.high, s.guide_cost.mode)
            logistics = rng.triangular(s.logistics_rate.low, s.logistics_rate.high, s.logistics_rate.mode)
            contingency = rng.triangular(s.contingency_rate.low, s.contingency_rate.high, s.contingency_rate.mode)
            loaded = (kit + guide) * (1 + logistics) * (1 + contingency)
            caps.append(floor(usable / loaded))
        caps.sort()
        return _percentile(caps, q)

    low = scenario_template.fixed_cost_inr
    high = max(1000.0, target_kits * max(1.0, scenario_template.kit_cost.high + scenario_template.guide_cost.high) * 2)
    while lower_capacity(high) < target_kits:
        high *= 2
    while high - low > tolerance_inr:
        mid = (low + high) / 2
        if lower_capacity(mid) >= target_kits:
            high = mid
        else:
            low = mid
    return {"target_kits": target_kits, "confidence": confidence,
            "minimum_cash_inr": round(high, 2), "tolerance_inr": tolerance_inr,
            "trials": trials, "seed": seed}


if __name__ == "__main__":
    import json
    base = UncertaintyScenario(100000, Range3(300, 400, 500))
    print(json.dumps(simulate_capacity(base), indent=2))
    print(json.dumps(minimum_cash_for_target(100, base), indent=2))
