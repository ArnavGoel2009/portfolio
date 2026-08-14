from __future__ import annotations
from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class SupplierOffer:
    supplier: str
    unit_kit_inr: float
    guide_unit_inr: float
    shipping_inr: float
    min_order_qty: int
    max_order_qty: int

    def validate(self) -> None:
        if not self.supplier.strip():
            raise ValueError("supplier is required")
        if min(self.unit_kit_inr, self.guide_unit_inr, self.shipping_inr) < 0:
            raise ValueError("costs must be non-negative")
        if self.min_order_qty <= 0 or self.max_order_qty < self.min_order_qty:
            raise ValueError("invalid order quantity bounds")

    @property
    def variable_unit_inr(self) -> float:
        return self.unit_kit_inr + self.guide_unit_inr

    def cost_for(self, qty: int) -> float:
        self.validate()
        if qty == 0:
            return 0.0
        if qty < self.min_order_qty or qty > self.max_order_qty:
            raise ValueError("quantity outside supplier bounds")
        return self.shipping_inr + qty * self.variable_unit_inr


def optimize_allocation(offers: list[SupplierOffer], target_kits: int) -> dict:
    """Find the exact minimum-cost allocation for target_kits.

    Each supplier can be unused (0) or used between MOQ and max_order_qty.
    Dynamic programming is exact for integer kit quantities and fail-closes when
    aggregate capacity/MOQs make the target infeasible.
    """
    if target_kits <= 0:
        raise ValueError("target_kits must be positive")
    if not offers:
        raise ValueError("at least one supplier offer is required")
    for offer in offers:
        offer.validate()

    # dp[q] = (cost, allocation tuple for processed suppliers)
    dp: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, tuple())}
    for offer in offers:
        nxt: dict[int, tuple[float, tuple[int, ...]]] = {}
        choices = [0] + list(range(offer.min_order_qty, min(offer.max_order_qty, target_kits) + 1))
        for already, (base_cost, allocation) in dp.items():
            for qty in choices:
                total_qty = already + qty
                if total_qty > target_kits:
                    break
                candidate = base_cost + offer.cost_for(qty)
                incumbent = nxt.get(total_qty)
                if incumbent is None or candidate < incumbent[0] - 1e-9:
                    nxt[total_qty] = (candidate, allocation + (qty,))
        dp = nxt

    if target_kits not in dp:
        return {
            "feasible": False,
            "target_kits": target_kits,
            "reason": "No exact allocation satisfies supplier MOQ/capacity constraints",
            "allocation": {},
            "total_cost_inr": None,
            "landed_unit_inr": None,
        }

    total_cost, quantities = dp[target_kits]
    allocation = {offer.supplier: qty for offer, qty in zip(offers, quantities) if qty > 0}
    return {
        "feasible": True,
        "target_kits": target_kits,
        "allocation": allocation,
        "total_cost_inr": round(total_cost, 2),
        "landed_unit_inr": round(total_cost / target_kits, 2),
        "suppliers_used": len(allocation),
    }


def funding_feasibility(cash_inr: float, offers: list[SupplierOffer], target_kits: int) -> dict:
    if cash_inr <= 0:
        raise ValueError("cash_inr must be positive")
    result = optimize_allocation(offers, target_kits)
    if not result["feasible"]:
        return {**result, "fundable": False, "shortfall_inr": None, "headroom_inr": None}
    delta = round(cash_inr - result["total_cost_inr"], 2)
    return {
        **result,
        "fundable": delta >= 0,
        "shortfall_inr": round(max(0.0, -delta), 2),
        "headroom_inr": round(max(0.0, delta), 2),
    }
