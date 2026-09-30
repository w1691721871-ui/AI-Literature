"""P18 Computer Use facade: plan, propose, approve/apply, verify and rollback."""

from __future__ import annotations

from pathlib import Path

from app.agent.research_autonomous_computer_agent import ResearchAutonomousComputerAgent
from app.services.computer_use_service import ComputerUseService
from app.services.computer_intelligence_service import ComputerIntelligenceService
from app.services.product_experience_service import ProductExperienceService
from app.tools.computer.execution_sandbox import ExecutionSandbox
from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class ResearchComputerUseAgent:
    def __init__(self, autonomous: ResearchAutonomousComputerAgent | None = None, changes: ComputerUseService | None = None,
                 actions: WorkspaceActionEngine | None = None, sandbox: ExecutionSandbox | None = None, intelligence: ComputerIntelligenceService | None = None,
                 experience: ProductExperienceService | None = None) -> None:
        self.autonomous = autonomous or ResearchAutonomousComputerAgent()
        self.changes = changes or ComputerUseService()
        self.actions = actions or WorkspaceActionEngine()
        self.sandbox = sandbox or ExecutionSandbox()
        self.intelligence = intelligence or ComputerIntelligenceService()
        self.experience = experience or ProductExperienceService()

    def create(self, goal: str, mode: str = "supervised", workspace_id: str | None = None) -> dict[str, object]:
        runtime = self.autonomous.create(goal, mode, workspace_id)
        self.intelligence.activity(runtime["id"], "ANALYZING", "Analyzing Workspace", "将检查项目结构、前端与安全边界。", "COMPLETED")
        self.experience.create_mission(str(runtime["id"]), goal)
        return {"id": runtime["id"], "goal": goal, "plan": self._plan(goal), "approval_required": True, "risk_level": "MEDIUM", "status": runtime["status"]}

    def start(self, task_id: str) -> dict[str, object]:
        runtime = self.autonomous.execute(task_id)
        self.experience.update_mission(task_id, 45, "PLANNING")
        goal = str(self.autonomous.storage.get(task_id)["user_goal"])
        proposal = self._proposal(goal)
        if proposal:
            change = self.changes.propose(task_id, proposal)
            review = self.intelligence.review(change)
            self.intelligence.activity(task_id, "PLANNING", "Planning Improvement", "已生成 Diff、风险说明与验证计划。", review["status"])
            self.experience.update_mission(task_id, 70, "WAITING_APPROVAL")
            self.autonomous.storage.add_artifact(task_id, "CODE_CHANGE", change["file_path"], "WAITING_APPROVAL", {"change_id": change["id"], "risk": "MEDIUM", "verification": "compileall"})
            self.autonomous._event(runtime, "Coding Agent", "EDITING", "WAITING_APPROVAL", "已生成可审阅文件修改提案。", f"{change['file_path']} · {change['operation']}")
        return self.get(task_id)

    def approve(self, task_id: str, note: str) -> dict[str, object]:
        pending = next((item for item in self.changes.changes(task_id) if item["status"] == "PROPOSED"), None)
        if pending is None: return self.autonomous.approve(task_id, note)
        row = self.changes.get(str(pending["id"])); path = self.actions._safe(row.file_path)
        current = path.read_text(encoding="utf-8")
        if self.changes._hash(current) != row.before_hash: raise ValueError("源文件已变化，拒绝应用过期修改提案。")
        self.changes.update_status(row.id, "APPROVED")
        path.write_text(row.after_content, encoding="utf-8")
        verified = path.read_text(encoding="utf-8") == row.after_content
        self.changes.update_status(row.id, "VERIFIED" if verified else "APPLIED")
        result = self.sandbox.validate("compileall")
        runtime = self.autonomous.storage.get(task_id)
        self.autonomous.storage.add_artifact(task_id, "TEST_RESULT", "compileall", "VERIFIED" if result.get("verification") == "SUCCESS" else "FAILED", result)
        self.autonomous._event(runtime, "Testing Agent", "VERIFYING", str(result.get("status")), "已完成批准后白名单验证。", str(result.get("verification")))
        self.intelligence.activity(task_id, "TESTING", "Verification Complete", "已运行批准后的白名单验证。", str(result.get("status")))
        self.experience.update_mission(task_id, 100 if result.get("verification") == "SUCCESS" else 90, "COMPLETED" if result.get("verification") == "SUCCESS" else "TESTING")
        return self.get(task_id)

    def rollback(self, task_id: str) -> dict[str, object]:
        applied = next((item for item in reversed(self.changes.changes(task_id)) if item["status"] in {"APPLIED", "VERIFIED"}), None)
        if applied is None: raise ValueError("没有可回滚的已应用文件修改。")
        row = self.changes.get(str(applied["id"])); path = self.actions._safe(row.file_path)
        if self.changes._hash(path.read_text(encoding="utf-8")) != row.after_hash: raise ValueError("文件已变化，不能安全回滚。")
        path.write_text(row.before_content, encoding="utf-8"); self.changes.update_status(row.id, "ROLLED_BACK")
        runtime = self.autonomous.storage.get(task_id); self.autonomous._event(runtime, "Reviewer Agent", "ROLLBACK", "COMPLETED", "已按已审核快照回滚文件修改。", row.file_path)
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, object]:
        changes=self.changes.changes(task_id)
        return {**self.autonomous.get(task_id), "changes": changes, "activity": self.intelligence.activities(task_id), "mission": self.experience.mission(task_id), "code_review": [self.intelligence.review(change) for change in changes], "verification_plan": self.intelligence.verification_plan(changes), "diff_summary": self.intelligence.diff_summary(changes)}
    def timeline(self, task_id: str) -> list[dict[str, object]]: return self.autonomous.timeline(task_id)
    def artifacts(self, task_id: str) -> list[dict[str, object]]: return self.autonomous.artifacts(task_id)
    def _proposal(self, goal: str) -> dict[str, object] | None:
        if not any(word in goal.lower() for word in ("ui", "首页", "front", "style", "样式")): return None
        target = "frontend/styles.css"; before = self.actions.read(target)["content"]
        addition = "\n/* P18 approved Computer Use focus refinement. */\n.home-research-input:focus-within{outline:1px solid rgba(99,241,220,.42)}\n"
        after = before if addition.strip() in before else before.rstrip() + addition
        return {"file_path": target, "operation": "append", "before_content": before, "after_content": after, "diff": self.actions.propose(target, "append", addition)["diff"]}
    @staticmethod
    def _plan(goal: str) -> list[dict[str, object]]:
        return [{"goal": goal, "required_tools": ["Workspace Explorer", "Coding Agent", "Testing Agent"], "affected_files": ["待环境观察确认"], "risk_level": "MEDIUM", "expected_output": "可审阅 Diff 与测试结果", "approval_required": True}]
