"""P27 finite adaptive-run endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.adaptive_agent_service import AdaptiveAgentService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
router=APIRouter(prefix="/api/missions",tags=["adaptive-agent"]); service=AdaptiveAgentService()
permissions=PermissionMiddleware()
class AdaptiveReview(BaseModel): status:str
@router.post("/{mission_id}/adaptive-run")
def adaptive_run(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_EXECUTE")
    try:return service.run_once(mission_id)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error
@router.get("/{mission_id}/iterations")
def iterations(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW"); return service.iterations(mission_id)
@router.get("/{mission_id}/graph-history")
def graph_history(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW"); return service.graph_history(mission_id)
@router.post("/{mission_id}/adaptive-review")
def adaptive_review(mission_id:str,payload:AdaptiveReview,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_APPROVE")
    try:return service.review(mission_id,payload.status)
    except ValueError as error: raise HTTPException(status_code=400,detail=str(error)) from error
