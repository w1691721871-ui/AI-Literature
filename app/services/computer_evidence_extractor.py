"""Safe conversion from public metadata candidates to candidate Evidence."""
from __future__ import annotations


class ComputerEvidenceExtractor:
    def extract(self, candidates: list[dict[str, object]], mission_id: str) -> list[dict[str, object]]:
        return [{"source": item.get("url"), "title": item.get("title"), "claim": "A public research metadata record relevant to the Mission was discovered.", "supporting_text_summary": f"Metadata candidate: {str(item.get('title') or '')[:280]}", "confidence": min(0.75, 0.35 + int(item.get("candidate_score") or 0) / 200), "related_mission": mission_id, "status": "CANDIDATE_EVIDENCE", "validation_required": True} for item in candidates]
