"""Public AI Mission Center endpoints, isolated from research execution APIs."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.mission import AIMissionCreate, AIMissionReview, AIMissionRevision
from app.services.ai_mission_service import AIMissionNotFoundError, AIMissionService
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
from app.services.audit_service import AuditService
from app.services.mission_lifecycle_service import MissionLifecycleError, MissionLifecycleService
from app.services.mission_activity_service import MissionActivityService
from app.services.ai_worker_runtime import AIWorkerRuntime


router = APIRouter(prefix="/api", tags=["ai-missions"])
service = AIMissionService()
permissions = PermissionMiddleware()
audit = AuditService()
lifecycle = MissionLifecycleService()
activity = MissionActivityService()
ai_worker_runtime = AIWorkerRuntime()


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def create_mission(payload: AIMissionCreate, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_CREATE")
    mission=service.create({**payload.model_dump(), "workspace_id": context.workspace_id})
    audit.record_event(context.workspace_id,context.user_id,"MISSION_CREATED","Mission",mission["id"],mission["id"],"Mission created in current Workspace.")
    return mission


@router.post("/missions/{mission_id}/run")
def run_mission(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    audit.record_event(context.workspace_id,context.user_id,"MISSION_EXECUTED","Mission",mission_id,mission_id,"Unified AI Worker execution started.")
    try:
        result=ai_worker_runtime.execute(mission_id, actor=context)
        audit.record_event(context.workspace_id,context.user_id,"MISSION_EXECUTED","Mission",mission_id,mission_id,"Unified AI Worker reached its bounded Skill result.",result.get("status","SUCCESS"))
        return result
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/missions/{mission_id}/control")
def mission_control(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return lifecycle.snapshot(mission_id, context.workspace_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="Mission is not available in this Workspace.") from error


@router.post("/missions/{mission_id}/pause")
def pause_mission(mission_id: str, reason: str = "", context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    try:
        result = lifecycle.pause(mission_id, context.workspace_id, context.user_id, reason)
        audit.record_event(context.workspace_id, context.user_id, "MISSION_PAUSED", "Mission", mission_id, mission_id, "Mission paused by an authorized Workspace member.")
        return result
    except MissionLifecycleError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/resume")
def resume_mission(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    try:
        result = lifecycle.resume(mission_id, context.workspace_id, context.user_id)
        worker = ai_worker_runtime.resume(mission_id, actor=context)
        audit.record_event(context.workspace_id, context.user_id, "MISSION_RESUMED", "Mission", mission_id, mission_id, "Mission resumed within existing approval boundaries.")
        return {**result, "worker": worker}
    except MissionLifecycleError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/recover")
def recover_mission(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    try:
        result = lifecycle.recover(mission_id, context.workspace_id, context.user_id)
        audit.record_event(context.workspace_id, context.user_id, "MISSION_RECOVERY_REQUESTED", "Mission", mission_id, mission_id, "Bounded Mission recovery prepared for human review.")
        return result
    except MissionLifecycleError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/review")
def review_mission(mission_id: str, payload: AIMissionReview, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_APPROVE")
    try:
        return service.review(mission_id, payload.status, payload.review_comment)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/revise")
def revise_mission(mission_id: str, payload: AIMissionRevision, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    try:
        return service.revise(mission_id, payload.change_summary)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/missions/{mission_id}/delivery")
def mission_delivery(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    try:
        return service.delivery(mission_id)
    except (AIMissionNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/missions")
def list_missions(context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    permissions.require(context, "MISSION_VIEW")
    return service.list(context.workspace_id)


@router.get("/missions/dashboard")
def mission_dashboard(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_VIEW")
    return service.dashboard(context.workspace_id)


@router.get("/missions/{mission_id}")
def mission_detail(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return service.detail(mission_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/missions/{mission_id}/timeline")
def mission_timeline(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return service.timeline(mission_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/missions/{mission_id}/activity")
def mission_activity(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return activity.timeline(mission_id, context.workspace_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail="Mission is not available in this Workspace.") from error


@router.get("/notifications")
def list_notifications(context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    permissions.require(context, "MISSION_VIEW")
    return service.notifications()


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.require(context, "MISSION_VIEW")
    try:
        return service.mark_notification_read(notification_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
