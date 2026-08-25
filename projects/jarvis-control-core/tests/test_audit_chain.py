import json,tempfile,unittest
from jarvis_core.audit_chain import *
from jarvis_core.policy_audit import AuditedGuardedTool
from jarvis_core.policy import Action,Rule,Decision,PolicyEngine,ApprovalTokenStore
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):self.t+=1;return self.t
class T(unittest.TestCase):
 def setUp(self):
  self.d=tempfile.TemporaryDirectory();self.c=Clock();self.a=AuditChain(self.d.name,self.c)
 def tearDown(self):self.d.cleanup()
 def test_clean_chain(self):
  self.a.append('TASK','codex',{'id':'1'});self.a.append('DONE','codex',{'id':'1'});self.assertTrue(self.a.verify().ok)
 def test_mutation_detected(self):
  self.a.append('TASK','codex',{'id':'1'});p=self.a.path;row=json.loads(p.read_text());row['data']['id']='2';p.write_text(json.dumps(row)+'\n');self.assertIn('HASH_MISMATCH:1',self.a.verify().errors)
 def test_reorder_detected(self):
  self.a.append('A','x',{});self.a.append('B','x',{});lines=self.a.path.read_text().splitlines();self.a.path.write_text('\n'.join(reversed(lines))+'\n');self.assertFalse(self.a.verify().ok)
 def test_middle_deletion_detected(self):
  for x in 'ABC':self.a.append(x,'x',{})
  lines=self.a.path.read_text().splitlines();self.a.path.write_text(lines[0]+'\n'+lines[2]+'\n');self.assertIn('PREV_HASH_MISMATCH:2',self.a.verify().errors)
 def test_checkpoint_detects_tail_truncation(self):
  key=b'secret';self.a.append('A','x',{});self.a.append('B','x',{});cp=self.a.checkpoint(key);lines=self.a.path.read_text().splitlines();self.a.path.write_text(lines[0]+'\n');self.assertIn('CHECKPOINT_HEAD_MISMATCH',self.a.verify(cp,key).errors)
 def test_checkpoint_mac_tamper(self):
  key=b'secret';self.a.append('A','x',{});cp=self.a.checkpoint(key);cp['mac']='0'*64;self.assertIn('CHECKPOINT_MAC_INVALID',self.a.verify(cp,key).errors)
 def test_denied_tool_is_audited(self):
  e=PolicyEngine();s=ApprovalTokenStore();g=AuditedGuardedTool(e,s,lambda:'ran',self.a,'shell');out=g.call(Action('codex','shell','host','exec'));self.assertTrue(out['blocked']);self.assertEqual(json.loads(self.a.path.read_text())['event'],'TOOL_BLOCKED')
 def test_approval_and_execution_are_both_audited(self):
  action=Action('codex','github','repo','merge','high');e=PolicyEngine([Rule('*','github','repo','merge',Decision.ALLOW,1)]);s=ApprovalTokenStore();s.grant('t',action);g=AuditedGuardedTool(e,s,lambda:'merged',self.a,'github');self.assertEqual(g.call(action,approval_token='t')['result'],'merged');events=[json.loads(x)['event'] for x in self.a.path.read_text().splitlines()];self.assertEqual(events,['APPROVAL_CONSUMED','TOOL_EXECUTED'])
 def test_failed_tool_is_audited(self):
  e=PolicyEngine([Rule('*','fs','*','read',Decision.ALLOW,1)]);s=ApprovalTokenStore();
  def boom():raise RuntimeError('x')
  g=AuditedGuardedTool(e,s,boom,self.a,'fs')
  with self.assertRaises(RuntimeError):g.call(Action('codex','fs','a','read'))
  self.assertEqual(json.loads(self.a.path.read_text())['event'],'TOOL_FAILED')
 def test_actor_change_tamper_detected(self):
  self.a.append('TOOL_EXECUTED','codex',{'tool':'git'});row=json.loads(self.a.path.read_text());row['actor']='claude';self.a.path.write_text(json.dumps(row)+'\n');self.assertFalse(self.a.verify().ok)
if __name__=='__main__':unittest.main()
