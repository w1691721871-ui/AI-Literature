"""Coordinate chunk persistence, embeddings, and full FAISS index rebuilds."""

import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.chunking_service import chunk_text
from app.services.database import SessionLocal, initialize_database
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import VectorStore


logger = logging.getLogger(__name__)


class RagIndexService:
    """Build a small local index by rebuilding it after each library mutation."""

    def __init__(self, session_factory=SessionLocal, vector_store: VectorStore | None = None) -> None:
        initialize_database()
        self._session_factory = session_factory
        self._vector_store = vector_store or VectorStore()

    def index_paper(self, paper_id: str) -> int:
        """Chunk and embed one saved paper, then rebuild the complete FAISS index."""
        session: Session = self._session_factory()
        try:
            paper = session.get(Paper, paper_id)
            if paper is None:
                raise ValueError("论文不存在，无法建立知识索引。")
            chunks = chunk_text(paper.text_content)
            if not chunks:
                raise ValueError("论文没有可用于知识检索的文本内容。")
            vectors = generate_embeddings([str(chunk["content"]) for chunk in chunks])
            if len(vectors) != len(chunks):
                raise ValueError("论文向量数量异常，无法建立知识索引。")
            session.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper_id))
            for chunk, vector in zip(chunks, vectors, strict=True):
                session.add(
                    PaperChunk(
                        paper_id=paper_id,
                        chunk_index=int(chunk["chunk_index"]),
                        section_title=str(chunk["section_title"]),
                        content=str(chunk["content"]),
                        embedding=json.dumps(vector),
                    )
                )
            paper.analysis_status = "indexed"
            paper.quality_status = "indexed"
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        self.rebuild_index()
        self._mark_ready(paper_id)
        return len(chunks)

    def _mark_ready(self, paper_id: str) -> None:
        """Mark a paper ready only after its vectors are persisted and searchable."""
        session: Session = self._session_factory()
        try:
            paper = session.get(Paper, paper_id)
            if paper is not None:
                paper.quality_status = "ready"
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def rebuild_index(self) -> None:
        """Build a fresh index from all chunk rows; small and safe for this MVP."""
        session: Session = self._session_factory()
        try:
            chunks = list(session.scalars(select(PaperChunk).order_by(PaperChunk.created_at, PaperChunk.chunk_index)))
            entries: list[tuple[str, list[float]]] = []
            for chunk in chunks:
                try:
                    vector = json.loads(chunk.embedding)
                except json.JSONDecodeError as error:
                    raise ValueError("论文片段向量格式异常，无法重建索引。") from error
                if not isinstance(vector, list) or not vector:
                    raise ValueError("论文片段向量格式异常，无法重建索引。")
                entries.append((chunk.id, [float(value) for value in vector]))
        finally:
            session.close()
        self._vector_store.remove_and_rebuild(entries)

    def mark_index_failed(self, paper_id: str) -> None:
        """Keep parsed material available when only the optional RAG index fails."""
        session: Session = self._session_factory()
        try:
            paper = session.get(Paper, paper_id)
            if paper is not None:
                paper.analysis_status = "failed"
                paper.quality_status = "failed"
                session.commit()
        except Exception:
            session.rollback()
            logger.exception("Unable to mark paper RAG indexing as failed")
        finally:
            session.close()
