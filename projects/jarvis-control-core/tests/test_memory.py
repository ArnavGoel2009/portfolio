import tempfile,unittest
from jarvis_core.memory import LocalMemoryStore
from jarvis_core.memory_planner import MemoryAwarePlanner
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
class T(unittest.TestCase):
 def setUp(self):self.d=tempfile.TemporaryDirectory();self.c=Clock();self.m=LocalMemoryStore(self.d.name,self.c)
 def tearDown(self):self.d.cleanup()
 def test_persists_across_restart(self):
  x=self.m.remember("JARVIS uses transactional task claims","github");m2=LocalMemoryStore(self.d.name,self.c);self.assertEqual(m2.retrieve("transactional claims")[0]["id"],x.id)
 def test_idempotent_remember(self):
  a=self.m.remember("same fact","drive");b=self.m.remember("same fact","drive");self.assertEqual(a.id,b.id)
 def test_relevant_memory_ranks_first(self):
  self.m.remember("ClearFlow gas sensing sewer robot validation","clearflow");self.m.remember("ThinkSmiths workshop funding partner","thinksmiths");self.assertEqual(self.m.retrieve("sewer gas robot")[0]["source"],"clearflow")
 def test_filter(self):
  self.m.remember("robot sensor","a",{"lane":"clearflow"});self.m.remember("robot lesson","b",{"lane":"thinksmiths"});self.assertEqual(len(self.m.retrieve("robot",filters={"lane":"clearflow"})),1)
 def test_provenance_in_context(self):
  self.m.remember("Postgres owns task leases","github");self.assertIn("source=github",self.m.context("task leases"))
 def test_empty_query(self):self.m.remember("anything","x");self.assertEqual(self.m.retrieve(""),[])
 def test_forget(self):
  x=self.m.remember("temporary","x");self.assertTrue(self.m.forget(x.id));self.assertEqual(self.m.retrieve("temporary"),[])
 def test_context_budget(self):
  for i in range(20):self.m.remember("jarvis memory "+("x"*100)+str(i),"x")
  self.assertLessEqual(len(self.m.context("jarvis memory",k=20,max_chars=500)),500)
 def test_planner_receives_memory(self):
  self.m.remember("Use evidence gates before completion","directive");seen={}
  def p(obj,ctx):seen["ctx"]=ctx;return ["inspect","build","test"]
  plan=MemoryAwarePlanner(self.m,p).plan("completion evidence");self.assertIn("evidence gates",seen["ctx"]);self.assertEqual(plan.steps[-1],"test")
 def test_planner_contract(self):
  with self.assertRaises(TypeError):MemoryAwarePlanner(self.m,lambda a,b:"bad").plan("x")
if __name__=="__main__":unittest.main()
