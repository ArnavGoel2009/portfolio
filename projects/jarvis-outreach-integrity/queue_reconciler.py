from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping, Any

@dataclass
class ReconcileResult:
    draft_id: str
    state: str
    tracker_subject: str = ""
    gmail_subject: str = ""

def reconcile(tracker_rows: Iterable[Mapping[str,Any]], gmail_drafts: Iterable[Mapping[str,Any]]):
    g={str(x.get("draft_id") or ""): x for x in gmail_drafts if x.get("draft_id")}
    seen=set()
    out=[]
    for r in tracker_rows:
        did=str(r.get("draft_id") or "")
        if not did:
            out.append(ReconcileResult("", "TRACKER_MISSING_DRAFT_ID"))
            continue
        if did in seen:
            out.append(ReconcileResult(did, "TRACKER_DUPLICATE_DRAFT_ID"))
            continue
        seen.add(did)
        d=g.get(did)
        if d is None:
            out.append(ReconcileResult(did, "GMAIL_DRAFT_MISSING", str(r.get("subject") or ""), ""))
            continue
        ts=str(r.get("subject") or "")
        gs=str(d.get("subject") or "")
        if ts != gs:
            state="SUBJECT_MISMATCH"
        elif str(r.get("recipient") or "").lower().strip() != str(d.get("recipient") or "").lower().strip():
            state="RECIPIENT_MISMATCH"
        else:
            state="MATCH"
        out.append(ReconcileResult(did,state,ts,gs))
    tracked={x.draft_id for x in out if x.draft_id}
    for did,d in g.items():
        if did not in tracked:
            out.append(ReconcileResult(did,"UNTRACKED_GMAIL_DRAFT","",str(d.get("subject") or "")))
    return out
