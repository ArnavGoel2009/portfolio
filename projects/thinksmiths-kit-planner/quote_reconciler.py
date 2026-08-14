from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Iterable

@dataclass(frozen=True)
class SupplierQuote:
    supplier: str
    quoted_on: date
    unit_kit_inr: float
    guide_unit_inr: float
    shipping_inr: float
    min_order_qty: int = 1

    def validate(self) -> None:
        if not self.supplier.strip():
            raise ValueError("supplier is required")
        if self.unit_kit_inr < 0 or self.guide_unit_inr < 0 or self.shipping_inr < 0:
            raise ValueError("quote costs must be non-negative")
        if self.min_order_qty <= 0:
            raise ValueError("min_order_qty must be positive")

    def landed_total(self, kits: int) -> float:
        self.validate()
        if kits < self.min_order_qty:
            raise ValueError("requested kits below supplier MOQ")
        return kits * (self.unit_kit_inr + self.guide_unit_inr) + self.shipping_inr

    def landed_unit(self, kits: int) -> float:
        return self.landed_total(kits) / kits

def rank_quotes(quotes: Iterable[SupplierQuote], kits: int, *, as_of: date, max_age_days: int = 30) -> list[dict]:
    if kits <= 0:
        raise ValueError("kits must be positive")
    if max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    rows=[]
    for q in quotes:
        q.validate()
        age=(as_of-q.quoted_on).days
        if age < 0:
            raise ValueError("quote date cannot be in the future")
        if age > max_age_days or kits < q.min_order_qty:
            continue
        total=q.landed_total(kits)
        rows.append({"supplier":q.supplier,"age_days":age,"landed_total_inr":round(total,2),"landed_unit_inr":round(total/kits,2),"min_order_qty":q.min_order_qty})
    rows.sort(key=lambda r:(r["landed_total_inr"],r["age_days"],r["supplier"]))
    return rows

def funding_coverage(cash_inr: float, quotes: Iterable[SupplierQuote], kits: int, *, as_of: date, max_age_days: int = 30) -> dict:
    if cash_inr <= 0:
        raise ValueError("cash_inr must be positive")
    ranked=rank_quotes(quotes,kits,as_of=as_of,max_age_days=max_age_days)
    if not ranked:
        return {"eligible_quotes":0,"fundable":False,"best_supplier":None,"shortfall_inr":None}
    best=ranked[0]
    shortfall=max(0.0,best["landed_total_inr"]-cash_inr)
    return {"eligible_quotes":len(ranked),"fundable":shortfall==0,"best_supplier":best["supplier"],"best_total_inr":best["landed_total_inr"],"shortfall_inr":round(shortfall,2)}
