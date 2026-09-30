"""P24 plan-only Computer Agent; no file write capability lives here."""

from __future__ import annotations


class ControlledComputerAgent:
    """Creates transparent plans from a request and observed workspace metadata."""

    def plan(self, task: str, profile: dict[str, object]) -> dict[str, object]:
        lowered = task.lower()
        frontend = any(word in lowered for word in ("ui", "首页", "front", "style", "样式"))
        target = "frontend/styles.css" if frontend else ""
        steps = [
            {"step": 1, "action": "扫描受控 ResearchOS Workspace", "tool": "Workspace Scanner", "reason": "确认项目结构和技术栈。"},
            {"step": 2, "action": f"检查 {target or '相关文件范围'}", "tool": "Workspace Read Tool", "reason": "仅在白名单内读取与任务相关的代码。"},
            {"step": 3, "action": "生成可审阅 Diff", "tool": "Diff Generator", "reason": "写入前必须提供 Before/After 与统一 Diff。"},
            {"step": 4, "action": "运行批准后的白名单验证", "tool": "Verification Agent", "reason": "只有人工批准后才执行，并验证结果。"},
        ]
        return {"goal": task, "required_tools": ["Workspace Scanner", "Workspace Read Tool", "Diff Generator", "Verification Agent"], "affected_files": [target] if target else [], "risk_level": "MEDIUM" if target else "LOW", "expected_output": "Action Plan、可审阅 Diff 与 Verification Report", "approval_required": True, "steps": steps, "workspace_summary": {key: profile.get(key) for key in ("project_type", "languages", "frameworks", "files_count")}}
