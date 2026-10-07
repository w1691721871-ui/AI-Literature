"""SQLite-backed checkpointing and safe restart assessment for AI Worker Missions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.models.ai_mission import AIMission
from app.models.mission_execution_checkpoint import MissionExecutionCheckpoint, MissionExecutionLease
from app.services.database import SessionLocal, initialize_database


class MissionLeaseError(RuntimeError):
    pass


class PersistentMissionExecutionService:
    """Persists bounded progress; restart recovery never replays unknown actions."""

    ACTIVE_PHASES = {"UNDERSTANDING", "PLANNING", "EXECUTING", "OBSERVING", "EVALUATING", "REPLANNING", "RECOVERING"}
    TERMINAL_PHASES = {"COMPLETED", "WAITING_REVIEW", "FAILED", "STOPPED", "PAUSED"}
    READ_ONLY_ACTIONS = {"RESEARCH", "COLLECT_EVIDENCE", "RETRIEVE_EVIDENCE", "SEARCH", "NAVIGATE", "EXTRACT", "VERIFY", "PLAN"}
    MAX_RECOVERY = 2
    MAX_TOTAL_STEPS = 5
    LEASE_SECONDS = 90

    def __init__(self, sessions=SessionLocal, *, initialize=True, worker_id: str | None = None):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self.worker_id = worker_id or f"worker-{uuid4().hex[:12]}"

    def checkpoint(self, mission: dict[str, object], *, phase: str, objective: str = "", next_action: str = "", observation: str = "", evaluation: str = "", waiting_reason: str = "", resume_policy: str | None = None) -> dict[str, object]:
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id:
            return {}
        session = self._sessions()
        try:
            row = self._row(session, str(mission["id"]), workspace_id, mission)
            row.phase = phase
            row.goal_summary = self._summary(mission.get("goal") or mission.get("title"))
            row.current_objective = self._summary(objective or row.current_objective)
            row.next_action = self._summary(next_action or row.next_action, 160)
            row.last_observation_summary = self._summary(observation or row.last_observation_summary)
            row.last_evaluation_summary = self._summary(evaluation or row.last_evaluation_summary)
            row.waiting_reason = self._summary(waiting_reason or "")
            if resume_policy:
                row.resume_policy = resume_policy
            session.commit()
            return self._data(row)
        finally:
            session.close()

    def begin_action(self, mission: dict[str, object], step_id: str, action_type: str, *, objective: str, safety: str = "READ_ONLY") -> dict[str, object]:
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id:
            return {"execute": True, "action_key": ""}
        session = self._sessions()
        try:
            row = self._row(session, str(mission["id"]), workspace_id, mission)
            action_key = f"{mission['id']}:{row.id}:{step_id}:{action_type}"
            completed = self._decode(row.completed_steps_summary)
            if len(completed) >= self.MAX_TOTAL_STEPS and step_id not in completed:
                row.phase = "WAITING_REVIEW"; row.resume_policy = "NEEDS_REVIEW"
                row.waiting_reason = "AI Employee reached the safe execution limit for this Mission and needs human direction."
                session.commit()
                return {"execute": False, "action_key": action_key, "reason": row.waiting_reason}
            if row.action_key == action_key and row.action_status == "ACTION_VERIFIED":
                return {"execute": False, "action_key": action_key, "reason": "This bounded action was already verified."}
            if row.action_status == "ACTION_STARTED":
                # A crash after an action started is never assumed successful.
                row.phase = "WAITING_REVIEW"
                row.waiting_reason = "A previous action was interrupted before its result was recorded. Review is required before retrying."
                row.resume_policy = "NEEDS_REVIEW"
                session.commit()
                return {"execute": False, "action_key": row.action_key, "reason": row.waiting_reason}
            row.phase = "EXECUTING"; row.current_objective = self._summary(objective)
            row.action_key = action_key; row.action_status = "ACTION_STARTED"; row.action_safety = safety
            row.next_action = "Observe and verify the bounded result"; row.waiting_reason = ""
            row.resume_policy = "RESUME_ELIGIBLE"
            session.commit()
            return {"execute": True, "action_key": action_key}
        finally:
            session.close()

    def observe_action(self, mission_id: str, observation: str) -> None:
        self._action_update(mission_id, "ACTION_OBSERVED", observation=observation)

    def verify_action(self, mission_id: str, *, step_id: str, observation: str, evaluation: str, success: bool, waiting_reason: str = "") -> None:
        session = self._sessions()
        try:
            row = session.scalar(select(MissionExecutionCheckpoint).where(MissionExecutionCheckpoint.mission_id == mission_id))
            if row is None:
                return
            completed = self._decode(row.completed_steps_summary)
            if success and step_id not in completed:
                completed.append(step_id)
            row.completed_steps_summary = json.dumps(completed, ensure_ascii=False)
            row.action_status = "ACTION_VERIFIED" if success else "ACTION_FAILED"
            row.phase = "EVALUATING" if success else "WAITING_REVIEW"
            row.last_observation_summary = self._summary(observation)
            row.last_evaluation_summary = self._summary(evaluation)
            row.waiting_reason = self._summary(waiting_reason)
            row.resume_policy = "RESUME_ELIGIBLE" if success else "NEEDS_REVIEW"
            session.commit()
        finally:
            session.close()

    def claim(self, mission: dict[str, object]) -> bool:
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id:
            return True
        now = self._now()
        session = self._sessions()
        try:
            existing = session.scalar(select(MissionExecutionLease).where(MissionExecutionLease.mission_id == mission["id"]))
            if existing and existing.lease_expires_at.replace(tzinfo=timezone.utc) > now and existing.worker_id != self.worker_id:
                return False
            if existing is None:
                existing = MissionExecutionLease(mission_id=str(mission["id"]), worker_id=self.worker_id, lease_expires_at=now + timedelta(seconds=self.LEASE_SECONDS)); session.add(existing)
            else:
                existing.worker_id = self.worker_id; existing.lease_started_at = now; existing.lease_expires_at = now + timedelta(seconds=self.LEASE_SECONDS)
            session.commit(); return True
        finally:
            session.close()

    def release(self, mission_id: str) -> None:
        session = self._sessions()
        try:
            row = session.scalar(select(MissionExecutionLease).where(MissionExecutionLease.mission_id == mission_id, MissionExecutionLease.worker_id == self.worker_id))
            if row:
                session.delete(row); session.commit()
        finally:
            session.close()

    def authorize_reviewed_continuation(self, mission: dict[str, object]) -> dict[str, object] | None:
        """Open a new bounded action only after the Mission's existing review approves it."""
        workspace_id = str(mission.get("workspace_id") or "")
        if not workspace_id or str(mission.get("status") or "").upper() != "APPROVED":
            return None
        session = self._sessions()
        try:
            row = session.scalar(select(MissionExecutionCheckpoint).where(MissionExecutionCheckpoint.mission_id == mission["id"]))
            if row is None or row.workspace_id != workspace_id:
                return None
            if row.resume_policy != "NEEDS_REVIEW":
                return self._data(row)
            # Approval never certifies an interrupted action as successful.
            # It only authorizes a *new* bounded action after the reviewer has
            # considered the uncertainty.
            row.phase = "PLANNING"; row.resume_policy = "RESUME_ELIGIBLE"
            row.action_key = ""; row.action_status = "ACTION_REVIEWED"; row.action_safety = ""
            row.waiting_reason = ""; row.next_action = "Run the next approved bounded step."
            session.commit(); return self._data(row)
        finally:
            session.close()

    def recovery_scan(self) -> dict[str, int]:
        """Run at startup: classify interrupted work but never auto-execute it."""
        session = self._sessions()
        recovered = review = 0
        try:
            rows = session.scalars(select(MissionExecutionCheckpoint)).all()
            for row in rows:
                mission = session.get(AIMission, row.mission_id)
                mission_status = str(mission.status or "").upper() if mission else ""
                # The Mission lifecycle remains authoritative: a restart must
                # not turn a deliberately paused, completed, or review-bound
                # Mission into runnable work merely because an older
                # checkpoint recorded an active phase.
                if mission_status == "PAUSED":
                    row.phase = "PAUSED"; row.resume_policy = "PAUSED"
                    row.next_action = "An authorized Workspace member must resume this Mission."
                    continue
                if mission_status in {"COMPLETED", "DELIVERY_READY"}:
                    row.phase = "COMPLETED"; row.resume_policy = "TERMINAL"
                    continue
                if mission_status in {"WAITING_REVIEW", "WAITING_ADAPTIVE_REVIEW", "FAILED", "REJECTED"}:
                    row.phase = "WAITING_REVIEW"; row.resume_policy = "NEEDS_REVIEW"
                    if not row.waiting_reason:
                        row.waiting_reason = "The Mission already has a human review or recorded failure boundary."
                    continue
                if row.phase not in self.ACTIVE_PHASES:
                    continue
                if row.action_status == "ACTION_STARTED":
                    row.phase = "WAITING_REVIEW"; row.resume_policy = "NEEDS_REVIEW"
                    row.waiting_reason = "The service restarted while an action result was unknown. Human review is required before any retry."
                    review += 1
                elif row.recovery_count >= self.MAX_RECOVERY:
                    row.phase = "WAITING_REVIEW"; row.resume_policy = "NEEDS_REVIEW"
                    row.waiting_reason = "The Mission reached its safe recovery limit and needs human review."
                    review += 1
                else:
                    row.phase = "RECOVERING"; row.resume_policy = "RESUME_ELIGIBLE"; row.recovery_count += 1
                    row.next_action = "An authorized Workspace member can continue the next bounded step."
                    recovered += 1
            session.commit()
            return {"resume_eligible": recovered, "waiting_review": review}
        finally:
            session.close()

    def snapshot(self, mission_id: str, workspace_id: str | None = None) -> dict[str, object] | None:
        session = self._sessions()
        try:
            row = session.scalar(select(MissionExecutionCheckpoint).where(MissionExecutionCheckpoint.mission_id == mission_id))
            if not row or (workspace_id and row.workspace_id != workspace_id):
                return None
            return self._data(row)
        finally:
            session.close()

    def _action_update(self, mission_id: str, status: str, *, observation: str) -> None:
        session = self._sessions()
        try:
            row = session.scalar(select(MissionExecutionCheckpoint).where(MissionExecutionCheckpoint.mission_id == mission_id))
            if row:
                row.action_status = status; row.last_observation_summary = self._summary(observation)
                session.commit()
        finally:
            session.close()

    def _row(self, session, mission_id: str, workspace_id: str, mission: dict[str, object]) -> MissionExecutionCheckpoint:
        row = session.scalar(select(MissionExecutionCheckpoint).where(MissionExecutionCheckpoint.mission_id == mission_id))
        if row is None:
            row = MissionExecutionCheckpoint(mission_id=mission_id, workspace_id=workspace_id, goal_summary=self._summary(mission.get("goal") or mission.get("title")))
            session.add(row); session.flush()
        if row.workspace_id != workspace_id:
            raise PermissionError("Mission checkpoint is not available in this Workspace.")
        return row

    @staticmethod
    def _summary(value: object, length: int = 500) -> str:
        return " ".join(str(value or "").split())[:length]

    @staticmethod
    def _decode(value: str) -> list[str]:
        try:
            decoded = json.loads(value)
            return [str(item) for item in decoded] if isinstance(decoded, list) else []
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _data(self, row: MissionExecutionCheckpoint) -> dict[str, object]:
        return {"phase": row.phase, "goal_summary": row.goal_summary, "current_objective": row.current_objective, "next_action": row.next_action, "completed_steps": self._decode(row.completed_steps_summary), "max_total_steps": self.MAX_TOTAL_STEPS, "last_observation": row.last_observation_summary, "last_evaluation": row.last_evaluation_summary, "action_status": row.action_status, "retry_count": row.retry_count, "recovery_count": row.recovery_count, "waiting_reason": row.waiting_reason, "resume_policy": row.resume_policy, "updated_at": row.updated_at}
