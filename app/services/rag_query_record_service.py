"""Persistence service for RAG question and report history."""

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.rag_query_record import RagQueryRecord
from app.services.database import SessionLocal, initialize_database


class RagQueryRecordNotFoundError(Exception):
    pass


class RagQueryRecordService:
    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def save(self, question: str, answer: str, sources: list[dict[str, object]], paper_ids: list[str], task_type: str) -> RagQueryRecord:
        record = RagQueryRecord(
            question=question,
            answer=answer,
            sources=json.dumps(sources, ensure_ascii=False),
            paper_ids=json.dumps(paper_ids, ensure_ascii=False),
            task_type=task_type,
        )
        session: Session = self._session_factory()
        try:
            session.add(record)
            session.commit()
            session.refresh(record)
            session.expunge(record)
            return record
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_questions(self) -> list[RagQueryRecord]:
        session: Session = self._session_factory()
        try:
            records = list(session.scalars(select(RagQueryRecord).where(RagQueryRecord.task_type != "report").order_by(RagQueryRecord.created_at.desc())))
            for record in records:
                session.expunge(record)
            return records
        finally:
            session.close()

    def get(self, record_id: str) -> tuple[RagQueryRecord, list[dict[str, object]], list[str]]:
        session: Session = self._session_factory()
        try:
            record = session.get(RagQueryRecord, record_id)
            if record is None:
                raise RagQueryRecordNotFoundError("历史知识问答不存在或已被删除。")
            sources = json.loads(record.sources)
            paper_ids = json.loads(record.paper_ids)
            if not isinstance(sources, list) or not isinstance(paper_ids, list):
                raise ValueError("历史知识问答格式异常，无法恢复。")
            session.expunge(record)
            return record, sources, paper_ids
        finally:
            session.close()

    def delete_for_paper(self, paper_id: str) -> None:
        """Delete records that reference a removed paper in their selected scope."""
        session: Session = self._session_factory()
        try:
            records = list(session.scalars(select(RagQueryRecord)))
            ids_to_delete = []
            for record in records:
                try:
                    selected_ids = json.loads(record.paper_ids)
                except json.JSONDecodeError:
                    selected_ids = []
                # An empty selected scope means the whole library.  In that
                # case, inspect the stored citations as well, so a record
                # cannot retain references to a paper that was deleted.
                try:
                    sources = json.loads(record.sources)
                except json.JSONDecodeError:
                    sources = []
                cited_paper_ids = {
                    str(source.get("paper_id"))
                    for source in sources
                    if isinstance(source, dict) and source.get("paper_id")
                }
                if paper_id in selected_ids or paper_id in cited_paper_ids:
                    ids_to_delete.append(record.id)
            if ids_to_delete:
                session.execute(delete(RagQueryRecord).where(RagQueryRecord.id.in_(ids_to_delete)))
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
