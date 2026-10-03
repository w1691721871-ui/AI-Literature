"""P24 public Computer Mission API; isolated from legacy Computer Use routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.computer_mission import ComputerMissionApproval, ComputerMissionCreate
from app.services.controlled_computer_mission_service import (
    ControlledComputerMissionNotFoundError,
    ControlledComputerMissionService,
)
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
from app.services.audit_service import AuditService


router = APIRouter(prefix="/api", tags=["computer-missions"])
service = ControlledComputerMissionService()
permissions = PermissionMiddleware()
audit = AuditService()


@router.post("/computer-missions", status_code=status.HTTP_201_CREATED)
def create_computer_mission(payload: ComputerMissionCreate, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    if not payload.mission_id:
        raise HTTPException(status_code=400, detail="Computer Skill requires a workspace-bound Mission.")
    permissions.mission(context, payload.mission_id, "COMPUTER_EXECUTE")
    return service.create(payload.model_dump())


@router.get("/computer-missions/{computer_mission_id}")
def get_computer_mission(computer_mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "MISSION_VIEW")
    try:
        return service.get(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/analyze")
def analyze_computer_mission(computer_mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "COMPUTER_EXECUTE")
    try:
        mission = service.analyze(computer_mission_id)
        action_plan = mission.get("action_plan", {}) if isinstance(mission.get("action_plan"), dict) else {}
        observation = action_plan.get("computer_observation", {}) if isinstance(action_plan.get("computer_observation"), dict) else {}
        environment = action_plan.get("environment_understanding", {}) if isinstance(action_plan.get("environment_understanding"), dict) else {}
        action = action_plan.get("controlled_action", {}) if isinstance(action_plan.get("controlled_action"), dict) else {}
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_OBSERVED", "ComputerMission", computer_mission_id, mission.get("mission_id"), "Read-only environment observation completed; vision mode is demo_only.")
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_ENVIRONMENT_ANALYZED", "ComputerMission", computer_mission_id, mission.get("mission_id"), str(environment.get("recommended_direction") or "Environment state analyzed."))
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_ACTION_PLANNED", "ComputerMission", computer_mission_id, mission.get("mission_id"), f"Controlled {action.get('action_type', 'VERIFY')} action planned.")
        if bool(action.get("requires_approval")) or mission.get("approval_status") == "PENDING":
            audit.record_event(context.workspace_id, context.user_id, "COMPUTER_APPROVAL_REQUIRED", "ComputerMission", computer_mission_id, mission.get("mission_id"), "Approval is required before any modifying Computer action.")
        return mission
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/computer-missions/{computer_mission_id}/diff")
def computer_mission_diff(computer_mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "MISSION_VIEW")
    try:
        mission = service.get(computer_mission_id)
        return {"status": mission["status"], "diff_content": mission["diff_content"], "approval_status": mission["approval_status"]}
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/approve")
def approve_computer_mission(computer_mission_id: str, payload: ComputerMissionApproval, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "MISSION_APPROVE")
    try:
        return service.approve(computer_mission_id, payload.decision, payload.note)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/computer-missions/{computer_mission_id}/execute")
def execute_computer_mission(computer_mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "COMPUTER_EXECUTE")
    try:
        mission = service.get(computer_mission_id)
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_EXECUTED", "ComputerMission", computer_mission_id, mission.get("mission_id"), "Controlled Computer Skill execution started.")
        result = service.execute(computer_mission_id)
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_EXECUTED", "ComputerMission", computer_mission_id, mission.get("mission_id"), "Controlled Computer Skill execution completed.", result.get("status", "SUCCESS"))
        verification = result.get("verification", {}) if isinstance(result.get("verification"), dict) else {}
        controlled = verification.get("controlled_verification", {}) if isinstance(verification.get("controlled_verification"), dict) else {}
        feedback = verification.get("environment_feedback", {}) if isinstance(verification.get("environment_feedback"), dict) else {}
        recovery = verification.get("recovery", {}) if isinstance(verification.get("recovery"), dict) else {}
        audit.record_event(context.workspace_id, context.user_id, "COMPUTER_VERIFIED", "ComputerMission", computer_mission_id, mission.get("mission_id"), str(controlled.get("summary") or "Controlled verification completed."), str(controlled.get("status") or result.get("status") or "NEEDS_REVIEW"))
        if feedback.get("status") == "RETRY":
            audit.record_event(context.workspace_id, context.user_id, "COMPUTER_ACTION_RETRY", "ComputerMission", computer_mission_id, mission.get("mission_id"), str(feedback.get("summary") or "A controlled retry was evaluated."))
        if recovery:
            audit.record_event(context.workspace_id, context.user_id, "COMPUTER_RECOVERY_STARTED", "ComputerMission", computer_mission_id, mission.get("mission_id"), str(recovery.get("summary") or "Controlled recovery was evaluated."), str(recovery.get("action") or "REQUEST_REVIEW"))
        return result
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/computer-missions/{computer_mission_id}/verification")
def computer_mission_verification(computer_mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.computer(context, computer_mission_id, "MISSION_VIEW")
    try:
        return service.verification(computer_mission_id)
    except ControlledComputerMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
