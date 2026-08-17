import io,json,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from jarvis_core.verify_cli import main

class VerifyCliTests(unittest.TestCase):
    def write(self,tasks,events):
        d=tempfile.TemporaryDirectory(); p=Path(d.name)
        (p/'tasks.json').write_text(json.dumps(tasks))
        (p/'audit.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
        return d,p
    def run_cli(self,p):
        out=io.StringIO()
        with redirect_stdout(out): code=main([str(p)])
        return code,json.loads(out.getvalue())
    def test_valid_state_exits_zero(self):
        task={'id':'1','status':'DONE','idempotency_key':'k','evidence':[{'type':'test','ref':'ok'}]}
        d,p=self.write([task],[{'ts':1,'event':'TASK_ADDED','task_id':'1'},{'ts':2,'event':'TASK_COMPLETED','task_id':'1'}])
        try:
            code,data=self.run_cli(p); self.assertEqual(code,0); self.assertTrue(data['ok'])
        finally:d.cleanup()
    def test_invalid_state_exits_two(self):
        task={'id':'1','status':'DONE','idempotency_key':'k','evidence':[]}
        d,p=self.write([task],[{'ts':1,'event':'TASK_COMPLETED','task_id':'1'}])
        try:
            code,data=self.run_cli(p); self.assertEqual(code,2); self.assertFalse(data['ok']); self.assertIn('DONE_WITHOUT_EVIDENCE:1',data['errors'])
        finally:d.cleanup()

if __name__=='__main__':unittest.main()
