import tempfile,unittest
from types import SimpleNamespace
from jarvis_core.scheduler import EventQueue,Scheduler
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
class Store:
 def __init__(self):self.tasks={}
 def add_task(self,title,lane,impact,urgency,confidence,effort,capabilities=None,approval_required=False,idempotency_key=None):
  if idempotency_key in self.tasks:return self.tasks[idempotency_key]
  t=SimpleNamespace(id="task-"+str(len(self.tasks)+1),title=title);self.tasks[idempotency_key]=t;return t
class Tests(unittest.TestCase):
 def setUp(self):self.d=tempfile.TemporaryDirectory();self.c=Clock();self.q=EventQueue(self.d.name,self.c);self.s=Store()
 def tearDown(self):self.d.cleanup()
 def payload(self):return {"title":"Run JARVIS evaluation","capabilities":["python"]}
 def test_future_event_not_claimed(self):self.q.enqueue("task",self.payload(),available_at=1010,idempotency_key="daily");self.assertIsNone(self.q.claim_due("s"))
 def test_due_event_claimed(self):self.q.enqueue("task",self.payload(),available_at=999,idempotency_key="daily");self.assertEqual(self.q.claim_due("s").idempotency_key,"daily")
 def test_idempotent_schedule(self):
  a=self.q.enqueue("task",self.payload(),idempotency_key="daily");b=self.q.enqueue("task",self.payload(),idempotency_key="daily");self.assertEqual(a.id,b.id)
 def test_lease_recovery(self):
  self.q.enqueue("task",self.payload(),idempotency_key="x");a=self.q.claim_due("a",5);self.c.t+=6;b=self.q.claim_due("b",5);self.assertEqual(a.id,b.id)
 def test_wrong_worker_cannot_ack(self):
  e=self.q.enqueue("task",self.payload());self.q.claim_due("a");self.assertFalse(self.q.ack(e.id,"b"))
 def test_nack_retries(self):
  e=self.q.enqueue("task",self.payload(),max_attempts=2);self.q.claim_due("a");self.assertTrue(self.q.nack(e.id,"a","boom"));self.assertEqual(self.q.snapshot()[0]["status"],"READY")
 def test_retry_exhaustion(self):
  e=self.q.enqueue("task",self.payload(),max_attempts=1);self.q.claim_due("a");self.assertFalse(self.q.nack(e.id,"a","boom"));self.assertEqual(self.q.snapshot()[0]["status"],"FAILED")
 def test_scheduler_end_to_end(self):
  self.q.enqueue("task",self.payload(),idempotency_key="eval-2026-08-21");out=Scheduler(self.q,self.s).tick();self.assertEqual(out["status"],"ENQUEUED");self.assertEqual(len(self.s.tasks),1)
 def test_crash_after_task_insert_does_not_duplicate(self):
  self.q.enqueue("task",self.payload(),idempotency_key="once");e=self.q.claim_due("scheduler",1);self.s.add_task("Run JARVIS evaluation","jarvis",7,7,8,4,idempotency_key=e.idempotency_key);self.c.t+=2;out=Scheduler(self.q,self.s).tick();self.assertEqual(out["status"],"ENQUEUED");self.assertEqual(len(self.s.tasks),1)
 def test_persistence_across_restart(self):
  self.q.enqueue("task",self.payload(),idempotency_key="persist");q2=EventQueue(self.d.name,self.c);self.assertEqual(q2.snapshot()[0]["idempotency_key"],"persist")
if __name__=="__main__":unittest.main()
