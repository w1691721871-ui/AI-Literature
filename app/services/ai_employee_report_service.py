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
        execution: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        evidence_refs = mission.get("evidence_refs")
        evidence_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0
        completed = [record for record in records if str(record.get("status") or "").upper() == "SUCCESS"]
        review_needed = any(str(record.get("status") or "").upper() == "WAITING_REVIEW" for record in records)
        status = str(mission.get("status") or "CREATED").upper()
        quality_data = dict(quality or {})
        execution_data = dict(execution or {})
        artifacts = self._artifacts(mission)
        completion = self._completion(status, evidence_count, review_needed, artifacts, quality_data, execution_data)
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
            "daily_work": self._daily_work(records, evidence_count, review_needed),
            "work_state": self._work_state(execution_data),
            "completion": completion,
            "next_step": self._next_step(status, review_needed, evidence_count, quality_data, completion),
            "boundary": "This report is derived only from saved Mission status, approved workflow records and Evidence references. It excludes prompts, chain-of-thought, secrets and raw external content.",
        }

    @staticmethod
    def _daily_work(records: Sequence[Mapping[str, object]], evidence_count: int, review_needed: bool) -> dict[str, object]:
        completed = [str(item.get("result_summary") or "")[:220] for item in records if str(item.get("status") or "").upper() == "SUCCESS"]
        concerns = []
        if evidence_count == 0:
            concerns.append("Traceable Evidence is not yet sufficient for a grounded research conclusion.")
        if any(str(item.get("status") or "").upper() == "FAILED" for item in records):
            concerns.append("A controlled step needs human attention before the Mission can continue.")
        return {
            "completed_today": completed[:3],
            "issues": concerns,
            "adjustment": "A bounded research adjustment is queued when the existing Adaptive workflow records an evidence gap." if any(str(item.get("status") or "").upper() == "REPLANNING" for item in records) else "No unverified strategy adjustment is claimed.",
            "waiting_for": "Human review" if review_needed else "The next authorized Skill step",
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
    def _work_state(execution: Mapping[str, object]) -> dict[str, str]:
        if not execution:
            return {"current": "The AI Worker is ready to begin an authorized step.", "next": "Prepare the first bounded task.", "issue": ""}
        return {
            "current": str(execution.get("observation") or "The AI Worker restored the latest saved work state."),
            "next": str(execution.get("next_action") or "Evaluate the next authorized step."),
            "issue": str(execution.get("stop_reason") or ""),
        }

    @staticmethod
    def _completion(status: str, evidence_count: int, review_needed: bool, artifacts: Sequence[Mapping[str, str]], quality: Mapping[str, object], execution: Mapping[str, object]) -> dict[str, str]:
        if status in {"COMPLETED", "DELIVERY_READY"} and artifacts and not execution.get("stop_reason"):
            return {"status": "COMPLETED", "reason": "The Mission has a recorded delivery outcome and no unresolved runtime issue."}
        if review_needed or status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW"}:
            return {"status": "WAITING_REVIEW", "reason": "A human decision is required before this Mission can advance."}
        if evidence_count == 0 or str(quality.get("quality") or "") == "NEEDS_EVIDENCE":
            return {"status": "PARTIALLY_COMPLETED", "reason": "The Mission cannot claim a grounded research outcome until traceable Evidence is available."}
        if status in {"FAILED", "REJECTED"} or execution.get("stop_reason"):
            return {"status": "NEEDS_REVIEW", "reason": "A recorded issue or boundary needs human direction before work can continue."}
        return {"status": "IN_PROGRESS", "reason": "Bounded work remains before the existing review and delivery boundaries."}

    @staticmethod
    def _next_step(status: str, review_needed: bool, evidence_count: int, quality: Mapping[str, object], completion: Mapping[str, str]) -> str:
        if completion.get("status") == "COMPLETED":
            return "Review the completed delivery and reuse it only within its recorded evidence boundary."
        if completion.get("status") == "NEEDS_REVIEW":
            return "Review the recorded issue and decide whether to revise the Mission or stop it."
        if status in {"COMPLETED", "DELIVERY_READY"}:
            return "Review the completed delivery and reuse it only within its recorded evidence boundary."
        if status in {"FAILED", "REJECTED"}:
            return "Review the recorded issue and decide whether to revise the Mission or stop it."
        if review_needed or status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW"}:
            return "Review the AI Worker’s evidence-backed result before it can progress."
        if evidence_count == 0 or str(quality.get("quality") or "") == "NEEDS_EVIDENCE":
            return "Collect or validate traceable Evidence before asking the AI Worker for a research conclusion."
        return "The AI Worker can continue its next bounded, authorized Skill step."
