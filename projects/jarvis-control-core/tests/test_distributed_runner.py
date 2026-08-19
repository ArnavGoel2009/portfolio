import unittest,time,threading
from types import SimpleNamespace
from jarvis_core.postgres_runner import PostgresRunner,WorkerResult
from jarvis_core.orchestrator import Orchestrator
class FakeStore:
 def __init__(self,tasks):self.tasks=tasks;self.lock=threading.Lock();self.done=[];self.failed=[];self.heartbeats=0
 def claim_next(self,agent,caps,lease):
  with self.lock:
   for t in self.tasks:
    if not getattr(t,'owner',None) and set(t.capabilities).issubset(caps):t.owner=agent;return t
  return None
 def heartbeat(self,id,agent,lease):self.heartbeats+=1;return any(t.id==id and t.owner==agent for t in self.tasks)
 def complete(self,id,agent,evidence,limitations):
  with self.lock:
   t=next(x for x in self.tasks if x.id==id)
   if t.owner!=agent:return False
   self.done.append(id);self.tasks.remove(t);return True
 def fail(self,id,agent,reason,retryable):self.failed.append((id,reason,retryable));return 'READY' if retryable else 'FAILED'
class W:
 def __init__(self,name,caps,delay=0,ok=True,evidence=True):self.name=name;self.capabilities=caps;self.delay=delay;self.ok=ok;self.has_evidence=evidence
 def execute(self,t):time.sleep(self.delay);return WorkerResult(self.ok,[{'type':'test','ref':self.name}] if self.has_evidence else [],[],None if self.ok else 'boom')
class Tests(unittest.TestCase):
 def task(self,id,caps):return SimpleNamespace(id=id,title=id,capabilities=caps,owner=None)
 def test_heartbeat(self):
  s=FakeStore([self.task('1',['python'])]);o=PostgresRunner(s,.01,.05).run_once(W('codex',['python'],.035));self.assertEqual(o['status'],'DONE');self.assertGreaterEqual(s.heartbeats,2)
 def test_lease_loss_blocks_commit(self):
  s=FakeStore([self.task('1',['python'])]);s.heartbeat=lambda *a:False;o=PostgresRunner(s,.01,.05).run_once(W('x',['python'],.025));self.assertEqual(o['status'],'LEASE_LOST');self.assertEqual(s.done,[])
 def test_multiworker_capability_routing(self):
  s=FakeStore([self.task('code',['python']),self.task('research',['research']),self.task('git',['git'])]);workers=[W('codex',['python','git']),W('gemini',['research'])];Orchestrator(lambda:PostgresRunner(s,.01,.05),workers,.001).run_until_idle(2);self.assertCountEqual(s.done,['code','research','git'])
 def test_no_double_execution_under_contention(self):
  s=FakeStore([self.task(str(i),['python']) for i in range(50)]);workers=[W('w'+str(i),['python'],.001) for i in range(8)];Orchestrator(lambda:PostgresRunner(s,.01,.05),workers,.001).run_until_idle(2);self.assertEqual(len(s.done),50);self.assertEqual(len(set(s.done)),50)
 def test_fake_success_rejected(self):
  s=FakeStore([self.task('1',['python'])]);o=PostgresRunner(s,.01,.05).run_once(W('x',['python'],evidence=False));self.assertEqual(o['status'],'REJECTED');self.assertFalse(s.failed[-1][2])
if __name__=='__main__':unittest.main()
