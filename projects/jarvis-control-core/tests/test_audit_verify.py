import json,tempfile,unittest
from pathlib import Path
from jarvis_core.audit_verify import verify_state

class AuditVerifierTests(unittest.TestCase):
 def write(self,tasks,events):
  d=tempfile.TemporaryDirectory(); p=Path(d.name)
  (p/'tasks.json').write_text(json.dumps(tasks))
  (p/'audit.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
  return d,p
 def test_valid_completed_task(self):
  t={'id':'1','status':'DONE','idempotency_key':'k','evidence':[{'type':'test','ref':'ok'}]}
  d,p=self.write([t],[{'ts':1,'event':'TASK_ADDED','task_id':'1'},{'ts':2,'event':'TASK_COMPLETED','task_id':'1'}])
  try:self.assertTrue(verify_state(p).ok)
  finally:d.cleanup()
 def test_done_without_evidence_fails(self):
  t={'id':'1','status':'DONE','idempotency_key':'k','evidence':[]}
  d,p=self.write([t],[{'ts':1,'event':'TASK_COMPLETED','task_id':'1'}])
  try:self.assertIn('DONE_WITHOUT_EVIDENCE:1',verify_state(p).errors)
  finally:d.cleanup()
 def test_orphan_event_fails(self):
  d,p=self.write([], [{'ts':1,'event':'TASK_CLAIMED','task_id':'ghost'}])
  try:self.assertTrue(any(x.startswith('ORPHAN_EVENT') for x in verify_state(p).errors))
  finally:d.cleanup()
 def test_non_monotonic_timestamp_fails(self):
  t={'id':'1','status':'READY','idempotency_key':'k','evidence':[]}
  d,p=self.write([t],[{'ts':2,'event':'TASK_ADDED','task_id':'1'},{'ts':1,'event':'TASK_CLAIMED','task_id':'1'}])
  try:self.assertTrue(any(x.startswith('NON_MONOTONIC_TIMESTAMP') for x in verify_state(p).errors))
  finally:d.cleanup()
 def test_duplicate_active_key_fails(self):
  a={'id':'1','status':'READY','idempotency_key':'k','evidence':[]}; b={'id':'2','status':'READY','idempotency_key':'k','evidence':[]}
  d,p=self.write([a,b],[{'ts':1,'event':'TASK_ADDED','task_id':'1'},{'ts':2,'event':'TASK_ADDED','task_id':'2'}])
  try:self.assertIn('DUPLICATE_ACTIVE_IDEMPOTENCY_KEY',verify_state(p).errors)
  finally:d.cleanup()
 def test_failed_key_can_be_reenqueued(self):
  failed={'id':'1','status':'FAILED','idempotency_key':'k','evidence':[]}
  replacement={'id':'2','status':'READY','idempotency_key':'k','evidence':[]}
  d,p=self.write([failed,replacement],[{'ts':1,'event':'TASK_ADDED','task_id':'1'},{'ts':2,'event':'TASK_FAILED','task_id':'1'},{'ts':3,'event':'TASK_ADDED','task_id':'2'}])
  try:self.assertNotIn('DUPLICATE_ACTIVE_IDEMPOTENCY_KEY',verify_state(p).errors)
  finally:d.cleanup()

if __name__=='__main__':unittest.main()
