"""User-readable, evidence-bound progress reports for the existing AI Worker.

This is a projection of persisted Mission and Runtime records, not another
planner or model call.  It deliberately never reads prompts, model responses,
raw browser content, or internal reasoning.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class AIEmployeeReportService:
    """Summarise a bounded Mission as an accountable employee update."""

    def build(
        self,
        mission: Mapping[str, object],
        records: Sequence[Mapping[str, object]],
        *,
        quality: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        evidence_refs = mission.get("evidence_refs")
        evidence_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0
        completed = [record for record in records if str(record.get("status") or "").upper() == "SUCCESS"]
        review_needed = any(str(record.get("status") or "").upper() == "WAITING_REVIEW" for record in records)
        status = str(mission.get("status") or "CREATED").upper()
        quality_data = dict(quality or {})
        artifacts = self._artifacts(mission)
        return {
            "mission_id": str(mission.get("id") or ""),
            "title": str(mission.get("title") or "Untitled mission"),
            "status": self._status(status, review_needed),
            "completed": self._completed(completed),
            "evidence": {
                "count": evidence_count,
                "summary": (
                    f"{evidence_count} traceable Evidence reference(s) are attached."
                    if evidence_count else
                    "No traceable Evidence is attached; the AI Worker cannot make a grounded research claim."
                ),
            },
            "artifacts": artifacts,
            "next_step": self._next_step(status, review_needed, evidence_count, quality_data),
            "boundary": "This report is derived only from saved Mission status, approved workflow records and Evidence references. It excludes prompts, chain-of-thought, secrets and raw external content.",
        }

    @staticmethod
    def _status(status: str, review_needed: bool) -> str:
        if status in {"COMPLETED", "DELIVERY_READY"}:
            return "Completed"
        if status in {"FAILED", "REJECTED"}:
            return "Needs attention"
        if review_needed or status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW"}:
            return "Waiting for your review"
        if status == "PAUSED":
            return "Paused"
        return "In progress"

    @staticmethod
    def _completed(records: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        seen: set[str] = set()
        for record in records:
            label = str(record.get("skill") or "AI Worker")
            if label in seen:
                continue
            seen.add(label)
            items.append({"area": label, "result": str(record.get("result_summary") or "A controlled task completed.")[:320]})
        return items[:4]

    @staticmethod
    def _artifacts(mission: Mapping[str, object]) -> list[dict[str, str]]:
        source = mission.get("artifacts") or mission.get("deliverables") or []
        if not isinstance(source, list):
            return []
        results = []
        for item in source:
            if isinstance(item, Mapping):
                results.append({"title": str(item.get("title") or item.get("name") or "Reviewable delivery"), "status": str(item.get("status") or "DRAFT")})
        return results[:4]

    @staticmethod
    def _next_step(status: str, review_needed: bool, evidence_count: int, quality: Mapping[str, object]) -> str:
        if status in {"COMPLETED", "DELIVERY_READY"}:
            return "Review the completed delivery and reuse it only within its recorded evidence boundary."
        if status in {"FAILED", "REJECTED"}:
            return "Review the recorded issue and decide whether to revise the Mission or stop it."
        if review_needed or status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW"}:
            return "Review the AI Worker’s evidence-backed result before it can progress."
        if evidence_count == 0 or str(quality.get("quality") or "") == "NEEDS_EVIDENCE":
            return "Collect or validate traceable Evidence before asking the AI Worker for a research conclusion."
        return "The AI Worker can continue its next bounded, authorized Skill step."
