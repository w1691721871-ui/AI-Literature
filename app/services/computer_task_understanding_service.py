"""Deterministic, explainable task understanding for controlled Computer work."""

from __future__ import annotations


class ComputerTaskUnderstandingService:
    """Classify a user goal before any Computer action is planned or executed."""

    def understand(self, goal: str) -> dict[str, object]:
        text = str(goal or "").strip()
        lowered = text.lower()
        research = any(term in lowered for term in ("research", "paper", "literature", "trend", "研究", "论文", "方向"))
        data = any(term in lowered for term in ("data", "dataset", "table", "数据", "表格"))
        document = any(term in lowered for term in ("report", "document", "proposal", "报告", "文档", "方案"))
        modifies = any(term in lowered for term in ("upload", "submit", "write", "modify", "update", "delete", "上传", "提交", "写入", "修改", "更新", "删除"))
        task_type = "RESEARCH_COLLECTION" if research else "DATA_PREPARATION" if data else "DOCUMENT_PREPARATION" if document else "CONTROLLED_WORKSPACE_TASK"
        capabilities = ["browser_research"] if research else []
        if data: capabilities.append("data_operation")
        if document: capabilities.append("report_preparation")
        if not capabilities: capabilities.append("controlled_verification")
        return {
            "goal_summary": text[:500] or "No executable goal was provided.",
            "task_type": task_type,
            "required_environment": "authorized workspace metadata" if not research else "authorized public-source discovery with Evidence validation",
            "required_skills": capabilities,
            "risk_level": "HIGH" if modifies else "LOW",
            "completion_criteria": "An approved action has completed its existing verification." if modifies else "A traceable candidate or verified workspace result is ready for review.",
            "approval_required": modifies,
            "boundary": "Task understanding is deterministic and stores no Prompt, chain of thought, source content or credentials.",
        }
