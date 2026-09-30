"""P16 top-level runtime that orchestrates the existing approval-first operator."""

from __future__ import annotations

from app.agent.research_computer_operator_pro import ResearchComputerOperatorPro
from app.tools.computer.code_intelligence_tool import CodeIntelligenceTool
from app.tools.computer.execution_sandbox import ExecutionSandbox
from app.tools.computer.workspace_explorer import WorkspaceExplorer


class ResearchComputerRuntimeAgent:
    """Builds public execution plans; mutations remain delegated to P15 approval gates."""
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self, operator: ResearchComputerOperatorPro | None = None, explorer: WorkspaceExplorer | None = None,
                 intelligence: CodeIntelligenceTool | None = None, sandbox: ExecutionSandbox | None = None) -> None:
        self.operator = operator or ResearchComputerOperatorPro()
        self.explorer = explorer or WorkspaceExplorer()
        self.intelligence = intelligence or CodeIntelligenceTool()
        self.sandbox = sandbox or ExecutionSandbox()

    def create(self, goal: str, mode: str = "supervised", workspace_id: str | None = None) -> dict[str, object]:
        task = self.operator.create_task(goal, mode, workspace_id)
        runtime_plan = self._plan(goal)
        self.operator.service.update_session(str(task["id"]), status="planning", plan=runtime_plan, artifact={"runtime": {"status": "PLANNING", "plan": runtime_plan}})
        self.operator._event(str(task["id"]), "Runtime Planner", "PLANNING", "COMPLETED", "已生成可审阅的 Computer Runtime 执行计划。", f"{len(runtime_plan)} 个步骤")
        return self.get(str(task["id"]))

    def execute(self, task_id: str) -> dict[str, object]:
        task = self.operator.service.get(task_id)
        goal = str(task["user_goal"])
        workspace = self.explorer.map()
        self.operator._event(task_id, "Workspace Explorer", "OBSERVING", "COMPLETED", "已完成项目结构观察。", str(workspace["workspace_map"].get("project_type")))
        if self._is_code(goal):
            insight = self.intelligence.analyze()
            self.operator._event(task_id, "Code Agent", "THINKING", "COMPLETED", "已完成静态代码理解。", f"Python：{insight['python_files']} · JS：{insight['javascript_files']}")
        outcome = self.operator.execute(task_id)
        artifact = dict(outcome.get("artifact", {})); artifact["runtime_workspace"] = workspace; outcome["artifact"] = artifact
        # The inner operator has already persisted status. This persists only metadata, never source text.
        self.operator.service.update_session(task_id, status=str(outcome["status"]), plan=list(outcome.get("plan", [])), artifact=artifact)
        return self.get(task_id)

    def approve(self, task_id: str, note: str) -> dict[str, object]:
        task = self.operator.service.get(task_id)
        action = next((item for item in task.get("actions", []) if item.get("status") == "PENDING_APPROVAL"), None)
        if not action:
            raise ValueError("当前没有等待批准的受控动作。")
        output = self.operator.approve(str(action["id"]), note)
        if action.get("action_type") == "apply_code_patch" and str(output.get("status")) == "completed":
            verification = self.sandbox.validate("compileall")
            self.operator._event(task_id, "Verification Agent", "VERIFYING", str(verification.get("status")), "已运行批准后的白名单代码验证。", str(verification.get("verification")))
            artifact = dict(output.get("artifact", {})); artifact["validation"] = verification
            self.operator.service.update_session(task_id, status="completed" if verification.get("verification") == "SUCCESS" else "failed", plan=list(output.get("plan", [])), artifact=artifact)
        return self.get(task_id)

    def retry(self, task_id: str) -> dict[str, object]:
        task = self.operator.service.get(task_id); artifact = dict(task.get("artifact", {})); attempts = int(artifact.get("recovery_attempts", 0))
        if attempts >= self.MAX_RECOVERY_ATTEMPTS:
            raise ValueError("已达到最多 3 次安全恢复尝试，等待人工处理。")
        if str(task.get("status")) not in {"failed", "insufficient_evidence"}:
            raise ValueError("当前任务未处于可恢复状态。")
        artifact["recovery_attempts"] = attempts + 1
        self.operator.service.update_session(task_id, status="recovering", plan=list(task.get("plan", [])), artifact=artifact)
        self.operator._event(task_id, "Recovery Agent", "RECOVERING", "RETRYING", "开始有限恢复尝试。", f"第 {attempts + 1}/3 次；不会绕过审批。")
        return self.execute(task_id)

    def get(self, task_id: str) -> dict[str, object]:
        task = self.operator.get(task_id)
        task["runtime_status"] = self._runtime_status(str(task.get("status", "planning")))
        task["events"] = self.timeline(task_id)
        task["artifacts"] = self.artifacts(task_id)
        return task

    def timeline(self, task_id: str) -> list[dict[str, object]]:
        return self.operator.events(task_id)

    def artifacts(self, task_id: str) -> list[dict[str, object]]:
        task = self.operator.get(task_id); artifact = dict(task.get("artifact", {})); items = []
        for patch in task.get("patches", []):
            items.append({"type": "Code Patch", "status": patch.get("status"), "path": patch.get("file_path"), "reference": patch.get("id")})
        for output in artifact.get("artifacts", []):
            items.append({"type": output.get("format", "Artifact"), "status": "Draft", "path": output.get("path"), "reference": output.get("path")})
        if artifact.get("evidence_refs"):
            items.append({"type": "Research Summary", "status": "Pending Review", "path": None, "reference": f"{len(artifact['evidence_refs'])} evidence references"})
        return items

    def _plan(self, goal: str) -> list[dict[str, object]]:
        code = self._is_code(goal); task = "代码结构与性能风险静态分析" if code else "授权环境与资料范围分析"
        steps = [
            ("observe", "扫描项目与授权工作区", "Workspace Explorer", "LOW", "Workspace Map", "环境元数据完整"),
            ("analyze", task, "Code Intelligence Tool" if code else "File System Analyzer", "LOW", "Code Insight Report" if code else "资料清单", "静态分析完成"),
            ("propose", "生成受控修改或交付建议", "Patch Generator" if code else "Document Tool", "MEDIUM", "Patch Proposal / Draft", "等待人工批准"),
            ("verify", "运行批准后的安全验证", "Execution Sandbox", "MEDIUM", "Validation Result", "白名单验证通过"),
        ]
        return [{"id": sid, "step": index, "step_name": name, "task_name": name, "purpose": "为达成用户目标提供可追踪依据。", "required_tool": tool, "risk_level": risk, "expected_output": output, "verification_method": check, "status": "pending"} for index, (sid, name, tool, risk, output, check) in enumerate(steps, 1)]

    @staticmethod
    def _is_code(goal: str) -> bool:
        text = goal.lower(); return any(word in text for word in ("代码", "code", "性能", "python", "fastapi", "vue", "ui", "前端"))

    @staticmethod
    def _runtime_status(status: str) -> str:
        return {"planning": "PLANNING", "waiting_approval": "WAITING_REVIEW", "completed": "COMPLETED", "failed": "FAILED", "recovering": "RECOVERING", "insufficient_evidence": "WAITING_EVIDENCE"}.get(status, status.upper())
