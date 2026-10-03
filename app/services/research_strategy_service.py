"""Evidence-bounded Research Intelligence for the existing Research Orchestrator.

This service is deliberately deterministic. It does not call a model, retrieve
new material, persist prompts, or turn a sparse reference list into a research
fact. It prepares a user-readable strategy and identifies evidence coverage
limits for the existing Research Skill and human review flow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class ResearchStrategyService:
    """Transforms a goal and already-authorized Evidence refs into safe insight."""

    _area_keywords = {
        "retrieval": ("rag", "retrieval", "检索", "faiss"),
        "methods": ("method", "方法", "模型", "agent"),
        "evaluation": ("evaluation", "benchmark", "performance", "实验", "评估", "性能"),
        "risk": ("risk", "limitation", "conflict", "风险", "局限", "冲突"),
        "delivery": ("proposal", "deliverable", "方案", "交付", "项目"),
    }

    def research_goal_analysis(self, research_goal: str, evidence_refs: Sequence[Mapping[str, Any]] | None = None) -> dict[str, object]:
        goal = self._goal(research_goal)
        areas = self._knowledge_areas(goal)
        return {
            "research_goal": goal,
            "research_questions": [
                f"What traceable Evidence is available for: {goal}?",
                f"Which conditions, sources, or scopes limit conclusions about: {goal}?",
                f"What additional Evidence is required before proposing a validation path for: {goal}?",
            ],
            "knowledge_areas": areas,
            "evidence_requirements": [
                "Use only traceable paper and chunk references returned by the existing Research Skill.",
                "Retain source and condition differences for human review rather than resolving conflicts automatically.",
                "Mark conclusions as insufficient when no traceable Evidence is attached.",
            ],
            "evaluation_criteria": [
                "Evidence coverage across the stated research questions.",
                "Source diversity and stated condition coverage.",
                "Conflict and human-review status before delivery.",
            ],
            "evidence_count": len(self._refs(evidence_refs)),
            "boundary": "Strategy is a planning summary, not a scientific conclusion or hidden model reasoning.",
        }

    def gap_analysis(self, evidence_refs: Sequence[Mapping[str, Any]] | None, *, workspace_id: str | None = None) -> dict[str, object]:
        refs = self._refs(evidence_refs, workspace_id=workspace_id)
        if not refs:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "current_knowledge": [],
                "established_findings": [],
                "uncertain_areas": [{
                    "statement": "No traceable Evidence is attached to this Mission, so research findings cannot be established.",
                    "evidence_refs": [],
                }],
                "potential_gaps": [{
                    "statement": "Evidence coverage is absent; collect authorized sources before comparing methods, conditions, or outcomes.",
                    "evidence_refs": [],
                }],
                "research_opportunities": [],
                "boundary": "No innovation or research conclusion is generated without traceable Evidence.",
            }

        sources = self._distinct_sources(refs)
        current_knowledge = [{
            "statement": f"Traceable Evidence is available from {ref['source']} ({ref['section']}).",
            "evidence_refs": [self._reference(ref)],
        } for ref in refs]
        uncertain = []
        gaps = []
        if len(sources) < 2:
            statement = "Current Evidence has limited source diversity; comparisons across research conditions remain uncertain."
            uncertain.append({"statement": statement, "evidence_refs": [self._reference(ref) for ref in refs]})
            gaps.append({"statement": "Add authorized sources that cover alternative methods, datasets, or experimental conditions.", "evidence_refs": [self._reference(ref) for ref in refs]})
        else:
            uncertain.append({"statement": "Source references are available, but applicability across conditions requires human review.", "evidence_refs": [self._reference(ref) for ref in refs]})
            gaps.append({"statement": "Compare the cited sources' stated conditions before treating apparent differences as a research opportunity.", "evidence_refs": [self._reference(ref) for ref in refs]})
        return {
            "status": "EVIDENCE_REVIEW_REQUIRED",
            "current_knowledge": current_knowledge,
            "established_findings": [{
                "statement": f"{len(refs)} traceable Evidence reference(s) from {len(sources)} source(s) are available for review.",
                "evidence_refs": [self._reference(ref) for ref in refs],
            }],
            "uncertain_areas": uncertain,
            "potential_gaps": gaps,
            "research_opportunities": self.generate_innovation_proposal(refs),
            "boundary": "Evidence coverage is not proof of a scientific conclusion; a reviewer must assess source scope and conditions.",
        }

    def generate_innovation_proposal(self, evidence_refs: Sequence[Mapping[str, Any]] | None, *, workspace_id: str | None = None) -> list[dict[str, object]]:
        refs = self._refs(evidence_refs, workspace_id=workspace_id)
        if not refs:
            return []
        citations = [self._reference(ref) for ref in refs]
        return [{
            "opportunity": "Prepare a human-reviewed validation plan for the conditions represented by current Evidence.",
            "reason": "The Mission has traceable Evidence references, but their scope and comparability still require explicit review.",
            "evidence_support": citations,
            "risk": "The referenced sources may use different methods, datasets, samples, or experimental conditions.",
            "validation_path": "Review source conditions, define a comparable evaluation scope, then seek approval before creating an experiment or delivery artifact.",
            "status": "REVIEW_REQUIRED",
        }]

    def mission_insight(self, mission: Mapping[str, Any]) -> dict[str, object]:
        workspace_id = str(mission.get("workspace_id") or "") or None
        refs = mission.get("evidence_refs")
        refs = refs if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)) else []
        strategy = self.research_goal_analysis(str(mission.get("goal") or mission.get("title") or "Research Mission"), refs)
        gaps = self.gap_analysis(refs, workspace_id=workspace_id)
        return {"strategy": strategy, "gap_analysis": gaps, "innovation_proposals": gaps["research_opportunities"]}

    def _knowledge_areas(self, goal: str) -> list[str]:
        lowered = goal.lower()
        selected = [name.replace("_", " ").title() for name, terms in self._area_keywords.items() if any(term in lowered for term in terms)]
        return selected or ["Research scope", "Evidence coverage", "Conditions and limitations"]

    @staticmethod
    def _goal(value: str) -> str:
        compact = " ".join(str(value or "").split())
        return compact[:500] or "Research Mission"

    @staticmethod
    def _refs(rows: Sequence[Mapping[str, Any]] | None, *, workspace_id: str | None = None) -> list[dict[str, str]]:
        result = []
        for row in rows or []:
            if not isinstance(row, Mapping):
                continue
            row_workspace = str(row.get("workspace_id") or "")
            if workspace_id and row_workspace and row_workspace != workspace_id:
                continue
            paper_id, chunk_id = str(row.get("paper_id") or ""), str(row.get("chunk_id") or "")
            if not paper_id or not chunk_id:
                continue
            result.append({"paper_id": paper_id, "chunk_id": chunk_id, "source": str(row.get("source") or "Untitled source"), "section": str(row.get("section") or "Source reference")})
        return result

    @staticmethod
    def _reference(ref: Mapping[str, str]) -> dict[str, str]:
        return {"paper_id": ref["paper_id"], "chunk_id": ref["chunk_id"], "source": ref["source"], "section": ref["section"]}

    @staticmethod
    def _distinct_sources(refs: Sequence[Mapping[str, str]]) -> set[str]:
        return {f"{ref['paper_id']}:{ref['source']}" for ref in refs}
