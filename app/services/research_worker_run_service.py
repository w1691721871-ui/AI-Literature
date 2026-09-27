"""SQLite persistence for bounded Research Worker state."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.research_worker_run import ResearchWorkerRun
from app.services.database import SessionLocal, initialize_database


class ResearchWorkerRunNotFoundError(Exception):
    pass


class ResearchWorkerRunService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def create(self, goal: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = ResearchWorkerRun(user_goal=goal, status="planning", current_step="正在理解任务并制定计划", current_phase="planning")
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._payload(record)
        finally:
            session.close()

    def update(self, run_id: str, *, status: str, current_step: str, current_phase: str, plan: list[dict[str, object]], selected_tools: list[dict[str, object]], tool_results: dict[str, object], reflection: dict[str, object], execution_history: list[dict[str, object]], output_file: str = "") -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = session.get(ResearchWorkerRun, run_id)
            if record is None:
                raise ResearchWorkerRunNotFoundError("Research Worker 执行记录不存在。")
            record.status = status
            record.current_step = current_step
            record.current_phase = current_phase
            record.plan = self._encode(plan)
            record.selected_tools = self._encode(selected_tools)
            record.tool_results = self._encode(tool_results)
            record.reflection = self._encode(reflection)
            record.execution_history = self._encode(execution_history)
            record.output_file = output_file
            session.commit()
            session.refresh(record)
            return self._payload(record)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, run_id: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = session.get(ResearchWorkerRun, run_id)
            if record is None:
                raise ResearchWorkerRunNotFoundError("Research Worker 执行记录不存在。")
            return self._payload(record)
        finally:
            session.close()

    @staticmethod
    def _encode(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _decode(value: str, fallback: object) -> object:
        try:
            return json.loads(value or "")
        except json.JSONDecodeError:
            return fallback

    def _payload(self, record: ResearchWorkerRun) -> dict[str, object]:
        return {
            "run_id": record.id, "user_goal": record.user_goal, "status": record.status,
            "current_step": record.current_step, "plan": self._decode(record.plan, []),
            "current_phase": record.current_phase,
            "tools": self._decode(record.selected_tools, []), "result": self._decode(record.tool_results, {}),
            "reflection": self._decode(record.reflection, {}), "output_file": record.output_file,
            "execution_history": self._decode(record.execution_history, []),
            "created_time": record.created_time, "updated_time": record.updated_time,
        }
