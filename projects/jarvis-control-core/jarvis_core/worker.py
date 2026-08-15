from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Callable, Any
import time

@dataclass
class WorkerResult:
    ok: bool
    evidence: list[dict]
    limitations: list[str]
    error: str|None = None

class Worker(Protocol):
    name: str
    capabilities: list[str]
    def execute(self, task: Any) -> WorkerResult: ...

class CallableWorker:
    def __init__(self,name:str,capabilities:list[str],fn:Callable[[Any],WorkerResult]):
        self.name=name; self.capabilities=capabilities; self.fn=fn
    def execute(self,task): return self.fn(task)

class Runner:
    """Claim one compatible task, execute a worker, and commit only evidence-backed success."""
    def __init__(self,core,clock=time.time): self.core=core; self.clock=clock
    def run_once(self,worker:Worker,lease_seconds=1800):
        task=self.core.claim_next(worker.name,worker.capabilities,lease_seconds)
        if task is None:return {"status":"IDLE"}
        started=self.clock()
        try:
            result=worker.execute(task)
        except Exception as exc:
            self.core.fail(task.id,worker.name,f"{type(exc).__name__}: {exc}",retryable=True)
            return {"status":"RETRY","task_id":task.id,"error":str(exc)}
        if result.ok:
            if not result.evidence:
                self.core.fail(task.id,worker.name,"worker returned success without evidence",retryable=False)
                return {"status":"REJECTED","task_id":task.id}
            self.core.complete(task.id,worker.name,result.evidence,result.limitations)
            return {"status":"DONE","task_id":task.id,"elapsed":self.clock()-started}
        self.core.fail(task.id,worker.name,result.error or "worker failed",retryable=True)
        return {"status":"RETRY","task_id":task.id,"error":result.error}
