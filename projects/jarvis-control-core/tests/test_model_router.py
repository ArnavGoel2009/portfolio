import unittest
from jarvis_core.model_router import *
def P(name,caps,ci,co,lat,q,ctx,available=True):return ModelProfile(name,frozenset(caps),ci,co,lat,q,ctx,available)
class Clock:
 def __init__(self):self.t=1000
 def __call__(self):return self.t
class T(unittest.TestCase):
 def setUp(self):self.ps=[P('fast',['chat','code'],.2,.4,100,.70,32000),P('strong',['chat','code','research'],3,15,800,.98,200000),P('mid',['chat','code','research'],1,4,350,.88,128000)]
 def req(self,**kw):
  d=dict(capabilities=frozenset(['code']),estimated_input_tokens=10000,estimated_output_tokens=2000);d.update(kw);return RouteRequest(**d)
 def test_capability_gate(self):self.assertNotEqual(ModelRouter(self.ps).route(self.req(capabilities=frozenset(['research']))).model,'fast')
 def test_quality_gate(self):self.assertEqual(ModelRouter(self.ps).route(self.req(min_quality=.95)).model,'strong')
 def test_latency_gate(self):self.assertEqual(ModelRouter(self.ps).route(self.req(max_latency_ms=150)).model,'fast')
 def test_context_gate(self):self.assertEqual(ModelRouter(self.ps).route(self.req(required_context_tokens=150000)).model,'strong')
 def test_cost_gate(self):self.assertEqual(ModelRouter(self.ps).route(self.req(max_cost_usd=.01)).model,'fast')
 def test_no_route(self):
  with self.assertRaises(NoRoute):ModelRouter(self.ps).route(self.req(min_quality=1.0))
 def test_cost_calculation(self):self.assertAlmostEqual(ModelRouter.estimate_cost(self.ps[0],self.req()),.0028)
 def test_circuit_breaker_opens(self):
  c=Clock();h=ProviderHealth(2,60,c);h.failure('strong');h.failure('strong');self.assertFalse(h.available('strong'))
 def test_circuit_breaker_recovers(self):
  c=Clock();h=ProviderHealth(1,60,c);h.failure('strong');c.t+=61;self.assertTrue(h.available('strong'))
 def test_fallback_after_failure(self):
  c=Clock();h=ProviderHealth(1,60,c);r=FallbackRouter(self.ps,h);a=r.route(self.req(min_quality=.85));r.report_failure(a.model);b=r.route(self.req(min_quality=.85));self.assertNotEqual(a.model,b.model)
 def test_unavailable_never_selected(self):self.assertEqual(ModelRouter([P('dead',['code'],0,0,1,1,999999,False),self.ps[0]]).route(self.req()).model,'fast')
 def test_deterministic(self):self.assertEqual(ModelRouter(self.ps).route(self.req()).model,ModelRouter(list(reversed(self.ps))).route(self.req()).model)
if __name__=='__main__':unittest.main()
