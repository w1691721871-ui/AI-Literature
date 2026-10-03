"""Build a reviewable, non-persisted brief from approved Evidence only."""
from __future__ import annotations
class ResearchBriefService:
    def draft(self, question: str, insight: dict[str, object]) -> dict[str, object] | None:
        if insight.get("status") != "EVIDENCE_BOUND_INSIGHT": return None
        return {"type":"RESEARCH_BRIEF","status":"NEEDS_REVIEW","research_question":question,"evidence_overview":insight["summary"],"current_trends":insight["trends"],"potential_research_gaps":insight["gap_candidates"],"supporting_evidence":insight["supporting_evidence"],"confidence":insight["confidence"],"boundary":"This is a reviewable draft, not a released Artifact. Existing Artifact generation and human approval remain required for delivery."}
