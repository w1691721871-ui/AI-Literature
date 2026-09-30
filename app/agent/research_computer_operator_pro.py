"""P14 controlled Computer Operator orchestration.

This layer extends the existing Computer Agent without replacing RAG, Evidence
or its approval boundary.  It executes only read-only operations automatically
and turns every mutation or code change into an explicit approval record.
"""

from __future__ import annotations

from app.agent.research_computer_task_planner import ResearchComputerTaskPlanner
from app.services.computer_environment_service import ComputerEnvironmentScanner
from app.services.computer_observation_service import ComputerObservationService
from app.services.computer_checkpoint_service import ComputerCheckpointService
from app.services.computer_action_executor import ComputerActionExecutor
from app.services.code_patch_service import CodePatchService
from app.services.research_computer_service import ResearchComputerService
from app.services.research_operator_memory_service import ResearchOperatorMemoryService
from app.tools.computer.browser_tool import BrowserTool
from app.tools.computer.code_tool import CodeAgentTool
from app.tools.computer.document_tool import ComputerDocumentTool
from app.tools.computer.file_system_tool import FileSystemTool
from app.tools.computer.permission_manager import PermissionManager
from app.tools.computer.pro_terminal_tool import ProSafeTerminalTool
from app.tools.knowledge_tool import KnowledgeTool


