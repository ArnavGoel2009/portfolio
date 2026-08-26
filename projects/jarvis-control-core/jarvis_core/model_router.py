from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
import time

@dataclass(frozen=True)
class ModelProfile:
    name: str
    capabilities: frozenset[str]
    cost_per_million_input: float
    cost_per_million_output: float
    latency_ms: int
    quality: float
    context_tokens: int
    available: bool = True

@dataclass(frozen=True)
class RouteRequest:
    capabilities: frozenset[str]
    estimated_input_tokens: int
    estimated_output_tokens: int
    min_quality: float = 0.0
    max_latency_ms: int | None = None
    max_cost_usd: float | None = None
    required_context_tokens: int = 0

@dataclass(frozen=True)
class RouteDecision:
    model: str
    score: float
    estimated_cost_usd: float
    reason: str

class NoRoute(RuntimeError): pass

class ModelRouter:
    """Deterministic constraint-first model router."""
    def __init__(self, profiles: Iterable[ModelProfile], quality_weight=.60, cost_weight=.25, latency_weight=.15):
        self.profiles=list(profiles); self.qw=quality_weight; self.cw=cost_weight; self.lw=latency_weight
        if not self.profiles: raise ValueError("at least one profile required")
    @staticmethod
    def estimate_cost(p, r):
        return (r.estimated_input_tokens/1_000_000*p.cost_per_million_input + r.estimated_output_tokens/1_000_000*p.cost_per_million_output)
    def eligible(self,p,r):
        cost=self.estimate_cost(p,r)
        return (p.available and r.capabilities.issubset(p.capabilities) and p.quality >= r.min_quality and p.context_tokens >= r.required_context_tokens and (r.max_latency_ms is None or p.latency_ms <= r.max_latency_ms) and (r.max_cost_usd is None or cost <= r.max_cost_usd))
    def route(self,r):
        candidates=[p for p in self.profiles if self.eligible(p,r)]
        if not candidates: raise NoRoute("no model satisfies hard constraints")
        costs={p.name:self.estimate_cost(p,r) for p in candidates}; max_cost=max(costs.values()) or 1.0; max_latency=max(p.latency_ms for p in candidates) or 1
        ranked=[]
        for p in candidates:
            score=self.qw*p.quality-self.cw*(costs[p.name]/max_cost)-self.lw*(p.latency_ms/max_latency); ranked.append((score,p))
        score,p=max(ranked,key=lambda x:(x[0],x[1].quality,-costs[x[1].name],-x[1].latency_ms,x[1].name))
        return RouteDecision(p.name,round(score,6),round(costs[p.name],8),f"meets capabilities={sorted(r.capabilities)}, quality>={r.min_quality}, context>={r.required_context_tokens}")

class ProviderHealth:
    def __init__(self,failure_threshold=3,cooldown_seconds=60,clock=time.time): self.threshold=failure_threshold;self.cooldown=cooldown_seconds;self.clock=clock;self.state={}
    def success(self,name): self.state[name]={"failures":0,"open_until":0}
    def failure(self,name):
        s=self.state.setdefault(name,{"failures":0,"open_until":0});s["failures"]+=1
        if s["failures"]>=self.threshold:s["open_until"]=self.clock()+self.cooldown
    def available(self,name):
        s=self.state.get(name,{"failures":0,"open_until":0})
        if s["open_until"] and self.clock()>=s["open_until"]:self.success(name);return True
        return not s["open_until"]
    def apply(self,profiles): return [ModelProfile(**{**asdict(p),"available":p.available and self.available(p.name)}) for p in profiles]

class FallbackRouter:
    def __init__(self,profiles,health=None,**weights):self.profiles=list(profiles);self.health=health or ProviderHealth();self.weights=weights
    def route(self,request,exclude=frozenset()): return ModelRouter([p for p in self.health.apply(self.profiles) if p.name not in exclude],**self.weights).route(request)
    def report_failure(self,name):self.health.failure(name)
    def report_success(self,name):self.health.success(name)
