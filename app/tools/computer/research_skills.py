"""Named, bounded research skills used by the Computer Agent plan.

Skills are transparent routing metadata, not hidden agents and not model
reasoning.  They state what the allowed tool can do and its evidence boundary.
"""

from __future__ import annotations


class ResearchSkillRouter:
    _skills = {
        "literature_organization": {
            "name": "Literature Organization Skill",
            "description": "Classifies permitted research assets and proposes topic/direction groupings without mutating files.",
            "evidence_boundary": "Produces an organization plan, not scientific findings.",
        },
        "paper_reading": {
            "name": "Paper Reading Skill",
            "description": "Organizes existing Evidence by method, experiment, limitations and future-validation fields.",
            "evidence_boundary": "Only references retrieved paper/chunk identifiers; it does not infer missing claims.",
        },
        "research_writing": {
            "name": "Research Writing Skill",
            "description": "Prepares Markdown/DOCX drafts from Evidence references after explicit approval.",
            "evidence_boundary": "Every draft is evidence-linked and remains a human-review artifact.",
        },
        "research_management": {
            "name": "Research Management Skill",
            "description": "Records approval gates, source-review requirements and delivery readiness.",
            "evidence_boundary": "Does not approve, publish or create a formal research decision automatically.",
        },
    }

    def catalog(self) -> list[dict[str, str]]:
        return [{"id": key, **value} for key, value in self._skills.items()]

    def get(self, skill_id: str) -> dict[str, str]:
        return {"id": skill_id, **self._skills[skill_id]}
