from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any
import threading

@dataclass
class WorkerResult:
    ok: bool
    evidence: list[dict]
    limitations: list[str]
    error: str|None=None

class Worker(Protocol):
    name: str
    capabilities: list[str]
    def execute(self, task: Any) -> WorkerResult: ...

class PostgresRunner:
    """Transactional claim -> execute -> evidence-gated completion with lease watchdog."""
    def __init__(self, store, heartbeat_seconds=30, lease_seconds=120):
        if heartbeat_seconds <= 0 or lease_seconds <= heartbeat_seconds:
            raise ValueError("lease_seconds must exceed heartbeat_seconds > 0")
        self.store=store; self.heartbeat_seconds=heartbeat_seconds; self.lease_seconds=lease_seconds

    def run_once(self, worker: Worker):
        task=self.store.claim_next(worker.name, worker.capabilities, self.lease_seconds)
        if task is None: return {"status":"IDLE"}
        stop=threading.Event(); lost=threading.Event()
        def renew():
            while not stop.wait(self.heartbeat_seconds):
                try:
                    if not self.store.heartbeat(task.id, worker.name, self.lease_seconds):
                        lost.set(); return
                except Exception:
                    lost.set(); return
        thread=threading.Thread(target=renew, daemon=True); thread.start()
        try:
            result=worker.execute(task)
        except Exception as exc:
            stop.set(); thread.join(timeout=1)
            self.store.fail(task.id, worker.name, f"{type(exc).__name__}: {exc}", True)
            return {"status":"RETRY","task_id":task.id,"error":str(exc)}
        stop.set(); thread.join(timeout=1)
        if lost.is_set():
            return {"status":"LEASE_LOST","task_id":task.id}
        if result.ok:
            if not result.evidence:
                self.store.fail(task.id, worker.name, "worker claimed success without evidence", False)
                return {"status":"REJECTED","task_id":task.id}
            if self.store.complete(task.id, worker.name, result.evidence, result.limitations):
                return {"status":"DONE","task_id":task.id}
            return {"status":"LEASE_LOST","task_id":task.id}
        state=self.store.fail(task.id, worker.name, result.error or "worker failed", True)
        return {"status":"RETRY" if state=="READY" else "FAILED","task_id":task.id}
