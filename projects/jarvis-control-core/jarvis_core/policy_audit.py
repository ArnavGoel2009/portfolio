from __future__ import annotations

class AuditedGuardedTool:
    """Policy-gated tool wrapper that writes every decision to an AuditChain."""
    def __init__(self,engine,approvals,fn,audit_chain,tool_name):
        self.engine=engine;self.approvals=approvals;self.fn=fn;self.audit=audit_chain;self.tool_name=tool_name
    def call(self,action,*args,approval_token=None,**kwargs):
        verdict=self.engine.evaluate(action)
        base={"tool":self.tool_name,"capability":action.capability,"resource":action.resource,
              "operation":action.operation,"risk":action.risk,"decision":verdict.decision.value}
        if verdict.decision.value=="DENY":
            self.audit.append("TOOL_BLOCKED",action.actor,{**base,"reason":verdict.reason})
            return {"ok":False,"blocked":True,"reason":verdict.reason}
        if verdict.decision.value=="REQUIRE_APPROVAL":
            approved=bool(approval_token and self.approvals.consume(approval_token,action))
            if not approved:
                self.audit.append("APPROVAL_REQUIRED",action.actor,{**base,"reason":verdict.reason})
                return {"ok":False,"blocked":True,"approval_required":True,"reason":verdict.reason}
            self.audit.append("APPROVAL_CONSUMED",action.actor,base)
        try:
            result=self.fn(*args,**kwargs)
        except Exception as exc:
            self.audit.append("TOOL_FAILED",action.actor,{**base,"error":f"{type(exc).__name__}: {exc}"})
            raise
        self.audit.append("TOOL_EXECUTED",action.actor,base)
        return {"ok":True,"blocked":False,"result":result}
