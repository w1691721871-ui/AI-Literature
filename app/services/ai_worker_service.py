"""AI Worker compatibility layer over existing ResearchOS services.

It deliberately does not execute research, retrieval, computer actions, or
delivery.  Those remain owned by the mature services already in the project.
The layer gives the product one understandable worker and four capabilities.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.schemas.mission_contract import MissionContract, WorkerSkill


class AIWorkerService:
    """Translate legacy Agent names into a single AI Worker capability model."""

    _SKILLS = (
        WorkerSkill(
            id="research",
            name="Research Skill",
            description="Plans evidence-backed research and retrieves traceable knowledge.",
            evidence_required=True,
        ),
        WorkerSkill(
            id="computer",
            name="Computer Skill",
            description="Analyzes a permitted workspace and prepares reviewable changes.",
            approval_required=True,
        ),
        WorkerSkill(
            id="delivery",
            name="Delivery Skill",
            description="Creates versioned, reviewable outputs linked to their evidence.",
            evidence_required=True,
            approval_required=True,
        ),
        WorkerSkill(
            id="review",
            name="Review Skill",
            description="Checks evidence boundaries, risks, and required human decisions.",
            approval_required=True,
        ),
    )

    # Kept private: these adapters preserve the existing implementation while
    # keeping internal role naming out of the ordinary user experience.
    _ADAPTERS = {
        "Research Skill": ("Research Agent", "Literature Agent", "Innovation Agent"),
        "Computer Skill": ("Computer Agent",),
        "Delivery Skill": ("Delivery Agent",),
        "Review Skill": ("Risk Agent", "Planner", "Evaluator", "Benchmark Agent", "Computer Runtime"),
    }

    def capabilities(self) -> dict[str, object]:
        return {
            "worker": {
                "name": "AI Worker",
                "description": "A controlled enterprise worker that plans, uses approved skills, and waits for human review.",
            },
            "skills": [skill.model_dump() for skill in self._SKILLS],
            "boundary": "Skills are adapters over existing ResearchOS services; they do not create unsupported Evidence or bypass approval.",
        }

    def contract_for_mission(self, mission: Mapping[str, object]) -> MissionContract:
        """Return a product contract from an existing Mission payload.

        This is a read-only adapter: legacy persistence and lifecycle state are
        not changed.  Unknown/legacy states remain visible instead of being
        silently promoted to a successful Worker state.
        """
        evidence_refs = mission.get("evidence_refs", [])
        evidence_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0
        goal = str(mission.get("goal") or mission.get("title") or "Untitled mission").strip()
        status = str(mission.get("status") or "CREATED")
        requires_review = status not in {"COMPLETED", "REJECTED", "FAILED"}
        stop_reason = mission.get("stop_reason")
        if stop_reason is not None:
            stop_reason = str(stop_reason)
        elif status in {"FAILED", "REJECTED"}:
            stop_reason = status

        return MissionContract(
            objective=goal,
            context={
                "mission_id": str(mission.get("id") or ""),
                "mission_type": str(mission.get("type") or mission.get("mission_type") or "RESEARCH"),
                "current_step": str(mission.get("current_step") or "Created"),
                "evidence_count": evidence_count,
                "review_status": status,
            },
            available_skills=list(self._SKILLS),
            evidence_requirement="TRACEABLE_EVIDENCE_REQUIRED",
            approval_requirement="HUMAN_REVIEW_REQUIRED" if requires_review else "REVIEW_RECORDED",
            outputs=["Evidence references", "Reviewable delivery draft", "Human review decision"],
            status=status,
            stop_reason=stop_reason,
        )

    def internal_adapters(self) -> dict[str, tuple[str, ...]]:
        """For code-level diagnostics only; never required by the user UI."""
        return dict(self._ADAPTERS)
