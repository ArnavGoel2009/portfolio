from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

GOOD = ("csr","foundation","grant","philanthropy","sustainability","community investment","social impact","sponsorship")
BAD = ("support","career","legal","privacy","press","media","sales","customer service","helpdesk","investor relations")

@dataclass
class RouteScore:
    score: int
    decision: str
    reasons: list[str]

def score_route(route: Mapping[str,Any]) -> RouteScore:
    score=0; reasons=[]
    source=str(route.get("source_type") or "").lower()
    role=str(route.get("role") or "").lower()
    named=bool(route.get("named_person"))
    current=bool(route.get("current"))
    inbound=bool(route.get("explicit_inbound_funding_route"))
    if source in {"first_party","official"}:
        score += 35; reasons.append("AUTHORITATIVE_SOURCE")
    else:
        reasons.append("NON_AUTHORITATIVE_SOURCE")
    if current:
        score += 20; reasons.append("CURRENT")
    else:
        reasons.append("NOT_CURRENT")
    if any(x in role for x in GOOD):
        score += 25; reasons.append("FUNDING_ROLE_MATCH")
    if any(x in role for x in BAD) and not any(x in role for x in GOOD):
        score -= 45; reasons.append("MISMATCHED_ROUTE")
    if named:
        score += 10; reasons.append("NAMED_PERSON")
    if inbound:
        score += 15; reasons.append("EXPLICIT_INBOUND_FUNDING_ROUTE")
    decision = "READY_ROUTE" if score >= 70 and "NON_AUTHORITATIVE_SOURCE" not in reasons and "NOT_CURRENT" not in reasons and "MISMATCHED_ROUTE" not in reasons else "HOLD_ROUTE"
    return RouteScore(score, decision, reasons)
