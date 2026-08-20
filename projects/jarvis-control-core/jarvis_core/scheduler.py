from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, os, threading, time, uuid

@dataclass(frozen=True)
class Event:
    id: str
    topic: str
    payload: dict
    available_at: float
    idempotency_key: str
    attempts: int = 0
    max_attempts: int = 3
    status: str = "READY"
    claimed_by: str|None = None
    lease_until: float|None = None

class EventQueue:
    """Crash-recoverable local event queue with leases and idempotency."""
    def __init__(self, state_dir, clock=time.time):
        self.root=Path(state_dir); self.root.mkdir(parents=True, exist_ok=True)
        self.path=self.root/"events.json"; self.lock=threading.RLock(); self.clock=clock
        if not self.path.exists(): self._write([])
    def _read(self): return json.loads(self.path.read_text())
    def _write(self, rows):
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(rows,indent=2,sort_keys=True)); os.replace(tmp,self.path)
    def enqueue(self, topic, payload, available_at=None, idempotency_key=None, max_attempts=3):
        key=idempotency_key or f"{topic}:{json.dumps(payload,sort_keys=True)}"
        with self.lock:
            rows=self._read(); existing=next((r for r in rows if r["idempotency_key"]==key and r["status"]!="FAILED"),None)
            if existing: return Event(**existing)
            e=Event(str(uuid.uuid4()),topic,payload,available_at or self.clock(),key,max_attempts=max_attempts)
            rows.append(e.__dict__); self._write(rows); return e
    def claim_due(self, worker, lease_seconds=60):
        now=self.clock()
        with self.lock:
            rows=self._read(); due=[]
            for i,r in enumerate(rows):
                expired=r["status"]=="CLAIMED" and (r["lease_until"] or 0)<now
                if (r["status"]=="READY" or expired) and r["available_at"]<=now and r["attempts"]<r["max_attempts"]: due.append((r["available_at"],i))
            if not due:return None
            _,i=min(due); rows[i]["status"]="CLAIMED"; rows[i]["claimed_by"]=worker; rows[i]["lease_until"]=now+lease_seconds; rows[i]["attempts"]+=1
            self._write(rows); return Event(**rows[i])
    def ack(self,event_id,worker):
        with self.lock:
            rows=self._read()
            for r in rows:
                if r["id"]==event_id:
                    if r["status"]!="CLAIMED" or r["claimed_by"]!=worker:return False
                    r["status"]="DONE";r["lease_until"]=None;self._write(rows);return True
            return False
    def nack(self,event_id,worker,error,retry_delay=0):
        with self.lock:
            rows=self._read()
            for r in rows:
                if r["id"]==event_id:
                    if r["claimed_by"]!=worker:return False
                    retry=r["attempts"]<r["max_attempts"];r["status"]="READY" if retry else "FAILED";r["claimed_by"]=None;r["lease_until"]=None;r["available_at"]=self.clock()+retry_delay;r["last_error"]=error;self._write(rows);return retry
            return False
    def snapshot(self):return self._read()

class Scheduler:
    """Maps due events into idempotent JARVIS tasks."""
    def __init__(self, events, task_store, worker_name="scheduler"):
        self.events=events;self.task_store=task_store;self.worker_name=worker_name
    def tick(self):
        e=self.events.claim_due(self.worker_name)
        if not e:return {"status":"IDLE"}
        try:
            p=e.payload
            task=self.task_store.add_task(p["title"],p.get("lane","jarvis"),p.get("impact",7),p.get("urgency",7),p.get("confidence",8),p.get("effort",4),capabilities=p.get("capabilities",[]),approval_required=p.get("approval_required",False),idempotency_key=e.idempotency_key)
            if not self.events.ack(e.id,self.worker_name):return {"status":"LEASE_LOST","event_id":e.id}
            return {"status":"ENQUEUED","event_id":e.id,"task_id":task.id}
        except Exception as exc:
            self.events.nack(e.id,self.worker_name,f"{type(exc).__name__}: {exc}",retry_delay=1)
            return {"status":"RETRY","event_id":e.id,"error":str(exc)}
