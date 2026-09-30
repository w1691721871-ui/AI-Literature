"""Team workflow, human review and graph-lite operations for Research Workspace.

All state is stored inside the existing workspace JSON snapshot.  This is a
product-model layer: it has no authentication system, does not create actions,
and never changes papers, chunks, FAISS, or evidence content.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.research_workspace_intelligence_service import ResearchWorkspaceIntelligenceService


class WorkflowPermissionError(ValueError):
    """Raised when a display-only role lacks the required review permission."""


class ReviewItemNotFoundError(ValueError):
    """Raised when a workspace review item cannot be found."""


class ResearchWorkspaceWorkflowService:
    """Apply a small, explicit human-in-the-loop workflow state machine."""

    REVIEWER_ROLES = {"reviewer", "leader"}
    LEADER_ROLES = {"leader"}

    def __init__(self, workspace_service: ResearchWorkspaceIntelligenceService) -> None:
        self._workspace = workspace_service

    def members(self, workspace_id: str) -> list[dict[str, object]]:
        snapshot = self._workspace.get_workspace(workspace_id)
        return list(snapshot.get("members", []))

    def workflow(self, workspace_id: str) -> dict[str, object]:
        snapshot = self._workspace.get_workspace(workspace_id)
        return dict(snapshot.get("workflow", {}))

    def review_items(self, workspace_id: str) -> list[dict[str, object]]:
        snapshot = self._workspace.get_workspace(workspace_id)
        return list(snapshot.get("review_items", []))

    def evidence_graph(self, workspace_id: str) -> dict[str, object]:
        snapshot = self._workspace.get_workspace(workspace_id)
        return dict(snapshot.get("evidence_graph", {}))

    def submit_review(
        self, workspace_id: str, item_id: str, reviewer_role: str, review_status: str, reviewer_note: str = ""
    ) -> dict[str, object]:
        """Record an explicit approval/rejection.  AI cannot call this path."""
        role = reviewer_role.strip().lower()
        if role not in self.REVIEWER_ROLES:
            raise WorkflowPermissionError("只有 Reviewer 或 Leader 角色可以确认或否决研究审核项。")
        if review_status not in {"approved", "rejected"}:
            raise ValueError("审核状态仅支持 approved 或 rejected。")
        snapshot = self._workspace.get_workspace(workspace_id)
        items = deepcopy(list(snapshot.get("review_items", [])))
        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)
        if item is None:
            raise ReviewItemNotFoundError("未找到该审核项。")
        item.update({"status": review_status, "reviewer_note": reviewer_note.strip(), "reviewer_role": role})
        snapshot["review_items"] = items
        if review_status == "rejected":
            state, reason = "evidence_collection", "Reviewer 认为当前 Evidence 不足，需要继续研究或补充资料。"
            snapshot["unresolved_questions"] = list(dict.fromkeys([
                *snapshot.get("unresolved_questions", []), "Reviewer 标记当前 Evidence 不足，需要补充研究资料。",
            ]))
        elif all(candidate.get("status") == "approved" for candidate in items):
            state, reason = "decision_pending", "Evidence 已通过人工审核，等待负责人形成正式 Decision；系统不会自动创建 Action。"
        else:
            state, reason = "evidence_review", "仍有待审核的 Evidence 关联判断。"
        snapshot["workflow"] = self._workflow(snapshot, state, reason)
        snapshot["human_review"] = {"required": True, "status": "已审核" if review_status == "approved" else "需补充资料"}
        return self._workspace.update_workspace_snapshot(workspace_id, snapshot)

    def mark_deliverable_draft(self, workspace_id: str, deliverable: dict[str, object]) -> dict[str, object]:
        """Move only a reviewed, evidence-grounded draft into the workflow."""
        snapshot = self._workspace.get_workspace(workspace_id)
        if not snapshot.get("evidence_summary"):
            raise ValueError("当前没有可验证资料，不能进入 Deliverable Draft。")
        if any(item.get("status") != "approved" for item in snapshot.get("review_items", [])):
            raise ValueError("Evidence Review 尚未完成，不能生成可交付草案。")
        outputs = list(snapshot.get("deliverables", []))
        outputs.append({
            "type": deliverable.get("type", "research_brief"), "title": deliverable.get("title", "Research Brief"),
            "status": deliverable.get("status", "draft"), "evidence_count": len(deliverable.get("evidence_refs", [])),
        })
        snapshot["deliverables"] = outputs[-6:]
        snapshot["workflow"] = self._workflow(snapshot, "deliverable_draft", "已生成经审核 Evidence 支撑的交付草案，仍需 Leader 确认完成。")
        return self._workspace.update_workspace_snapshot(workspace_id, snapshot)

    def complete(self, workspace_id: str, role: str) -> dict[str, object]:
        if role.strip().lower() not in self.LEADER_ROLES:
            raise WorkflowPermissionError("只有 Leader 角色可以确认 Research Workspace 已完成。")
        snapshot = self._workspace.get_workspace(workspace_id)
        if not snapshot.get("deliverables") or snapshot.get("workflow", {}).get("current_state") != "deliverable_draft":
            raise ValueError("完成前需要存在经审核的 Deliverable Draft。")
        snapshot["workflow"] = self._workflow(snapshot, "completed", "Leader 已确认当前交付草案完成；后续正式项目与 Action 仍需独立创建。")
        return self._workspace.update_workspace_snapshot(workspace_id, snapshot)

    @staticmethod
    def _workflow(snapshot: dict[str, object], state: str, reason: str) -> dict[str, object]:
        existing = dict(snapshot.get("workflow", {}))
        history = list(existing.get("history", ["created", "research_planning", "evidence_collection"]))
        if state not in history:
            history.append(state)
        existing.update({"current_state": state, "history": history, "reason": reason})
        return existing
