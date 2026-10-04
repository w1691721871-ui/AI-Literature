"""Explainable, bounded strategy selection for the existing Computer Skill.

This is deliberately a planning adapter: it selects a safe route from
authorized Mission context and persisted controlled-Mission state.  It neither
executes actions nor turns unverified sources into Evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class ComputerStrategyService:
    """Choose the next controlled Computer route without hidden reasoning."""

    def build(
        self,
        mission: Mapping[str, object],
        context: Mapping[str, object],
        computer_execution: Mapping[str, object] | None,
    ) -> dict[str, object]:
        goal = str(mission.get("goal") or mission.get("title") or "").strip()
        environment = self._environment(computer_execution)
        state = self._workspace_state(mission, context, computer_execution)
        options = self._options(mission, context, environment)
        selected = self._select(options, computer_execution)
        decision = self._decision(selected, computer_execution)
        quality = self._quality(mission, computer_execution)
        return {
            "strategy": selected,
            "alternatives": options,
            "decision": decision,
            "workspace_state": state,
            "quality": quality,
            "employee_summary": self._summary(goal, selected, decision, quality),
            "boundary": "Strategy uses only current Workspace metadata, authorized Computer Memory summaries and controlled-Mission state. It never exposes prompts, secrets, source bodies or internal reasoning.",
        }

    @staticmethod
    def _environment(execution: Mapping[str, object] | None) -> dict[str, object]:
        execution = execution or {}
        observation = execution.get("observation") if isinstance(execution.get("observation"), Mapping) else {}
        return {
            "current_state": str(observation.get("state") or "not observed"),
            "available_actions": [str(item) for item in observation.get("available_actions", []) if isinstance(item, str)][:6],
            "vision_mode": str(observation.get("vision_mode") or "demo_only"),
            "risk_level": "HIGH" if str(execution.get("status") or "") == "WAITING_APPROVAL" else "LOW",
        }

    @staticmethod
    def _workspace_state(
        mission: Mapping[str, object], context: Mapping[str, object], execution: Mapping[str, object] | None
    ) -> dict[str, object]:
        knowledge = context.get("knowledge") if isinstance(context.get("knowledge"), Mapping) else {}
        computer_memory = context.get("computer_memory") if isinstance(context.get("computer_memory"), list) else []
        artifacts = context.get("artifacts") if isinstance(context.get("artifacts"), list) else []
        status = str((execution or {}).get("status") or "READY")
        return {
            "available_resources": {
                "traceable_evidence": len(knowledge.get("traceable_evidence_refs", []) or []),
                "approved_artifacts": len(artifacts),
                "authorized_computer_memory": len(computer_memory),
            },
            "completed_task": status == "COMPLETED",
            "in_progress": status == "RUNNING",
            "requires_user_action": status in {"WAITING_APPROVAL", "NEEDS_REVIEW"},
            "failed_task": status == "NEEDS_REVIEW",
            "mission_id": mission.get("id"),
        }

    @staticmethod
    def _options(mission: Mapping[str, object], context: Mapping[str, object], environment: Mapping[str, object]) -> list[dict[str, object]]:
        goal = str(mission.get("goal") or mission.get("title") or "")
        lowered = goal.lower()
        evidence = len(((context.get("knowledge") or {}).get("traceable_evidence_refs") or [])) if isinstance(context.get("knowledge"), Mapping) else 0
        source_materials = mission.get("source_materials")
        has_authorized_material = isinstance(source_materials, Sequence) and not isinstance(source_materials, (str, bytes)) and bool(source_materials)
        options = []
        if any(term in lowered for term in ("paper", "research", "literature", "论文", "研究", "资料")):
            if has_authorized_material:
                options.append({"id": "AUTHORIZED_MATERIAL", "label": "Analyze authorized material", "reason": "Use already authorized Workspace material before requesting additional public sources.", "requires_approval": False})
            options.append({"id": "PUBLIC_DISCOVERY", "label": "Collect public research candidates", "reason": "Public candidates can fill an Evidence gap but remain candidates until validated.", "requires_approval": False})
        if any(term in lowered for term in ("data", "table", "dataset", "数据", "表格")):
            options.append({"id": "READ_ONLY_DATA", "label": "Prepare a read-only data summary", "reason": "Authorized data can be summarized without modifying the source.", "requires_approval": True})
        if any(term in lowered for term in ("report", "brief", "proposal", "报告", "调研", "方案")) or evidence:
            options.append({"id": "REVIEWABLE_DELIVERY", "label": "Prepare a reviewable delivery", "reason": "A versioned draft can be prepared only from traceable Evidence and remains pending review.", "requires_approval": True})
        if not options:
            options.append({"id": "SAFE_CLARIFICATION", "label": "Request task clarification", "reason": "No safe route can be selected until the outcome and authorized material are clear.", "requires_approval": False})
        return options[:3]

    @staticmethod
    def _select(options: Sequence[Mapping[str, object]], execution: Mapping[str, object] | None) -> dict[str, object]:
        status = str((execution or {}).get("status") or "READY")
        if status in {"WAITING_APPROVAL", "NEEDS_REVIEW"}:
            return {"id": "HUMAN_REVIEW", "label": "Wait for human review", "reason": "A controlled task already reached a mandatory human decision boundary.", "requires_approval": True}
        return dict(options[0]) if options else {"id": "SAFE_CLARIFICATION", "label": "Request task clarification", "reason": "No route is available.", "requires_approval": False}

    @staticmethod
    def _decision(strategy: Mapping[str, object], execution: Mapping[str, object] | None) -> dict[str, str]:
        status = str((execution or {}).get("status") or "READY")
        if status in {"WAITING_APPROVAL", "NEEDS_REVIEW"} or strategy.get("requires_approval"):
            return {"action": "WAIT_REVIEW", "reason": "The selected route has an existing human approval or review boundary."}
        if str(strategy.get("id")) == "SAFE_CLARIFICATION":
            return {"action": "REQUEST_INPUT", "reason": "The current Mission does not establish a safe, authorized outcome."}
        return {"action": "EXECUTE", "reason": "The selected route is read-only or Evidence-gated within the existing Computer Skill boundary."}

    @staticmethod
    def _quality(mission: Mapping[str, object], execution: Mapping[str, object] | None) -> dict[str, object]:
        execution = execution or {}
        status = str(execution.get("status") or "READY")
        artifact = execution.get("artifact") if isinstance(execution.get("artifact"), Mapping) else {}
        evidence_count = int(artifact.get("evidence_count") or len(mission.get("evidence_refs") or []))
        if status == "NEEDS_REVIEW":
            return {"status": "NEEDS_REVIEW", "summary": "The result has an unresolved verification or approval requirement.", "evidence_coverage": evidence_count}
        if status == "COMPLETED" and artifact:
            return {"status": "REVIEWABLE", "summary": "A result exists but remains subject to the existing human review workflow.", "evidence_coverage": evidence_count}
        return {"status": "IN_PROGRESS", "summary": "Quality will be assessed after a controlled result and verification are available.", "evidence_coverage": evidence_count}

    @staticmethod
    def _summary(goal: str, strategy: Mapping[str, object], decision: Mapping[str, object], quality: Mapping[str, object]) -> dict[str, str]:
        return {
            "completed": "No new Computer outcome has been completed in this strategy assessment.",
            "approach": str(strategy.get("label") or "Safe controlled route"),
            "issue": "Human review is required before continuing." if decision.get("action") == "WAIT_REVIEW" else "No blocking issue is currently recorded.",
            "next_step": str(decision.get("reason") or "Review the controlled Mission state."),
            "quality_status": str(quality.get("status") or "IN_PROGRESS"),
            "goal": goal[:240],
        }
