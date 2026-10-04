"""Team collaboration projections over the existing Workspace and Mission model."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, select

from app.models.ai_mission import AIMission, AIMissionEvent
from app.models.approval import ApprovalRequest
from app.models.artifact import Artifact
from app.models.governance import WorkspaceUserRole
from app.models.identity import User
from app.models.mission_collaboration import MissionParticipant, MissionReviewComment
from app.services.audit_service import AuditService
from app.services.database import SessionLocal, initialize_database


class MissionCollaborationError(ValueError):
    pass


class MissionCollaborationService:
    """Allows only Workspace members to collaborate on a Mission."""

    _ROLE_LABELS = {
        "OWNER": "Owner", "ADMIN": "Workspace administrator", "MANAGER": "Research lead",
        "MEMBER": "Researcher", "REVIEWER": "Reviewer", "VIEWER": "Viewer",
    }

    def __init__(self, sessions: Callable = SessionLocal, *, initialize: bool = True, audit=None):
        if initialize:
            initialize_database()
        self._sessions = sessions
        self._audit = audit or AuditService(sessions, initialize=False)

    def members(self, workspace_id: str) -> list[dict[str, object]]:
        session = self._sessions()
        try:
            rows = session.scalars(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == workspace_id).order_by(WorkspaceUserRole.created_at)).all()
            return [self._member(session, row) for row in rows]
        finally:
            session.close()

    def assign(self, workspace_id: str, mission_id: str, user_id: str, responsibility: str, *, actor_id: str) -> dict[str, object]:
        clean = " ".join(str(responsibility or "").split())[:240] or "Mission collaborator"
        session = self._sessions()
        try:
            self._mission(session, mission_id, workspace_id)
            membership = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == workspace_id, WorkspaceUserRole.user_id == user_id))
            if membership is None or session.get(User, user_id) is None:
                raise MissionCollaborationError("Only an existing Workspace member can be assigned to this Mission.")
            row = session.scalar(select(MissionParticipant).where(MissionParticipant.mission_id == mission_id, MissionParticipant.user_id == user_id))
            if row is None:
                row = MissionParticipant(mission_id=mission_id, workspace_id=workspace_id, user_id=user_id, responsibility=clean, assigned_by=actor_id)
                session.add(row)
            else:
                row.responsibility = clean; row.assigned_by = actor_id
            session.commit(); session.refresh(row)
            result = self._participant(session, row)
        finally:
            session.close()
        self._audit.record_event(workspace_id, actor_id, "MISSION_PARTICIPANT_ASSIGNED", "Mission", mission_id, mission_id, "A Workspace member was assigned a Mission responsibility.")
        return result

    def comment(self, workspace_id: str, mission_id: str, user_id: str, comment: str, *, target_type: str = "MISSION", target_id: str = "", status: str = "COMMENTED") -> dict[str, object]:
        clean = " ".join(str(comment or "").split())
        if not clean or len(clean) > 2000:
            raise MissionCollaborationError("A collaboration comment must contain 1–2000 characters.")
        session = self._sessions()
        try:
            self._mission(session, mission_id, workspace_id)
            membership = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == workspace_id, WorkspaceUserRole.user_id == user_id))
            if membership is None:
                raise MissionCollaborationError("Only a Workspace member can comment on this Mission.")
            row = MissionReviewComment(mission_id=mission_id, workspace_id=workspace_id, user_id=user_id, target_type=str(target_type or "MISSION")[:40], target_id=str(target_id or "")[:36], status=str(status or "COMMENTED")[:40], comment=clean)
            session.add(row); session.commit(); session.refresh(row)
            result = self._comment(session, row)
        finally:
            session.close()
        self._audit.record_event(workspace_id, user_id, "MISSION_COMMENTED", "Mission", mission_id, mission_id, "A Workspace member added a reviewable Mission comment.")
        return result

    def mission(self, workspace_id: str, mission_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            self._mission(session, mission_id, workspace_id)
            participants = [self._participant(session, row) for row in session.scalars(select(MissionParticipant).where(MissionParticipant.mission_id == mission_id, MissionParticipant.workspace_id == workspace_id).order_by(MissionParticipant.created_at)).all()]
            comments = [self._comment(session, row) for row in session.scalars(select(MissionReviewComment).where(MissionReviewComment.mission_id == mission_id, MissionReviewComment.workspace_id == workspace_id).order_by(MissionReviewComment.created_at)).all()]
            events = [self._ai_event(item) for item in session.scalars(select(AIMissionEvent).where(AIMissionEvent.mission_id == mission_id).order_by(AIMissionEvent.created_at)).all()]
            return {"mission_id": mission_id, "participants": participants, "comments": comments, "activity": sorted([*events, *[self._human_event(item) for item in comments]], key=lambda item: str(item["created_at"]))[-30:], "boundary": "Collaboration includes only this Workspace’s persisted Mission events and member comments. Prompts, reasoning traces, credentials and raw source bodies are excluded."}
        finally:
            session.close()

    def dashboard(self, workspace_id: str) -> dict[str, object]:
        session = self._sessions()
        try:
            missions = list(session.scalars(select(AIMission).where(AIMission.workspace_id == workspace_id)).all())
            ids = [mission.id for mission in missions]
            artifacts = list(session.scalars(select(Artifact).where(Artifact.mission_id.in_(ids))).all()) if ids else []
            pending = int(session.scalar(select(func.count(ApprovalRequest.id)).where(ApprovalRequest.workspace_id == workspace_id, ApprovalRequest.status == "PENDING")) or 0)
            evidence = sum(len(self._refs(mission.evidence_refs_json)) for mission in missions)
            return {"members": self.members(workspace_id), "active_missions": sum(mission.status not in {"COMPLETED", "FAILED", "REJECTED"} for mission in missions), "pending_reviews": pending, "artifacts": len(artifacts), "traceable_evidence_refs": evidence, "boundary": "Dashboard totals are derived from the current Workspace only and do not infer research outcomes."}
        finally:
            session.close()

    def _mission(self, session, mission_id: str, workspace_id: str) -> AIMission:
        mission = session.get(AIMission, mission_id)
        if mission is None or mission.workspace_id != workspace_id:
            raise MissionCollaborationError("Mission is not available in this Workspace.")
        return mission

    def _member(self, session, row: WorkspaceUserRole) -> dict[str, object]:
        user = session.get(User, row.user_id)
        return {"user_id": row.user_id, "display_name": user.display_name if user else "Workspace member", "role": row.role, "role_label": self._ROLE_LABELS.get(row.role, "Workspace member"), "can_view": True, "can_edit": row.role in {"OWNER", "ADMIN", "MANAGER", "MEMBER"}, "can_review": row.role in {"OWNER", "ADMIN", "MANAGER", "REVIEWER"}, "can_manage": row.role in {"OWNER", "ADMIN"}}

    def _participant(self, session, row: MissionParticipant) -> dict[str, object]:
        membership = session.scalar(select(WorkspaceUserRole).where(WorkspaceUserRole.workspace_id == row.workspace_id, WorkspaceUserRole.user_id == row.user_id))
        user = session.get(User, row.user_id)
        return {"id": row.id, "user_id": row.user_id, "display_name": user.display_name if user else "Workspace member", "role": membership.role if membership else "VIEWER", "responsibility": row.responsibility, "assigned_by": row.assigned_by, "created_at": row.created_at}

    def _comment(self, session, row: MissionReviewComment) -> dict[str, object]:
        user = session.get(User, row.user_id)
        return {"id": row.id, "user_id": row.user_id, "display_name": user.display_name if user else "Workspace member", "target_type": row.target_type, "target_id": row.target_id, "status": row.status, "comment": row.comment, "created_at": row.created_at}

    @staticmethod
    def _ai_event(row: AIMissionEvent) -> dict[str, object]:
        return {"actor": "AI Worker", "kind": "AI_ACTIVITY", "action": row.action[:180], "summary": row.result_summary[:500], "created_at": row.created_at}

    @staticmethod
    def _human_event(comment: dict[str, object]) -> dict[str, object]:
        return {"actor": comment["display_name"], "kind": "TEAM_COMMENT", "action": "Added review feedback", "summary": str(comment["comment"])[:500], "created_at": comment["created_at"]}

    @staticmethod
    def _refs(value: str) -> list[object]:
        import json
        try:
            parsed = json.loads(value or "[]")
            return parsed if isinstance(parsed, list) else []
        except ValueError:
            return []
