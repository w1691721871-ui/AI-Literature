"""Factual, privacy-bounded context memory built from existing workspace metadata."""

from __future__ import annotations

import json
import re
from collections import Counter

from sqlalchemy import select

from app.models.research_memory import ResearchMemory
from app.models.research_workspace import ResearchWorkspace
from app.services.database import SessionLocal, initialize_database


class ResearchGoalMemoryService:
    scope = "research_goal_context"

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._sessions = session_factory

    def refresh(self) -> dict[str, object]:
        session = self._sessions()
        try:
            workspaces = list(session.scalars(select(ResearchWorkspace).order_by(ResearchWorkspace.created_at.desc())).all())
            goals = [item.name for item in workspaces if item.name]
            data = {
                "research_direction": self._terms(goals),
                "preferred_output": "Evidence-grounded research deliverable draft",
                "frequent_tasks": self._frequent(goals),
                "workspace_history": [{"workspace_id": item.id, "title": item.name} for item in workspaces[:8]],
                "memory_boundary": "仅由 Workspace 标题、任务类型和交付偏好构成；不保存论文全文、隐私文件、Prompt 或内部推理。",
            }
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == self.scope))
            if record is None:
                record = ResearchMemory(scope=self.scope)
                session.add(record)
            record.memory_json = json.dumps(data, ensure_ascii=False)
            session.commit()
            return data
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self) -> dict[str, object]:
        session = self._sessions()
        try:
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == self.scope))
            if record is None:
                return self.refresh()
            try:
                value = json.loads(record.memory_json)
                return value if isinstance(value, dict) else self.refresh()
            except json.JSONDecodeError:
                return self.refresh()
        finally:
            session.close()

    @staticmethod
    def _terms(values: list[str]) -> list[str]:
        tokens = []
        for value in values:
            tokens.extend(part for part in re.split(r"[^\w\u4e00-\u9fff]+", value) if len(part) >= 2 and not part.isdigit())
        return [item for item, _ in Counter(tokens).most_common(8)]

    @staticmethod
    def _frequent(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))[:5]
