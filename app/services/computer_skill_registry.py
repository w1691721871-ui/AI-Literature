"""Controlled Computer Skill catalog for the existing Computer Skill adapter."""

from __future__ import annotations


class ComputerSkillRegistry:
    """Declares bounded Computer capabilities; it never executes an action."""

    _SKILLS = (
        {
            "id": "browser_research", "name": "Browser Research",
            "inputs": ["Authorized public source", "Mission goal"],
            "outputs": ["Candidate source references", "Evidence request"],
            "permission": "KNOWLEDGE_ACCESS", "risk_level": "LOW",
            "approval_required": False,
            "boundary": "Sources remain external candidates until the existing Evidence workflow validates them.",
        },
        {
            "id": "document_preparation", "name": "Document Preparation",
            "inputs": ["Authorized source material", "Approved Evidence"],
            "outputs": ["Reviewable Artifact draft"],
            "permission": "MISSION_EXECUTE", "risk_level": "MEDIUM",
            "approval_required": True,
            "boundary": "A draft is never released without the existing human approval flow.",
        },
        {
            "id": "data_operation", "name": "Data Operation",
            "inputs": ["Approved read-only data source"],
            "outputs": ["Reviewable analysis result"],
            "permission": "CONNECTOR_ACCESS", "risk_level": "MEDIUM",
            "approval_required": True,
            "boundary": "Only registered read-only sources may be used; no dataset is fabricated.",
        },
        {
            "id": "report_preparation", "name": "Report Preparation",
            "inputs": ["Traceable Evidence", "Mission context"],
            "outputs": ["Evidence-linked delivery draft"],
            "permission": "MISSION_EXECUTE", "risk_level": "MEDIUM",
            "approval_required": True,
            "boundary": "The existing Artifact service preserves versions, Evidence links and review status.",
        },
    )

    def catalog(self) -> list[dict[str, object]]:
        return [dict(skill) for skill in self._SKILLS]

    def match(self, goal: str) -> list[dict[str, object]]:
        lowered = str(goal or "").lower()
        selected = [self._SKILLS[0]]
        if any(term in lowered for term in ("document", "file", "paper", "文档", "论文")):
            selected.append(self._SKILLS[1])
        if any(term in lowered for term in ("data", "table", "dataset", "数据", "表格")):
            selected.append(self._SKILLS[2])
        if any(term in lowered for term in ("report", "proposal", "delivery", "报告", "方案", "交付")):
            selected.append(self._SKILLS[3])
        return [dict(skill) for skill in selected]
