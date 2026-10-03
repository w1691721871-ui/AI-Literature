"""Finite pause, resume and recovery controls over the existing Mission service."""

from __future__ import annotations

from sqlalchemy import select

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.mission_control import MissionControlState
from app.services.database import SessionLocal, initialize_database


class MissionLifecycleError(ValueError):
    pass


class MissionLifecycleService:
    """Adds human-controlled continuity without changing AI Worker execution."""

    MAX_RECOVERIES = 2
    _TERMINAL = {"COMPLETED", "REJECTED"}

    def __init__(self, sessions=SessionLocal, *, initialize=True):
        if initialize:
            initialize_database()
        self._sessions = sessions

    def pause(self, mission_id: str, workspace_id: str, user_id: str, reason: str = "") -> dict[str, object]:
        session = self._sessions()
        try:
            mission = self._mission(session, mission_id, workspace_id)
            if mission.status in self._TERMINAL or mission.status == "PAUSED":
                raise MissionLifecycleError("Mission cannot be paused in its current state.")
            control = self._control(session, mission)
            control.prior_status = mission.status
            control.paused_by_id = user_id
            control.pause_reason = reason.strip()[:500]
            mission.status = "PAUSED"; mission.current_step = "Paused by Workspace member"
            self._event(session, mission, "Paused", "PAUSED", "Mission is paused. No Skill will execute until an authorized member resumes it.")
            session.commit(); session.refresh(control)
            return self._data(mission, control)
        finally:
            session.close()

    def resume(self, mission_id: str, workspace_id: str, user_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = self._mission(session, mission_id, workspace_id)
            control = self._control(session, mission)
            if mission.status != "PAUSED":
                raise MissionLifecycleError("Mission is not paused.")
            restored = control.prior_status if control.prior_status not in self._TERMINAL | {"PAUSED", "FAILED"} else "PLANNING"
            mission.status = restored; mission.current_step = "Ready to continue"
            self._event(session, mission, "Resumed", restored, "Mission was resumed within its existing review and execution boundaries.")
            session.commit(); session.refresh(control)
            return self._data(mission, control)
        finally:
            session.close()

    def recover(self, mission_id: str, workspace_id: str, user_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = self._mission(session, mission_id, workspace_id)
            control = self._control(session, mission)
            if mission.status != "FAILED":
                raise MissionLifecycleError("Only a failed Mission can enter controlled recovery.")
            if control.recovery_count >= min(control.max_recoveries, self.MAX_RECOVERIES):
                raise MissionLifecycleError("Mission recovery limit reached; human review is required.")
            control.recovery_count += 1
            mission.status = "NEEDS_REVISION"; mission.current_step = "Recovery plan ready for human review"
            self._event(session, mission, "Recovery", "NEEDS_REVISION", "A bounded recovery plan was prepared. Human confirmation is required before work continues.")
            session.commit(); session.refresh(control)
            return self._data(mission, control)
        finally:
            session.close()

    def snapshot(self, mission_id: str, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            mission = self._mission(session, mission_id, workspace_id)
            return self._data(mission, self._control(session, mission))
        finally:
            session.close()

    def _mission(self, session, mission_id: str, workspace_id: str) -> AIMission:
        mission = session.get(AIMission, mission_id)
        if mission is None or mission.workspace_id != workspace_id:
            raise PermissionError("Mission is not available in this Workspace.")
        return mission

    def _control(self, session, mission: AIMission) -> MissionControlState:
        row = session.scalar(select(MissionControlState).where(MissionControlState.mission_id == mission.id))
        if row is None:
            row = MissionControlState(mission_id=mission.id, workspace_id=mission.workspace_id, prior_status=mission.status)
            session.add(row); session.flush()
        if row.workspace_id != mission.workspace_id:
            raise PermissionError("Mission control state is not available in this Workspace.")
        return row

    @staticmethod
    def _event(session, mission: AIMission, action: str, status: str, summary: str) -> None:
        session.add(AIMissionEvent(mission_id=mission.id, stage="Mission Control", action=action, status=status, evidence_count=0, result_summary=summary))

    @staticmethod
    def _data(mission: AIMission, control: MissionControlState) -> dict[str, object]:
        return {"mission_id": mission.id, "workspace_id": mission.workspace_id, "status": mission.status, "current_step": mission.current_step, "recovery_count": control.recovery_count, "max_recoveries": min(control.max_recoveries, MissionLifecycleService.MAX_RECOVERIES), "pause_reason": control.pause_reason if mission.status == "PAUSED" else "", "next_action": "Resume Mission" if mission.status == "PAUSED" else "Request human revision" if mission.status == "NEEDS_REVISION" else "Continue within existing controls"}
