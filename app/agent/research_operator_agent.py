"""A bounded, evidence-first task execution layer for ResearchOS.

Research Operator is intentionally not computer control.  Its tools are an
allow-list and its plans stop for a human before an artifact becomes a final
deliverable or any file mutation is carried out.
"""

from __future__ import annotations

from typing import Protocol

from app.services.research_operator_service import ResearchOperatorService
from app.tools.browser_research_tool import BrowserResearchTool
from app.tools.code_execution_tool import CodeExecutionTool
from app.tools.document_generator import DocumentGenerator
from app.tools.file_operator import FileOperator
from app.tools.knowledge_import_tool import KnowledgeImportTool
from app.tools.knowledge_tool import KnowledgeTool
from app.tools.workspace_operator import WorkspaceOperator


class _KnowledgeSearch(Protocol):
    def search(self, query: str, paper_ids: list[str] | None = None, top_k: int = 6) -> list[dict[str, object]]: ...


class ResearchOperatorAgent:
    """Plan → controlled tools → reviewable draft, with no hidden reasoning."""

    def __init__(
        self,
        *,
        task_service: ResearchOperatorService | None = None,
        file_operator: FileOperator | None = None,
        document_generator: DocumentGenerator | None = None,
        knowledge_tool: _KnowledgeSearch | None = None,
        browser_tool: BrowserResearchTool | None = None,
        code_tool: CodeExecutionTool | None = None,
        import_tool: KnowledgeImportTool | None = None,
        workspace_tool: WorkspaceOperator | None = None,
    ) -> None:
        self._tasks = task_service or ResearchOperatorService()
        self._file = file_operator or FileOperator()
        self._document = document_generator or DocumentGenerator()
        self._knowledge = knowledge_tool or KnowledgeTool()
        self._browser = browser_tool or BrowserResearchTool()
        self._code = code_tool or CodeExecutionTool()
        self._import = import_tool or KnowledgeImportTool(self._file)
        self._workspace = workspace_tool or WorkspaceOperator(self._file)

    def tool_catalog(self) -> list[dict[str, str]]:
        return [
            {"name": self._file.name, "description": self._file.description, "permission": "read_only_or_approval_required"},
            {"name": self._workspace.name, "description": self._workspace.description, "permission": "read_only"},
            {"name": "knowledge_retrieval", "description": "Reuse the existing RAG retrieval service for traceable evidence.", "permission": "read_only"},
            {"name": self._document.name, "description": self._document.description, "permission": "draft_only"},
            {"name": self._browser.name, "description": self._browser.description, "permission": "connector_only"},
            {"name": self._code.name, "description": self._code.description, "permission": "allow_list_only"},
            {"name": self._import.name, "description": self._import.description, "permission": "approval_required"},
        ]

    def create_task(self, user_goal: str, workspace_id: str | None = None) -> dict[str, object]:
        goal = user_goal.strip()
        if not goal:
            raise ValueError("请输入需要由 Research Operator 执行的科研任务。")
        task_type = self._task_type(goal)
        plan = self._plan(goal, task_type)
        task = self._tasks.create(user_goal=goal, workspace_id=workspace_id, task_type=task_type, plan=plan)
        task_id = str(task["id"])
        tools: list[dict[str, object]] = []
        evidence_refs: list[dict[str, object]] = []
        artifact: dict[str, object] = {}
        try:
            workspace_profile = self._workspace.profile()
            tools.append(self._tool_event(self._workspace.name, "profile_workspace", workspace_profile))
            self._tasks.record_action(task_id, tool_name=self._workspace.name, action="profile_workspace", result=workspace_profile)
            inventory = self._file.inspect()
            tools.append(self._tool_event(self._file.name, "inspect_workspace", inventory))
            self._tasks.record_action(task_id, tool_name=self._file.name, action="inspect_workspace", result=inventory)
            self._complete(plan, "Inspect research workspace")

            if task_type == "file_organization":
                file_plan = self._file.organization_plan()
                tools.append(self._tool_event(self._file.name, "prepare_organization_plan", file_plan))
                self._tasks.record_action(task_id, tool_name=self._file.name, action="prepare_organization_plan", result=file_plan)
                self._complete(plan, "Prepare organization plan")
                artifact = {"type": "file_organization_plan", "status": "approval_required", "plan": file_plan, "human_review_required": True}
                self._wait(plan, "Human review")
                return self._tasks.update_execution(task_id, status="waiting_approval", plan=plan, tools=tools, evidence_refs=[], artifact=artifact, approval_status="pending")

            sources = self._retrieve(goal)
            evidence_refs = self._evidence_refs(sources)
            knowledge_result = {"source_count": len(evidence_refs), "status": "completed" if evidence_refs else "no_evidence"}
            tools.append(self._tool_event("knowledge_retrieval", "retrieve_evidence", knowledge_result))
            self._tasks.record_action(task_id, tool_name="knowledge_retrieval", action="retrieve_evidence", result=knowledge_result)
            self._complete(plan, "Retrieve evidence")

            if any(token in goal.lower() for token in ("2025", "最新", "latest", "web")):
                browser_result = self._browser.search(goal)
                tools.append(self._tool_event(self._browser.name, "request_connector", browser_result))
                self._tasks.record_action(task_id, tool_name=self._browser.name, action="request_connector", result=browser_result)

            if any(token in goal.lower() for token in ("csv", "xlsx", "数据", "dataset")):
                data_result = self._code.analyze()
                tools.append(self._tool_event(self._code.name, "inspect_dataset", data_result))
                self._tasks.record_action(task_id, tool_name=self._code.name, action="inspect_dataset", result=data_result)

            if task_type == "knowledge_import":
                import_plan = self._import.prepare()
                tools.append(self._tool_event(self._import.name, "prepare_import", import_plan))
                self._tasks.record_action(task_id, tool_name=self._import.name, action="prepare_import", result=import_plan)
                artifact = {"type": "knowledge_import_plan", "status": "approval_required", "plan": import_plan, "human_review_required": True}
                self._wait(plan, "Human review")
                return self._tasks.update_execution(task_id, status="waiting_approval", plan=plan, tools=tools, evidence_refs=evidence_refs, artifact=artifact, approval_status="pending")

            document_type = self._document_type(task_type)
            document = self._document.generate(task_id, document_type=document_type, objective=goal, evidence_refs=evidence_refs)
            tools.append(self._tool_event(self._document.name, "generate_draft", document))
            self._tasks.record_action(task_id, tool_name=self._document.name, action="generate_draft", result=document)
            if document.get("status") == "INSUFFICIENT_EVIDENCE":
                self._wait(plan, "Evidence required")
                return self._tasks.update_execution(task_id, status="insufficient_evidence", plan=plan, tools=tools, evidence_refs=[], artifact=document, approval_status="not_available")
            self._complete(plan, "Generate evidence-grounded draft")
            self._wait(plan, "Human review")
            return self._tasks.update_execution(task_id, status="waiting_approval", plan=plan, tools=tools, evidence_refs=evidence_refs, artifact=document, approval_status="pending")
        except Exception as error:
            failure = {"status": "failed", "message": "受控工具未完成任务，未生成科研结论。", "error_type": type(error).__name__}
            tools.append(self._tool_event("operator", "safe_failure", failure))
            self._tasks.record_action(task_id, tool_name="operator", action="safe_failure", result=failure)
            return self._tasks.update_execution(task_id, status="failed", plan=plan, tools=tools, evidence_refs=evidence_refs, artifact=failure, approval_status="not_available")

    def list_tasks(self) -> list[dict[str, object]]:
        return self._tasks.list()

    def get_task(self, task_id: str) -> dict[str, object]:
        return self._tasks.get(task_id)

    def approve(self, task_id: str, reviewer_note: str = "") -> dict[str, object]:
        return self._tasks.approve(task_id, reviewer_note)

    def reject(self, task_id: str, reviewer_note: str = "") -> dict[str, object]:
        return self._tasks.reject(task_id, reviewer_note)

    @staticmethod
    def _task_type(goal: str) -> str:
        normalized = goal.lower()
        if any(token in normalized for token in ("整理", "目录", "分类", "文件")):
            return "file_organization"
        if any(token in normalized for token in ("导入", "upload")):
            return "knowledge_import"
        if any(token in normalized for token in ("实验", "验证方案", "experiment")):
            return "experiment_plan"
        if any(token in normalized for token in ("申报", "proposal", "项目方案")):
            return "research_proposal"
        if any(token in normalized for token in ("综述", "review")):
            return "literature_review"
        if any(token in normalized for token in ("交付", "客户", "delivery")):
            return "customer_delivery_report"
        return "technical_report"

    @staticmethod
    def _plan(goal: str, task_type: str) -> list[dict[str, object]]:
        if task_type == "file_organization":
            steps = [("Inspect research workspace", "Workspace Operator", "Profile permitted workspace materials"), ("Prepare organization plan", "File Operator", "Create a proposed taxonomy without moving files"), ("Human review", "Human Approval", "Approve any future file mutation")]
        elif task_type == "knowledge_import":
            steps = [("Inspect research workspace", "Workspace Operator", "Profile permitted workspace materials"), ("Prepare import plan", "Knowledge Import Tool", "Route candidates to the formal upload flow"), ("Human review", "Human Approval", "Confirm any data import")]
        else:
            steps = [("Inspect research workspace", "Workspace Operator", "Profile permitted workspace materials"), ("Retrieve evidence", "Knowledge Core", "Reuse existing RAG evidence only"), ("Generate evidence-grounded draft", "Document Generator", "Create a reviewable draft without unsupported conclusions"), ("Human review", "Human Approval", "Approve or reject the draft")]
        return [{"step": index + 1, "action": action, "tool": tool, "purpose": purpose, "status": "pending", "goal_summary": goal[:180]} for index, (action, tool, purpose) in enumerate(steps)]

    def _retrieve(self, goal: str) -> list[dict[str, object]]:
        try:
            return list(self._knowledge.search(goal, top_k=6))
        except Exception:
            return []

    @staticmethod
    def _evidence_refs(sources: list[dict[str, object]]) -> list[dict[str, object]]:
        refs = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            paper_id = source.get("paper_id")
            chunk_id = source.get("chunk_id") or source.get("id")
            if not paper_id and not chunk_id:
                continue
            refs.append({"paper_id": paper_id, "chunk_id": chunk_id, "paper_title": source.get("paper_title") or source.get("title") or "未命名资料", "section": source.get("section") or source.get("chapter") or "未标注章节", "score": source.get("score")})
        return refs

    @staticmethod
    def _tool_event(name: str, action: str, result: dict[str, object]) -> dict[str, object]:
        return {"tool_name": name, "action": action, "status": result.get("status", "completed"), "result_summary": result.get("message") or f"已完成受控调用；可验证证据数：{result.get('source_count', result.get('evidence_count', 0))}", "approval_required": result.get("status") == "approval_required"}

    @staticmethod
    def _complete(plan: list[dict[str, object]], action: str) -> None:
        for step in plan:
            if step["action"] == action:
                step["status"] = "completed"

    @staticmethod
    def _wait(plan: list[dict[str, object]], action: str) -> None:
        for step in plan:
            if step["action"] == action:
                step["status"] = "waiting"

    @staticmethod
    def _document_type(task_type: str) -> str:
        return task_type if task_type in DocumentGenerator._titles else "technical_report"
