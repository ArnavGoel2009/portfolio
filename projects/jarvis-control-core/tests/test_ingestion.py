import tempfile,unittest
from jarvis_core.ingestion import *
from types import SimpleNamespace
class Memory:
 def __init__(self):self.rows={}
 def remember(self,text,source,metadata=None,memory_id=None):self.rows[memory_id]={"text":text,"source":source,"metadata":metadata};return SimpleNamespace(id=memory_id)
class T(unittest.TestCase):
 def setUp(self):self.d=tempfile.TemporaryDirectory();self.m=Memory();self.i=MemoryIngestor(self.m,self.d.name)
 def tearDown(self):self.d.cleanup()
 def test_github_provenance(self):
  a=GitHubAdapter().normalize("o/r","a.py","hello");r=self.i.ingest(**a);self.assertEqual(self.m.rows[r.memory_ids[0]]["metadata"]["path"],"a.py")
 def test_drive_provenance(self):
  a=DriveAdapter().normalize("id1","Directive","build real things","doc");r=self.i.ingest(**a);self.assertEqual(self.m.rows[r.memory_ids[0]]["metadata"]["title"],"Directive")
 def test_task_outcome(self):
  a=TaskOutcomeAdapter().normalize({"id":"t1","title":"build","status":"DONE","lane":"jarvis","evidence":[{"ref":"x"}]});self.i.ingest(**a);self.assertIn("Evidence",next(iter(self.m.rows.values()))["text"])
 def test_unchanged_idempotent(self):
  a=GitHubAdapter().normalize("o/r","x","same");x=self.i.ingest(**a);y=self.i.ingest(**a);self.assertEqual(x.id,y.id);self.assertEqual(len(self.m.rows),1)
 def test_changed_reingests(self):
  self.i.ingest(**GitHubAdapter().normalize("o/r","x","v1"));self.i.ingest(**GitHubAdapter().normalize("o/r","x","v2"));self.assertEqual(len(self.i._manifest()),1);self.assertEqual(len(self.m.rows),2)
 def test_secret_redaction(self):
  self.i.ingest("drive","x","api_key=SUPERSECRET123456789");self.assertNotIn("SUPERSECRET",next(iter(self.m.rows.values()))["text"])
 def test_openai_secret_redaction(self):
  self.i.ingest("drive","x","sk-abcdefghijklmnopqrstuvwxyz123456");self.assertNotIn("sk-",next(iter(self.m.rows.values()))["text"])
 def test_chunking(self):self.assertGreater(len(self.i.ingest("drive","x","word "*1000).memory_ids),1)
 def test_manifest_restart(self):
  a=GitHubAdapter().normalize("o/r","x","same");x=self.i.ingest(**a);y=MemoryIngestor(self.m,self.d.name).ingest(**a);self.assertEqual(x.id,y.id)
 def test_hash_metadata(self):
  r=self.i.ingest("drive","x","abc");self.assertEqual(self.m.rows[r.memory_ids[0]]["metadata"]["content_hash"],r.content_hash)
if __name__=="__main__":unittest.main()