class ResearchComputerOperatorPro:
    """Finite, approval-first execution loop for research-computing tasks."""

    TEAM = (
        ("Planner Agent", "规划受控执行步骤"),
        ("Computer Agent", "扫描环境并协调已批准工具"),
        ("File Agent", "只读理解授权资料"),
        ("Code Agent", "静态分析并提出 Patch 建议"),
        ("Document Agent", "基于 Evidence 创建待审核草稿"),
        ("Reviewer Agent", "在高风险动作前等待人工确认"),
        ("Recovery Agent", "在可恢复错误后提供安全替代路径"),
    )

    def __init__(self, *, service: ResearchComputerService | None = None, planner: ResearchComputerTaskPlanner | None = None,
                 scanner: ComputerEnvironmentScanner | None = None, file_tool: FileSystemTool | None = None,
                 code_tool: CodeAgentTool | None = None, terminal: ProSafeTerminalTool | None = None,
                 knowledge: KnowledgeTool | None = None, document: ComputerDocumentTool | None = None,
                 browser: BrowserTool | None = None, permissions: PermissionManager | None = None,
                 memory: ResearchOperatorMemoryService | None = None, observation: ComputerObservationService | None = None,
                 checkpoints: ComputerCheckpointService | None = None, patches: CodePatchService | None = None,
                 executor: ComputerActionExecutor | None = None) -> None:
        self.service = service or ResearchComputerService()
        self.planner = planner or ResearchComputerTaskPlanner()
        self.scanner = scanner or ComputerEnvironmentScanner()
        self.file = file_tool or FileSystemTool()
        self.code = code_tool or CodeAgentTool()
        self.terminal = terminal or ProSafeTerminalTool()
        self.knowledge = knowledge or KnowledgeTool()
        self.document = document or ComputerDocumentTool()
        self.browser = browser or BrowserTool()
        self.permissions = permissions or PermissionManager()
        self.memory = memory or ResearchOperatorMemoryService()
        self.observation = observation or ComputerObservationService(self.scanner)
        self.checkpoints = checkpoints or ComputerCheckpointService()
        self.patches = patches or CodePatchService()
        self.executor = executor or ComputerActionExecutor(permissions=self.permissions, files=self.file, patches=self.patches)

    def catalog(self) -> dict[str, object]:
        return {
            "execution_modes": {
                "assist": "仅分析、生成计划和建议，不执行写入。",
                "supervised": "自动完成低风险只读操作；写入和高风险操作必须人工批准。",
                "research": "允许 Evidence 绑定草稿的受控准备；不删除数据、不提交代码、不发布内容。",
            },
            "tools": [
                {"name": "environment_scanner", "risk": "LOW", "description": "扫描授权目录与项目结构元数据。"},
                {"name": self.file.name, "risk": "LOW / HIGH", "description": "读取资料；文件移动、复制、删除始终需批准。"},
                {"name": self.code.name, "risk": "LOW / MEDIUM", "description": "静态分析代码；Patch 仅生成建议。"},
                {"name": "knowledge_retrieval", "risk": "LOW", "description": "复用已有 RAG，返回可追溯 Evidence。"},
                {"name": self.document.name, "risk": "MEDIUM", "description": "仅从 Evidence 生成待审核 Markdown/DOCX 草稿。"},
                {"name": self.terminal.name, "risk": "LOW", "description": "仅允许预定义验证命令。"},
                {"name": self.browser.name, "risk": "MEDIUM", "description": "外部来源仅作为人工核验候选。"},
            ],
            "memory_boundary": "仅保存任务摘要、输出格式和模板偏好；不保存密码、私密文件、论文全文、Prompt 或内部推理。",
        }

    def environment(self) -> dict[str, object]:
        # Keep P14's public environment endpoint compatible. P15 consumes the
        # richer observation envelope internally before every execution.
        return self.scanner.scan()

    def create_task(self, goal: str, mode: str = "assist", workspace_id: str | None = None, external_urls: list[str] | None = None) -> dict[str, object]:
        preview = self.planner.preview(goal)
        session = self.service.create_session(user_goal=preview["goal"], workspace_id=workspace_id, task_type=str(preview["task_type"]), plan=list(preview["plan"]))
        task_id = str(session["id"])
        self._event(task_id, "Planner Agent", "PLANNING", "COMPLETED", "已理解目标并生成受控执行计划。", f"{len(preview['plan'])} 个步骤；模式：{mode}")
        self.checkpoints.save(task_id, "planning", [], list(preview["plan"]), "ACTIVE")
        self.memory.record_plan(goal=str(preview["goal"]), task_type=str(preview["task_type"]), expected_output=str(preview["expected_output"]))
        return {**session, "execution_mode": mode, "external_urls": external_urls or [], "team": self._team(task_id), "events": self.service.events(task_id), "status": "planning"}

    def execute(self, task_id: str) -> dict[str, object]:
        task = self.service.get(task_id)
        plan = list(task.get("plan", [])); goal = str(task["user_goal"]); task_type = str(task["task_type"])
        try:
            self._event(task_id, "Computer Agent", "OBSERVING", "RUNNING", "正在扫描授权环境。")
            observation = self.observation.observe(); environment = observation["profile"]
            self._record(task_id, "environment_scanner", "scan_environment", {}, environment, False, "COMPLETED")
            self._done(plan, "scan_files")
            self._event(task_id, "Computer Agent", "OBSERVING", "COMPLETED", "已完成环境扫描。", self._environment_summary(environment))
            self.checkpoints.save(task_id, "observation", [{"action": "scan_environment", "status": "COMPLETED"}], [step for step in plan if step.get("status") != "completed"], "ACTIVE")

            if self._is_code_task(goal):
                return self._run_code(task, plan, environment)
            if task_type == "file_organization":
                return self._run_files(task, plan, environment)
            if task_type == "browser_research":
                return self._run_browser(task, plan, environment)
            return self._run_research(task, plan, environment)
        except Exception as error:  # Recovery is deliberately conservative.
            message = f"受控执行遇到 {type(error).__name__}，未继续执行写入操作。"
            self._event(task_id, "Recovery Agent", "RECOVERY", "RUNNING", "正在停止未批准操作并准备安全恢复。")
            self._event(task_id, "Recovery Agent", "RECOVERY", "FAILED", message, "建议核对授权目录、输入目标或工具配置后重新执行。")
            self.checkpoints.save(task_id, "recovery", [], [step for step in plan if step.get("status") != "completed"], "RECOVERY_REQUIRED")
            return self.service.update_session(task_id, status="failed", plan=plan, artifact={"status": "RECOVERY_FAILED", "message": message, "human_review_required": True})

    def approve(self, action_id: str, note: str) -> dict[str, object]:
        task, action = self.service.review_action(action_id, approved=True, reviewer_note=note)
        task_id = str(task["id"])
        self._event(task_id, "Reviewer Agent", "WAITING_APPROVAL", "APPROVED", "负责人已批准受控操作。")
        if action["action_type"] == "apply_code_patch":
            self._event(task_id, "Code Agent", "EXECUTING", "RUNNING", "正在应用已审核的代码 Patch。")
            result = self.executor.execute("apply_code_patch", dict(action.get("input_data", {})), approved=True)
            verified = str(result.get("verification", "FAILED")) == "SUCCESS"
            self._event(task_id, "Verifier Agent", "VERIFYING", "COMPLETED" if verified else "FAILED", "已完成 Patch 内容校验。" if verified else "Patch 校验失败，未继续其他写入。")
            self.checkpoints.save(task_id, "patch_verification", [{"action": "apply_code_patch", "status": result.get("status")}], [], "COMPLETED" if verified else "RECOVERY_REQUIRED")
            task = self.service.update_session(task_id, status="completed" if verified else "failed", plan=list(task["plan"]), artifact={**dict(task.get("artifact", {})), "patch_execution": result, "human_review_required": not verified})
        if action["action_type"] == "create_document":
            data = action.get("input_data", {})
            artifact = self.document.create_draft(task_id, str(data.get("document_type", "literature_review")), str(task["user_goal"]), list(data.get("evidence_refs", [])))
            plan = list(task["plan"]); self._done(plan, "prepare"); self._done(plan, "approval"); self._done(plan, "deliver")
            task = self.service.update_session(task_id, status="completed" if artifact.get("status") != "INSUFFICIENT_EVIDENCE" else "insufficient_evidence", plan=plan, artifact=artifact)
            self._event(task_id, "Document Agent", "COMPLETED", "COMPLETED", "已生成 Evidence 绑定的待审核草稿。", f"Evidence：{artifact.get('evidence_count', 0)}")
        return self._payload(task)

    def reject(self, action_id: str, note: str) -> dict[str, object]:
        task, _ = self.service.review_action(action_id, approved=False, reviewer_note=note)
        self._event(str(task["id"]), "Reviewer Agent", "WAITING_APPROVAL", "REJECTED", "负责人拒绝了受控操作；未执行写入或发布。")
        return self._payload(task)

    def get(self, task_id: str) -> dict[str, object]: return self._payload(self.service.get(task_id))
    def events(self, task_id: str) -> list[dict[str, object]]: return self.service.events(task_id)

    def _run_code(self, task, plan, environment):
        task_id = str(task["id"]); analysis = self.code.inspect(str(task["user_goal"]))
        self._record(task_id, self.code.name, "analyze_code", {"goal": task["user_goal"]}, analysis, False, "COMPLETED")
        self._done(plan, "understand")
        self._event(task_id, "Code Agent", "EXECUTING", "COMPLETED", "已完成代码结构静态分析。", f"扫描 {analysis['source_file_count']} 个源文件")
        patch = self.patches.propose_home_ui_focus(task_id)
        permission = self.permissions.assess("apply_code_patch")
        proposal = {"type": "code_optimization_plan", "analysis": analysis, "environment": environment, "code_patch": patch, "human_review_required": True}
        self._record(task_id, self.code.name, "apply_code_patch", {"patch_id": patch["id"], "file_path": patch["file_path"]}, {"message": "已生成可审阅 Diff；写入代码前必须人工确认。", "patch_id": patch["id"]}, True, str(permission["status"]))
        self._event(task_id, "Reviewer Agent", "WAITING_APPROVAL", "PENDING_APPROVAL", "代码修改建议等待人工确认。", "未写入 Patch")
        self.checkpoints.save(task_id, "waiting_patch_approval", [{"action": "analyze_code", "status": "COMPLETED"}], [{"action": "apply_code_patch", "patch_id": patch["id"], "status": "PENDING_APPROVAL"}], "WAITING_APPROVAL")
        return self._payload(self.service.update_session(task_id, status="waiting_approval", plan=plan, artifact=proposal))

    def _run_files(self, task, plan, environment):
        task_id = str(task["id"]); inventory = self.file.scan(); organization = self.file.plan_organization()
        self._record(task_id, self.file.name, "inspect_files", {}, inventory, False, "COMPLETED")
        permission = self.permissions.assess("move_files")
        self._record(task_id, self.file.name, "organize_files", {}, organization, True, str(permission["status"]))
        self._done(plan, "understand"); self._done(plan, "scan_files"); self._done(plan, "organize")
        self._event(task_id, "File Agent", "EXECUTING", "COMPLETED", "已完成论文资料清单与分类建议。", f"资料：{inventory.get('file_count', 0)}")
        self._event(task_id, "Reviewer Agent", "WAITING_APPROVAL", "PENDING_APPROVAL", "文件移动、复制或删除计划等待人工确认。", "未修改任何文件")
        artifact = {"type": "file_organization_plan", "environment": environment, "inventory": inventory, "plan": organization, "human_review_required": True}
        return self._payload(self.service.update_session(task_id, status="waiting_approval", plan=plan, artifact=artifact))

    def _run_browser(self, task, plan, environment):
        task_id = str(task["id"]); request = self.browser.request(str(task["user_goal"]))
        self._record(task_id, self.browser.name, "external_candidate_request", {}, request, True, "PENDING_APPROVAL")
        self._event(task_id, "Computer Agent", "WAITING_APPROVAL", "PENDING_APPROVAL", "外部来源候选需人工核验，未进入知识库或 Evidence。")
        return self._payload(self.service.update_session(task_id, status="waiting_approval", plan=plan, artifact={"type": "external_candidate_review", "environment": environment, "detail": request, "human_review_required": True}))

    def _run_research(self, task, plan, environment):
        task_id = str(task["id"]); goal = str(task["user_goal"])
        self._event(task_id, "File Agent", "EXECUTING", "COMPLETED", "已完成授权资料环境检查。")
        try: sources = list(self.knowledge.search(goal, top_k=6))
        except Exception: sources = []
        refs = self._refs(sources)
        self._record(task_id, "knowledge_retrieval", "retrieve_evidence", {"goal": goal}, {"evidence_count": len(refs)}, False, "COMPLETED")
        self._done(plan, "understand"); self._done(plan, "retrieve"); self._done(plan, "read")
        self._event(task_id, "Computer Agent", "OBSERVING", "COMPLETED", "已检查可追溯研究依据。", f"Evidence：{len(refs)}")
        if not refs:
            self._event(task_id, "Recovery Agent", "RECOVERY", "WAITING_EVIDENCE", "当前没有可验证资料，请上传科研文件或先建立知识库。", "未生成科研结论")
            return self._payload(self.service.update_session(task_id, status="insufficient_evidence", plan=plan, artifact={"status": "INSUFFICIENT_EVIDENCE", "environment": environment, "message": "当前没有可验证资料，请上传科研文件。", "human_review_required": True}))
        permission = self.permissions.assess("create_document")
        request = {"document_type": self._document_type(task["task_type"]), "evidence_refs": refs}
        self._record(task_id, self.document.name, "create_document", request, {"message": "Evidence 绑定草稿已准备，等待人工批准。"}, True, str(permission["status"]))
        self._done(plan, "prepare"); self._event(task_id, "Document Agent", "WAITING_APPROVAL", "PENDING_APPROVAL", "报告草稿等待人工确认。", f"Evidence：{len(refs)}")
        return self._payload(self.service.update_session(task_id, status="waiting_approval", plan=plan, artifact={"type": "evidence_grounded_document", "environment": environment, "evidence_refs": refs, "human_review_required": True}))

    def _payload(self, task: dict[str, object]) -> dict[str, object]:
        result = dict(task); task_id = str(task["id"]); result["events"] = self.service.events(task_id); result["team"] = self._team(task_id); result["checkpoint"] = self.checkpoints.get(task_id); result["patches"] = self.patches.list_for_task(task_id); return result
    def _team(self, task_id: str) -> list[dict[str, str]]:
        events = self.service.events(task_id); latest = {item["agent_name"]: item for item in events}
        return [{"name": name, "role": role, "status": str(latest.get(name, {}).get("status", "PENDING"))} for name, role in self.TEAM]
    def _event(self, task_id, agent, event_type, status, message, result_summary=""):
        return self.service.add_event(task_id, agent_name=agent, event_type=event_type, tool_name="", status=status, message=message, result_summary=result_summary)
    def _record(self, task_id, tool, action, input_data, result, approval, status):
        self.service.add_action(task_id, tool_name=tool, action_type=action, input_data=input_data, result=result, status=status, approval_required=approval)
    @staticmethod
    def _done(plan, action):
        for step in plan:
            if step.get("id") == action: step["status"] = "completed"
    @staticmethod
    def _is_code_task(goal: str) -> bool:
        text = goal.lower(); return any(word in text for word in ("代码", "code", "ui", "前端", "fastapi", "vue", "app.js", "styles.css"))
    @staticmethod
    def _refs(sources):
        return [{"paper_id": item.get("paper_id"), "chunk_id": item.get("chunk_id") or item.get("id"), "paper_title": item.get("paper_title") or item.get("title") or "未命名资料", "section": item.get("section") or item.get("chapter") or "未标注章节", "score": item.get("score")} for item in sources if isinstance(item, dict) and (item.get("paper_id") or item.get("chunk_id") or item.get("id"))]
    @staticmethod
    def _document_type(task_type): return "experiment_plan" if task_type == "experiment_plan" else "research_proposal" if task_type == "research_proposal" else "literature_review"
    @staticmethod
    def _environment_summary(environment):
        workspace = environment.get("workspace", {}) if isinstance(environment, dict) else {}
        return f"授权工作区文件：{workspace.get('file_count', 0)}；文档：{workspace.get('document_count', 0)}"
