"""Deterministic validation between LLM planning and any system execution."""
from app.services.agent_registry import AgentRegistry

class PlanValidationError(ValueError): pass

class PlanValidator:
    allowed_tools={"KNOWLEDGE_CONNECTOR","FILE_CONNECTOR","DATABASE_CONNECTOR","COMPUTER_AGENT"}
    def __init__(self, registry=None): self.registry=registry or AgentRegistry()
    def validate(self, plan, *, policy=None, permission_check=None):
        if not isinstance(plan,dict): raise PlanValidationError("Plan must be a structured object.")
        agents=plan.get("agents",[]); tools=plan.get("tools",[]); steps=plan.get("steps",[]); risks=plan.get("risk_points",[])
        if not all(isinstance(x,str) and x in self.registry._agents for x in agents): raise PlanValidationError("Plan references an unregistered Agent.")
        if not all(isinstance(x,str) and x in self.allowed_tools for x in tools): raise PlanValidationError("Plan references a disallowed Tool.")
        if not steps or not all(isinstance(x,str) and len(x)<=200 for x in steps): raise PlanValidationError("Plan requires bounded, user-readable steps.")
        if not isinstance(risks,list) or not all(isinstance(x,str) and len(x)<=300 for x in risks): raise PlanValidationError("Plan risk points are invalid.")
        if policy:
            if len(steps)>min(int(policy.get("max_iterations",10)),10): raise PlanValidationError("Plan exceeds the configured iteration budget.")
            if len(tools)>int(policy.get("max_tool_calls",10)): raise PlanValidationError("Plan exceeds the configured tool-call budget.")
        if permission_check: permission_check("MISSION_CREATE")
        return {"valid":True,"agents":agents,"tools":tools,"steps":steps,"risk_points":risks}
