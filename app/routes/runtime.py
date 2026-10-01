"""Production-runtime APIs; Mission business APIs remain compatible."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.config_service import ConfigService
from app.services.runtime_monitor_service import RuntimeMonitor
from app.services.task_runtime_service import AgentWorker, TaskQueue

router = APIRouter(prefix="/api/runtime", tags=["runtime"])
queue = TaskQueue()
monitor = RuntimeMonitor()


class RuntimeTaskCreate(BaseModel):
    mission_id: str = Field(min_length=1, max_length=36)


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: RuntimeTaskCreate) -> dict[str, object]:
    try:
        return queue.enqueue(payload.mission_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/tasks")
def list_tasks() -> list[dict[str, object]]:
    return queue.list()


@router.post("/worker/run-once")
def run_worker_once() -> dict[str, object]:
    task = AgentWorker().run_once()
    return {"status": "IDLE" if task is None else "PROCESSED", "task": task}


@router.get("/monitor")
def runtime_monitor() -> dict[str, object]:
    return monitor.snapshot()


@router.get("/health")
def runtime_health() -> dict[str, object]:
    return {"status": "ok", "components": monitor.health_components()}


@router.get("/config")
def runtime_config() -> dict[str, object]:
    return ConfigService().summary()
