"""Explicit validation workflow for Computer-discovered candidate Evidence."""
from __future__ import annotations


class EvidenceValidationOrchestrator:
    def validate_candidates(self, candidates: list[dict[str, object]], mission_id: str) -> dict[str, object]:
        reviewed=[]
        for item in candidates:
            score=float(item.get("confidence") or 0)
            source=str(item.get("source") or "")
            eligible=bool(item.get("validation_required")) and source.startswith("https://") and bool(item.get("title"))
            reviewed.append({"source":source,"title":item.get("title"),"related_mission":mission_id,"confidence":round(score,2),"validation_status":"PENDING_HUMAN_REVIEW" if eligible else "REJECTED","validation_reason":"Traceable public candidate requires an authorized reviewer decision." if eligible else "Candidate lacks required traceable metadata.","status":"CANDIDATE"})
        return {"mission_id":mission_id,"candidates":reviewed,"approved_evidence":[],"status":"WAITING_REVIEW" if any(x["validation_status"]=="PENDING_HUMAN_REVIEW" for x in reviewed) else "NEEDS_REVIEW","boundary":"Candidates remain candidates. Only the existing authorized Evidence review workflow can create approved Evidence."}
