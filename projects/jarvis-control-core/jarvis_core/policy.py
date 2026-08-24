from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import fnmatch, time

class Decision(str, Enum):
    ALLOW="ALLOW"
    DENY="DENY"
    REQUIRE_APPROVAL="REQUIRE_APPROVAL"

@dataclass(frozen=True)
class Action:
    actor:str
    capability:str
    resource:str
    operation:str
    risk:str="low"

@dataclass(frozen=True)
class Rule:
    actor:str="*"
    capability:str="*"
    resource:str="*"
    operation:str="*"
    decision:Decision=Decision.DENY
    priority:int=0

@dataclass(frozen=True)
class Verdict:
    decision:Decision
    rule:Rule|None
    reason:str

class PolicyEngine:
    """Deterministic, default-deny authorization boundary for JARVIS tools."""
    def __init__(self,rules=None,high_risk_requires_approval=True):
        self.rules=list(rules or [])
        self.high_risk_requires_approval=high_risk_requires_approval

    @staticmethod
    def _match(rule:Rule,a:Action)->bool:
        return all((
            fnmatch.fnmatchcase(a.actor,rule.actor),
            fnmatch.fnmatchcase(a.capability,rule.capability),
            fnmatch.fnmatchcase(a.resource,rule.resource),
            fnmatch.fnmatchcase(a.operation,rule.operation),
        ))

    def evaluate(self,a:Action)->Verdict:
        matches=[r for r in self.rules if self._match(r,a)]
        if not matches:
            return Verdict(Decision.DENY,None,"default deny: no matching rule")
        matches.sort(key=lambda r:(r.priority,
            sum(x!="*" for x in (r.actor,r.capability,r.resource,r.operation))),reverse=True)
        r=matches[0]
        if a.risk=="high" and self.high_risk_requires_approval and r.decision==Decision.ALLOW:
            return Verdict(Decision.REQUIRE_APPROVAL,r,"high-risk action requires human approval")
        return Verdict(r.decision,r,"matched policy rule")

class ApprovalTokenStore:
    """Single-use, scoped approval tokens with expiry."""
    def __init__(self,clock=time.time):
        self.clock=clock; self.tokens={}
    def grant(self,token,action:Action,ttl_seconds=900):
        if ttl_seconds<=0: raise ValueError("ttl_seconds must be positive")
        self.tokens[token]=(action,self.clock()+ttl_seconds,False)
    def consume(self,token,action:Action)->bool:
        row=self.tokens.get(token)
        if not row:return False
        expected,expiry,used=row
        if used or self.clock()>expiry or expected!=action:return False
        self.tokens[token]=(expected,expiry,True);return True

class GuardedTool:
    """Wraps any callable tool behind policy + optional human approval."""
    def __init__(self,engine:PolicyEngine,approvals:ApprovalTokenStore,fn):
        self.engine=engine;self.approvals=approvals;self.fn=fn
    def call(self,action:Action,*args,approval_token=None,**kwargs):
        v=self.engine.evaluate(action)
        if v.decision==Decision.DENY:
            return {"ok":False,"blocked":True,"reason":v.reason}
        if v.decision==Decision.REQUIRE_APPROVAL:
            if not approval_token or not self.approvals.consume(approval_token,action):
                return {"ok":False,"blocked":True,"approval_required":True,"reason":v.reason}
        return {"ok":True,"blocked":False,"result":self.fn(*args,**kwargs)}
