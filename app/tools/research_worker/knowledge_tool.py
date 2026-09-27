"""Research Worker adapter for the existing RAG retrieval stack."""

from app.tools.knowledge_tool import KnowledgeTool as ExistingKnowledgeTool
from app.tools.research_worker.base import Tool


class KnowledgeTool(Tool):
    name = "knowledge_tool"
    description = "复用现有 RAG、FAISS 和 Retriever 检索已索引论文证据。"

    def __init__(self, tool: ExistingKnowledgeTool | None = None) -> None:
        self._tool = tool or ExistingKnowledgeTool()

    def execute(self, goal: str) -> dict[str, object]:
        sources = self._tool.search(goal, top_k=5)
        return {"source_count": len(sources), "sources": sources}
