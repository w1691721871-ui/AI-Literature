"""Read-only P25 observability endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from app.services.agent_evaluation_service import AgentEvaluationService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware

router=APIRouter(prefix="/api",tags=["agent-observability"])
service=AgentEvaluationService()
permissions=PermissionMiddleware()

@router.get("/evaluations")
def evaluations(context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context)
    return service.evaluations()

@router.get("/evaluations/{mission_id}")
def evaluation(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW")
    try:return service.get(mission_id)
    except ValueError as error: raise HTTPException(status_code=404,detail=str(error)) from error

@router.get("/agent-metrics")
def agent_metrics(context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context); return service.metrics()

@router.get("/adaptive-metrics")
def adaptive_metrics(context:IdentityContext=Depends(permissions.current)):
    permissions.admin_console(context); return service.adaptive_metrics()

@router.get("/agent-traces/{mission_id}")
def agent_traces(mission_id:str,context:IdentityContext=Depends(permissions.current)):
    permissions.mission(context,mission_id,"MISSION_VIEW"); return service.traces(mission_id)
