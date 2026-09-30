"""P26 planning, graph, registry and memory endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.agent_memory_service import AgentMemoryService
from app.services.agent_registry import AgentRegistry
from app.services.dynamic_planner_service import DynamicPlannerService

router=APIRouter(prefix="/api",tags=["dynamic-planner"])
planner=DynamicPlannerService(); memories=AgentMemoryService(); registry=AgentRegistry()

class PlannerRequest(BaseModel):
    goal: str = Field(min_length=1,max_length=2000)
    mission_type: str = "RESEARCH"
    mission_id: str | None = None

@router.post("/planner/analyze")
def analyze(payload:PlannerRequest):
    try:return planner.analyze(payload.goal,payload.mission_type,payload.mission_id)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error

@router.get("/missions/{mission_id}/plan")
def mission_plan(mission_id:str):
    try:return planner.plan(mission_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-memory")
def agent_memory(): return memories.list()

@router.post("/agent-memory/{memory_id}/delete")
def delete_memory(memory_id:str):
    try:return memories.delete(memory_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-registry")
def agent_registry(): return registry.list()
