from __future__ import annotations
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from typing import Any
import hashlib, json, os, time, uuid

class TaskStatus(str, Enum):
    READY='READY'; CLAIMED='CLAIMED'; DONE='DONE'; FAILED='FAILED'; BLOCKED='BLOCKED'; WAITING_APPROVAL='WAITING_APPROVAL'
class EvidenceError(ValueError): pass
class ClaimConflict(RuntimeError): pass
class ApprovalRequired(RuntimeError): pass

@dataclass
class Task:
    id:str; title:str; lane:str; impact:int; urgency:int; confidence:int; effort:int
    status:str=TaskStatus.READY.value; claimed_by:str|None=None; lease_until:float|None=None
    dependencies:list[str]=field(default_factory=list); capabilities:list[str]=field(default_factory=list)
    approval_required:bool=False; approval_granted:bool=False; idempotency_key:str|None=None
    attempts:int=0; max_attempts:int=3; evidence:list[dict[str,Any]]=field(default_factory=list); limitations:list[str]=field(default_factory=list)
    @property
    def score(self): return round((.45*self.impact+.30*self.urgency+.25*self.confidence)*(11-self.effort)/10,3)

class JarvisCore:
    def __init__(self,state_dir:str|Path,clock=time.time):
        self.root=Path(state_dir); self.root.mkdir(parents=True,exist_ok=True)
        self.tasks_path=self.root/'tasks.json'; self.audit_path=self.root/'audit.jsonl'; self.lock_path=self.root/'.state.lock'; self.clock=clock
        if not self.tasks_path.exists(): self._write([])
    def _read(self): return json.loads(self.tasks_path.read_text())
    def _write(self,rows):
        tmp=self.tasks_path.with_suffix('.tmp'); tmp.write_text(json.dumps(rows,indent=2,sort_keys=True)); os.replace(tmp,self.tasks_path)
    def _audit(self,event,**data):
        with self.audit_path.open('a') as f: f.write(json.dumps({'ts':self.clock(),'event':event,**data},sort_keys=True)+'\n')
    def _acquire(self,timeout=.5):
        start=time.monotonic()
        while True:
            try:
                fd=os.open(self.lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.write(fd,str(os.getpid()).encode()); os.close(fd); return
            except FileExistsError:
                if time.monotonic()-start>timeout: raise ClaimConflict('state lock busy')
                time.sleep(.01)
    def _release(self):
        try:self.lock_path.unlink()
        except FileNotFoundError:pass
    def add_task(self,title,lane,impact,urgency,confidence,effort,dependencies=None,capabilities=None,approval_required=False,idempotency_key=None,max_attempts=3):
        for n,v in {'impact':impact,'urgency':urgency,'confidence':confidence,'effort':effort}.items():
            if not 1<=v<=10: raise ValueError(f'{n} must be 1..10')
        key=idempotency_key or hashlib.sha256(f'{lane}:{title}'.encode()).hexdigest()[:20]
        self._acquire()
        try:
            rows=self._read(); existing=next((r for r in rows if r.get('idempotency_key')==key and r['status']!=TaskStatus.FAILED.value),None)
            if existing:return Task(**existing)
            t=Task(str(uuid.uuid4()),title,lane,impact,urgency,confidence,effort,dependencies=dependencies or [],capabilities=capabilities or [],approval_required=approval_required,idempotency_key=key,max_attempts=max_attempts)
            rows.append(asdict(t)); self._write(rows)
        finally:self._release()
        self._audit('TASK_ADDED',task_id=t.id,score=t.score,key=key); return t
    def approve(self,task_id,approved_by):
        self._acquire()
        try:
            rows=self._read()
            for r in rows:
                if r['id']==task_id:
                    r['approval_granted']=True
                    if r['status']==TaskStatus.WAITING_APPROVAL.value:r['status']=TaskStatus.READY.value
                    self._write(rows); break
            else: raise KeyError(task_id)
        finally:self._release()
        self._audit('TASK_APPROVED',task_id=task_id,approved_by=approved_by)
    def _deps_done(self,r,rows):
        by={x['id']:x for x in rows}; return all(d in by and by[d]['status']==TaskStatus.DONE.value for d in r.get('dependencies',[]))
    def _eligible(self,r,rows,agent_caps,now):
        expired=r['status']==TaskStatus.CLAIMED.value and (r.get('lease_until') or 0)<now
        return (r['status']==TaskStatus.READY.value or expired) and set(r.get('capabilities',[])).issubset(agent_caps) and r.get('attempts',0)<r.get('max_attempts',3) and self._deps_done(r,rows)
    def claim_next(self,agent,capabilities=None,lease_seconds=1800):
        caps=set(capabilities or []); self._acquire()
        try:
            rows=self._read(); now=self.clock(); candidates=[(Task(**r),i) for i,r in enumerate(rows) if self._eligible(r,rows,caps,now)]
            if not candidates:return None
            t,i=max(candidates,key=lambda x:(x[0].score,x[0].impact,x[0].urgency))
            if rows[i].get('approval_required') and not rows[i].get('approval_granted'):
                rows[i]['status']=TaskStatus.WAITING_APPROVAL.value; self._write(rows); self._audit('APPROVAL_BLOCKED',task_id=t.id,agent=agent); return None
            rows[i]['status']=TaskStatus.CLAIMED.value; rows[i]['claimed_by']=agent; rows[i]['lease_until']=now+lease_seconds; rows[i]['attempts']=rows[i].get('attempts',0)+1
            self._write(rows); t=Task(**rows[i])
        finally:self._release()
        self._audit('TASK_CLAIMED',task_id=t.id,agent=agent,attempt=t.attempts); return t
    def heartbeat(self,task_id,agent,lease_seconds=1800):
        self._acquire()
        try:
            rows=self._read()
            for r in rows:
                if r['id']==task_id:
                    if r['status']!=TaskStatus.CLAIMED.value or r.get('claimed_by')!=agent: raise ClaimConflict('not owner')
                    r['lease_until']=self.clock()+lease_seconds; self._write(rows); until=r['lease_until']; break
            else:raise KeyError(task_id)
        finally:self._release()
        self._audit('LEASE_RENEWED',task_id=task_id,agent=agent,lease_until=until)
    def complete(self,task_id,agent,evidence,limitations=None):
        if not evidence:raise EvidenceError('completion requires evidence')
        for e in evidence:
            if not e.get('type') or not e.get('ref'):raise EvidenceError('evidence requires type and ref')
        self._acquire()
        try:
            rows=self._read()
            for r in rows:
                if r['id']==task_id:
                    if r['status']!=TaskStatus.CLAIMED.value or r.get('claimed_by')!=agent:raise ClaimConflict('not owner')
                    r['status']=TaskStatus.DONE.value;r['evidence']=evidence;r['limitations']=limitations or [];r['lease_until']=None;self._write(rows);break
            else:raise KeyError(task_id)
        finally:self._release()
        self._audit('TASK_COMPLETED',task_id=task_id,agent=agent,evidence_count=len(evidence))
    def fail(self,task_id,agent,reason,retryable=True):
        self._acquire()
        try:
            rows=self._read()
            for r in rows:
                if r['id']==task_id:
                    if r.get('claimed_by')!=agent:raise ClaimConflict('wrong agent')
                    retry=retryable and r.get('attempts',0)<r.get('max_attempts',3); r['status']=TaskStatus.READY.value if retry else TaskStatus.FAILED.value;r['claimed_by']=None;r['lease_until']=None;r['limitations']=[reason];self._write(rows);status=r['status'];break
            else:raise KeyError(task_id)
        finally:self._release()
        self._audit('TASK_FAILED',task_id=task_id,agent=agent,reason=reason,next_status=status)
    def snapshot(self):
        rows=self._read(); return {'tasks':rows,'counts':{s.value:sum(r['status']==s.value for r in rows) for s in TaskStatus}}
