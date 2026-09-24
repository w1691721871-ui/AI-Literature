"""Retrieve evidence chunks for the multi-paper research question Agent."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.services.database import SessionLocal, initialize_database
from app.services.embedding_service import generate_embedding
from app.services.rerank_service import keyword_coverage, rerank_chunks
from app.services.vector_store import VectorStore


class RetrievalService:
    """Use query embeddings and the local FAISS store to find paper evidence."""

    def __init__(self, session_factory=SessionLocal, vector_store: VectorStore | None = None) -> None:
        initialize_database()
        self._session_factory = session_factory
        self._vector_store = vector_store or VectorStore()

    def retrieve(
        self,
        question: str,
        paper_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, object]]:
        """Return top evidence chunks, optionally restricted to selected papers."""
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("请输入科研知识问题。")
        query_embedding = generate_embedding(normalized_question)
        selected_ids = {paper_id for paper_id in (paper_ids or []) if paper_id}

        # Search all local vectors when filtering so valid selected-paper chunks
        # are not lost simply because an unrelated paper ranked first.
        candidate_count = self._count_chunks() if selected_ids else max(10, top_k)
        ranked = self._vector_store.search_vectors(query_embedding, candidate_count)
        if not ranked:
            return []

        score_by_chunk_id = dict(ranked)
        session: Session = self._session_factory()
        try:
            rows = list(
                session.execute(
                    select(PaperChunk, Paper.title)
                    .join(Paper, PaperChunk.paper_id == Paper.paper_id)
                    .where(PaperChunk.id.in_(score_by_chunk_id))
                )
            )
        finally:
            session.close()

        result: list[dict[str, object]] = []
        for chunk, paper_title in rows:
            if selected_ids and chunk.paper_id not in selected_ids:
                continue
            result.append(
                {
                    "paper_id": chunk.paper_id,
                    "paper_title": paper_title,
                    "section": chunk.section_title,
                    "content": chunk.content,
                    "semantic_score": score_by_chunk_id[chunk.id],
                    "keyword_score": keyword_coverage(normalized_question, chunk.content),
                }
            )
        for item in result:
            # FAISS returns cosine similarity after normalization. Convert the
            # possible [-1, 1] range to [0, 1] before the hybrid blend.
            semantic_score = max(0.0, min(1.0, (float(item["semantic_score"]) + 1) / 2))
            item["hybrid_score"] = semantic_score * 0.7 + float(item["keyword_score"]) * 0.3
        result.sort(key=lambda item: float(item["hybrid_score"]), reverse=True)
        return rerank_chunks(normalized_question, result[:10], top_k=top_k)

    def _count_chunks(self) -> int:
        session: Session = self._session_factory()
        try:
            return len(list(session.scalars(select(PaperChunk.id))))
        finally:
            session.close()
