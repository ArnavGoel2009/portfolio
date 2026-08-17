import json, sys, tempfile, unittest
from pathlib import Path
from jarvis_core import JarvisCore, Runner, SubprocessWorker

class SubprocessTests(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory(); self.c=JarvisCore(self.d.name)
    def tearDown(self): self.d.cleanup()
    def task(self): return self.c.add_task('execute native boundary','jarvis',9,8,9,3,capabilities=['python'])
    def worker_for_payload(self,payload):
        td=tempfile.TemporaryDirectory(); agent=Path(td.name)/'agent.py'
        agent.write_text("import json,os,sys\npayload=json.loads(sys.argv[2]);json.dump(payload,open(os.environ['JARVIS_RESULT_PATH'],'w'))")
        w=SubprocessWorker('cli',['python'],[sys.executable,str(agent),'{task_file}',json.dumps(payload)],allowed_executables=[Path(sys.executable).name],timeout=5)
        return td,w
    def test_end_to_end_subprocess(self):
        self.task()
        with tempfile.TemporaryDirectory() as td:
            agent=Path(td)/'agent.py'
            agent.write_text("import json,os,sys\nt=json.load(open(sys.argv[1]));json.dump({'ok':True,'evidence':[{'type':'execution','ref':'fixture:'+t['id']}],'limitations':['fixture'],'error':None},open(os.environ['JARVIS_RESULT_PATH'],'w'))")
            w=SubprocessWorker('cli',['python'],[sys.executable,str(agent),'{task_file}'],allowed_executables=[Path(sys.executable).name],timeout=5)
            self.assertEqual(Runner(self.c).run_once(w)['status'],'DONE')
    def test_missing_result_retries(self):
        self.task(); w=SubprocessWorker('noop',['python'],[sys.executable,'-c','pass','{task_file}'],allowed_executables=[Path(sys.executable).name],timeout=5)
        self.assertEqual(Runner(self.c).run_once(w)['status'],'RETRY')
    def test_nonzero_retries(self):
        self.task(); w=SubprocessWorker('boom',['python'],[sys.executable,'-c','import sys;sys.exit(7)','{task_file}'],allowed_executables=[Path(sys.executable).name],timeout=5)
        self.assertEqual(Runner(self.c).run_once(w)['status'],'RETRY')
    def test_executable_allowlist(self):
        w=SubprocessWorker('bad',[],['python','x'],allowed_executables=['node'])
        with self.assertRaises(PermissionError): w._argv('task.json')
    def test_string_evidence_fails_closed_without_stuck_claim(self):
        self.task(); td,w=self.worker_for_payload({'ok':True,'evidence':'not-a-list','limitations':[],'error':None})
        try:
            out=Runner(self.c).run_once(w)
            self.assertEqual(out['status'],'RETRY')
            self.assertEqual(self.c.snapshot()['counts']['CLAIMED'],0)
            self.assertEqual(self.c.snapshot()['counts']['READY'],1)
        finally: td.cleanup()
    def test_non_object_result_fails_closed(self):
        self.task(); td,w=self.worker_for_payload(['bad'])
        try:
            out=Runner(self.c).run_once(w)
            self.assertEqual(out['status'],'RETRY')
            self.assertEqual(self.c.snapshot()['counts']['CLAIMED'],0)
        finally: td.cleanup()
    def test_malformed_evidence_item_fails_closed(self):
        self.task(); td,w=self.worker_for_payload({'ok':True,'evidence':['bad'],'limitations':[],'error':None})
        try:
            out=Runner(self.c).run_once(w)
            self.assertEqual(out['status'],'RETRY')
            self.assertEqual(self.c.snapshot()['counts']['CLAIMED'],0)
        finally: td.cleanup()
    def test_result_size_limit(self):
        self.task()
        with tempfile.TemporaryDirectory() as td:
            agent=Path(td)/'agent.py'
            agent.write_text("import os\nopen(os.environ['JARVIS_RESULT_PATH'],'w').write('x'*200)")
            w=SubprocessWorker('cli',['python'],[sys.executable,str(agent),'{task_file}'],allowed_executables=[Path(sys.executable).name],timeout=5,max_result_bytes=100)
            self.assertEqual(Runner(self.c).run_once(w)['status'],'RETRY')
            self.assertEqual(self.c.snapshot()['counts']['CLAIMED'],0)

if __name__=='__main__': unittest.main()
