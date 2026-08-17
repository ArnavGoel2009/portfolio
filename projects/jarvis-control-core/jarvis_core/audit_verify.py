from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

KNOWN_EVENTS={
 'TASK_ADDED','TASK_APPROVED','APPROVAL_BLOCKED','TASK_CLAIMED',
 'LEASE_RENEWED','TASK_COMPLETED','TASK_FAILED'
}

@dataclass
class AuditReport:
 ok: bool
 errors: list[str]
 event_count: int
 task_count: int


def verify_state(state_dir:str|Path)->AuditReport:
 root=Path(state_dir)
 tasks_path=root/'tasks.json'; audit_path=root/'audit.jsonl'
 errors=[]
 try:
  tasks=json.loads(tasks_path.read_text())
 except Exception as e:
  return AuditReport(False,[f'TASKS_UNREADABLE:{type(e).__name__}'],0,0)
 ids=[str(t.get('id') or '') for t in tasks]
 id_set=set(ids)
 if any(not x for x in ids): errors.append('TASK_WITHOUT_ID')
 if len(id_set)!=len(ids): errors.append('DUPLICATE_TASK_ID')
 active_keys=set()
 for t in tasks:
  k=t.get('idempotency_key')
  if k and t.get('status')!='FAILED':
   if k in active_keys: errors.append('DUPLICATE_ACTIVE_IDEMPOTENCY_KEY')
   active_keys.add(k)
  if t.get('status')=='DONE' and not t.get('evidence'): errors.append(f'DONE_WITHOUT_EVIDENCE:{t.get("id")}')
 try:
  lines=[x for x in audit_path.read_text().splitlines() if x.strip()]
 except FileNotFoundError:
  lines=[]; errors.append('AUDIT_LOG_MISSING')
 events=[]
 last_ts=None
 for n,line in enumerate(lines,1):
  try:e=json.loads(line)
  except Exception:
   errors.append(f'AUDIT_JSON_INVALID:{n}'); continue
  events.append(e)
  if e.get('event') not in KNOWN_EVENTS: errors.append(f'UNKNOWN_EVENT:{n}:{e.get("event")}')
  ts=e.get('ts')
  if not isinstance(ts,(int,float)): errors.append(f'INVALID_TIMESTAMP:{n}')
  elif last_ts is not None and ts<last_ts: errors.append(f'NON_MONOTONIC_TIMESTAMP:{n}')
  if isinstance(ts,(int,float)): last_ts=ts
  tid=e.get('task_id')
  if tid and tid not in id_set: errors.append(f'ORPHAN_EVENT:{n}:{tid}')
 completed={e.get('task_id') for e in events if e.get('event')=='TASK_COMPLETED'}
 for t in tasks:
  if t.get('status')=='DONE' and t.get('id') not in completed: errors.append(f'DONE_WITHOUT_COMPLETION_EVENT:{t.get("id")}')
 return AuditReport(not errors,errors,len(events),len(tasks))
