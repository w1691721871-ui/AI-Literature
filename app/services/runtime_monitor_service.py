"""Safe operational metrics for the deployment runtime."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.runtime_task import RuntimeTask
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import SessionLocal
from app.services.storage_service import StorageProvider


class RuntimeMonitor:
    def __init__(self, session_factory=SessionLocal, storage: StorageProvider | None = None):
        self._sessions = session_factory
        self._storage = storage or StorageProvider()

    def snapshot(self) -> dict[str, object]:
        session = self._sessions()
        try:
            tasks = session.scalars(select(RuntimeTask)).all()
            completed = [task.execution_time for task in tasks if task.execution_time is not None]
            return {
                "active_missions": sum(task.status == "RUNNING" for task in tasks),
                "running_agents": sum(task.status == "RUNNING" for task in tasks),
                "failed_tasks": sum(task.status == "FAILED" for task in tasks),
                "queue_length": sum(task.status == "QUEUED" for task in tasks),
                "retry_count": sum(task.retry_count for task in tasks),
                "average_duration": round(sum(completed) / len(completed), 3) if completed else 0.0,
                "worker_status": "READY",
                "services": self.health_components(session),
            }
        finally:
            session.close()

    def health_components(self, session=None) -> dict[str, dict[str, str]]:
        owns_session = session is None
        session = session or self._sessions()
        try:
            try:
                session.execute(select(func.count(Paper.paper_id))).scalar_one()
                database = {"status": "PASS", "detail": "Database reachable."}
                chunks = int(session.scalar(select(func.count(PaperChunk.id))) or 0)
                vector_store = {"status": "PASS" if chunks else "WARNING", "detail": "Indexed chunks available." if chunks else "No indexed chunks."}
            except Exception:
                database = {"status": "FAILED", "detail": "Database unavailable."}
                vector_store = {"status": "FAILED", "detail": "Vector index cannot be checked."}
            return {"database": database, "storage": self._storage.health(), "worker": {"status": "PASS", "detail": "Worker runtime ready."}, "vector_store": vector_store}
        finally:
            if owns_session:
                session.close()
