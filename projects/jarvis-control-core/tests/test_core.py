import tempfile,unittest
from pathlib import Path
from jarvis_core import JarvisCore,EvidenceError
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
class T(unittest.TestCase):
 def setUp(self):self.d=tempfile.TemporaryDirectory();self.clock=Clock();self.c=JarvisCore(self.d.name,self.clock)
 def tearDown(self):self.d.cleanup()
 def add(self,title='x',**kw):return self.c.add_task(title,'jarvis',9,8,9,3,**kw)
 def test_priority(self):
  self.c.add_task('filler','lab',2,2,9,2); high=self.add('state');self.assertEqual(self.c.claim_next('codex').id,high.id)
 def test_exclusive(self):self.add();self.assertIsNotNone(self.c.claim_next('a'));self.assertIsNone(self.c.claim_next('b'))
 def test_lease_recovery(self):
  t=self.add();self.c.claim_next('a',lease_seconds=5);self.clock.t+=6;self.assertEqual(self.c.claim_next('b').id,t.id)
 def test_heartbeat(self):
  t=self.add();self.c.claim_next('a',lease_seconds=5);self.clock.t+=4;self.c.heartbeat(t.id,'a',10);self.clock.t+=2;self.assertIsNone(self.c.claim_next('b'))
 def test_evidence_gate(self):
  t=self.add();self.c.claim_next('a')
  with self.assertRaises(EvidenceError):self.c.complete(t.id,'a',[])
 def test_dependencies(self):
  a=self.add('a');self.add('b',dependencies=[a.id]);self.assertEqual(self.c.claim_next('x').id,a.id)
 def test_capability_routing(self):self.add(capabilities=['browser']);self.assertIsNone(self.c.claim_next('coder',['python']));self.assertIsNotNone(self.c.claim_next('browser',['browser']))
 def test_approval_gate(self):
  t=self.add(approval_required=True);self.assertIsNone(self.c.claim_next('a'));self.c.approve(t.id,'arnav');self.assertEqual(self.c.claim_next('a').id,t.id)
 def test_approval_task_does_not_starve_ready_work(self):
  gated=self.c.add_task('approve me','jarvis',10,10,10,1,approval_required=True)
  ready=self.c.add_task('safe work','jarvis',8,8,8,2)
  claimed=self.c.claim_next('agent')
  self.assertEqual(claimed.id,ready.id)
  by={t['id']:t for t in self.c.snapshot()['tasks']}
  self.assertEqual(by[gated.id]['status'],'WAITING_APPROVAL')
 def test_idempotent_enqueue(self):
  a=self.add('same',idempotency_key='K');b=self.add('same',idempotency_key='K');self.assertEqual(a.id,b.id);self.assertEqual(len(self.c.snapshot()['tasks']),1)
 def test_retry_then_fail(self):
  t=self.add(max_attempts=2);self.c.claim_next('a');self.c.fail(t.id,'a','boom');self.assertEqual(self.c.snapshot()['counts']['READY'],1);self.c.claim_next('a');self.c.fail(t.id,'a','boom');self.assertEqual(self.c.snapshot()['counts']['FAILED'],1)
 def test_completion(self):
  t=self.add();self.c.claim_next('a');self.c.complete(t.id,'a',[{'type':'test','ref':'13/13'}]);self.assertEqual(self.c.snapshot()['counts']['DONE'],1)
 def test_audit(self):self.add();self.c.claim_next('a');self.assertGreaterEqual(len((Path(self.d.name)/'audit.jsonl').read_text().splitlines()),2)
if __name__=='__main__':unittest.main()
