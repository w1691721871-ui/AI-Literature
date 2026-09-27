"""Controlled wrapper around the existing RAG retrieval stack."""

from app.services.retrieval_service import RetrievalService


class KnowledgeTool:
    """Expose existing FAISS/RAG retrieval as a named Agent tool."""

    name = "knowledge_retrieval"

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval_service = retrieval_service or RetrievalService()

    def search(self, query: str, paper_ids: list[str] | None = None, top_k: int = 6) -> list[dict[str, object]]:
        return self._retrieval_service.retrieve(query, paper_ids, top_k=top_k)
