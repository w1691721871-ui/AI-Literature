"""Independent persistence service for the research paper library."""

import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.analysis_record import AnalysisRecord
from app.models.paper_chunk import PaperChunk
from app.services.rag_query_record_service import RagQueryRecordService
from app.services.database import SessionLocal, initialize_database
from app.services.document_store import delete_pdf_file, save_pdf_file
from app.services.pdf_service import extract_pdf_text
from app.services.rag_index_service import RagIndexService


logger = logging.getLogger(__name__)


class LibraryPaperNotFoundError(Exception):
    """Raised when a requested persisted paper does not exist."""


class PaperLibraryService:
    """Store source PDFs and extracted text without depending on PaperAnalysisAgent."""

    def __init__(self, session_factory=SessionLocal) -> None:
        initialize_database()
        self._session_factory = session_factory

    def save_uploaded_paper(
        self,
        file_content: bytes,
        filename: str,
        document_type: str = "paper",
    ) -> Paper:
        """Extract text with the shared PDF service, then persist file and metadata."""
        paper_text = extract_pdf_text(file_content)
        paper_id = str(uuid4())
        stored_file_path = save_pdf_file(file_content, paper_id)
        paper = Paper(
            paper_id=paper_id,
            title=self._title_from_filename(filename),
            filename=filename or "untitled.pdf",
            file_path=stored_file_path,
            text_content=paper_text,
            analysis_status="parsed",
            document_type=document_type,
        )
        session: Session = self._session_factory()
        try:
            session.add(paper)
            session.commit()
            session.refresh(paper)
        except Exception:
            session.rollback()
            delete_pdf_file(stored_file_path)
            raise
        finally:
            session.close()

        # RAG indexing is an enhancement to the existing paper library. The
        # paper remains available to the original Agent if a vector request is
        # temporarily unavailable.
        rag_index_service = RagIndexService()
        try:
            rag_index_service.index_paper(paper_id)
        except Exception as error:
            logger.warning("Paper RAG indexing failed | type=%s", type(error).__name__)
            rag_index_service.mark_index_failed(paper_id)
        return self.get_paper(paper_id)

    def list_papers(self) -> list[Paper]:
        """Return persisted papers newest first for the future library API."""
        session: Session = self._session_factory()
        try:
            return list(
                session.scalars(select(Paper).order_by(Paper.upload_time.desc()))
            )
        finally:
            session.close()

    def get_paper(self, paper_id: str) -> Paper:
        """Return one persisted paper for internal services; callers control exposure."""
        session: Session = self._session_factory()
        try:
            paper = session.get(Paper, paper_id)
            if paper is None:
                raise LibraryPaperNotFoundError("论文不存在或已被删除。")
            session.expunge(paper)
            return paper
        finally:
            session.close()

    def delete_paper(self, paper_id: str) -> None:
        """Delete a persisted paper record and its corresponding stored PDF."""
        session: Session = self._session_factory()
        try:
            paper = session.get(Paper, paper_id)
            if paper is None:
                raise LibraryPaperNotFoundError("论文不存在或已被删除。")
            file_path = paper.file_path
            # Keep the local knowledge space consistent: reports cannot outlive
            # the paper they were created from.
            session.execute(
                delete(AnalysisRecord).where(AnalysisRecord.paper_id == paper_id)
            )
            session.execute(
                delete(PaperChunk).where(PaperChunk.paper_id == paper_id)
            )
            session.delete(paper)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        # RAG history records have multi-paper JSON scopes, so clean them via
        # their dedicated service after the paper deletion commits.
        RagQueryRecordService().delete_for_paper(paper_id)
        delete_pdf_file(file_path)
        try:
            RagIndexService().rebuild_index()
        except Exception as error:
            # The database and source file were already removed safely. Future
            # uploads rebuild the small local index again.
            logger.warning("RAG index rebuild after paper deletion failed | type=%s", type(error).__name__)

    @staticmethod
    def _title_from_filename(filename: str) -> str:
        """Use the filename stem until a later analysis step supplies a paper title."""
        title = Path(filename or "untitled.pdf").stem.strip()
        return title or "未命名论文"
