"""Production-runtime APIs; Mission business APIs remain compatible."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.config_service import ConfigService
from app.services.runtime_monitor_service import RuntimeMonitor
from app.services.task_runtime_service import AgentWorker, TaskQueue
from app.services.ai_worker_runtime import AIWorkerRuntime
from app.services.ai_mission_service import AIMissionNotFoundError
from app.services.identity_service import IdentityContext
from app.services.permission_middleware import PermissionMiddleware
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])
queue = TaskQueue()
monitor = RuntimeMonitor()
ai_worker_runtime = AIWorkerRuntime()
permissions = PermissionMiddleware()
audit = AuditService()


class RuntimeTaskCreate(BaseModel):
    mission_id: str = Field(min_length=1, max_length=36)


@router.get("/missions/{mission_id}")
def worker_mission_runtime(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_VIEW")
    try:
        return ai_worker_runtime.snapshot(mission_id)
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/missions/{mission_id}/execute")
def execute_worker_mission_runtime(mission_id: str, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, mission_id, "MISSION_EXECUTE")
    audit.record_event(context.workspace_id,context.user_id,"MISSION_EXECUTED","Mission",mission_id,mission_id,"Unified runtime execution started.")
    try:
        result=ai_worker_runtime.execute(mission_id)
        audit.record_event(context.workspace_id,context.user_id,"MISSION_EXECUTED","Mission",mission_id,mission_id,"Unified runtime recorded a bounded Skill result.",result.get("status","SUCCESS"))
        return result
    except AIMissionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: RuntimeTaskCreate, context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.mission(context, payload.mission_id, "MISSION_EXECUTE")
    try:
        return queue.enqueue(payload.mission_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/tasks")
def list_tasks(context: IdentityContext = Depends(permissions.current)) -> list[dict[str, object]]:
    permissions.admin_console(context)
    return queue.list()


@router.post("/worker/run-once")
def run_worker_once(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.admin_console(context)
    task = AgentWorker().run_once()
    return {"status": "IDLE" if task is None else "PROCESSED", "task": task}


@router.get("/monitor")
def runtime_monitor(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.admin_console(context)
    return monitor.snapshot()


@router.get("/health")
def runtime_health(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.admin_console(context)
    return {"status": "ok", "components": monitor.health_components()}


@router.get("/config")
def runtime_config(context: IdentityContext = Depends(permissions.current)) -> dict[str, object]:
    permissions.admin_console(context)
    return ConfigService().summary()
