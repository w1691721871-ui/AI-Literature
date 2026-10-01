"""LLM-native runtime APIs. All plans are validated before existing execution."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from app.models.agent_trace import AgentTrace
from app.models.prompt_template import PromptTemplate
from app.services.agent_runtime_loop import AgentRuntimeLoop
from app.services.database import SessionLocal, initialize_database
from app.services.llm_gateway import LLMGateway
from app.services.governance_service import GovernanceService, PermissionService, GovernanceError

router=APIRouter(prefix="/api/llm-runtime",tags=["llm-runtime"])
loop=AgentRuntimeLoop()

class RuntimeExecute(BaseModel):
    policy: dict = Field(default_factory=dict)
    workspace_id: str | None = None
    user_id: str | None = None

@router.post("/missions/{mission_id}/execute")
def execute(mission_id:str,payload:RuntimeExecute):
    try:
        policy=payload.policy or None; permission=None
        if payload.workspace_id and payload.user_id:
            policy=GovernanceService().policy(payload.workspace_id)
            permission=lambda action: PermissionService().check(payload.workspace_id,payload.user_id,action)
        return loop.execute(mission_id,policy=policy,permission_check=permission)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error
    except GovernanceError as error: raise HTTPException(status_code=403,detail=str(error)) from error

@router.get("/missions/{mission_id}/observations")
def observations(mission_id:str): return loop.observations(mission_id)

@router.get("/dashboard")
def dashboard():
    initialize_database(); s=SessionLocal()
    try:
        traces=s.scalars(select(AgentTrace).where(AgentTrace.trigger=="LLM_RUNTIME")).all()
        latency=[x.latency for x in traces if x.latency is not None]
        return {"model":LLMGateway().configuration(),"requests":len(traces),"failures":sum(x.status in {"FAILED","BLOCKED"} for x in traces),"average_latency":round(sum(latency)/len(latency),3) if latency else 0.0,"boundary":"Dashboard contains invocation metadata only; prompts, responses, CoT and secrets are not stored."}
    finally:s.close()

@router.get("/prompt-templates")
def templates():
    initialize_database();s=SessionLocal()
    try:return [{"agent_type":x.agent_type,"version":x.version,"status":x.status,"schema_version":x.schema_version,"created_at":x.created_at} for x in s.scalars(select(PromptTemplate).order_by(PromptTemplate.created_at.desc())).all()]
    finally:s.close()
