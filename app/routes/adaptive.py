"""P27 finite adaptive-run endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.adaptive_agent_service import AdaptiveAgentService
router=APIRouter(prefix="/api/missions",tags=["adaptive-agent"]); service=AdaptiveAgentService()
class AdaptiveReview(BaseModel): status:str
@router.post("/{mission_id}/adaptive-run")
def adaptive_run(mission_id:str):
    try:return service.run_once(mission_id)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error
@router.get("/{mission_id}/iterations")
def iterations(mission_id:str): return service.iterations(mission_id)
@router.get("/{mission_id}/graph-history")
def graph_history(mission_id:str): return service.graph_history(mission_id)
@router.post("/{mission_id}/adaptive-review")
def adaptive_review(mission_id:str,payload:AdaptiveReview):
    try:return service.review(mission_id,payload.status)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error
