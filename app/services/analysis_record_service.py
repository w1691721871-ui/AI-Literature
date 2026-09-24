"""Persistence service for report history in the research workspace."""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis_record import AnalysisRecord
from app.models.paper import Paper
from app.services.database import SessionLocal, initialize_database


class AnalysisRecordNotFoundError(Exception):
    """Raised when a requested saved report does not exist."""


class AnalysisRecordService:
    """Save and load structured Agent reports without storing PDF content again."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def save_analysis_record(
        self,
        *,
        paper_id: str,
        task: str,
        scenario: str,
        role: str,
        analysis_result: dict[str, object],
        source_type: str = "library",
    ) -> AnalysisRecord:
        """Serialize one existing Agent response as JSON for later viewing."""
        record = AnalysisRecord(
            paper_id=paper_id,
            task=task,
            scenario=scenario,
            role=role,
            source_type=source_type,
            analysis_result=json.dumps(analysis_result, ensure_ascii=False, default=str),
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

    def list_analysis_records(self) -> list[tuple[AnalysisRecord, str]]:
        """Return report metadata with paper titles, newest first."""
        session: Session = self._session_factory()
        try:
            rows = list(
                session.execute(
                    select(AnalysisRecord, Paper.title)
                    .join(Paper, AnalysisRecord.paper_id == Paper.paper_id)
                    .order_by(AnalysisRecord.created_at.desc())
                )
            )
            for record, _title in rows:
                session.expunge(record)
            return rows
        finally:
            session.close()

    def get_analysis_record(self, record_id: str) -> tuple[AnalysisRecord, str, dict[str, object]]:
        """Restore the original Agent response from its stored JSON string."""
        session: Session = self._session_factory()
        try:
            row = session.execute(
                select(AnalysisRecord, Paper.title)
                .join(Paper, AnalysisRecord.paper_id == Paper.paper_id)
                .where(AnalysisRecord.id == record_id)
            ).one_or_none()
            if row is None:
                raise AnalysisRecordNotFoundError("研究报告不存在或已被删除。")
            record, paper_title = row
            try:
                result = json.loads(record.analysis_result)
            except json.JSONDecodeError as error:
                raise ValueError("保存的分析结果格式异常，无法恢复报告。") from error
            if not isinstance(result, dict):
                raise ValueError("保存的分析结果格式异常，无法恢复报告。")
            session.expunge(record)
            return record, paper_title, result
        finally:
            session.close()

    def get_overview(self) -> dict[str, int | datetime | None]:
        """Return small workspace counters without exposing paper text."""
        session: Session = self._session_factory()
        try:
            paper_count = session.scalar(select(func.count(Paper.paper_id))) or 0
            parsed_count = session.scalar(
                select(func.count(Paper.paper_id)).where(Paper.analysis_status == "parsed")
            ) or 0
            analysis_count = session.scalar(select(func.count(AnalysisRecord.id))) or 0
            last_analysis_time = session.scalar(select(func.max(AnalysisRecord.created_at)))
            return {
                "paper_count": paper_count,
                "parsed_count": parsed_count,
                "analysis_count": analysis_count,
                "last_analysis_time": last_analysis_time,
            }
        finally:
            session.close()
