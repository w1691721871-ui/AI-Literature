"""Minimal metadata-only memory for Research Operator sessions.

The service reuses the existing ResearchMemory table.  It stores goal labels,
selected template types and artifact formats only; it never stores PDF text,
Evidence content, prompts or user-private workspace files.
"""

from __future__ import annotations

import json

from sqlalchemy import select

from app.models.research_memory import ResearchMemory
from app.services.database import SessionLocal, initialize_database


class ResearchOperatorMemoryService:
    scope = "research_operator_preferences"

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def record_plan(self, *, goal: str, task_type: str, expected_output: str) -> dict[str, object]:
        session = self._session_factory()
        try:
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == self.scope))
            if record is None:
                record = ResearchMemory(scope=self.scope)
                session.add(record)
            data = self._decode(record.memory_json)
            history = list(data.get("recent_tasks", []))
            history.insert(0, {"goal_summary": goal[:180], "task_type": task_type, "expected_output": expected_output})
            data["recent_tasks"] = history[:8]
            data["preferred_output"] = expected_output
            data["memory_boundary"] = "仅保存任务摘要、模板类型和输出偏好；不保存论文全文、Evidence 内容、Prompt 或内部推理。"
            record.memory_json = json.dumps(data, ensure_ascii=False)
            session.commit()
            return data
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self) -> dict[str, object]:
        session = self._session_factory()
        try:
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == self.scope))
            return self._decode(record.memory_json) if record else {"recent_tasks": [], "memory_boundary": "暂无任务偏好记录。"}
        finally:
            session.close()

    @staticmethod
    def _decode(value: str | None) -> dict[str, object]:
        try:
            loaded = json.loads(value or "{}")
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
