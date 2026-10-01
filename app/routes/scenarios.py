"""P37 Scenario Center APIs; runs delegate to the established Mission runtime."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.governance_service import GovernanceError, PermissionService
from app.services.scenario_demo_service import ScenarioDemoService, ScenarioError
router = APIRouter(prefix="/api", tags=["scenarios"]); service = ScenarioDemoService()
class ScenarioRunRequest(BaseModel):
    scenario_id: str = Field(min_length=1); workspace_id: str | None = None; user_id: str | None = None; policy: dict = Field(default_factory=dict)
@router.get("/scenarios")
def scenarios(): return service.list()
@router.post("/scenarios/run")
def run(payload: ScenarioRunRequest):
    try:
        permission = (lambda action: PermissionService().check(payload.workspace_id, payload.user_id, action)) if payload.workspace_id and payload.user_id else None
        return service.run(payload.scenario_id, permission_check=permission, policy=payload.policy or None)
    except GovernanceError as error: raise HTTPException(status_code=403, detail=str(error)) from error
    except ScenarioError as error: raise HTTPException(status_code=404, detail=str(error)) from error
@router.get("/scenarios/{scenario_id}")
def scenario(scenario_id: str):
    for item in service.list():
        if item["id"] == scenario_id: return item
    raise HTTPException(status_code=404, detail="Scenario not found.")
@router.get("/scenario-runs/{run_id}")
def scenario_run(run_id: str):
    try: return service.detail(run_id)
    except ScenarioError as error: raise HTTPException(status_code=404, detail=str(error)) from error
