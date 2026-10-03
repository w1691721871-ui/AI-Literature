"""FastAPI dependencies that resolve identity before authorization decisions."""

from __future__ import annotations

from fastapi import Header, HTTPException, status
from sqlalchemy import select

from app.models.ai_mission import AIMission
from app.models.artifact import Artifact
from app.models.computer_mission import ComputerMission
from app.models.connector import Connector
from app.models.enterprise_memory import KnowledgeAsset
from app.models.governance import GovernanceWorkspace
from app.services.database import SessionLocal
from app.services.governance_service import GovernanceError, PermissionService
from app.services.identity_service import IdentityContext, IdentityError, IdentityService


class PermissionMiddleware:
    """Dependency-style enforcement; it never trusts user/workspace request fields."""

    def __init__(self, identities=None, permissions=None, sessions=SessionLocal):
        self.identities = identities or IdentityService(sessions, initialize=False)
        self.permissions = permissions or PermissionService(sessions, initialize=False)
        self._sessions = sessions

    def current(self, authorization: str | None = Header(default=None)) -> IdentityContext:
        token = ""
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        try:
            return self.identities.context_for_token(token)
        except IdentityError as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace authentication required.") from error

    def require(self, context: IdentityContext, permission: str) -> None:
        try:
            self.permissions.check(context.workspace_id, context.user_id, permission)
        except GovernanceError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace permission denied.") from error

    def admin_console(self, context: IdentityContext) -> None:
        """Protect governance APIs independently of frontend navigation."""
        session = self._sessions()
        try:
            workspace = session.get(GovernanceWorkspace, context.workspace_id)
            is_demo = bool(workspace and workspace.name == IdentityService.demo_workspace_name)
        finally:
            session.close()
        if is_demo or context.role not in {"OWNER", "ADMIN"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workspace administration is not available for this session.",
            )

    def mission(self, context: IdentityContext, mission_id: str, permission: str) -> None:
        self._resource_workspace(context, AIMission, mission_id, permission)

    def artifact(self, context: IdentityContext, artifact_id: str, permission: str) -> None:
        session = self._sessions()
        try:
            artifact = session.get(Artifact, artifact_id)
            mission = session.get(AIMission, artifact.mission_id) if artifact else None
            self._assert_workspace(context, mission.workspace_id if mission else None, permission)
        finally:
            session.close()

    def computer(self, context: IdentityContext, computer_id: str, permission: str) -> None:
        session = self._sessions()
        try:
            computer = session.get(ComputerMission, computer_id)
            mission = session.get(AIMission, computer.mission_id) if computer and computer.mission_id else None
            self._assert_workspace(context, mission.workspace_id if mission else None, permission)
        finally:
            session.close()

    def connector(self, context: IdentityContext, connector_id: str, permission: str = "CONNECTOR_ACCESS") -> None:
        self._resource_workspace(context, Connector, connector_id, permission)

    def knowledge(self, context: IdentityContext, asset_id: str, permission: str) -> None:
        self._resource_workspace(context, KnowledgeAsset, asset_id, permission)

    def _resource_workspace(self, context, model, resource_id, permission):
        session = self._sessions()
        try:
            row = session.get(model, resource_id)
            self._assert_workspace(context, getattr(row, "workspace_id", None) if row else None, permission)
        finally:
            session.close()

    def _assert_workspace(self, context, workspace_id, permission):
        if not workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resource is not assigned to an authorized Workspace.")
        if workspace_id != context.workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-workspace access denied.")
        self.require(context, permission)
