"""Finite multi-step public research worker built on the controlled engine."""
from __future__ import annotations

from app.services.computer_execution_engine import ComputerExecutionEngine
from app.services.computer_evidence_extractor import ComputerEvidenceExtractor
from app.services.research_query_planner import ResearchQueryPlanner
from app.services.source_quality_service import SourceQualityService


class ResearchBrowserWorker:
    MAX_QUERIES = 5
    MAX_ADJUSTMENTS = 2
    def __init__(self, engine=None, planner=None, scorer=None, extractor=None):
        self.engine = engine or ComputerExecutionEngine(); self.planner = planner or ResearchQueryPlanner(); self.scorer = scorer or SourceQualityService(); self.extractor = extractor or ComputerEvidenceExtractor()

    def run(self, mission_id: str, goal: str, *, permission_granted: bool) -> dict[str, object]:
        plan = self.planner.plan(goal); timeline=[]; candidates=[]
        for index, query in enumerate(plan["queries"][:self.MAX_QUERIES], 1):
            result = self.engine.execute({"action_type": "SEARCH", "input": query}, permission_granted=permission_granted)
            timeline.append({"step": index, "name": "Research discovery", "status": result["status"], "summary": result["summary"]})
            if result["status"] == "WAITING_APPROVAL": return {"status": "WAITING_APPROVAL", "plan": plan, "timeline": timeline, "candidates": [], "candidate_evidence": [], "artifact": None}
            candidates.extend((result.get("result") or {}).get("candidates") or [])
        ranked = self.scorer.evaluate(candidates, str(plan["topic"])); evidence = self.extractor.extract(ranked, mission_id)
        adjustments=[]
        # A sparse result does not become a conclusion.  The Worker may make
        # at most two read-only query adjustments, then it returns to the
        # existing Evidence and human-review boundary.
        for round_number in range(1, self.MAX_ADJUSTMENTS + 1):
            if len(evidence) >= 3:
                break
            adjustment = self.planner.adapt(goal, round_number=round_number)
            queries = adjustment.get("queries") if isinstance(adjustment.get("queries"), list) else []
            if not queries:
                break
            adjustments.append({"round": round_number, "summary": adjustment.get("summary", "A bounded public-source adjustment was prepared.")})
            timeline.append({"step": len(timeline)+1, "name": "Research adjustment", "status": "RUNNING", "summary": str(adjustment.get("summary") or "")})
            for query in queries:
                result = self.engine.execute({"action_type": "SEARCH", "input": query}, permission_granted=permission_granted)
                timeline.append({"step": len(timeline)+1, "name": "Research discovery", "status": result["status"], "summary": result["summary"]})
                if result["status"] == "WAITING_APPROVAL":
                    return {"status": "WAITING_APPROVAL", "plan": plan, "timeline": timeline, "candidates": [], "candidate_evidence": [], "artifact": None, "adjustments": adjustments}
                candidates.extend((result.get("result") or {}).get("candidates") or [])
            ranked = self.scorer.evaluate(candidates, str(plan["topic"])); evidence = self.extractor.extract(ranked, mission_id)
        quality = self._verify(evidence, plan)
        timeline.extend([{"step": len(timeline)+1, "name": "Source evaluation", "status": "COMPLETED", "summary": f"{len(ranked)} unique public-source candidates were evaluated."}, {"step": len(timeline)+2, "name": "Evidence preparation", "status": quality["status"], "summary": quality["summary"]}])
        return {"status": quality["status"], "plan": plan, "timeline": timeline, "candidates": ranked, "candidate_evidence": evidence, "artifact": None, "adjustments": adjustments, "next_action": quality["next_action"], "boundary": "Candidate Evidence must enter the existing validation and human-review workflow before Knowledge Memory or an Artifact can be created."}

    @staticmethod
    def _verify(evidence, plan):
        directions = len(plan["related_directions"])
        if len(evidence) >= 3: return {"status": "READY_FOR_EVIDENCE_VALIDATION", "summary": f"{len(evidence)} candidates provide a reviewable research starting set.", "next_action": "Validate candidate Evidence with the existing Evidence workflow."}
        if directions: return {"status": "NEEDS_REVIEW", "summary": "Candidate coverage is insufficient for a trend conclusion.", "next_action": "Broaden the authorized search or request human review."}
        return {"status": "NEEDS_REVIEW", "summary": "No sufficient candidate set was found; no conclusion or Artifact was created.", "next_action": "Refine the research goal or provide approved sources."}
