"""Allow-listed Research Worker tool execution only."""

from app.tools.research_worker.tool_router import ResearchWorkerToolRouter


class ResearchWorkerExecutor:
    def __init__(self, router: ResearchWorkerToolRouter) -> None:
        self._router = router

    def execute_file(self) -> dict[str, object]:
        return self._router.file_tool.execute()

    def execute_data(self) -> dict[str, object]:
        return self._router.data_tool.execute()

    def execute_knowledge(self, goal: str) -> dict[str, object]:
        return self._router.knowledge_tool.execute(goal)

    def execute_project(self, goal: str, evidence_count: int) -> dict[str, object]:
        return self._router.project_tool.execute(goal, evidence_count)

    def execute_document(self, run_id: str, content: str) -> dict[str, object]:
        return self._router.document_tool.execute(run_id, "Research Worker 科研执行交付物", content, generate_docx=True)
