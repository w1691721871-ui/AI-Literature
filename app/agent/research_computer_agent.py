"""Bounded execution coordinator for ResearchOS' Computer Execution Layer."""

from __future__ import annotations

from app.agent.research_computer_task_planner import ResearchComputerTaskPlanner
from app.services.research_operator_memory_service import ResearchOperatorMemoryService
from app.services.research_computer_service import ResearchComputerService
from app.tools.computer.browser_tool import BrowserTool
from app.tools.computer.document_tool import ComputerDocumentTool
from app.tools.computer.file_system_tool import FileSystemTool
from app.tools.computer.permission_manager import PermissionManager
from app.tools.computer.screen_reader import ScreenReader
from app.tools.computer.terminal_tool import TerminalTool
from app.tools.computer.research_skills import ResearchSkillRouter
from app.tools.knowledge_tool import KnowledgeTool


class ResearchComputerAgent:
    """Creates execution plans and never performs high-risk actions automatically."""

    def __init__(self, *, service: ResearchComputerService | None = None, file_tool: FileSystemTool | None = None, knowledge_tool: KnowledgeTool | None = None, document_tool: ComputerDocumentTool | None = None, browser_tool: BrowserTool | None = None, screen_reader: ScreenReader | None = None, terminal_tool: TerminalTool | None = None, permissions: PermissionManager | None = None, planner: ResearchComputerTaskPlanner | None = None, skills: ResearchSkillRouter | None = None, memory: ResearchOperatorMemoryService | None = None) -> None:
        self._service = service or ResearchComputerService()
        self._file = file_tool or FileSystemTool(); self._knowledge = knowledge_tool or KnowledgeTool()
        self._document = document_tool or ComputerDocumentTool(); self._browser = browser_tool or BrowserTool()
        self._screen = screen_reader or ScreenReader(); self._terminal = terminal_tool or TerminalTool(); self._permissions = permissions or PermissionManager()
        self._planner = planner or ResearchComputerTaskPlanner()
        self._skills = skills or ResearchSkillRouter()
        # Fixture agents frequently inject an in-memory task service.  In that
        # case do not let a test silently write the production SQLite memory.
        self._memory = memory if memory is not None else (ResearchOperatorMemoryService() if service is None else None)

    def tool_catalog(self) -> list[dict[str, str]]:
        tools = [
            {"name": self._screen.name, "description": self._screen.description, "mode": "privacy_safe_connector"},
            {"name": self._file.name, "description": self._file.description, "mode": "read_and_plan"},
            {"name": self._browser.name, "description": self._browser.description, "mode": "connector_only"},
            {"name": self._document.name, "description": self._document.description, "mode": "approval_gated_draft"},
            {"name": self._terminal.name, "description": self._terminal.description, "mode": "allow_list_only"},
        ]
        return tools + [{"name": item["name"], "description": item["description"], "mode": "skill"} for item in self._skills.catalog()]

    def preview_task(self, goal: str) -> dict[str, object]:
        """Return a plan only; this does not create a session or invoke tools."""
        return self._planner.preview(goal)

    def memory_snapshot(self) -> dict[str, object]:
        if self._memory is None:
            return {"recent_tasks": [], "memory_boundary": "当前为隔离执行环境，未读取或写入持久任务偏好。"}
        return self._memory.get()

    def create_task(self, goal: str, workspace_id: str | None = None, external_urls: list[str] | None = None) -> dict[str, object]:
        goal = goal.strip()
        if not goal: raise ValueError("请输入需要由 Computer Agent 处理的科研任务。")
        preview = self.preview_task(goal)
        task_type = str(preview["task_type"]); plan = list(preview["plan"])
        item = self._service.create_session(user_goal=goal, workspace_id=workspace_id, task_type=task_type, plan=plan); task_id = str(item["id"])
        if self._memory is not None:
            self._memory.record_plan(goal=goal, task_type=task_type, expected_output=str(preview["expected_output"]))
        inventory = self._file.scan(); self._record(task_id, "computer_file_system", "scan_workspace", {}, inventory, False); self._done(plan, "understand")
        self._done(plan, "scan_files")
        if task_type == "file_organization":
            plan_result = self._file.plan_organization(); permission = self._permissions.assess("move_files")
            self._record(task_id, "computer_file_system", "move_files", {"goal": goal}, plan_result, bool(permission["approval_required"]), str(permission["status"]))
            self._done(plan, "organize"); self._wait(plan, "approval")
            return self._service.update_session(task_id, status="waiting_approval", plan=plan, artifact={"type": "organization_plan", "status": "PENDING_APPROVAL", "plan": plan_result, "boundary": "未移动、复制或删除任何文件。"})
        if task_type == "browser_research":
            candidates = [self._browser.open_and_extract(url) for url in (external_urls or [])]
            request = self._browser.request(goal, "search") if not candidates else {
                "status": "external_candidate_review",
                "operation": "open_extract",
                "candidate_sources": [source for item in candidates for source in item.get("candidate_sources", [])],
                "boundary": "外部候选来源需人工核验；不会自动进入正式 Evidence 或知识库。",
            }
            permission = self._permissions.assess("download_source")
            self._record(task_id, self._browser.name, "download_source", {"topic": goal}, request, bool(permission["approval_required"]), str(permission["status"]))
            self._done(plan, "external_search"); self._done(plan, "source_review"); self._wait(plan, "approval")
            return self._service.update_session(task_id, status="waiting_approval", plan=plan, artifact={"type": "browser_research_request", "status": "PENDING_APPROVAL", "detail": request})
        sources = self._retrieve(goal); refs = self._refs(sources); self._record(task_id, "knowledge_retrieval", "retrieve_evidence", {"goal": goal}, {"source_count": len(refs), "evidence_boundary": "仅使用已有知识库来源。"}, False); self._done(plan, "retrieve")
        self._record(task_id, "paper_reading_skill", "organize_evidence", {"goal": goal}, {"source_count": len(refs), "message": "已按可追溯 Evidence 整理阅读范围；未生成无依据研究结论。"}, False); self._done(plan, "read")
        if not refs:
            self._wait(plan, "approval")
            return self._service.update_session(task_id, status="insufficient_evidence", plan=plan, artifact={"status": "INSUFFICIENT_EVIDENCE", "message": "当前没有可验证 Evidence，Computer Agent 不生成科研草稿。"})
        permission = self._permissions.assess("create_document")
        draft_request = {"document_type": self._document_type(task_type), "evidence_refs": refs, "human_review_required": True}
        self._record(task_id, self._document.name, "create_document", draft_request, {"message": "草稿生成已计划，等待人工批准后执行。"}, bool(permission["approval_required"]), str(permission["status"]))
        self._done(plan, "prepare"); self._wait(plan, "approval")
        return self._service.update_session(task_id, status="waiting_approval", plan=plan, artifact={"type": "evidence_grounded_document", "status": "PENDING_APPROVAL", "evidence_refs": refs, "message": "Evidence 已检索。批准后才会生成 Markdown/DOCX 草稿。"})

    def approve_action(self, action_id: str, reviewer_note: str) -> dict[str, object]:
        task, action = self._service.review_action(action_id, approved=True, reviewer_note=reviewer_note)
        # Approval is recorded first. Only document drafts are safely materialized afterwards.
        if action["action_type"] == "create_document":
            input_data = action["input_data"]; evidence_refs = input_data.get("evidence_refs", []) if isinstance(input_data, dict) else []
            artifact = self._document.create_draft(str(task["id"]), str(input_data.get("document_type", "technical_report")), str(task["user_goal"]), evidence_refs)
            plan = task["plan"]; self._done(plan, "prepare"); self._done(plan, "approval"); self._done(plan, "deliver")
            return self._service.update_session(str(task["id"]), status="completed" if artifact.get("status") != "INSUFFICIENT_EVIDENCE" else "insufficient_evidence", plan=plan, artifact=artifact)
        return task

    def reject_action(self, action_id: str, reviewer_note: str) -> dict[str, object]:
        task, _ = self._service.review_action(action_id, approved=False, reviewer_note=reviewer_note)
        return task
    def get(self, task_id: str) -> dict[str, object]: return self._service.get(task_id)
    def list(self) -> list[dict[str, object]]: return self._service.list()

    def _record(self, task_id, tool, action, input_data, result, approval_required, status="completed"):
        self._service.add_action(task_id, tool_name=tool, action_type=action, input_data=input_data, result=result, status=status, approval_required=approval_required)
    def _retrieve(self, goal):
        try: return list(self._knowledge.search(goal, top_k=6))
        except Exception: return []
    @staticmethod
    def _refs(sources):
        return [{"paper_id": item.get("paper_id"), "chunk_id": item.get("chunk_id") or item.get("id"), "paper_title": item.get("paper_title") or item.get("title") or "未命名资料", "section": item.get("section") or item.get("chapter") or "未标注章节", "score": item.get("score")} for item in sources if isinstance(item, dict) and (item.get("paper_id") or item.get("chunk_id") or item.get("id"))]
    @staticmethod
    def _done(plan, action):
        for step in plan:
            if step.get("id") == action or step.get("action") == action: step["status"] = "completed"
    @staticmethod
    def _wait(plan, action):
        for step in plan:
            if step.get("id") == action or step.get("action") == action: step["status"] = "waiting"
    @staticmethod
    def _document_type(task_type):
        return "experiment_plan" if task_type == "experiment_plan" else "research_proposal" if task_type == "research_proposal" else "literature_review"
