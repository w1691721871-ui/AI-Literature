"""P17 bounded autonomous engineering loop over the existing P16 Runtime Agent."""

from __future__ import annotations

from app.agent.research_computer_runtime_agent import ResearchComputerRuntimeAgent
from app.services.autonomous_computer_service import AutonomousComputerService
from app.tools.computer.execution_sandbox import ExecutionSandbox
from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class ResearchAutonomousComputerAgent:
    MAX_LOOPS = 5

    def __init__(self, runtime: ResearchComputerRuntimeAgent | None = None, storage: AutonomousComputerService | None = None,
                 sandbox: ExecutionSandbox | None = None, workspace_actions: WorkspaceActionEngine | None = None) -> None:
        self.runtime = runtime or ResearchComputerRuntimeAgent()
        self.storage = storage or AutonomousComputerService()
        self.sandbox = sandbox or ExecutionSandbox()
        self.workspace_actions = workspace_actions or WorkspaceActionEngine()

    def create(self, goal: str, mode: str = "supervised", workspace_id: str | None = None) -> dict[str, object]:
        task = self.runtime.create(goal, mode, workspace_id)
        row = self.storage.create(str(task["id"]), str(goal), list(task["plan"]))
        self._event(row, "Autonomous Runtime", "CREATED", "COMPLETED", "已创建受控自主工程任务。", "等待启动执行")
        return self.get(str(row["id"]))

    def execute(self, runtime_id: str) -> dict[str, object]:
        row = self.storage.get(runtime_id)
        if int(row["loop_count"]) >= self.MAX_LOOPS: return self._human_review(row, "已达到最多 5 次执行循环。")
        self.storage.update(runtime_id, status="ANALYZING", loop_count=int(row["loop_count"]) + 1)
        self._event(row, "Planner Agent", "UNDERSTANDING", "COMPLETED", "正在理解目标并检查受控执行边界。")
        self._event(row, "Planner Agent", "PLANNING", "COMPLETED", "已生成工程执行计划。", f"{len(row['plan'])} 个步骤")
        output = self.runtime.execute(str(row["computer_task_id"]))
        self._record_runtime_artifacts(runtime_id, output)
        status = str(output.get("runtime_status", ""))
        if status == "WAITING_REVIEW":
            self.storage.update(runtime_id, status="EDITING")
            self._event(row, "Reviewer Agent", "APPROVAL", "WAITING_APPROVAL", "Patch 或交付物等待人工确认；未应用任何修改。")
        elif status in {"WAITING_EVIDENCE", "FAILED"}:
            self.storage.update(runtime_id, status="FAILED")
            self._event(row, "Debug Agent", "RECOVERY", "WAITING_REVIEW", "当前运行缺少可验证资料或遇到安全失败，等待人工决定是否重试。")
        else:
            self.storage.update(runtime_id, status="TESTING")
            verification = self.sandbox.validate("compileall")
            self.storage.add_artifact(runtime_id, "TEST_RESULT", "compileall", "VERIFIED" if verification.get("verification") == "SUCCESS" else "FAILED", verification)
            self._event(row, "Testing Agent", "VERIFYING", str(verification.get("status")), "已完成白名单基础验证。", str(verification.get("verification")))
            self.storage.update(runtime_id, status="SUCCESS" if verification.get("verification") == "SUCCESS" else "FAILED")
        return self.get(runtime_id)

    def approve(self, runtime_id: str, note: str) -> dict[str, object]:
        row = self.storage.get(runtime_id); self.storage.update(runtime_id, status="TESTING")
        output = self.runtime.approve(str(row["computer_task_id"]), note)
        self._record_runtime_artifacts(runtime_id, output)
        if str(output.get("runtime_status")) == "COMPLETED":
            self.storage.update(runtime_id, status="SUCCESS")
            self._event(row, "Testing Agent", "VERIFYING", "COMPLETED", "已应用经批准动作，并完成白名单验证。")
        else:
            self.storage.update(runtime_id, status="FAILED")
            self._event(row, "Debug Agent", "RECOVERY", "WAITING_REVIEW", "批准后验证未通过，未进行额外修改。")
        return self.get(runtime_id)

    def retry(self, runtime_id: str) -> dict[str, object]:
        row = self.storage.get(runtime_id); count = int(row["loop_count"])
        if count >= self.MAX_LOOPS: return self._human_review(row, "恢复次数达到上限，需人工审核。")
        self.storage.add_recovery(runtime_id, count + 1, "RETRYING", "重新执行只读观察、分析与白名单验证；不会绕过人工审批。")
        self.storage.update(runtime_id, status="FIXING")
        self._event(row, "Debug Agent", "RECOVERING", "RETRYING", "开始有限恢复循环。", f"第 {count + 1}/{self.MAX_LOOPS} 次")
        return self.execute(runtime_id)

    def get(self, runtime_id: str) -> dict[str, object]:
        row = self.storage.get(runtime_id); task = self.runtime.get(str(row["computer_task_id"]))
        return {**row, "computer_task": task, "artifacts": self.storage.artifacts(runtime_id), "recoveries": self.storage.recoveries(runtime_id), "timeline": self.timeline(runtime_id)}

    def timeline(self, runtime_id: str) -> list[dict[str, object]]:
        row = self.storage.get(runtime_id)
        return self.runtime.timeline(str(row["computer_task_id"]))

    def artifacts(self, runtime_id: str) -> list[dict[str, object]]: return self.storage.artifacts(runtime_id)

    def _record_runtime_artifacts(self, runtime_id: str, output: dict[str, object]) -> None:
        existing = {(item["type"], item["name"], item["status"]) for item in self.storage.artifacts(runtime_id)}
        for artifact in output.get("artifacts", []):
            value = (str(artifact.get("type")), str(artifact.get("path") or artifact.get("reference")), str(artifact.get("status")))
            if value not in existing:
                self.storage.add_artifact(runtime_id, value[0].upper().replace(" ", "_"), value[1], value[2], dict(artifact))

    def _event(self, row: dict[str, object], agent: str, phase: str, status: str, message: str, summary: str = "") -> None:
        self.runtime.operator._event(str(row["computer_task_id"]), agent, phase, status, message, summary)

    def _human_review(self, row: dict[str, object], message: str) -> dict[str, object]:
        self.storage.update(str(row["id"]), status="FAILED")
        self._event(row, "Reviewer Agent", "RECOVERY", "HUMAN_REVIEW", message)
        return self.get(str(row["id"]))
