"""Read-only evidence cards for the ResearchOS trust experience.

The service intentionally exposes only short chunk excerpts and source metadata.
It does not invent claims, run another model, or return complete source files.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import SessionLocal, initialize_database


class EvidenceCenterService:
    """Return factual knowledge-base evidence suitable for product display."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def list_evidence(self, limit: int = 24) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, 60))
        session: Session = self._session_factory()
        try:
            rows = list(
                session.execute(
                    select(PaperChunk, Paper.title, Paper.filename, Paper.document_type)
                    .join(Paper, PaperChunk.paper_id == Paper.paper_id)
                    .order_by(PaperChunk.created_at.desc())
                    .limit(safe_limit)
                )
            )
        finally:
            session.close()

        return [
            {
                "paper_id": chunk.paper_id,
                "source_file": filename or title,
                "paper_title": title,
                "document_type": document_type or "paper",
                "section": chunk.section_title or "正文",
                "content": self._excerpt(chunk.content),
                "related_agent": "Knowledge Agent",
                "basis": "已上传科研知识库片段",
            }
            for chunk, title, filename, document_type in rows
        ]

    @staticmethod
    def _excerpt(content: str) -> str:
        normalized = " ".join((content or "").split())
        return normalized[:500] + ("…" if len(normalized) > 500 else "")
