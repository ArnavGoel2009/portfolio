"""Monte Carlo funding-risk model for ThinkSmiths kit batches.

All cost ranges are planning assumptions, not supplier quotations. The model estimates
how often a cash ceiling covers a target batch when unit, guide, logistics, contingency
and fixed costs vary within user-supplied ranges. A deterministic seed makes results
reproducible for review and testing.
"""
from __future__ import annotations

import math
import random
from typing import Dict, Tuple

Range = Tuple[float, float]


def _validate_range(name: str, bounds: Range, *, max_value: float | None = None) -> None:
    if len(bounds) != 2:
        raise ValueError(f"{name} must contain exactly (min, max)")
    low, high = bounds
    if low < 0 or high < low:
        raise ValueError(f"{name} must be non-negative and ordered")
    if max_value is not None and high > max_value:
        raise ValueError(f"{name} cannot exceed {max_value}")


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate percentile of an empty sample")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def estimate_funding_risk(
    cash_inr: float,
    target_kits: int,
    kit_cost_range: Range,
    guide_cost_range: Range = (40.0, 60.0),
    logistics_rate_range: Range = (0.05, 0.12),
    contingency_rate_range: Range = (0.05, 0.10),
    fixed_cost_range: Range = (0.0, 0.0),
    *,
    iterations: int = 5000,
    seed: int = 42,
) -> Dict[str, float | int]:
    """Estimate the risk that a cash ceiling cannot fund ``target_kits``.

    Each trial draws uniformly from the supplied planning ranges. Rates are applied
    multiplicatively to direct per-kit cost, matching ``FundingPlan`` in
    ``funding_engine.py``. The output contains affordability probability and cost
    percentiles that can be used to choose a less brittle funding ask.
    """
    if cash_inr <= 0:
        raise ValueError("cash_inr must be positive")
    if not isinstance(target_kits, int) or target_kits <= 0:
        raise ValueError("target_kits must be a positive integer")
    if not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("iterations must be a positive integer")

    _validate_range("kit_cost_range", kit_cost_range)
    _validate_range("guide_cost_range", guide_cost_range)
    _validate_range("logistics_rate_range", logistics_rate_range, max_value=1.0)
    _validate_range("contingency_rate_range", contingency_rate_range, max_value=1.0)
    _validate_range("fixed_cost_range", fixed_cost_range)

    rng = random.Random(seed)
    total_costs: list[float] = []
    affordable = 0

    for _ in range(iterations):
        kit_cost = rng.uniform(*kit_cost_range)
        guide_cost = rng.uniform(*guide_cost_range)
        logistics_rate = rng.uniform(*logistics_rate_range)
        contingency_rate = rng.uniform(*contingency_rate_range)
        fixed_cost = rng.uniform(*fixed_cost_range)
        direct_cost = kit_cost + guide_cost
        total = fixed_cost + target_kits * direct_cost * (1 + logistics_rate) * (1 + contingency_rate)
        total_costs.append(total)
        affordable += total <= cash_inr

    total_costs.sort()
    return {
        "cash_inr": round(cash_inr, 2),
        "target_kits": target_kits,
        "iterations": iterations,
        "seed": seed,
        "probability_affordable": round(affordable / iterations, 4),
        "probability_over_budget": round(1 - affordable / iterations, 4),
        "median_total_inr": round(_percentile(total_costs, 0.50), 2),
        "p90_total_inr": round(_percentile(total_costs, 0.90), 2),
        "p95_total_inr": round(_percentile(total_costs, 0.95), 2),
        "min_total_inr": round(total_costs[0], 2),
        "max_total_inr": round(total_costs[-1], 2),
    }


if __name__ == "__main__":
    import json

    example = estimate_funding_risk(
        50000,
        100,
        (300, 500),
        iterations=10000,
        seed=42,
    )
    print(json.dumps(example, indent=2))
