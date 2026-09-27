"""SQLite persistence for Research Brain run status and safe execution summaries."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.autonomous_research_run import AutonomousResearchRun
from app.services.database import SessionLocal, initialize_database


class AutonomousResearchRunNotFoundError(Exception):
    """Raised when a requested execution record cannot be found."""


class AutonomousResearchRunService:
    """Store user-facing plans, tools, reflections and final outputs only."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def create(self, goal: str) -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = AutonomousResearchRun(goal=goal, status="pending")
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._payload(record)
        finally:
            session.close()

    def update(self, run_id: str, *, status: str, task_plan: dict[str, object], execution_timeline: list[dict[str, object]], tool_results: dict[str, object], environment_profile: dict[str, object], memory_snapshot: dict[str, object], reflection: dict[str, object], final_output: dict[str, object], current_step: str, current_tool: str = "", completed_tasks: list[str] | None = None, next_plan: list[dict[str, object]] | None = None, failure_reason: str = "") -> dict[str, object]:
        session: Session = self._session_factory()
        try:
            record = session.get(AutonomousResearchRun, run_id)
            if record is None:
                raise AutonomousResearchRunNotFoundError("自主科研任务不存在。")
            record.status = status
            record.task_plan = self._encode(task_plan)
            record.execution_timeline = self._encode(execution_timeline)
            record.tool_results = self._encode(tool_results)
            record.environment_profile = self._encode(environment_profile)
            record.memory_snapshot = self._encode(memory_snapshot)
            record.reflection = self._encode(reflection)
            record.final_output = self._encode(final_output)
            record.current_step = current_step
            record.current_tool = current_tool
            record.completed_tasks = self._encode(completed_tasks or [])
            record.next_plan = self._encode(next_plan or [])
            record.failure_reason = failure_reason
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
            record = session.get(AutonomousResearchRun, run_id)
            if record is None:
                raise AutonomousResearchRunNotFoundError("自主科研任务不存在。")
            return self._payload(record)
        finally:
            session.close()

    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        session: Session = self._session_factory()
        try:
            records = list(session.scalars(select(AutonomousResearchRun).order_by(AutonomousResearchRun.updated_at.desc()).limit(max(1, min(limit, 50)))))
            return [self._payload(record) for record in records]
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

    def _payload(self, record: AutonomousResearchRun) -> dict[str, object]:
        return {
            "id": record.id,
            "goal": record.goal,
            "status": record.status,
            "task_plan": self._decode(record.task_plan, {}),
            "execution_timeline": self._decode(record.execution_timeline, []),
            "tool_results": self._decode(record.tool_results, {}),
            "environment_profile": self._decode(record.environment_profile, {}),
            "memory_snapshot": self._decode(record.memory_snapshot, {}),
            "reflection": self._decode(record.reflection, {}),
            "final_output": self._decode(record.final_output, {}),
            "current_step": record.current_step,
            "current_tool": record.current_tool,
            "completed_tasks": self._decode(record.completed_tasks, []),
            "next_plan": self._decode(record.next_plan, []),
            "failure_reason": record.failure_reason,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
