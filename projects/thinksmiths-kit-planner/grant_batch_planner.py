from __future__ import annotations
from dataclasses import dataclass
import math
import random
from typing import Iterable, Sequence

@dataclass(frozen=True)
class CostScenario:
    kit_cost_inr: float
    guide_cost_inr: float
    logistics_rate: float
    contingency_rate: float
    fixed_cost_inr: float = 0.0

    def validate(self) -> None:
        if self.kit_cost_inr < 0 or self.guide_cost_inr < 0 or self.fixed_cost_inr < 0:
            raise ValueError("costs must be non-negative")
        if not 0 <= self.logistics_rate <= 1:
            raise ValueError("logistics_rate must be in [0,1]")
        if not 0 <= self.contingency_rate <= 1:
            raise ValueError("contingency_rate must be in [0,1]")

    def total_cost(self, kits: int) -> float:
        if not isinstance(kits, int) or kits <= 0:
            raise ValueError("kits must be a positive integer")
        self.validate()
        direct = self.kit_cost_inr + self.guide_cost_inr
        return self.fixed_cost_inr + kits * direct * (1 + self.logistics_rate) * (1 + self.contingency_rate)

def generate_scenarios(*, iterations: int, seed: int, kit_cost_range: tuple[float, float], guide_cost_range: tuple[float, float], logistics_rate_range: tuple[float, float], contingency_rate_range: tuple[float, float], fixed_cost_range: tuple[float, float] = (0.0, 0.0)) -> list[CostScenario]:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    ranges = {"kit_cost_range": kit_cost_range, "guide_cost_range": guide_cost_range, "logistics_rate_range": logistics_rate_range, "contingency_rate_range": contingency_rate_range, "fixed_cost_range": fixed_cost_range}
    for name, pair in ranges.items():
        if len(pair) != 2 or pair[0] < 0 or pair[1] < pair[0]:
            raise ValueError(f"{name} must be ordered and non-negative")
    if logistics_rate_range[1] > 1 or contingency_rate_range[1] > 1:
        raise ValueError("rate ranges must not exceed 1")
    rng = random.Random(seed)
    return [CostScenario(rng.uniform(*kit_cost_range), rng.uniform(*guide_cost_range), rng.uniform(*logistics_rate_range), rng.uniform(*contingency_rate_range), rng.uniform(*fixed_cost_range)) for _ in range(iterations)]

def affordability_probability(cash_inr: float, kits: int, scenarios: Sequence[CostScenario]) -> float:
    if cash_inr <= 0:
        raise ValueError("cash_inr must be positive")
    if not scenarios:
        raise ValueError("at least one scenario is required")
    return sum(s.total_cost(kits) <= cash_inr for s in scenarios) / len(scenarios)

def robust_batch_recommendation(cash_inr: float, candidate_batches: Iterable[int], scenarios: Sequence[CostScenario], *, min_confidence: float = 0.90) -> dict:
    if not 0 < min_confidence <= 1:
        raise ValueError("min_confidence must be in (0,1]")
    batches = sorted(set(candidate_batches))
    if not batches or any((not isinstance(b, int) or b <= 0) for b in batches):
        raise ValueError("candidate_batches must contain positive integers")
    probs = {b: affordability_probability(cash_inr, b, scenarios) for b in batches}
    feasible = [b for b in batches if probs[b] >= min_confidence]
    chosen = max(feasible) if feasible else 0
    return {"cash_inr": round(cash_inr, 2), "min_confidence": min_confidence, "chosen_batch": chosen, "probability_affordable": round(probs[chosen], 4) if chosen else 0.0, "batch_probabilities": {str(k): round(v, 4) for k, v in probs.items()}, "fail_closed": chosen == 0}

def minimum_cash_for_batch(target_batch: int, scenarios: Sequence[CostScenario], *, min_confidence: float = 0.90, tolerance_inr: float = 1.0) -> float:
    if target_batch <= 0:
        raise ValueError("target_batch must be positive")
    if tolerance_inr <= 0:
        raise ValueError("tolerance_inr must be positive")
    if not 0 < min_confidence <= 1:
        raise ValueError("min_confidence must be in (0,1]")
    if not scenarios:
        raise ValueError("at least one scenario is required")
    costs = sorted(s.total_cost(target_batch) for s in scenarios)
    rank = max(1, math.ceil(min_confidence * len(costs)))
    exact = costs[rank - 1]
    return math.ceil(exact / tolerance_inr) * tolerance_inr
