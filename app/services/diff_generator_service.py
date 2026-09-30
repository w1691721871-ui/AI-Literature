"""Deterministic, proposal-only diff generation for the P24 sandbox."""

from __future__ import annotations

from app.tools.computer.workspace_action_engine import WorkspaceActionEngine


class DiffGeneratorService:
    """Generates a deliberately narrow UI focus proposal; it never writes files."""

    def __init__(self, actions: WorkspaceActionEngine | None = None) -> None:
        self.actions = actions or WorkspaceActionEngine()

    def generate(self, task: str, file_path: str) -> dict[str, object]:
        lowered = task.lower()
        if file_path != "frontend/styles.css" or not any(word in lowered for word in ("ui", "首页", "front", "style", "样式", "focus")):
            return {"status": "NO_SAFE_DIFF", "file_path": file_path, "operation": "none", "before_content": "", "after_content": "", "diff": "", "reason": "当前任务未形成可安全、可确定的源码修改提案；请补充目标文件和预期行为。"}
        before = str(self.actions.read(file_path)["content"])
        addition = "\n/* Controlled Computer Mission: approved focus affordance. */\n.home-research-input:focus-visible{outline:1px solid rgba(99,241,220,.42);outline-offset:3px}\n"
        if addition.strip() in before:
            return {"status": "NO_SAFE_DIFF", "file_path": file_path, "operation": "none", "before_content": before, "after_content": before, "diff": "", "reason": "相同的受控提案已存在；不会生成重复修改。"}
        proposal = self.actions.propose(file_path, "append", addition)
        return {**proposal, "status": "PROPOSED", "before_content": before, "after_content": before.rstrip() + addition, "reason": "仅生成可审阅的前端焦点状态提案；需人工批准后才可写入。"}
