"""Finite LLM-plan runtime that delegates real work to existing Mission services."""
from __future__ import annotations
from sqlalchemy import select
from app.models.agent_observation import AgentObservation
from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission
from app.services.ai_mission_service import AIMissionService
from app.services.adaptive_agent_service import AdaptiveAgentService
from app.services.database import SessionLocal, initialize_database
from app.services.llm_gateway import LLMGateway
from app.services.plan_validation_service import PlanValidator, PlanValidationError
from app.services.tool_selector_service import ToolSelector

class AgentRuntimeLoop:
    MAX_ROUNDS=10
    def __init__(self, session_factory=SessionLocal, *, initialize=True, gateway=None, validator=None, selector=None, mission_service=None, adaptive_service=None):
        if initialize: initialize_database()
        self.s=session_factory; self.gateway=gateway or LLMGateway(); self.validator=validator or PlanValidator(); self.selector=selector or ToolSelector(); self.missions=mission_service or AIMissionService(session_factory,initialize=False); self.adaptive=adaptive_service or AdaptiveAgentService(session_factory,initialize=False)
    def execute(self, mission_id, *, policy=None, permission_check=None):
        session=self.s()
        try:
            mission=session.get(AIMission,mission_id)
            if not mission: raise ValueError("Mission does not exist.")
            goal=mission.goal or mission.title
        finally: session.close()
        raw,meta=self.gateway.generate_plan(goal,"RESEARCH",list(self.validator.registry._agents),list(self.validator.allowed_tools))
        source="LLM" if raw else "DETERMINISTIC_FALLBACK"
        if not raw:
            # This is a safe fallback plan, not a fabricated research result.
            raw={"goal":goal,"agents":["Research Agent","Literature Agent","Delivery Agent"],"tools":["KNOWLEDGE_CONNECTOR"],"steps":["Validate available evidence","Run existing evidence-bounded Mission","Route output to Human Review"],"risk_points":["Evidence may be insufficient; no unsupported conclusion may be produced."]}
        try: plan=self.validator.validate(raw,policy=policy,permission_check=permission_check)
        except PlanValidationError as error: return self._record(mission_id,"Runtime Plan","Plan rejected",False,f"Plan validation blocked execution: {error}",meta,0,"BLOCKED")
        tools=self.selector.select(plan["agents"],requested_tools=plan["tools"],policy=policy,permission_check=permission_check)
        self._record(mission_id,"Runtime Plan","Structured plan accepted",True,f"{source} plan accepted with {len(plan['steps'])} bounded steps and {len(tools)} approved tools.",meta,0,"PLANNING")
        # Existing Mission service remains the only component that performs RAG / delivery work.
        if len(plan["steps"]) > self.MAX_ROUNDS: return self._record(mission_id,"Runtime Loop","Budget reached",False,"Runtime budget exceeded; human review is required.",meta,0,"WAITING_REVIEW")
        try:
            result=self.missions.run(mission_id)
        except RuntimeError:
            # Existing Adaptive Loop owns finite recovery and graph versioning.
            recovery=self.adaptive.run_once(mission_id)
            self._record(mission_id,"Runtime Loop","Adaptive replan",False,recovery["summary"],meta,1,recovery["decision"])
            return {"mission_id":mission_id,"status":"WAITING_REVIEW" if recovery["decision"]=="REQUEST_REVIEW" else "REPLANNING","source":source,"plan":{**plan,"tools":tools},"recovery":recovery}
        status="WAITING_REVIEW" if result.get("status") in {"WAITING_REVIEW","WAITING_ADAPTIVE_REVIEW"} else "COMPLETED"
        return {"mission_id":mission_id,"status":status,"source":source,"plan":{**plan,"tools":tools},"result_status":result.get("status"),"observation":"Existing Mission execution completed; final decisions remain subject to Human Review."}
    def _record(self,mission_id,agent,action,success,summary,meta,iteration,status):
        session=self.s()
        try:
            session.add(AgentObservation(mission_id=mission_id,agent=agent,action=action,result_summary=summary,success=success))
            session.add(AgentTrace(trace_id=mission_id,mission_id=mission_id,step=action,message=summary,agent_name=agent,action=action,status=status,duration=float(meta.get("latency",0.0)),output_summary=summary,tool_used="LLM Gateway" if meta.get("status")=="SUCCESS" else "Deterministic Planner",iteration=iteration,decision=status,trigger="LLM_RUNTIME",model_name=str(meta.get("model","")),latency=float(meta.get("latency",0.0)),token_usage_summary=str(meta.get("token_usage_summary",""))))
            session.commit()
        finally: session.close()
        return {"mission_id":mission_id,"status":status,"summary":summary}
    def observations(self,mission_id):
        session=self.s()
        try:return [{"agent":x.agent,"action":x.action,"result_summary":x.result_summary,"success":x.success,"created_at":x.created_at} for x in session.scalars(select(AgentObservation).where(AgentObservation.mission_id==mission_id).order_by(AgentObservation.created_at)).all()]
        finally: session.close()
