"""Bounded asynchronous-style Mission queue and worker runtime."""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select

from app.models.agent_trace import AgentTrace
from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.runtime_task import RuntimeTask
from app.services.ai_mission_service import AIMissionService
from app.services.config_service import ConfigService
from app.services.database import SessionLocal, initialize_database


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TaskQueue:
    def __init__(self, session_factory=SessionLocal, *, initialize: bool = True):
        if initialize:
            initialize_database()
        self._sessions = session_factory

    def enqueue(self, mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            if not session.get(AIMission, mission_id):
                raise ValueError("Mission does not exist.")
            existing = session.scalar(select(RuntimeTask).where(RuntimeTask.mission_id == mission_id, RuntimeTask.status.in_(("QUEUED", "RUNNING", "WAITING_REVIEW"))))
            if existing:
                return self._serialize(existing)
            task = RuntimeTask(mission_id=mission_id)
            session.add(task); session.commit(); session.refresh(task)
            return self._serialize(task)
        finally:
            session.close()

    def list(self) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            return [self._serialize(task) for task in session.scalars(select(RuntimeTask).order_by(RuntimeTask.created_at.desc())).all()]
        finally:
            session.close()

    @staticmethod
    def _serialize(task: RuntimeTask) -> dict[str, object]:
        return {"id": task.id, "mission_id": task.mission_id, "status": task.status, "retry_count": task.retry_count, "failure_reason": task.failure_reason, "worker_id": task.worker_id, "execution_time": task.execution_time, "created_at": task.created_at, "started_at": task.started_at, "completed_at": task.completed_at}


class AgentWorker:
    """Runs queued Missions under finite retry and human-review boundaries."""

    def __init__(self, session_factory=SessionLocal, *, mission_service=None, config: ConfigService | None = None, worker_id: str | None = None, initialize: bool = True):
        if initialize:
            initialize_database()
        self._sessions = session_factory
        self._missions = mission_service or AIMissionService(session_factory, initialize=False)
        self._config = config or ConfigService()
        self.worker_id = worker_id or f"agent-worker-{uuid4().hex[:8]}"

    def run_once(self) -> dict[str, object] | None:
        session = self._sessions()
        try:
            task = session.scalar(select(RuntimeTask).where(RuntimeTask.status == "QUEUED").order_by(RuntimeTask.created_at.asc()))
            if not task:
                return None
            task.status, task.worker_id, task.started_at = "RUNNING", self.worker_id, _now()
            session.commit(); task_id, mission_id = task.id, task.mission_id
        finally:
            session.close()
        start = perf_counter()
        try:
            outcome = self._missions.run(mission_id)
            terminal = "WAITING_REVIEW" if outcome.get("status") in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW"} else "SUCCESS"
            return self._complete(task_id, terminal, perf_counter() - start, "")
        except Exception as error:
            return self._recover(task_id, perf_counter() - start, str(error))

    def _complete(self, task_id: str, status: str, duration: float, failure_reason: str) -> dict[str, object]:
        session = self._sessions()
        try:
            task = session.get(RuntimeTask, task_id)
            task.status, task.execution_time, task.failure_reason, task.completed_at = status, round(duration, 3), failure_reason, _now()
            session.add(AgentTrace(trace_id=task.mission_id, mission_id=task.mission_id, step="Runtime Worker", message="Mission executed by controlled runtime.", agent_name="Agent Worker", action="Mission execution", status=status, duration=task.execution_time, output_summary="Runtime execution completed; review remains human-controlled.", tool_used=f"Worker:{task.worker_id}", iteration=task.retry_count, decision=status))
            session.commit(); session.refresh(task)
            return TaskQueue._serialize(task)
        finally:
            session.close()

    def _recover(self, task_id: str, duration: float, reason: str) -> dict[str, object]:
        session = self._sessions()
        try:
            task = session.get(RuntimeTask, task_id); max_retries = self._config.load().max_retries
            task.execution_time, task.failure_reason = round(duration, 3), "Runtime execution failed; details are available to an authorized reviewer."
            task.retry_count += 1
            if task.retry_count >= max_retries:
                task.status, task.completed_at = "WAITING_REVIEW", _now()
                mission = session.get(AIMission, task.mission_id)
                if mission:
                    mission.status = "WAITING_REVIEW"
                    session.add(AIMissionEvent(mission_id=mission.id, stage="Runtime Recovery", action="Retry limit reached", status="WAITING_REVIEW", evidence_count=0, result_summary="Runtime retries are exhausted; human review is required."))
            else:
                task.status = "QUEUED"
            session.commit(); session.refresh(task)
            return TaskQueue._serialize(task)
        finally:
            session.close()
