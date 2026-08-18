from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import json


class DBConnection(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> Any: ...


@dataclass
class ClaimedTask:
    id: str
    title: str
    lane: str
    score: float
    capabilities: list[str]
    attempts: int
    lease_until: str | None
    payload: dict[str, Any]


class PostgresTaskStore:
    """Thin client for transactional JARVIS Postgres functions.

    Concurrency correctness lives in PostgreSQL, not in this Python process, so
    independent Claude/Codex/Gemini workers can safely claim tasks from separate hosts.
    """

    def __init__(self, conn: DBConnection):
        self.conn = conn

    def enqueue(self, *, title: str, lane: str, impact: int, urgency: int,
                confidence: int, effort: int, capabilities: list[str] | None = None,
                dependencies: list[str] | None = None, approval_required: bool = False,
                idempotency_key: str | None = None, max_attempts: int = 3,
                payload: dict[str, Any] | None = None) -> str:
        row = self.conn.execute(
            "select jarvis_enqueue(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) as id",
            (title, lane, impact, urgency, confidence, effort, capabilities or [],
             dependencies or [], approval_required, idempotency_key, max_attempts,
             json.dumps(payload or {})),
        ).fetchone()
        return str(row[0])

    def claim_next(self, agent: str, capabilities: list[str], lease_seconds: int = 1800) -> ClaimedTask | None:
        row = self.conn.execute(
            "select * from jarvis_claim_next(%s,%s,%s)",
            (agent, capabilities, lease_seconds),
        ).fetchone()
        if row is None:
            return None
        return ClaimedTask(str(row[0]), row[1], row[2], float(row[3]),
                           list(row[4] or []), int(row[5]),
                           str(row[6]) if row[6] is not None else None, row[7] or {})

    def heartbeat(self, task_id: str, agent: str, lease_seconds: int = 1800) -> bool:
        row = self.conn.execute("select jarvis_heartbeat(%s,%s,%s)",
                                (task_id, agent, lease_seconds)).fetchone()
        return bool(row and row[0])

    def complete(self, task_id: str, agent: str, evidence: list[dict[str, Any]], limitations: list[str] | None = None) -> bool:
        if not evidence or any(not e.get("type") or not e.get("ref") for e in evidence):
            raise ValueError("completion requires evidence entries containing type and ref")
        row = self.conn.execute("select jarvis_complete(%s,%s,%s::jsonb,%s)",
                                (task_id, agent, json.dumps(evidence), limitations or [])).fetchone()
        return bool(row and row[0])

    def fail(self, task_id: str, agent: str, reason: str, retryable: bool = True) -> str:
        row = self.conn.execute("select jarvis_fail(%s,%s,%s,%s)",
                                (task_id, agent, reason, retryable)).fetchone()
        if not row:
            raise RuntimeError("jarvis_fail returned no result")
        return str(row[0])
