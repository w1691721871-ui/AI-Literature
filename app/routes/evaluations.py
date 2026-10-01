"""Read-only P25 observability endpoints."""
from fastapi import APIRouter, HTTPException
from app.services.agent_evaluation_service import AgentEvaluationService

router=APIRouter(prefix="/api",tags=["agent-observability"])
service=AgentEvaluationService()

@router.get("/evaluations")
def evaluations():
    return service.evaluations()

@router.get("/evaluations/{mission_id}")
def evaluation(mission_id:str):
    try:return service.get(mission_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-metrics")
def agent_metrics(): return service.metrics()

@router.get("/adaptive-metrics")
def adaptive_metrics(): return service.adaptive_metrics()

@router.get("/agent-traces/{mission_id}")
def agent_traces(mission_id:str): return service.traces(mission_id)
