"""Build a small, factual lab memory from local metadata and history.

This module is intentionally distinct from RAG: it records organization-level
context and counts, while document evidence remains in papers/chunks/FAISS.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from sqlalchemy import func, select

from app.models.autonomous_research_run import AutonomousResearchRun
from app.models.paper import Paper
from app.models.research_outcome import ResearchOutcome
from app.models.research_project import ResearchProject
from app.models.research_memory import ResearchMemory
from app.services.database import SessionLocal, initialize_database


class ResearchMemoryService:
    """Persist and retrieve a compact factual laboratory profile."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def refresh_lab_profile(self) -> dict[str, object]:
        session = self._session_factory()
        try:
            papers = list(session.scalars(select(Paper).order_by(Paper.upload_time.desc())))
            profile = {
                "scope": "lab_profile",
                "research_directions": self._directions_from_titles([paper.title for paper in papers]),
                "knowledge_assets": {
                    "papers": len(papers),
                    "ready_papers": sum(1 for paper in papers if paper.quality_status == "ready"),
                },
                "organization_context": {
                    "projects": session.scalar(select(func.count(ResearchProject.id))) or 0,
                    "outcomes": session.scalar(select(func.count(ResearchOutcome.id))) or 0,
                    "historical_agent_runs": session.scalar(select(func.count(AutonomousResearchRun.id))) or 0,
                },
                "memory_boundary": "长期记忆只保存实验室资料数量、标题推断方向和任务历史统计；不保存论文全文，也不替代知识库证据。",
            }
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == "lab_profile"))
            if record is None:
                record = ResearchMemory(scope="lab_profile")
                session.add(record)
            record.memory_json = json.dumps(profile, ensure_ascii=False)
            session.commit()
            return profile
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_lab_profile(self) -> dict[str, object]:
        session = self._session_factory()
        try:
            record = session.scalar(select(ResearchMemory).where(ResearchMemory.scope == "lab_profile"))
            if record is None:
                return self.refresh_lab_profile()
            try:
                return json.loads(record.memory_json)
            except json.JSONDecodeError:
                return self.refresh_lab_profile()
        finally:
            session.close()

    @staticmethod
    def _directions_from_titles(titles: list[str]) -> list[str]:
        """Return only title-derived terms; no semantic claims are fabricated."""
        terms: list[str] = []
        for title in titles:
            normalized = re.sub(r"[\W_]+", " ", title or "")
            terms.extend(part for part in normalized.split() if len(part) >= 2 and not part.isdigit())
        return [term for term, _count in Counter(terms).most_common(8)]
