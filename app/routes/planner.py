"""P26 planning, graph, registry and memory endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.agent_memory_service import AgentMemoryService
from app.services.agent_registry import AgentRegistry
from app.services.dynamic_planner_service import DynamicPlannerService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware

router=APIRouter(prefix="/api",tags=["dynamic-planner"])
planner=DynamicPlannerService(); memories=AgentMemoryService(); registry=AgentRegistry()
permissions=PermissionMiddleware()

class PlannerRequest(BaseModel):
    goal: str = Field(min_length=1,max_length=2000)
    mission_type: str = "RESEARCH"
    mission_id: str | None = None

@router.post("/planner/analyze")
def analyze(payload:PlannerRequest,context:IdentityContext=Depends(permissions.current)):
    if payload.mission_id:
        permissions.mission(context,payload.mission_id,"MISSION_VIEW")
    else:
        permissions.require(context,"MISSION_CREATE")
    try:return planner.analyze(payload.goal,payload.mission_type,payload.mission_id)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error

@router.get("/missions/{mission_id}/plan")
def mission_plan(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW")
    try:return planner.plan(mission_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-memory")
def agent_memory(context:IdentityContext=Depends(permissions.current)):
    # Legacy memory records pre-date workspace scoping, so never expose them
    # outside the existing administrator boundary.
    permissions.admin_console(context); return memories.list()

@router.post("/agent-memory/{memory_id}/delete")
def delete_memory(memory_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context)
    try:return memories.delete(memory_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-registry")
def agent_registry(context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context); return registry.list()
