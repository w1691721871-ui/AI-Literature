"""P53 unified, approval-bounded runtime for the single AI Worker product role."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from typing import Any

from sqlalchemy import select

from app.models.runtime_execution import RuntimeExecution
from app.models.mission_contract import MissionContract as MissionContractRecord, RuntimeExecutionState
from app.services.adaptive_agent_service import AdaptiveAgentService
from app.services.autonomous_execution_service import AutonomousExecutionService
from app.services.ai_mission_service import AIMissionNotFoundError, AIMissionService
from app.services.ai_worker_service import AIWorkerService
from app.services.database import SessionLocal, initialize_database
from app.services.research_strategy_service import ResearchStrategyService
from app.services.mission_intelligence_service import MissionIntelligenceService
from app.services.mission_quality_service import MissionQualityService
from app.services.skill_capability_registry import SkillCapabilityRegistry
from app.services.skill_registry import SkillRegistry, SkillResult
from app.services.ai_team_orchestrator import AITeamOrchestrator
from app.services.workspace_context_service import WorkspaceContextService
from app.services.workspace_memory_service import WorkspaceMemoryService
from app.services.ai_employee_report_service import AIEmployeeReportService


class ResearchOrchestrator:
    """Product control role: selects existing Skills, never reimplements them."""

    def __init__(self, strategy_service: ResearchStrategyService | None = None):
        self._strategy = strategy_service or ResearchStrategyService()

    def build_plan(self, registry: SkillRegistry, mission: Mapping[str, Any]) -> list[tuple[str, object]]:
        return registry.plan(mission)

    def research_insight(self, mission: Mapping[str, Any]) -> dict[str, object]:
        """Expose a safe, Evidence-bounded strategy projection for the product UI."""
        return self._strategy.mission_insight(mission)


class AIWorkerRuntime:
    """Runs legacy capabilities as a single, finite, auditable AI Worker lifecycle."""

    # These are product-safe lifecycle states.  The detailed action history is
    # retained in RuntimeExecution; this field intentionally never stores a
    # prompt, a model trace, or a raw tool payload.
    EXECUTION_STATES = {
        "CREATED", "UNDERSTANDING", "PLANNING", "EXECUTING", "OBSERVING",
        "EVALUATING", "REPLANNING", "WAITING_REVIEW", "COMPLETED",
    }

    def __init__(
        self,
        session_factory: Callable = SessionLocal,
        *,
        initialize: bool = True,
        mission_service=None,
        worker_service=None,
        registry=None,
        adaptive_service=None,
        autonomous_service=None,
        mission_intelligence=None,
        quality_service=None,
        capability_registry=None,
        context_service=None,
        team_orchestrator=None,
        workspace_memory_service=None,
    ):
        if initialize:
            initialize_database()
        self._sessions = session_factory
        self._missions = mission_service or AIMissionService(session_factory, initialize=False)
        self._worker = worker_service or AIWorkerService()
        self._registry = registry or SkillRegistry(mission_service=self._missions)
        self._adaptive = adaptive_service or AdaptiveAgentService(session_factory, initialize=False)
        self._autonomous = autonomous_service or AutonomousExecutionService()
        self._capabilities = capability_registry or SkillCapabilityRegistry()
        self._intelligence = mission_intelligence or MissionIntelligenceService(session_factory, initialize=False, capabilities=self._capabilities)
        self._quality = quality_service or MissionQualityService()
        self._orchestrator = ResearchOrchestrator()
        self._context = context_service or WorkspaceContextService(session_factory, initialize=False)
        self._team = team_orchestrator or AITeamOrchestrator()
        self._workspace_memory = workspace_memory_service or WorkspaceMemoryService(session_factory, initialize=False)
        self._employee_report = AIEmployeeReportService()

    def snapshot(self, mission_id: str, *, actor=None) -> dict[str, object]:
        mission = self._mission(mission_id)
        context = self._context.build(mission, actor=actor)
        understanding = self._intelligence.analyze_mission_goal(str(mission.get("goal") or mission.get("title") or ""))
        contract = self._worker.contract_for_mission(mission)
        self._sync_contract(mission, contract, "CREATED")
        records = self._records(mission_id)
        execution = self._execution_state(mission_id)
        waiting_action = next((record["result_summary"] for record in reversed(records) if record["status"] == "WAITING_REVIEW"), None)
        computer_plan = None
        computer_execution = None
        if mission.get("computer_missions"):
            from app.services.computer_task_planner import ComputerTaskPlanner
            from app.services.computer_mission_runtime import ComputerMissionRuntime
            from app.services.artifact_service import ArtifactService
            from app.services.computer_strategy_service import ComputerStrategyService
            from app.services.computer_reflection_service import ComputerReflectionService
            computer_plan = ComputerTaskPlanner().plan(mission, context)
            artifacts = ArtifactService(self._sessions, initialize=False).list(mission_id)
            computer_execution = ComputerMissionRuntime().summarize(
                mission.get("computer_missions"), task_plan=computer_plan, artifacts=artifacts,
            )
            computer_intelligence = ComputerStrategyService().build(mission, context, computer_execution)
            computer_reflection = ComputerReflectionService().reflect(mission, computer_intelligence)
        else:
            computer_intelligence = None
            computer_reflection = None
        intelligence = self._mission_intelligence_snapshot(mission)
        return {
            "mission": {
                "id": mission["id"], "title": mission.get("title"), "objective": contract.objective,
                "status": mission.get("status"), "evidence_count": contract.context["evidence_count"],
                "approval_requirement": contract.approval_requirement,
            },
            "skills": self._team.presentation(self._registry, mission, context, understanding=understanding),
            "team_plan": self._team.plan_summary(self._registry, mission, context, understanding=understanding),
            "computer_plan": computer_plan,
            "computer_execution": computer_execution,
            "computer_intelligence": computer_intelligence,
            "computer_reflection": computer_reflection,
            "context": self._context.presentation(context),
            "timeline": records,
            "execution": execution,
            "research_insight": self._orchestrator.research_insight(mission),
            "mission_intelligence": intelligence,
            "autonomous_progress": self._autonomous.progress(mission, records),
            "employee_report": self._employee_report.build(
                mission,
                records,
                quality=intelligence.get("quality") if isinstance(intelligence, Mapping) else None,
                execution=execution,
            ),
            "status": execution["state"] if execution else (records[-1]["status"] if records else str(mission.get("status") or "CREATED")),
            "waiting_action": waiting_action,
        }

    def execute(self, mission_id: str, *, actor=None) -> dict[str, object]:
        mission = self._mission(mission_id)
        if str(mission.get("status") or "").upper() == "PAUSED":
            raise ValueError("Mission is paused. An authorized Workspace member must resume it before AI Worker execution.")
        context = self._context.build(mission, actor=actor)
        mission = {**mission, "ai_context": context}
        contract = self._worker.contract_for_mission(mission)
        if not contract.objective:
            raise ValueError("Mission Contract 缺少 objective。")

        self._sync_contract(mission, contract, "PLANNING")
        self._state(mission_id, "UNDERSTANDING", "AI Worker", "The AI Worker is checking the mission goal and authorized Workspace context.", "Mission goal is available.", "Prepare a bounded plan", "")
        self._prepare_mission_intelligence(mission)
        understanding = self._intelligence.analyze_mission_goal(str(mission.get("goal") or mission.get("title") or ""))
        self._state(mission_id, "PLANNING", "AI Worker", "Authorized Workspace context is ready.", "Identity, Workspace, Mission, Knowledge and approved Memory are available.", "Plan approved Skills", "")
        for index, (skill_id, adapter) in enumerate(self._team.plan(self._registry, mission, context, understanding=understanding), start=1):
            step_id = f"{skill_id}-{index}"
            adapter.validate(mission)
            record_id = self._record(mission_id, step_id, adapter.name, "PLAN", "PLANNED", "Skill added to the controlled AI Worker plan.", "")
            self._update(record_id, "RUNNING", "Skill execution started within existing service boundaries.", "")
            self._state(mission_id, "EXECUTING", adapter.name, "The AI Worker started an authorized Skill step.", "", "Observe the result", "")
            self._set_mission_phase(mission, "OBSERVE")
            try:
                result = adapter.execute(mission)
            except Exception as error:
                result = SkillResult("FAILED", "A controlled Skill action failed.", self._safe_error(error), "EXECUTE")

            self._state(mission_id, "OBSERVING", adapter.name, adapter.observe(result), "The result is being checked against the Mission goal.", "Evaluate the result", "")
            status = "WAITING_REVIEW" if result.status in {"WAITING_REVIEW", "NEEDS_EVIDENCE"} else result.status
            observation = adapter.observe(result)
            summary = result.result_summary
            if result.status in {"NEEDS_EVIDENCE", "FAILED"}:
                decision = self._adaptive.run_once(mission_id)
                observation = f"{observation} Adaptive decision: {decision.get('decision', 'REQUEST_REVIEW')}."
                summary = f"{summary} {decision.get('summary', '')}".strip()
                status = "WAITING_REVIEW" if decision.get("decision") == "REQUEST_REVIEW" else "FAILED" if result.status == "FAILED" else "WAITING_REVIEW"
                # A successful evidence-retrieval decision is the one safe
                # continuation that can happen without another human action:
                # it is read-only, remains inside the existing Research Skill,
                # and runs at most once in this execution window.  Everything
                # else (including failed actions, Computer work, and a second
                # insufficient result) stays at the established review gate.
                if (
                    result.status == "NEEDS_EVIDENCE"
                    and decision.get("decision") == "CONTINUE"
                    and skill_id == "research"
                ):
                    self._update(
                        record_id,
                        "REPLANNING",
                        observation,
                        f"{summary} One bounded evidence follow-up is now running.",
                        result.action_type,
                    )
                    self._state(
                        mission_id,
                        "REPLANNING",
                        adapter.name,
                        "The first evidence pass was insufficient; the AI Worker is running one approved read-only follow-up.",
                        "The existing adaptive policy recovered traceable candidate references.",
                        "Verify the follow-up result",
                        "",
                    )
                    mission = self._mission(mission_id)
                    context = self._context.build(mission, actor=actor)
                    mission = {**mission, "ai_context": context}
                    retry_id = self._record(
                        mission_id,
                        f"{step_id}-replan",
                        adapter.name,
                        "REPLAN",
                        "PLANNED",
                        "One bounded, read-only evidence follow-up was authorized by the existing adaptive policy.",
                        "",
                    )
                    self._update(retry_id, "RUNNING", "Bounded evidence follow-up started.", "")
                    try:
                        result = adapter.execute(mission)
                    except Exception as error:
                        result = SkillResult("FAILED", "A bounded evidence follow-up did not complete.", self._safe_error(error), "RETRIEVE_EVIDENCE")
                    record_id = retry_id
                    observation = adapter.observe(result)
                    summary = result.result_summary
                    status = "WAITING_REVIEW" if result.status in {"WAITING_REVIEW", "NEEDS_EVIDENCE"} else result.status
            # Mission state can change inside an adapter. It is reloaded only
            # after the action, never synthesized from an internal trace.
            mission = self._mission(mission_id)
            context = self._context.build(mission, actor=actor)
            mission = {**mission, "ai_context": context}
            latest_contract = self._worker.contract_for_mission(mission)
            intelligence_state = self._complete_mission_skill(mission, skill_id, result.status)
            quality = self._quality.evaluate_completion(mission, intelligence_state)
            self._set_mission_phase(mission, "QUALITY_CHECK", quality_status=str(quality["quality"]), blocked_reason="" if result.status == "SUCCESS" else result.status)
            mission_decision = self._autonomous.decide_next_step(
                {"workspace_id": mission.get("workspace_id"), "evidence_refs": mission.get("evidence_refs") or [], "approval_state": latest_contract.approval_requirement},
                intelligence_state,
                {"status": result.status, "action_type": result.action_type, "summary": observation},
                workspace_id=mission.get("workspace_id"),
            )
            if mission_decision["decision"] == "REPLAN":
                self._replan_mission(mission, {"status": result.status, "summary": observation})
                self._state(mission_id, "REPLANNING", adapter.name, "The current Evidence set is insufficient, so the AI Worker queued one bounded research adjustment.", str(mission_decision["reason"]), "Continue the approved research plan", str(mission_decision["stop_reason"]))
            autonomous = self._autonomous.evaluate_current_state(
                {
                    "workspace_id": mission.get("workspace_id"),
                    "evidence_refs": mission.get("evidence_refs") or [],
                    "approval_state": latest_contract.approval_requirement,
                    "execution_state": "COMPLETED" if str(mission.get("status") or "").upper() == "COMPLETED" else "",
                },
                {"completed_steps": index, "max_steps": self._autonomous.MAX_STEPS, "current_skill": adapter.name, **intelligence_state},
                {"status": result.status, "action_type": result.action_type, "summary": observation},
                workspace_id=mission.get("workspace_id"),
            )
            self._state(mission_id, "EVALUATING", adapter.name, observation, str(autonomous["reason"]), str(autonomous["action"]), str(autonomous["stop_reason"]))
            if autonomous["decision"] in {"REQUEST_REVIEW", "STOP"} and status == "SUCCESS":
                status = "WAITING_REVIEW" if autonomous["decision"] == "REQUEST_REVIEW" else "FAILED"
                summary = f"{summary} {autonomous['reason']}".strip()
            self._update(record_id, status, observation, summary, result.action_type)
            execution_state = "WAITING_REVIEW" if status in {"WAITING_REVIEW", "FAILED"} else "EXECUTING"
            next_action = "Human review required" if status == "WAITING_REVIEW" else str(autonomous["action"])
            self._state(mission_id, execution_state, adapter.name, observation, adapter.evaluate(result), next_action, str(autonomous["stop_reason"]))
            if status != "SUCCESS" or autonomous["decision"] == "STOP":
                self._sync_contract(mission, latest_contract, execution_state, str(autonomous["stop_reason"] or result.status))
                break
        else:
            self._sync_contract(mission, self._worker.contract_for_mission(mission), "COMPLETED")
            self._state(mission_id, "COMPLETED", "AI Worker", "All bounded Skill steps completed.", "The Mission has reached its recorded completion boundary.", "Review the completed delivery", "")
        self._workspace_memory.record_mission_summary(mission, owner_id=getattr(actor, "user_id", None))
        snapshot = self.snapshot(mission_id, actor=actor)
        self._remember_computer_reflection(mission, snapshot)
        return self.snapshot(mission_id, actor=actor)

    def resume(self, mission_id: str, *, actor=None) -> dict[str, object]:
        """Continue from persisted, authorized state instead of restarting a Mission.

        Pause/resume is only observable between bounded Skill actions because
        execution is synchronous.  The method therefore reloads the saved
        Mission, current runtime state, and fresh Workspace Context before it
        makes a continuation decision.  Review and security boundaries are
        never resumed automatically.
        """
        mission = self._mission(mission_id)
        context = self._context.build(mission, actor=actor)
        previous = self._execution_state(mission_id) or {}
        status = str(mission.get("status") or "").upper()
        if status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW", "FAILED", "REJECTED", "COMPLETED"}:
            self._state(
                mission_id,
                "WAITING_REVIEW" if status.startswith("WAITING") else "COMPLETED" if status == "COMPLETED" else "EVALUATING",
                str(previous.get("skill") or "AI Worker"),
                str(previous.get("observation") or "The Mission was resumed from its saved state."),
                "The existing review, failure, or completion boundary remains in effect.",
                "Review the saved Mission state before any further work.",
                str(previous.get("stop_reason") or status),
            )
            return self.snapshot(mission_id, actor=actor)
        if status not in {"CREATED", "PLANNING", "NEEDS_REVISION", "ADAPTIVE_REPLANNING", "APPROVED"}:
            return self.snapshot(mission_id, actor=actor)
        self._state(
            mission_id,
            "PLANNING",
            str(previous.get("skill") or "AI Worker"),
            "The AI Worker restored the saved Mission context, latest observation, and next authorized step.",
            "The saved Workspace boundary and current approval requirements were checked again.",
            "Continue the next bounded authorized Skill",
            "",
        )
        # Context is rebuilt above rather than reused from a prior request;
        # this protects a resumed Mission from stale membership or workspace
        # state. ``execute`` rebuilds it again immediately before the Skill.
        del context
        return self.execute(mission_id, actor=actor)

    def _remember_computer_reflection(self, mission: Mapping[str, Any], snapshot: Mapping[str, object]) -> None:
        """Persist a terminal Computer learning via existing safe Workspace Memory."""
        execution = snapshot.get("computer_execution") if isinstance(snapshot.get("computer_execution"), Mapping) else {}
        reflection = snapshot.get("computer_reflection") if isinstance(snapshot.get("computer_reflection"), Mapping) else {}
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id or not execution or str(execution.get("status") or "") not in {"COMPLETED", "NEEDS_REVIEW"}:
            return
        from app.services.computer_intelligence_service import ComputerIntelligenceService
        from app.services.computer_reflection_service import ComputerReflectionService
        ComputerReflectionService().remember(workspace_id, reflection, ComputerIntelligenceService(self._sessions, initialize=False))

    def _sync_contract(self, mission, contract, execution_state: str, stop_reason: str = "") -> None:
        """Persist a contract only for a workspace-bound Mission; legacy data stays readable."""
        workspace_id = mission.get("workspace_id")
        if not workspace_id:
            return
        session = self._sessions()
        try:
            row = session.scalar(select(MissionContractRecord).where(MissionContractRecord.mission_id == mission["id"]))
            task_type = str(mission.get("type") or "RESEARCH").upper()
            if task_type not in {"RESEARCH", "COMPUTER", "DELIVERY", "REVIEW"}:
                task_type = "RESEARCH"
            data = {
                "workspace_id": workspace_id, "goal": contract.objective,
                "task_type": task_type,
                "input_context": json.dumps(contract.context, ensure_ascii=False),
                "available_skills": json.dumps([skill.model_dump() for skill in contract.available_skills], ensure_ascii=False),
                "evidence_refs": json.dumps(mission.get("evidence_refs") or [], ensure_ascii=False),
                "approval_state": contract.approval_requirement, "execution_state": execution_state,
                "stop_reason": stop_reason or contract.stop_reason or "",
            }
            if row is None:
                row = MissionContractRecord(mission_id=mission["id"], owner_id=None, artifact_refs="[]", **data); session.add(row)
            else:
                for key, value in data.items(): setattr(row, key, value)
            session.commit()
        finally:
            session.close()

    def _prepare_mission_intelligence(self, mission: Mapping[str, Any]) -> None:
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id:
            return
        understanding = self._intelligence.analyze_mission_goal(str(mission.get("goal") or mission.get("title") or ""))
        plan = self._intelligence.build_task_plan(str(mission["id"]), understanding)
        self._intelligence.ensure_state(str(mission["id"]), workspace_id, plan)
        self._intelligence.set_phase(str(mission["id"]), workspace_id, "PLAN")
        self._state(str(mission["id"]), "PLANNING", "AI Worker", "Mission goal was translated into existing Skill tasks.", "User-readable task plan created.", "Execute bounded Skill", "")

    def _complete_mission_skill(self, mission: Mapping[str, Any], skill_id: str, result_status: str) -> dict[str, object]:
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id:
            return {"pending_tasks": [], "completed_tasks": [], "blocked_reason": "", "replan_count": 0, "max_replan_count": 2}
        return self._intelligence.complete_skill_task(str(mission["id"]), workspace_id, skill_id, blocked=result_status != "SUCCESS")

    def _set_mission_phase(self, mission: Mapping[str, Any], phase: str, **kwargs) -> None:
        workspace_id = str(mission.get("workspace_id") or "")
        if workspace_id:
            self._intelligence.set_phase(str(mission["id"]), workspace_id, phase, **kwargs)

    def _replan_mission(self, mission: Mapping[str, Any], observation: Mapping[str, object]) -> None:
        workspace_id = str(mission.get("workspace_id") or "")
        if workspace_id:
            refs = mission.get("evidence_refs")
            self._intelligence.replan_mission(str(mission["id"]), workspace_id, observation, len(refs) if isinstance(refs, list) else 0)

    def _mission_intelligence_snapshot(self, mission: Mapping[str, Any]) -> dict[str, object]:
        understanding = self._intelligence.analyze_mission_goal(str(mission.get("goal") or mission.get("title") or ""))
        workspace_id = str(mission.get("workspace_id") or "")
        if workspace_id:
            plan = self._intelligence.build_task_plan(str(mission["id"]), understanding)
            state = self._intelligence.ensure_state(str(mission["id"]), workspace_id, plan)
        else:
            state = {"current_phase": "CREATED", "completed_tasks": [], "pending_tasks": self._intelligence.build_task_plan(str(mission["id"]), understanding), "blocked_reason": "", "replan_count": 0, "max_replan_count": 2, "quality_status": "NOT_EVALUATED"}
        quality = self._quality.evaluate_completion(mission, state)
        return {"understanding": understanding, "current_phase": state["current_phase"], "completed_tasks": state["completed_tasks"], "pending_tasks": state["pending_tasks"], "blocked_reason": state["blocked_reason"], "replan_count": state["replan_count"], "max_replan_count": state["max_replan_count"], "quality": quality}

    def _state(self, mission_id, current_step, current_skill, observation, evaluation, next_action, stop_reason) -> None:
        if current_step not in self.EXECUTION_STATES:
            raise ValueError(f"Unsupported AI Worker execution state: {current_step}")
        session = self._sessions()
        try:
            row = session.scalar(select(RuntimeExecutionState).where(RuntimeExecutionState.mission_id == mission_id))
            if row is None:
                row = RuntimeExecutionState(mission_id=mission_id); session.add(row)
            row.current_step=current_step; row.current_skill=current_skill; row.observation_summary=observation; row.evaluation_result=evaluation; row.next_action=next_action; row.stop_reason=stop_reason
            session.commit()
        finally:
            session.close()

    def _execution_state(self, mission_id: str) -> dict[str, object] | None:
        session = self._sessions()
        try:
            row = session.scalar(select(RuntimeExecutionState).where(RuntimeExecutionState.mission_id == mission_id))
            if row is None:
                return None
            return {
                "state": row.current_step,
                "skill": row.current_skill,
                "observation": row.observation_summary,
                "evaluation": row.evaluation_result,
                "next_action": row.next_action,
                "stop_reason": row.stop_reason,
                "updated_at": row.updated_at,
            }
        finally:
            session.close()

    def _mission(self, mission_id: str) -> dict[str, Any]:
        try:
            mission = self._missions.detail(mission_id)
        except AIMissionNotFoundError:
            raise
        if not mission:
            raise AIMissionNotFoundError("AI Mission 不存在。")
        return dict(mission)

    def _record(self, mission_id: str, step_id: str, skill: str, action: str, status: str, observation: str, result: str) -> str:
        session = self._sessions()
        try:
            row = RuntimeExecution(mission_id=mission_id, step_id=step_id, skill=skill, action_type=action, status=status, observation_summary=observation, result_summary=result)
            session.add(row); session.commit(); return row.id
        finally:
            session.close()

    def _update(self, record_id: str, status: str, observation: str, result: str, action: str | None = None) -> None:
        session = self._sessions()
        try:
            row = session.get(RuntimeExecution, record_id)
            if row is None:
                raise ValueError("Runtime execution record 不存在。")
            row.status = status
            row.observation_summary = observation
            row.result_summary = result
            if action:
                row.action_type = action
            session.commit()
        finally:
            session.close()

    def _records(self, mission_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            rows = session.scalars(select(RuntimeExecution).where(RuntimeExecution.mission_id == mission_id).order_by(RuntimeExecution.created_at.asc())).all()
            return [{"id": row.id, "step_id": row.step_id, "skill": row.skill, "action_type": row.action_type, "status": row.status, "observation_summary": row.observation_summary, "result_summary": row.result_summary, "created_at": row.created_at} for row in rows]
        finally:
            session.close()

    @staticmethod
    def _safe_error(error: Exception) -> str:
        # Do not expose stack traces, prompts, secrets, or raw model outputs.
        return f"{type(error).__name__}: controlled Skill execution did not complete."
