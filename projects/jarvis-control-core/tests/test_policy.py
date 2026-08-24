import unittest
from jarvis_core.policy import *
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
class T(unittest.TestCase):
 def test_default_deny(self):
  self.assertEqual(PolicyEngine().evaluate(Action("codex","git","repo","read")).decision,Decision.DENY)
 def test_allow_read(self):
  e=PolicyEngine([Rule("*","git","repo","read",Decision.ALLOW,1)]);self.assertEqual(e.evaluate(Action("codex","git","repo","read")).decision,Decision.ALLOW)
 def test_specific_rule_beats_wildcard(self):
  e=PolicyEngine([Rule("*","git","*","*",Decision.ALLOW,1),Rule("codex","git","prod","delete",Decision.DENY,1)]);self.assertEqual(e.evaluate(Action("codex","git","prod","delete")).decision,Decision.DENY)
 def test_priority_beats_specificity(self):
  e=PolicyEngine([Rule("codex","git","prod","delete",Decision.DENY,1),Rule("*","git","*","*",Decision.ALLOW,10)]);self.assertEqual(e.evaluate(Action("codex","git","prod","delete")).decision,Decision.ALLOW)
 def test_high_risk_escalates(self):
  e=PolicyEngine([Rule("*","github","*","merge",Decision.ALLOW,1)]);self.assertEqual(e.evaluate(Action("claude","github","repo","merge","high")).decision,Decision.REQUIRE_APPROVAL)
 def test_approval_single_use(self):
  c=Clock();s=ApprovalTokenStore(c);a=Action("x","github","r","merge","high");s.grant("t",a);self.assertTrue(s.consume("t",a));self.assertFalse(s.consume("t",a))
 def test_approval_scoped(self):
  s=ApprovalTokenStore();a=Action("x","github","a","merge","high");b=Action("x","github","b","merge","high");s.grant("t",a);self.assertFalse(s.consume("t",b))
 def test_approval_expiry(self):
  c=Clock();s=ApprovalTokenStore(c);a=Action("x","github","a","merge","high");s.grant("t",a,5);c.t+=6;self.assertFalse(s.consume("t",a))
 def test_guard_blocks(self):
  g=GuardedTool(PolicyEngine(),ApprovalTokenStore(),lambda:"ran");self.assertTrue(g.call(Action("x","shell","host","exec"))["blocked"])
 def test_guard_executes_allowed(self):
  e=PolicyEngine([Rule("*","fs","workspace/*","read",Decision.ALLOW,1)]);g=GuardedTool(e,ApprovalTokenStore(),lambda x:x+1);self.assertEqual(g.call(Action("x","fs","workspace/a","read"),2)["result"],3)
 def test_guard_requires_valid_approval(self):
  e=PolicyEngine([Rule("*","github","repo","merge",Decision.ALLOW,1)]);s=ApprovalTokenStore();a=Action("x","github","repo","merge","high");g=GuardedTool(e,s,lambda:"merged");self.assertTrue(g.call(a)["approval_required"]);s.grant("ok",a);self.assertEqual(g.call(a,approval_token="ok")["result"],"merged")
if __name__=="__main__":unittest.main()
