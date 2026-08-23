import tempfile, unittest
from pathlib import Path
from jarvis_core.evals import EvalCase, EvalSuite

class Tests(unittest.TestCase):
    def cases(self):
        return [
            EvalCase("evidence gate", "finish task", {"required_keys":["status","evidence"], "equals":{"status":"DONE"}, "min_evidence":1}),
            EvalCase("bounded plan", "plan work", {"required_keys":["steps"], "max_steps":4}),
        ]

    def test_all_pass(self):
        suite=EvalSuite(self.cases())
        def subject(obj):
            return {"status":"DONE","evidence":[{"type":"test","ref":"x"}],"steps":["inspect","build","test"]}
        summary=suite.summary(suite.run(subject))
        self.assertEqual(summary["pass_rate"],1.0)

    def test_missing_evidence_fails(self):
        suite=EvalSuite([self.cases()[0]])
        result=suite.run(lambda _: {"status":"DONE","evidence":[]})[0]
        self.assertFalse(result.passed); self.assertFalse(result.checks["min_evidence"])

    def test_wrong_status_fails(self):
        suite=EvalSuite([self.cases()[0]])
        result=suite.run(lambda _: {"status":"FAILED","evidence":[{"ref":"x"}]})[0]
        self.assertFalse(result.checks["equals:status"])

    def test_too_many_steps_fails(self):
        suite=EvalSuite([self.cases()[1]])
        result=suite.run(lambda _: {"steps":["1","2","3","4","5"]})[0]
        self.assertFalse(result.checks["max_steps"])

    def test_exception_is_failure(self):
        suite=EvalSuite([self.cases()[1]])
        def boom(_): raise RuntimeError("bad")
        result=suite.run(boom)[0]
        self.assertFalse(result.passed); self.assertIn("_exception",result.output)

    def test_forbidden_value(self):
        c=EvalCase("approval", "external action", {"forbidden":{"action":["AUTO_SEND"]}})
        self.assertFalse(EvalSuite([c]).run(lambda _: {"action":"AUTO_SEND"})[0].passed)

    def test_save_reproducible_artifact(self):
        suite=EvalSuite([self.cases()[1]])
        results=suite.run(lambda _: {"steps":["test"]})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"eval.json"; suite.save(results,p); self.assertTrue(p.exists()); self.assertIn('"passed": true',p.read_text())

if __name__=="__main__": unittest.main()
