from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Iterable, Mapping, Any

INTERNAL_TOKEN_PATTERNS = [
    re.compile(r"\[(?:PORTFOLIO|TSC|JARVIS)[^\]]*\]", re.I),
    re.compile(r"\b(?:QUEUE\s*SEND|JARVIS\s*QUEUE|READY|HOLD|CANCEL(?:LED)?)\b", re.I),
]
MONEY_TERMS = re.compile(
    r"\b(fund(?:ing)?|grant|donation|donate|sponsor(?:ship)?|cash contribution|csr funding|financial support|underwrite)\b",
    re.I,
)
BAD_ROUTE_TERMS = {
    "support", "careers", "career", "privacy", "legal", "press", "media",
    "investor", "sales", "customer service", "helpdesk"
}
GOOD_ROUTE_TERMS = {
    "csr", "foundation", "grants", "grant", "philanthropy", "sustainability",
    "community investment", "social impact", "sponsorship", "education"
}

def canonical_org(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", (name or "").lower())
    drops = {"foundation","trust","india","limited","ltd","pvt","private","company","co","group","the"}
    toks = [t for t in s.split() if t not in drops]
    return " ".join(toks).strip()

def subject_tokens(subject: str) -> list[str]:
    hits=[]
    for pat in INTERNAL_TOKEN_PATTERNS:
        hits.extend(m.group(0) for m in pat.finditer(subject or ""))
    return hits

def route_role_ok(route_role: str) -> bool:
    role=(route_role or "").strip().lower()
    if not role:
        return False
    if any(x in role for x in BAD_ROUTE_TERMS) and not any(x in role for x in GOOD_ROUTE_TERMS):
        return False
    return any(x in role for x in GOOD_ROUTE_TERMS)

def is_direct_money_ask(subject: str, body: str) -> bool:
    text=f"{subject or ''}\n{body or ''}"
    if not MONEY_TERMS.search(text):
        return False
    tail=text[max(0, int(len(text)*0.55)):]
    if not MONEY_TERMS.search(tail):
        return False
    lower=tail.lower()
    weak_starts=("could you partner","can we partner","would you collaborate","could you provide materials",
                 "could you donate materials","could you print","could you distribute")
    if any(x in lower for x in weak_starts):
        return False
    return True

@dataclass
class Finding:
    draft_id: str
    organisation: str
    status: str
    reasons: list[str]

def audit_rows(rows: Iterable[Mapping[str, Any]], prior_orgs: Iterable[str]=()) -> list[Finding]:
    prior={canonical_org(x) for x in prior_orgs if canonical_org(x)}
    seen_ids=set()
    seen_orgs=set()
    out=[]
    for r in rows:
        reasons=[]
        did=str(r.get("draft_id") or "").strip()
        org=str(r.get("organisation") or "").strip()
        subj=str(r.get("subject") or "")
        body=str(r.get("body") or "")
        route_role=str(r.get("route_role") or "")
        verification=str(r.get("verification_source") or "").strip()
        canon=canonical_org(org)
        if not did:
            reasons.append("MISSING_DRAFT_ID")
        elif did in seen_ids:
            reasons.append("DUPLICATE_DRAFT_ID")
        if canon:
            if canon in prior:
                reasons.append("DUPLICATE_ORGANISATION_PRIOR")
            if canon in seen_orgs:
                reasons.append("DUPLICATE_ORGANISATION_BATCH")
        else:
            reasons.append("MISSING_ORGANISATION")
        toks=subject_tokens(subj)
        if toks:
            reasons.append("INTERNAL_SUBJECT_TOKEN:"+"|".join(toks))
        if not is_direct_money_ask(subj, body):
            reasons.append("NOT_DIRECT_MONEY_ASK")
        if not verification:
            reasons.append("MISSING_VERIFICATION_SOURCE")
        if not route_role_ok(route_role):
            reasons.append("ROUTE_ROLE_NOT_FUNDING_APPROPRIATE")
        status="READY" if not reasons else "HOLD"
        out.append(Finding(did, org, status, reasons))
        if did: seen_ids.add(did)
        if canon: seen_orgs.add(canon)
    return out

def summary(findings: Iterable[Finding]) -> dict[str, int]:
    f=list(findings)
    return {
        "total": len(f),
        "ready": sum(x.status=="READY" for x in f),
        "hold": sum(x.status!="READY" for x in f),
    }
