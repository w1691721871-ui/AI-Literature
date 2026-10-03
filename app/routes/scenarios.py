"""P37 Scenario Center APIs; runs delegate to the established Mission runtime."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.governance_service import GovernanceError, PermissionService
from app.services.scenario_demo_service import ScenarioDemoService, ScenarioError
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
router = APIRouter(prefix="/api", tags=["scenarios"]); service = ScenarioDemoService(); permissions=PermissionMiddleware()
class ScenarioRunRequest(BaseModel):
    scenario_id: str = Field(min_length=1); workspace_id: str | None = None; user_id: str | None = None; policy: dict = Field(default_factory=dict)
@router.get("/scenarios")
def scenarios(context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"MISSION_VIEW"); return service.list()
@router.post("/scenarios/run")
def run(payload: ScenarioRunRequest,context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"MISSION_CREATE")
    try:
        permission = lambda action: PermissionService().check(context.workspace_id, context.user_id, action)
        return service.run(payload.scenario_id, workspace_id=context.workspace_id, permission_check=permission, policy=payload.policy or None)
    except GovernanceError as error: raise HTTPException(status_code=403, detail=str(error)) from error
    except ScenarioError as error: raise HTTPException(status_code=404, detail=str(error)) from error
@router.get("/scenarios/{scenario_id}")
def scenario(scenario_id: str,context:IdentityContext=Depends(permissions.current)):
    permissions.require(context,"MISSION_VIEW")
    for item in service.list():
        if item["id"] == scenario_id: return item
    raise HTTPException(status_code=404, detail="Scenario not found.")
@router.get("/scenario-runs/{run_id}")
def scenario_run(run_id: str,context:IdentityContext=Depends(permissions.current)):
    try:
        result=service.detail(run_id)
        permissions.mission(context,result["mission"]["id"],"MISSION_VIEW")
        return result
    except ScenarioError as error: raise HTTPException(status_code=404, detail=str(error)) from error
